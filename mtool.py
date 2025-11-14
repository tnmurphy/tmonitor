"""
A test tool for sending and receiving data from the backend.
"""

import argparse
import requests
import json
import time
from sensor_reading import SensorReadingPayload


def send_data(url):
    dt = int(time.time())
    r = SensorReadingPayload(sensor="TEST", unit="C", value=20.1, recorded_timestamp=dt)
    rj = r.model_dump()
    print(rj)
    response = requests.post(f"{url}/sense", json=[rj])
    print(f"status={response.status_code}")


def receive_data(url):
    st = int(time.time()) - 60*60
    response = requests.get(f"{url}/read?start_timestamp={st}&limit=100")
    print(f"status={response.status_code}")
    output = json.dumps(response.json(), indent=2)
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
