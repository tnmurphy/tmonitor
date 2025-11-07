import requests
import json
from datetime import datetime, timezone

from sensor_reading import SensorReading

url = "http://127.0.0.1:5000"
response = requests.get(url+"/read")

print(f"status={response.status_code}")
output = json.dumps(response.json(), indent=2)
print(f"readings={output}")
