import requests
from datetime import datetime, timezone
import time

from sensor_reading import SensorReadingPayload

url = "http://127.0.0.1:5000"
dt = int(time.time())
r = SensorReadingPayload(sensor = "1", unit = "C", value = 20.1, recorded_timestamp=dt)

rj = r.model_dump()
print(rj)

response = requests.post(url+"/sense", json=rj)

print(f"status={response.status_code}")
