"""
Tests for the sensor_reading module

"""

from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
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
    SensorSummary,
    SensorReadingPayload,
    SampleMethod,
    BucketChain,
    Average,
    Minimum,
    Maximum,
    Sampler,
)

TEST_SENSOR = "sensor_1"
TEST_UNIT = "C"
TEST_VALUE = 25.5
TEST_TIMESTAMP = int(time.time())
TEST_RECEIVED_TIMESTAMP = int(time.time())


@pytest.fixture
def database_engine_test():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def ten_readings(database_engine_test):
    """create ten readings from the same sensor  with the same units"""
    with Session(database_engine_test) as write_session:
        start_timestamp = int(time.time())
        timestamp = start_timestamp
        temperature = 16.0
        for i in range(0, 10):
            r = SensorReading(
                sensor=TEST_SENSOR,
                unit=TEST_UNIT,
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
    return database_engine_test, start_timestamp


@pytest.fixture
def sample_readings():
    """Fixture to create sample SensorReading objects"""
    return [
        SensorReading(
            sensor=TEST_SENSOR,
            unit="C",
            value=10.0,
            recorded_timestamp=1000,
            received_timestamp=1001,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit="C",
            value=15.0,
            recorded_timestamp=1001,
            received_timestamp=1002,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit="C",
            value=20.0,
            recorded_timestamp=1002,
            received_timestamp=1003,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit="C",
            value=5.0,
            recorded_timestamp=1003,
            received_timestamp=1004,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit="C",
            value=12.0,
            recorded_timestamp=1004,
            received_timestamp=1005,
        ),
    ]


@pytest.fixture
def sample_bucket(sample_readings):
    """Fixture to create a sample bucket with test data"""
    bucket = SampleBucket(
        timestamp=1000,
        methods={SampleMethod.AVG, SampleMethod.MIN_, SampleMethod.MAX_},
    )
    for reading in sample_readings:
        bucket.add(reading)
    return bucket


class TestSensorReading:

    client = TestClient(main.app)

    def test_fetch(self, ten_readings):
        """see if we can fetch more than one reading"""
        engine, timestamp = ten_readings
        print(f"{engine=} {timestamp=}")

        with Session(engine) as read_session:
            fetched_readings = SensorReading.fetch(
                session=read_session,
                start_timestamp=timestamp,
                period=1000,
                units={TEST_UNIT},
                sensors={TEST_SENSOR},
                limit=10,
            )
            values = [r.value for r in fetched_readings]
            assert len(values) == 10

            missfirst = SensorReading.fetch(
                session=read_session,
                start_timestamp=timestamp + 5,
                period=1000,
                units={TEST_UNIT},
                sensors={TEST_SENSOR},
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


def test_sample_bucket_initialization():
    """Test that SampleBucket is initialized correctly"""
    bucket = SampleBucket(
        timestamp=1000,
        methods={SampleMethod.AVG, SampleMethod.MIN_},
    )

    assert bucket.timestamp == 1000
    assert len(bucket.methods) == 2


def test_add_out_of_range_reading():
    """Test that adding a reading with timestamp before bucket timestamp raises ValueError"""
    bucket = SampleBucket(timestamp=1000, methods={SampleMethod.AVG})

    reading = SensorReading(
        sensor=TEST_SENSOR,
        unit=TEST_UNIT,
        value=10.0,
        recorded_timestamp=999,  # Before bucket timestamp
        received_timestamp=1000,
    )

    with pytest.raises(ValueError):
        bucket.add(reading)


def test_sample_bucket_samples(sample_bucket):
    """Test that the samples method returns correct values"""
    timestamp, samples = sample_bucket.samples()

    assert int(timestamp) > 0

    avg_key = TEST_SENSOR + "_" + TEST_UNIT + "_" + SampleMethod.AVG.value

    assert avg_key in samples
    min_key = TEST_SENSOR + "_" + TEST_UNIT + "_" + SampleMethod.MIN_.value
    assert min_key in samples
    max_key = TEST_SENSOR + "_" + TEST_UNIT + "_" + SampleMethod.MAX_.value
    assert max_key in samples

    # Check average calculation
    avg_sample = samples[avg_key]
    assert avg_sample == pytest.approx(12.4)  # (10+15+20+5+12)/5 = 12.4

    # Check min calculation
    min_sample = samples[min_key]
    assert min_sample == 5.0

    # Check max calculation
    max_sample = samples[max_key]
    assert max_sample == 20.0


def test_downsample_method():
    """Test the downsample static method"""
    readings = [
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=10.0,
            recorded_timestamp=1000,
            received_timestamp=1001,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=15.0,
            recorded_timestamp=1001,
            received_timestamp=1002,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=20.0,
            recorded_timestamp=1002,
            received_timestamp=1003,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=5.0,
            recorded_timestamp=1003,
            received_timestamp=1004,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=12.0,
            recorded_timestamp=1004,
            received_timestamp=1005,
        ),
        SensorReading(
            sensor=TEST_SENSOR,
            unit=TEST_UNIT,
            value=8.0,
            recorded_timestamp=1005,
            received_timestamp=1006,
        ),
    ]

    result = BucketChain.downsample(
        data=readings,
        sample_methods=SampleMethod.from_str("avg,min,max"),
        bucket_count=2,
        start_timestamp=1000 - 1,
        end_timestamp=1006 + 1,
    )

    assert len(result) == 2

    # First bucket (timestamps 1000-1003)
    su = TEST_SENSOR + "_" + TEST_UNIT
    assert result[0][su + "_avg"] == pytest.approx(15.0)  # (10+15+20)/4
    assert result[0][su + "_min"] == 10.0
    assert result[0][su + "_max"] == 20.0

    # Second bucket (timestamps 1004-1005)
    assert result[1][su + "_avg"] == pytest.approx(8.33333)  # (5+12+8)/3
    assert result[1][su + "_min"] == 5.0
    assert result[1][su + "_max"] == 12.0


def test_sampler_factory():
    """Test that the Sampler factory returns the correct sampler instances"""
    avg_sampler = Sampler.factory(SampleMethod.AVG)
    assert isinstance(avg_sampler, Average)

    min_sampler = Sampler.factory(SampleMethod.MIN_)
    assert isinstance(min_sampler, Minimum)

    max_sampler = Sampler.factory(SampleMethod.MAX_)
    assert isinstance(max_sampler, Maximum)


def test_empty_bucket_samples():
    """Test that an empty bucket returns empty samples"""
    bucket = SampleBucket(timestamp=1000, methods={SampleMethod.AVG})

    timestamp, samples = bucket.samples()
    assert timestamp > 0
    assert len(samples) == 0


# Edge cases
def test_empty_data():
    empty_data = []
    downsampled = BucketChain.downsample(
        empty_data, 10, [SampleMethod.AVG], start_timestamp=-1, end_timestamp=-1
    )
    assert downsampled == []


def test_single_data_point():
    single_data = [
        SensorReading.from_payload(
            SensorReadingPayload(
                sensor=TEST_SENSOR,
                unit=TEST_UNIT,
                value=TEST_VALUE,
                recorded_timestamp=TEST_TIMESTAMP,
            )
        )
    ]
    print(f"{single_data[0].unit=}  {single_data[0].sensor=}")
    downsampled = BucketChain.downsample(
        single_data,
        10,
        [SampleMethod.AVG],
        start_timestamp=TEST_TIMESTAMP,
        end_timestamp=TEST_TIMESTAMP + 1,
    )
    assert len(downsampled) == 1
    sus = TEST_SENSOR + "_" + TEST_UNIT + "_avg"
    assert sus in downsampled[0]


def test_invalid_units():
    with pytest.raises(ValueError):
        SensorReadingPayload(
            sensor=TEST_SENSOR,
            unit="invalid_unit",
            value=TEST_VALUE,
            recorded_timestamp=TEST_TIMESTAMP,
        )
