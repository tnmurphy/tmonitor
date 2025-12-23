"""
Models and database for sensor readings
"""

from sqlmodel import (
    Field,
    Session,
    SQLModel,
    create_engine,
    select,
    DateTime,
    Enum,
    Column,
)
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
import time
from enum import Enum


allowed_units = set(["C", "%", "lux", "kPa", "bool"])

class SampleMethod:
    pass


class Sampler:
    """Abstract base class for samplers which have values added to them and return some sort
       of summary of those values such as an average or maximum.
    """
    registry = {}

    def __init__(self):
        pass

    def add(self, value: float):
        pass

    def sample(self) -> float:
        return 0.0

    @staticmethod
    def factory(method: SampleMethod):
        return Sampler.registry[method.value]()


class Average(Sampler):
    """ Keep a total and count of all values added and return the average when sampled """
    method_name = "AVG"
    method_value = "avg"

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


Sampler.registry[Average.method_value] = Average


class Minimum(Sampler):
    """Retain the smallest value added and return that as the sample """
    method_name = "MIN_"
    method_value = "min"

    def __init__(self):
        self.minimum = None

    def add(self, value: float):
        if self.minimum is None or value < self.minimum:
            self.minimum = value

    def sample(self) -> float:
        return self.minimum


Sampler.registry[Minimum.method_value] = Minimum


class Maximum(Sampler):
    """Retain the largest value added and return that as the sample """
    method_name = "MAX_"
    method_value = "max"

    def __init__(self):
        self.maximum = None  # practical minimum

    def add(self, value: float):
        if self.maximum is None or value > self.maximum:
            self.maximum = value

    def sample(self) -> float:
        return self.maximum

Sampler.registry[Maximum.method_value] = Maximum

class Raw(Sampler):
    """ Just pick the first data item seen"""
    method_name = "RAW"
    method_value = "raw"

    def __init__(self):
        self.chosen = None  # practical minimum

    def add(self, value: float):
        if self.chosen is None:
            self.chosen = value

    def sample(self) -> float:
        return self.chosen


Sampler.registry[Raw.method_value] = Raw

# Build up the enum from the classes that were declared
samps = [(v.method_name,k) for k,v in Sampler.registry.items()]
SampleMethod = Enum('SampleMethod', samps)
def sample_method_from_str(s: str) -> set[SampleMethod]:
    strmethods = [u.strip() for u in s.split(",")]
    methods = { SampleMethod(m) for m in strmethods }
    return methods

SampleMethod.from_str = sample_method_from_str



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

    @field_validator('unit')
    @classmethod
    def unit_must_be_in_allowed(cls, u: str):
        if not u in allowed_units:
            raise ValueError(f"unknown unit: {u}")
        return u


class SensorReading(SQLModel, table=True):
    """
    A reading from  a sensor as stored in the database.
    """

    sensor: str = Field(index=True, default=None, primary_key=True)
    unit: str = Field(default=None, primary_key=True)
    value: float = Field(default=None)

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
    def sensorlist(
        cls,
        session: Session,
    ) -> list[str]:
        sel = select(SensorReading.sensor).distinct()
        alldata = session.scalars(sel).all()
        return alldata

    @classmethod
    def fetch(
        cls,
        session: Session,
        start_timestamp: int = None,
        period: int = 600,
        limit=1000,
        units: set[str] = set(["C"]),
        sensors: set[str] | None = None,
    ) -> list["SensorReading"]:
        if start_timestamp is None:
            start_timestamp = int(time.time()) - period

        invalid_units = units.difference(allowed_units)
        if len(invalid_units) > 0:
            raise ValueError("invalid units supplied" + invalid_units)

        sel = select(SensorReading)
        if sensors is not None:
            sel = sel.where(SensorReading.sensor.in_(sensors))

        end_timestamp = start_timestamp + period

        sel = sel.where(SensorReading.received_timestamp > start_timestamp)
        sel = sel.where(SensorReading.received_timestamp <= end_timestamp)
        sel = sel.where(SensorReading.unit.in_(units))
        sel = sel.order_by(SensorReading.received_timestamp)
        sel = sel.limit(limit)

        alldata = session.scalars(sel).all()

        return alldata


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
                f"adding values from outside the bucket  {r.recorded_timestamp} to sample bucket "
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

    def samples(self) -> tuple[int, dict[str, float]]:
        """Returns the bucket's timestamp and a dictionary with all samples.
        samples are named with <sensorname>_<unitname>_<samplemethod>
        """
        if self.sample_count == 0:
            return self.timestamp, {}

        samples = {}
        for su, samplers in self.sensor_units.items():
            for s in samplers:
                try:
                    key = (
                        su + "_" + s.method_value
                    )  # e.g. sensor1_C_avg or sensor2_kpa_max
                    samples[key] = s.sample()
                except ValueError as e:
                    pass  # Average of an empty bucket for example - just don't record any value
        return self.timestamp, samples


