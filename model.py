from dataclasses import dataclass
from enum import IntEnum

@dataclass
class GroupPosition:
    latitude: float
    longitude: float
    altitude: float

    def __init__(self, latitude: float, longitude: float, altitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        if not self.is_valid():
            raise ValueError("Invalid position values")

    def is_valid(self) -> bool:
        """Check if the position values are within valid ranges."""
        return (
            -90.0 <= self.latitude <= 90.0 and
            -180.0 <= self.longitude <= 180.0 and
            self.altitude >= 0.0
        )

class DroneState(IntEnum):
    INIT = 0
    MONITOR = 1
    TO_MED_SUPPLY = 2
    TO_GROUP = 3
    LOW_BATTERY = 4
