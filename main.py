from fastapi import FastAPI, Request
from sensor_reading import SensorReading, SensorReadingPayload
from fastapi.responses import JSONResponse
from sensor_reading import SensorReading
from sqlmodel import Session, select

app = FastAPI()

@app.post("/sense", response_class=JSONResponse)
def sensor_event(request: Request, reading: SensorReadingPayload):
    print(f"{reading=}")
    r = SensorReading.from_payload(reading)
    with Session(request.app.state.engine) as session:
        session.add(r)
        session.commit()
    s = {"message": "OK"}
    return JSONResponse(s, status_code=200)


@app.get("/read", response_class=JSONResponse)
def get_reading(request: Request) -> list[SensorReading]:
    rlist =[]
    with Session(request.app.state.engine) as session:
        statement = select(SensorReading)
        results = session.exec(statement).fetchall()
        print("\nresults dir=", dir(results))
        print("\nresults=", results)
        rlist = [r.model_dump() for r in results]

    return JSONResponse(rlist, status_code=200)

