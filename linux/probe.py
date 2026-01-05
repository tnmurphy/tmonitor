#!/usr/bin/env python3
"""
A probe that records various values from a sensorhat
on a raspberry pi and uploads them to a service in
json format.

Author: Timothy Norman Murphy <tnmurphy@gmail.com> (c) 2025
LICENSE: MIT
"""

import asyncio
import uvloop
import aiohttp
from typing import List
from devicereader import DeviceReader
from time import time
import socket
socket.gethostname()

import logging

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 300
MINIMUM_INTERVAL = 30
POST_URL = "http://chivero:5000/sense"


async def read_devices(queue: asyncio.Queue, readers: List[DeviceReader]) -> None:
    """Read from all devices and enqueue the readings."""
    while True:
        for reader in readers:
            try:
                logger.info("tprobe: reading...")
                readings = await reader.read()
                await queue.put(readings)
                logger.info(f"tprobe: enqueued {len(readings)} readings at {time()}")
                logger.info(f"tprobe: Readings: {readings}")
            except Exception as e:
                logger.info(f"tprobe: error reading from device: {e}")
        await asyncio.sleep(DEFAULT_INTERVAL)


async def send_readings(queue: asyncio.Queue, url: str) -> None:
    """Dequeue readings and send them to the specified URL."""
    async with aiohttp.ClientSession() as session:
        while True:
            readings = await queue.get()
            try:
                async with session.post(url, json=readings) as resp:
                    if resp.status == 200:
                        logger.info(
                            f"tprobe: sent {len(readings)} readings to {url} at {time()}"
                        )
                    else:
                        logger.info(
                            f"tprobe: error: failed to send readings: {resp.status}"
                        )
            except Exception as e:
                logger.info(f"tprobe: error sending readings: {e}")
            queue.task_done()


async def main(name: str, interval: int = DEFAULT_INTERVAL) -> None:
    queue = asyncio.Queue()

    from sensorhub import SensorHubReader

    # Initialize your device readers here
    readers = [
        SensorHubReader(sensor_node=name),
        # Add more readers here as needed
    ]

    tasks = [
        asyncio.create_task(read_devices(queue, readers)),
        asyncio.create_task(send_readings(queue, POST_URL)),
    ]
    logger.info("tprobe: starting tasks")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    import argparse
    import socket
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="name of this probe, defaults to hostname", default=socket.gethostname())
    parser.add_argument("--interval", help="reporting interval in seconds", type=int, default=DEFAULT_INTERVAL)
    args = parser.parse_args()
    assert len(args.name.strip()) > 0
    assert args.interval  >= MINIMUM_INTERVAL # we don't want the probe to pester the service.

    logging.basicConfig(level = logging.INFO, format="%(message)s")

    logger.info("tprobe: startup\n")
    uvloop.install()
    asyncio.run(main(args.name, args.interval))
