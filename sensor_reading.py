"""
Models and database for sensor readings
"""

from sqlmodel import Field, Session, SQLModel, create_engine, select, DateTime, Enum, Column
from pydantic import BaseModel
from datetime import datetime, timezone
import time
import enum


class SampleMethod(enum.Enum):
    """how the reading came about - either raw from a sensor or an average or other selection from raw
    readings"""

    raw = 0  # a reading straight from  a sensor
    max_ = 1  # the maximum reading from a set of raw readings in a particular bucket
    min_ = 2  # the minimum reading from a set of raw readings in a particular bucket

    avg = 3  # the average reading in a particular time bucket


allowed_units = set(["C", "%", "lux", "kPa", "bool"])


class SensorReadingPayload(BaseModel):
    """
    A reading from a sensor such as a temperature or pressure sensor.
    It's assumed to have a simgle numeric value. This is a payload
    in an incoming JSON message from a sensor.
    """

    sensor: str
    unit: str
    value: float
    recorded_timestamp: int


class SensorReading(SQLModel, table=True):
    """
    A reading from  a sensor as stored in the database.

    """

    sensor: str = Field(index=True, default=None, primary_key=True)
    unit: str = Field(default=None)
    value: float = Field(default=None)
    method: str = Field(sa_column=Column(Enum(SampleMethod)),default=SampleMethod.raw)

    recorded_timestamp: int = Field(default=None, primary_key=True)
    received_timestamp: int = Field(default=None)

    @classmethod
    def from_payload(cls, sp: SensorReadingPayload):
        received = int(time.time())
        return cls(
            sensor=sp.sensor,
            unit=sp.unit,
            value=sp.value,
            recorded_timestamp=sp.recorded_timestamp,
            received_timestamp=received,
        )

    def assert_matching_type(self, unit: str, sensor: str):
        if unit != self.unit:
            raise ValueError(f"mismatched units units: {unit} <> {self.unit}")
        if sensor != self.sensor:
            raise ValueError(f"mismatched sensor {sensor} <> {self.sensor}")

    @classmethod
    def fetch(
        cls,
        session: Session,
        start_timestamp: int = None,
        period: int = 600,
        limit=1000,
        units: set[str] = set(["C"]),
        sensors: set = None,
    ) -> list['SensorReading']:
        if start_timestamp is None:
            start_timestamp = int(time.time()) - period

        invalid_units = units.difference(allowed_units)
        if len(invalid_units) > 0:
            raise ValueError("invalid units supplied" + invalid_units)

        sel = select(SensorReading)
        if sensors is not None:
            sel = sel.where(SensorReading.sensor.in_(sensors))

        sel = sel.where(SensorReading.received_timestamp > start_timestamp)
        sel = sel.where(SensorReading.received_timestamp <= start_timestamp + period)
        sel = sel.where(SensorReading.unit.in_(units))
        sel = sel.order_by(SensorReading.received_timestamp)
        sel = sel.limit(limit)

        alldata = session.scalars(sel).all()

        return alldata


class Sampler:
    registry = {}

    def __init__(self):
        pass

    def add(self, value: float):
        pass

    def sample(self) -> float:
        return 0.0

    @staticmethod
    def factory(method: SampleMethod):
        return Sampler.registry[method]()


class Average(Sampler):
    method = SampleMethod.avg

    def __init__(self):
        self.total = 0.0
        self.count = 0

    def add(self, value: float):
        self.total += value
        self.count += 1

    def sample(self) -> float:
        if self.count <= 0:
            raise ValueError("nothing to average")
        return self.total / self.count


Sampler.registry[Average.method] = Average


class Minimum(Sampler):
    method = SampleMethod.min_

    def __init__(self):
        self.minimum = None

    def add(self, value: float):
        if self.minimum is None or value < self.minimum:
            self.minimum = value

    def sample(self) -> float:
        return self.minimum


Sampler.registry[Minimum.method] = Minimum


class Maximum(Sampler):
    method = SampleMethod.max_

    def __init__(self):
        self.maximum = None  # practical minimum

    def add(self, value: float):
        if self.maximum is None or value > self.maximum:
            self.maximum = value

    def sample(self) -> float:
        return self.maximum


Sampler.registry[Maximum.method] = Maximum


