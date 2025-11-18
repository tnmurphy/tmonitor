import asyncio
import uvloop
import aiohttp
from typing import List, Dict, Any
from devicereader import DeviceReader
from time import time

DEFAULT_INTERVAL=300
POST_URL="http://chivero:5000/sense"

async def read_devices(queue: asyncio.Queue, readers: List[DeviceReader]) -> None:
    """Read from all devices and enqueue the readings."""
    while True:
        for reader in readers:
            try:
                readings = await reader.read()
                await queue.put(readings)
                print(f"Enqueued {len(readings)} readings at {asyncio.get_event_loop().time()}")
                print(f"Readings: {readings}")
            except Exception as e:
                print(f"Error reading from device: {e}")
        await asyncio.sleep(DEFAULT_INTERVAL)

async def send_readings(queue: asyncio.Queue, url: str) -> None:
    """Dequeue readings and send them to the specified URL."""
    async with aiohttp.ClientSession() as session:
        while True:
            readings = await queue.get()
            try:
                async with session.post(url, json=readings) as resp:
                    if resp.status == 200:
                        print(f"Sent {len(readings)} readings to {url} at {time.time()}")
                    else:
                        print(f"Failed to send readings: {resp.status}")
            except Exception as e:
                print(f"Error sending readings: {e}")
            queue.task_done()

async def main(interval: int = DEFAULT_INTERVAL) -> None:
    global DEFAULT_INTERVAL
    DEFAULT_INTERVAL = interval
    queue = asyncio.Queue()

    from sensorhub import SensorHubReader
    # Initialize your device readers here
    readers = [
        SensorHubReader(),
        # Add more readers here as needed
    ]

    tasks = [
        asyncio.create_task(read_devices(queue, readers)),
        asyncio.create_task(send_readings(queue, POST_URL))
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main(DEFAULT_INTERVAL))

