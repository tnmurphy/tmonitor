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
            raise ValueError(f"mismatched sensor {r.sensor} <> {self.sensor}")


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

    def __init__(self, timestamp, sensor, unit, methods: set[SampleMethod]):
        self.sensor = sensor
        self.unit = unit
        self.timestamp = timestamp

        self.samplers = []
        for m in methods:
            self.samplers.append(Sampler.factory(m))

    def add(self, r: SensorReading):
        if r.recorded_timestamp < self.timestamp:
            raise ValueError(
                f"adding values from outside the bucket  {r.recorded_timestamp} to sample bucket for {self.sensor}"
            )
        for s in self.samplers:
            s.add(r.value)

    def samples(self):
        samples_ = {}
        for s in self.samplers:
            try:
                samples_[s.method] = SensorReading(
                    sensor=self.sensor, unit=self.unit, value=s.sample()
                )
            except ValueError as e:
               pass # Average of an empty bucket for example - just don't record any value
        return samples_

    @staticmethod
    def downsample(
        data: list[SensorReading], methods: set[SampleMethod], bucket_count: int
    ) -> list[SensorReading]:
        """
        Creates a number of buckets, "puts" the data into them and then
        samples the data to return a list of sensor readings.
        The input data is assumed to be ordered by increasing timestamps

        returns a dictionary with the sample method as a key and the set
        of samples for that method. e.g.
        {
          "avg" : [ 12.0, 13.0, 15.0 ],
          "min_": [  5.0, 10.0, 8.5  ]
        }

        """
        buckets = []
        start_timestamp = data[0].recorded_timestamp
        end_timestamp = data[-1].recorded_timestamp
        time_range = end_timestamp - start_timestamp
        bucket_size = time_range / bucket_count

        sensor = data[0].sensor
        unit = data[0].unit

        # create the buckets
        for i in range(0, bucket_count):
            timestamp = start_timestamp + i * bucket_size
            b = SampleBucket(timestamp, sensor, unit, methods)
            buckets.append(b)

        # pop each element of the raw data into the appropriate bucket.
        for r in data:
            float_slot = (r.recorded_timestamp - start_timestamp) / bucket_size
            slot = int(float_slot)
            if  slot >= bucket_count:
                # The last data item will likely want to fit in an outer bucket. Shove it in the last.
                #print(f"overfill {slot=} {bucket_count=} {r.recorded_timestamp=} {r.value=} {bucket_size=} {float_slot=} {time_range=}")
                slot = bucket_count-1
            buckets[slot].add(r)

        downsampled_series = {m: [] for m in methods}
        for b in buckets:
            bucket_samples = b.samples()
            for method_, reading in bucket_samples.items():
                downsampled_series[method_].append(reading)

        return downsampled_series


class SensorSummary(BaseModel):
    """
    This is what is returned to a client for tmonitor, such as a web
    app or phone app  - it contains several lists of data organised
    by sensor, reading type and downsampling method.
    """

    readings_by_sensor: dict[str, dict[str, SensorReading]]

    @classmethod
    def organise_readings(cls, alldata: list[SensorReading], units: set[str]):
        """The input is a result from a database query which may be readings of multiple
        sensors or sensor types. separate data by sensor then unit type so that it's easy
        for it to be displayed on a different axis."""

        instance = cls(readings_by_sensor={})

        for d in alldata:
            if d.sensor not in instance.readings_by_sensor:
                instance.readings_by_sensor[d.sensor] = {
                    u: {SampleMethod.raw: []} for u in units
                }
            readings_by_unit = instance.readings_by_sensor[d.sensor]
            readings_by_unit[d.unit][SampleMethod.raw].append(d)

        return instance

    def downsample(self, methods: set[SampleMethod], bucket_count: int):
        new_readings = {}
        for sensorname, units in self.readings_by_sensor.items():
            new_readings[sensorname] = {}
            new_units = {}
            for unit, data in units.items():
                sampled_data = downsample(data[SampleMethod.raw], methods, bucket_count)
                new_units[unit] = sampled_data

    @classmethod
    def fetch(
        cls,
        session: Session,
        start_timestamp: int = None,
        period: int = 600,
        limit=1000,
        units: set[str] = set(["C"]),
        sensors: set = None,
        sample_buckets=None,
        sample_type=None,
    ) -> 'SensorSummary':
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

        # if sample_type is None or raw:  What's left out is samples like min-max, average, random etc.
        
        sampled_summary = cls.organise_readings(alldata, units)
        print(sampled_summary)
        return sampled_summary
