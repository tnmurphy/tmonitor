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
from sensor_reading import SensorReading

@pytest.fixture
def ten_readings(database_engine):
    with Session(database_engine) as write_session:
        start_timestamp = int(time.time())
        timestamp = start_timestamp
        temperature = 16.0
        for i in range(0,10):
            r = SensorReading(
                sensor="test_create_reading_1",
                unit="C",
                value=temperature,
                recorded_timestamp=timestamp,
                received_timestamp=timestamp + 1,
            )
            temperature = round(temperature + random.randint(0,30)/random.randint(10,15),4)
            timestamp += 10
            write_session.add(r)
        write_session.commit()
        return database_engine, start_timestamp



class TestSensorReading:

    client = TestClient(main.app)

    def test_fetch_readings(self, ten_readings):
        """ see if we can fetch more than one reading """
        database_engine, timestamp = ten_readings
        
        readings = None
        with Session(main.app.state.engine) as read_session:
           readings = SensorReading.fetch_readings(session=read_session, start_timestamp=timestamp, period=1000, limit=10)
           values = [r.value for r in readings]
           assert len(values) == 10

           missfirst = SensorReading.fetch_readings(session=read_session, start_timestamp=timestamp+5, period=1000, limit=10)
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
