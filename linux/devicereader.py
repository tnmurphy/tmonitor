from typing import List, Dict, Any

class DeviceReader:
    """Base class for all device readers."""
    async def read(self) -> List[Dict[str, Any]]:
        """Read and return a list of sensor readings."""
        raise NotImplementedError