class SampleBucket:
    """
    The sample bucket holds samplers (like an Average or Minimum
    or Maximum sampler) that summarise a particular range of times
    starting at "timestamp" and return some kind of sample value
    when all the data for that bucket has been added to it.
    """

    def __init__(self, timestamp, methods: set[SampleMethod]):
        self.timestamp = timestamp
        self.sample_count = 0

        self.sensor_units = {}
        self.methods = methods

    def add(self, r: SensorReading):
        if r.recorded_timestamp < self.timestamp:
            raise ValueError(
                f"adding values from outside the bucket  {r.recorded_timestamp} to sample bucket for {self.sensor}"
            )
        su = f"{r.sensor}_{r.unit}"

        if su not in self.sensor_units:
            samplers = []
            for m in self.methods:
                samplers.append(Sampler.factory(m))
            self.sensor_units[su] = samplers

        for s in self.sensor_units[su]:
            s.add(r.value)

        self.sample_count += 1

    def samples(self) -> int, dict[str, float]:
        """Returns the bucket's timestamp and a dictionary with all samples.
           samples are named with <sensorname>_<unitname>_<samplemethod>
           """
        if self.sample_count == 0:
            return None

        samples = {}
        for su, samplers in self.sensor_units.items():
            for s in samplers:
                try:
                    key = su+s.method  # e.g. sensor1_C_avg or sensor2_kpa_max
                    samples[key] = s.sample()
                except ValueError as e:
                    pass  # Average of an empty bucket for example - just don't record any value
        return self.timestamp, samples


class SensorSummary:
    def __init__(self, start_timestamp: int, end_timestamp: int, bucket_count: int):
        self.buckets = []
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        time_range = end_timestamp - start_timestamp
        self.bucket_size = time_range / bucket_count

        for i in range(0, bucket_count):
            timestamp = start_timestamp + i * self.bucket_size
            b = SampleBucket(timestamp, sensor, unit, methods)
            self.buckets.append(b)

    def add_reading(self, r: SensorReading):
        float_slot = (r.recorded_timestamp - self.start_timestamp) / self.bucket_size
        slot = int(float_slot)
        if  slot >= self.bucket_count:
            # The last data item will likely want to fit in an outer bucket. Shove it in the last.
            #print(f"overfill {slot=} {bucket_count=} {r.recorded_timestamp=} {r.value=} {bucket_size=} {float_slot=} {time_range=}")
            slot = self.bucket_count - 1
        self.buckets[slot].add(r)

    @classmethod
    def downsample(cls,
        data: list[SensorReading], methods: set[SampleMethod], bucket_count: int
    ) -> list[SensorReading]:
        """
        Creates a number of buckets, "puts" the data into them and then
        samples the data to return a list of sensor readings.
        The input data is assumed to be ordered by increasing timestamps

        returns a dictionary with the sample method as a key and the set
        of samples for that method. e.g.
        { "unit": "C", "data": [
          { "avg" : 14.0, "min_": 12.0, "timestamp": 123 },
          { "avg" : 15.0, "min_": 13.0, "timestamp": 124 },
          { "avg" : 16.0, "min_": 15.0, "timestamp": 125 },
          { "avg" :  6.0, "min_":  5.0, "timestamp": 123 },
          { "avg" :  5.0, "min_":  1.0, "timestamp": 124 },
          { "avg" :  6.0, "min_":  4.0, "timestamp": 125 }
          ]
        }

        """
        bucket_chain = cls( start_timestamp=data[0].recorded_timestamp,
                            end_timestamp=data[-1].recorded_timestamp,
                            bucket_count=bucket_count)

        sensor = data[0].sensor
        unit = data[0].unit

        # pop each element of the raw data into the appropriate bucket.
        for r in data:
            bucket_chain.add_reading(r)

        data = []
        for b in self.bucket_chain:
            timestamp, bucket_samples = b.samples()
            if len(bucket_samples) == 0:
                continue
            bucket_samples["_timestamp"] = timestamp
            data.append(bucket_samples)
        return data

    @classmethod
    def sample(
        cls,
        session: Session,
        start_timestamp: int = None,
        period: int = 600,
        limit=1000,
        units: set[str] = set(["C"]),
        sample_methods: set[str] = set(["avg"]),
        sensors: set = None,
        sample_buckets=None,
        sample_type=None,
    ) -> 'SensorSummary':

        alldata = SensorReading.fetch(
                session, start_timestamp, period, limit, units, sensors)

        summary = cls(start_timestamp, start_timestamp + period, sample_methods, bucket_count)

        downsampled_data = self.downsample(alldata, methods)
        return alldata
