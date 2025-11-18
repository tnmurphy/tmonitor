import smbus
from devicereader import DeviceReader

class SensorHubReader(DeviceReader):
    """Read from a sensorhub and return probe data"""
    def __init__(self, bus: smbus.SMBus = None, address: int = 0x17):
        if bus is None
            self.bus = smbus.SMBus(1)
        else:
            self.bus = bus
        self.address = address

    async def read(self) -> List[Dict[str, Any]]:
        """Read and return sensor data from SensorHub."""
        aReceiveBuf = []
        aReceiveBuf.append(0x00)  # Placeholder
        for i in range(0x01, 0x0D + 1):
            aReceiveBuf.append(self.bus.read_byte_data(self.address, i))

        # Process sensor data
        readings = []

        # Temperature
        temp = self.bus.read_byte_data(self.address, 0x05)
        readings.append({
            "sensor": "temperature",
            "unit": "C",
            "value": float(temp),
            "recorded_timestamp": int(asyncio.get_event_loop().time())
        })

        # Humidity
        humidity = self.bus.read_byte_data(self.address, 0x06)
        readings.append({
            "sensor": "humidity",
            "unit": "%",
            "value": float(humidity),
            "recorded_timestamp": int(asyncio.get_event_loop().time())
        })

        # Light
        light = (self.bus.read_byte_data(self.address, 0x03) << 8) | (self.bus.read_byte_data(self.address, 0x02))
        readings.append({
            "sensor": "light",
            "unit": "lux",
            "value": float(light),
            "recorded_timestamp": int(asyncio.get_event_loop().time())
        })

        # Pressure
        pressure = (self.bus.read_byte_data(self.address, 0x0B) << 16) | (
            (self.bus.read_byte_data(self.address, 0x0A) << 8)) | (
            (self.bus.read_byte_data(self.address, 0x09)))
        readings.append({
            "sensor": "pressure",
            "unit": "kPa",
            "value": float(pressure),
            "recorded_timestamp": int(asyncio.get_event_loop().time())
        })

        # Human presence
        human = self.bus.read_byte_data(self.address, 0x0D)
        readings.append({
            "sensor": "human_presence",
            "unit": "bool",
            "value": float(human),
            "recorded_timestamp": int(asyncio.get_event_loop().time())
        })

        return readings

