"""
Models and database for sensor readings
"""

from sqlmodel import Field, Session, SQLModel, create_engine, select, DateTime, Enum
from pydantic import BaseModel
from datetime import datetime, timezone
import time

# engine = create_engine("sqlite:///:memory:")


class SensorReadingPayload(BaseModel):
    sensor: str = Field(index=True, default=None)
    unit: str = Field(default=None)
    value: float = Field(default=None)
    recorded_timestamp: int = Field(default=None)


class SensorReading(SQLModel, table=True):
    sensor: str = Field(index=True, default=None, primary_key=True)
    unit: str = Field(default=None)
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

    @classmethod
    def fetch_readings(cls, session: Session, start_timestamp: int = None, limit=10):
        if start_timestamp is not None:
            sel = (
                select(SensorReading)
                .where(SensorReading.received_timestamp > start_timestamp)
                .order_by(SensorReading.received_timestamp)
                .limit(limit)
            )
        else:
            sel = (
                select(SensorReading)
                .order_by(SensorReading.received_timestamp)
                .limit(limit)
            )

        result = session.scalars(sel).all()
        return result
