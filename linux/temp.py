import smbus
from devicereader import DeviceReader
from typing import List, Dict, Any
import time

class TemperatureReader(DeviceReader):
    """Read from a sensorhub and return probe data"""
    def __init__(self, bus: smbus.SMBus = None, address: int = 0x17):
        if bus is None:
            self.bus = smbus.SMBus(1)
        else:
            self.bus = bus
        self.address = address

    def read(self) -> float:
        """Read and return sensor data from SensorHub."""
        aReceiveBuf = []
        aReceiveBuf.append(0x00)  # Placeholder
        for i in range(0x01, 0x0D + 1):
            aReceiveBuf.append(self.bus.read_byte_data(self.address, i))

        # Process sensor data
        readings = []
        read_time = int(time.time())

        # Temperature
        temp = self.bus.read_byte_data(self.address, 0x05)
        readings.append({
            "sensor": "temperature",
            "unit": "C",
            "value": float(temp),
            "recorded_timestamp": read_time
        })

        return temp