class BucketChain:
    """ A string of buckets that are adjacent in time from first to next """
    def __init__(
        self,
        start_timestamp: int,
        end_timestamp: int,
        bucket_count: int,
        methods: set[SampleMethod],
    ):
        self.buckets = []
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        time_range = end_timestamp - start_timestamp
        self.bucket_size = time_range / bucket_count
        self.bucket_count = bucket_count
        self.sample_count = 0

        for i in range(0, bucket_count):
            timestamp = int(start_timestamp + i * self.bucket_size)
            b = SampleBucket(timestamp, methods)
            self.buckets.append(b)

    def add_reading(self, r: SensorReading):
        float_slot = (r.recorded_timestamp - self.start_timestamp) / self.bucket_size
        slot = int(float_slot)
        if slot >= self.bucket_count:
            # The last data item will likely want to fit in an outer bucket. Shove it in the last.
            # print(f"overfill {slot=} {bucket_count=} {r.recorded_timestamp=} {r.value=} {bucket_size=} {float_slot=} {time_range=}")
            slot = self.bucket_count - 1
        self.buckets[slot].add(r)
        self.sample_count += 1

    @classmethod
    def downsample(
        cls, data: list[SensorReading], bucket_count: int, sample_methods: set[SampleMethod]
    ) -> list[dict[str, float]]:
        """
        Creates a number of buckets which cover the time period of
        the data from the first to last reading and "puts" the data
        into them.  Then samples the data to return a list of samples.
        The input data is assumed to be ordered by increasing timestamps

        The format of this list is driven by how a popular graphing UI
        component works. To accomodate multiple sensors, types of sensor
        and sampling methods we create a list in which each item contains
        all the values that relate to a particular time.

        To distinquish each value they're named with their sensor,
        unit and sampling method.
        e.g.
        [
          { "sensor1_C_avg" : 14.0, "sensor1_C_min_": 12.0, "timestamp": 123 },
          { "sensor1_C_avg" : 15.0, "sensor1_C_min_": 13.0, "timestamp": 124 },
        ]

        With 2 sensors both recording averages this would be:
        [
          { "sensor1_C_avg" : 14.0, "sensor2_C_avg": 12.0, "timestamp": 123 },
          { "sensor1_C_avg" : 15.0, "sensor2_C_min_": 13.0, "timestamp": 124 },
        ]

        """
        if len(data) < 1:
            return []

        try:
            start_timestamp = data[0].recorded_timestamp
            # +1 ensures we have a range that's >0 and the 
            # last item will awlays be put in the last bucket
            end_timestamp = data[-1].recorded_timestamp+1
        except IndexError:
            return []

        bucket_chain = cls(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            bucket_count=bucket_count,
            methods=sample_methods,
        )

        # pop each element of the raw data into the appropriate bucket.
        for r in data:
            bucket_chain.add_reading(r)

        downsampled_data = []
        for b in bucket_chain.buckets:
            timestamp, bucket_samples = b.samples()
            if bucket_samples is None or len(bucket_samples) == 0:
                continue
            bucket_samples["timestamp"] = timestamp
            downsampled_data.append(bucket_samples)
        return downsampled_data


class SensorSummary(BaseModel):
    downsampled_data: list[dict]

    @classmethod
    def sample(
        cls,
        session: Session,
        start_timestamp: int | None = None,
        period: int = 600,
        limit=1000,
        sensors: set[str] | None = None,
        units: set[str] = set(["C"]),
        sample_methods: set[SampleMethod] = set([SampleMethod.AVG]),
        sample_buckets=10,
    ) -> "SensorSummary":
        if start_timestamp is None:
            start_timestamp = int(datetime.now().timestamp())

        alldata = SensorReading.fetch(
            session, start_timestamp, period, limit, units, sensors
        )

        summary = cls(
            downsampled_data=BucketChain.downsample(
                alldata, sample_buckets, sample_methods
            )
        )
        return summary
