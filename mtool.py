"""
A test tool for sending and receiving data from the backend.
"""

import argparse
import requests
import json
import time
from datetime import datetime
from sensor_reading import SensorReadingPayload


def send_data(url):
    dt = int(time.time())
    r = SensorReadingPayload(sensor="TEST", unit="C", value=20.1, recorded_timestamp=dt)
    rj = r.model_dump()
    print(rj)
    response = requests.post(f"{url}/sense", json=[rj])
    print(f"status={response.status_code}")


def receive_data(url):
    period = 60*60
    st = int(time.time()) - period  # 1 hour back
    response = requests.get(f"{url}/read?start_timestamp={st}&period={period}&limit=100")
    print(f"status={response.status_code}")
    response_json = response.json()['readings']
    for j in response_json:
        recorded = datetime.fromtimestamp(j['recorded_timestamp'])
        j['recorded_time'] = recorded.isoformat()
        received = datetime.fromtimestamp(j['received_timestamp'])
        j['received_time'] = received.isoformat()

    sorted_readings = sorted(response_json, key=lambda x: x['recorded_time'])
    output = json.dumps(sorted_readings, indent=2)
    print(f"readings={output}")


def main():
    parser = argparse.ArgumentParser(
        description="Send or receive sensor data from API."
    )
    parser.add_argument(
        "operation",
        choices=["send", "receive"],
        help="Operation to perform: 'send' or 'receive'",
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:5000", help="Base URL of the API"
    )
    args = parser.parse_args()

    if args.operation == "send":
        send_data(args.url)
    elif args.operation == "receive":
        receive_data(args.url)


if __name__ == "__main__":
    main()
