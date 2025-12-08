"""
Models and database for sensor readings
"""

from sqlmodel import Field, Session, SQLModel, create_engine, select, DateTime, Enum
from pydantic import BaseModel
from datetime import datetime, timezone
import time
import enum


class ReadingMethod(enum.Enum):
    """ how the reading came about - either raw from a sensor or an average or other selection from raw
        readings """
    raw = 0   # a reading straight from  a sensor
    max_ = 1  # the maximum reading from a set of raw readings in a particular bucket
    min_ = 2  # the minimum reading from a set of raw readings in a particular bucket
 
    avg = 3   # the average reading in a particular time bucket

allowed_units = set(["C", "%", "lux", "kPa", "bool"])

class SensorReadingPayload(BaseModel):
    sensor: str = Field(index=True, default=None)
    unit: str = Field(default=None)
    value: float = Field(default=None)
    recorded_timestamp: int = Field(default=None)


class SensorReading(SQLModel, table=True):
    sensor: str = Field(index=True, default=None, primary_key=True)
    unit: str = Field(default=None)
    value: float = Field(default=None)
    method: str = Enum(ReadingMethod, default=ReadingMethod.raw)
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


class SampleBucket:
    """when downsampling results there are several ways to do it. This Abstract class is the root."""
    bucket_registry = {}

    def samples(self):
        """return the downsampled data"""
        pass

    def add(self, SensorReading):
        pass

    @staticmethod
    def bucket_factory(method: ReadingMethod, timestamp, sensor, unit):
        return SampleBucket.bucket_registry[method](timestamp, sensor, unit)


class AverageBucket(SampleBucket):
    method = ReadingMethod.avg
    def init(self, timestamp, sensor, unit):
        self.sensor = sensor
        self.total = 0.0
        self.count = 0
        self.unit = unit
        self.timestamp = timestamp

    def add(self, r: SensorReading):
        if r.unit != self.unit:
            raise ValueError(
                f"adding value with units: {r.unit} to sample bucket of units {self.unit}"
            )
        if r.sensor != self.sensor:
            raise ValueError(
                f"adding values from different sensors {r.sensor} to sample bucket for {self.sensor}"
            )
        if r.timestamp < self.timestamp:
            raise ValueError(
                f"adding values from outside the bucket  {r.timestamp} to sample bucket for {self.sensor}"
            )

        self.count += r.value
        self.total += 1

    def sample(self):
        return SensorReading(
            sensor=self.sensor, unit=self.unit, value=self.total / self.count
        )

# Register the class that handles the 'avg' method
SampleBucket.bucket_registry[ReadingMethod.avg] = AverageBucket


def downsample(
    data: list[SensorReading], method: ReadingMethod, bucket_count: int
) -> list[SensorReading]:
    """returns a list of sensor readings
       data is assumed to be ordered by increasing timestamps
    """
    buckets =[]
    start_timestamp = data[0].recorded_timestamp
    end_timestamp = data[-1].recorded_timestamp
    bucket_size = (end_timestamp - start_timestamp) / bucket_count

    for i in range(0, bucket_count):
        timestamp = start_timestamp + i*bucket_size
        b = SampleBucket.bucket_factory(method, timestamp, sensor, unit)
        buckets.append(b)

    for r in data:
        slot = int((r.recorded_timestamp - start_timestamp)/bucket_size)
        buckets[slot].add(r)

    return buckets


def organise_readings(alldata: list[SensorReading], units: set[str]):
    """ separate data by sensor then unit type so that it's easy
    for it to be displayed on a different axis. """

    readings_by_sensor = {}
    for d in alldata:
        if d.sensor not in readings_by_sensor:
            readings_by_sensor[d.sensor] = {u: [] for u in units}
        readings_by_unit = readings_by_sensor[d.sensor]
        readings_by_unit[d.unit].append(d)

    return readings_by_sensor


def fetch_readings(
    session: Session,
    start_timestamp: int = None,
    period: int = 600,
    limit=1000,
    units: set[str] = set(["C"]),
    sensors: set = None,
    sample_buckets=None,
    sample_type=None
):
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
    return organise_readings(alldata, units)
