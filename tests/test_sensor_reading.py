from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from sqlmodel import Session, select
from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import sys
import time

# Add the project root directory to the sys path
sys.path.append(str(Path(__file__).absolute().parents[1]))

import main
from sensor_reading import SensorReading


class TestSensorReading:

    client = TestClient(main.app)

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
