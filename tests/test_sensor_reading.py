from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from sqlmodel import Session, select
from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import sys
import time
import random

# Add the project root directory to the sys path
sys.path.append(str(Path(__file__).absolute().parents[1]))

import main
from datetime import datetime, timezone
from sensor_reading import (
    SampleBucket,
    SensorReading,
    SensorReadingPayload,
    SampleMethod,
    Average,
    Minimum,
#    Maximum,
    Sampler
)


@pytest.fixture
def ten_readings(database_engine):
    with Session(database_engine) as write_session:
        start_timestamp = int(time.time())
        timestamp = start_timestamp
        temperature = 16.0
        for i in range(0, 10):
            r = SensorReading(
                sensor="test_create_reading_1",
                unit="C",
                value=temperature,
                recorded_timestamp=timestamp,
                received_timestamp=timestamp + 1,
            )
            temperature = round(
                temperature + random.randint(0, 30) / random.randint(10, 15), 4
            )
            timestamp += 10
            write_session.add(r)
        write_session.commit()
        return database_engine, start_timestamp


class TestSensorReading:

    client = TestClient(main.app)

    def test_fetch_readings(self, ten_readings):
        """see if we can fetch more than one reading"""
        database_engine, timestamp = ten_readings

        readings = None
        with Session(main.app.state.engine) as read_session:
            readings = SensorReading.fetch_readings(
                session=read_session, start_timestamp=timestamp, period=1000, limit=10
            )
            values = [r.value for r in readings]
            assert len(values) == 10

            missfirst = SensorReading.fetch_readings(
                session=read_session,
                start_timestamp=timestamp + 5,
                period=1000,
                limit=10,
            )
            print(missfirst)
            assert len(missfirst) == 9
            assert missfirst[0].recorded_timestamp > timestamp

    def test_create_reading(self, database_engine):
        """
        Create a record and fetch it. Bascially check the database
        setup is working.
        """
        timestamp = int(time.time())
        r = SensorReading(
            sensor="test_create_reading_1",
            unit="C",
            value=21.1,
            recorded_timestamp=timestamp,
            received_timestamp=timestamp + 1,
        )

        with Session(database_engine) as write_session:
            write_session.add(r)
            write_session.commit()

        with Session(main.app.state.engine) as read_session:
            result = read_session.execute(
                select(SensorReading).where(
                    SensorReading.sensor == "test_create_reading_1"
                )
            ).all()
            assert len(result) == 1



@pytest.fixture
def sample_readings():
    """Fixture to create sample SensorReading objects"""
    return [
        SensorReading(
            sensor="temp",
            unit="C",
            value=10.0,
            recorded_timestamp=1000,
            received_timestamp=1001,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=15.0,
            recorded_timestamp=1001,
            received_timestamp=1002,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=20.0,
            recorded_timestamp=1002,
            received_timestamp=1003,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=5.0,
            recorded_timestamp=1003,
            received_timestamp=1004,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=12.0,
            recorded_timestamp=1004,
            received_timestamp=1005,
            method=SampleMethod.raw
        )
    ]

@pytest.fixture
def sample_bucket(sample_readings):
    """Fixture to create a sample bucket with test data"""
    bucket = SampleBucket(
        timestamp=1000,
        sensor="temp",
        unit="C",
        methods={SampleMethod.avg, SampleMethod.min_, SampleMethod.max_}
    )
    for reading in sample_readings:
        bucket.add(reading)
    return bucket

def test_sample_bucket_initialization():
    """Test that SampleBucket is initialized correctly"""
    bucket = SampleBucket(
        timestamp=1000,
        sensor="temp",
        unit="C",
        methods={SampleMethod.avg, SampleMethod.min_}
    )

    assert bucket.timestamp == 1000
    assert bucket.sensor == "temp"
    assert bucket.unit == "C"
    assert len(bucket.samplers) == 2

def test_add_out_of_range_reading():
    """Test that adding a reading with timestamp before bucket timestamp raises ValueError"""
    bucket = SampleBucket(
        timestamp=1000,
        sensor="temp",
        unit="C",
        methods={SampleMethod.avg}
    )

    reading = SensorReading(
        sensor="temp",
        unit="C",
        value=10.0,
        recorded_timestamp=999,  # Before bucket timestamp
        received_timestamp=1000,
        method=SampleMethod.raw
    )

    with pytest.raises(ValueError):
        bucket.add(reading)

def test_sample_bucket_samples(sample_bucket):
    """Test that the samples method returns correct values"""
    samples = sample_bucket.samples()

    assert SampleMethod.avg in samples
    assert SampleMethod.min_ in samples
    assert SampleMethod.max_ in samples

    # Check average calculation
    avg_sample = samples[SampleMethod.avg]
    assert avg_sample.value == pytest.approx(12.5)  # (10+15+20+5+12)/5 = 12.4

    # Check min calculation
    min_sample = samples[SampleMethod.min_]
    assert min_sample.value == 5.0

    # Check max calculation
    max_sample = samples[SampleMethod.max_]
    assert max_sample.value == 20.0

def test_downsample_method():
    """Test the downsample static method"""
    readings = [
        SensorReading(
            sensor="temp",
            unit="C",
            value=10.0,
            recorded_timestamp=1000,
            received_timestamp=1001,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=15.0,
            recorded_timestamp=1001,
            received_timestamp=1002,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=20.0,
            recorded_timestamp=1002,
            received_timestamp=1003,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=5.0,
            recorded_timestamp=1003,
            received_timestamp=1004,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=12.0,
            recorded_timestamp=1004,
            received_timestamp=1005,
            method=SampleMethod.raw
        ),
        SensorReading(
            sensor="temp",
            unit="C",
            value=8.0,
            recorded_timestamp=1005,
            received_timestamp=1006,
            method=SampleMethod.raw
        )
    ]

    result = SampleBucket.downsample(
        data=readings,
        methods={SampleMethod.avg, SampleMethod.min_},
        bucket_count=2
    )

    assert len(result[SampleMethod.avg]) == 2
    assert len(result[SampleMethod.min_]) == 2

    # First bucket (timestamps 1000-1003)
    assert result[SampleMethod.avg][0].value == pytest.approx(13.75)  # (10+15+20+5)/4
    assert result[SampleMethod.min_][0].value == 5.0

    # Second bucket (timestamps 1004-1005)
    assert result[SampleMethod.avg][1].value == pytest.approx(10.0)  # (12+8)/2
    assert result[SampleMethod.min_][1].value == 8.0

def test_sampler_factory():
    """Test that the Sampler factory returns the correct sampler instances"""
    avg_sampler = Sampler.factory(SampleMethod.avg)
    assert isinstance(avg_sampler, Average)

    min_sampler = Sampler.factory(SampleMethod.min_)
    assert isinstance(min_sampler, Minimum)

def test_empty_bucket_samples():
    """Test that an empty bucket returns empty samples"""
    bucket = SampleBucket(
        timestamp=1000,
        sensor="temp",
        unit="C",
        methods={SampleMethod.avg}
    )

    samples = bucket.samples()
    assert len(samples) == 0

