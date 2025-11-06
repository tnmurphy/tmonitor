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
                received_timestamp=received)
