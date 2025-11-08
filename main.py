"""
Push-Monitoring API

Clients periodically upload code.

Copyright (C) 2025 <tnmurphy@gmail.com>
"""

from fastapi import FastAPI, Request
from sensor_reading import SensorReading, SensorReadingPayload
from fastapi.responses import JSONResponse
from sensor_reading import SensorReading
from sqlmodel import Session, select
import time

app = FastAPI()


@app.post("/sense", response_class=JSONResponse)
def sensor_event(request: Request, reading: SensorReadingPayload):
    print(f"{reading=}")
    r = SensorReading.from_payload(reading)
    with Session(request.app.state.engine) as session:
        session.add(r)
        session.commit()
    s = {"message": "OK", "current_timestamp": int(time.time())}
    return JSONResponse(s, status_code=200)


@app.get("/read", response_class=JSONResponse)
def get_reading(request: Request) -> list[SensorReading]:
    rlist = []
    with Session(request.app.state.engine) as session:
        statement = select(SensorReading)
        results = session.exec(statement).fetchall()
        print("\nresults dir=", dir(results))
        print("\nresults=", results)
        rlist = [r.model_dump() for r in results]
        response = {"readings": rlist, "current_timestamp": int(time.time())}

    return JSONResponse(response, status_code=200)
