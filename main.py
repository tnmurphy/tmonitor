"""
Push-Monitoring API

"Probes" periodically upload sensor readings to
this service which records them in a database.

A client such as a web app can read the data. 

Copyright (C) 2025 <tnmurphy@gmail.com>
"""

from fastapi import FastAPI, Request
from sensor_reading import SensorReading, SensorReadingPayload
from fastapi.responses import JSONResponse
from sensor_reading import SensorReading
from sqlmodel import Session, select
import time
from typing import List
import logger
import traceback


app = FastAPI()

@app.middleware("http")
async def add_logger_with_correlator(request: Request, call_next):
    """
    Set up the request to have a logger and a correlation id
    in the state. This lets everything following use the same
    correlation id and logging setup just by having access
    to the request. Saves repeating the same thing in each handler.
    """
    request.state.logger = logger.RequestLogger()
    request.state.correlator = request.state.logger.correlator
    b = await request.body()
    request.state.logger.debug(f"request body: {b}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc):
    """
       Catch all for any exceptions that we have not handled in the
       endpoints. This saves a great deal of repetition and eliminates
       potential omissions.
    """
    request.state.logger.exception(
        f"Generic: {type(exc)}: {exc} trace: {traceback.format_exception(exc)}" 
    )
    response = {
        "id": request.state.correlator,
        "description": "Internal Server Error",
        "description_key": "internal.server.error",
    }
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(response),
        headers={"X-Correlation-Id": correlator},
    )

@app.post("/sense", response_class=JSONResponse)
def sensor_event(request: Request, readings: List[SensorReadingPayload]):
    """
       Probes send sensor readings to this. The input is a list
       of SensorReadingPayloads in json.
       It returns the current time so that probes without a clock 
       battery can sync up.
    """
    request.state.logger.debug(f"/sense {readings=}")
    with Session(request.app.state.engine) as session:
        for reading in readings:
            r = SensorReading.from_payload(reading)
            session.add(r)
        session.commit()
    s = {"message": "OK", "current_timestamp": int(time.time())}
    return JSONResponse(s, status_code=200)


@app.get("/read", response_class=JSONResponse)
def get_reading(request: Request) -> list[SensorReading]:
    """
       Returns a list of readings.
    """
    rlist = []
    with Session(request.app.state.engine) as session:
        statement = select(SensorReading)
        results = session.exec(statement).fetchall()
        request.state.logger.debug(f"{results=}")
        rlist = [r.model_dump() for r in results]
        response = {"readings": rlist, "current_timestamp": int(time.time())}

    return JSONResponse(response, status_code=200)
