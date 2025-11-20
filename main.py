"""
Push-Monitoring API

"Probes" periodically upload sensor readings to
this service which records them in a database.

A client such as a web app can read the data.


MIT License

Copyright (c) 2025 Timothy Norman Murphy <tnmurphy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import logger
import traceback

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from sensor_reading import SensorReading, SensorReadingPayload

from typing import List
from http import HTTPStatus
import time
import sys


app = FastAPI()


origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
    "http://rhodes.local:5000",
    "http://chivero:5000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    response = await call_next(request)
    return response


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch all for any exceptions that we have not handled in the
    endpoints. This saves a great deal of repetition and eliminates
    potential omissions.
    """

    # The following snippet of code is aimed at python 3.9 that's installed on raspberry pi.
    # When that changes to a more recent version then traceback.format_exception can lose the
    # last two parameters and we won't need to call sys.exc_info

    major, minor = sys.version_info[:2]
    assert major >= 3  # will not work on 2
    if minor <= 9:
        # Here we can't get the exception information for some reason because
        # it's all None by the time this function is called.
        # I'm not sure 10 is better, only that 9 definitely doesn't work.
        request.state.logger.exception(f"Generic: {type(exc).__name__}: '{exc}'")
    else:  # More modern python.
        request.state.logger.exception(
            f"Generic: {type(exc)}: '{exc}' trace: {traceback.format_exception(exc)}"
        )

    response = {
        "id": request.state.correlator,
        "description": "Internal Server Error",
        "description_key": "internal.server.error",
    }
    return JSONResponse(
        response,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        headers={"X-Correlation-Id": request.state.correlator},
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
        try:
            for reading in readings:
                r = SensorReading.from_payload(reading)
                session.add(r)
            session.commit()
        except IntegrityError:
            raise HTTPError(409, "Possible duplicate")

    response = {
        "id": request.state.correlator,
        "description": "ok",
        "description_key": "ok",
        "current_timestamp": int(time.time()),
    }
    return JSONResponse(response, status_code=200)


@app.get("/read", response_class=JSONResponse)
def get_reading(
        request: Request, start_timestamp: int = None, period: int = 600, limit=100
) -> list[SensorReading]:
    """
    Returns a list of readings.
    """
    rlist = []
    with Session(request.app.state.engine) as session:
        results = SensorReading.fetch_readings(
                session, start_timestamp=start_timestamp, period=period, limit=limit
        )
        request.state.logger.debug(f"{results=}")
        rlist = [r.model_dump() for r in results]
        response = {"readings": rlist, "current_timestamp": int(time.time())}

    return JSONResponse(response, status_code=200)
