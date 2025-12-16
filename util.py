from mavsdk import System
from math import sqrt

async def is_position_reached(
        drone: System,
        latitude: float,
        longitude: float,
        altitude: float,
        threshold: float = 0.0002) -> bool:
    """Checks if the drone has reached the given location within the threshold."""
    async for pos in drone.telemetry.position():
        lat_diff = abs(pos.latitude_deg - latitude)
        lon_diff = abs(pos.longitude_deg - longitude)
        alt_diff = abs(pos.absolute_altitude_m - altitude)
        if lat_diff < threshold and lon_diff < threshold and alt_diff < threshold:
            return True
        return False

async def get_distance_between(
        drone: System,
        latitude: float,
        longitude: float,
        altitude: float) -> float:
    """Returns the distance in degrees/meters between the drone and the given location."""
    async for pos in drone.telemetry.position():
        lat_diff = pos.latitude_deg - latitude
        lon_diff = pos.longitude_deg - longitude
        alt_diff = pos.absolute_altitude_m - altitude
        distance = sqrt(lat_diff**2 + lon_diff**2 + alt_diff**2)
        return distance
