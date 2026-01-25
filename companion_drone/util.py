from mavsdk import System
from math import sqrt
from logging import getLogger, INFO, basicConfig
from model import DroneState

basicConfig(level=INFO)
logger = getLogger(__name__)

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

from math import sqrt, cos, radians

async def get_distance_between(
    drone: System,
    latitude: float,
    longitude: float,
    altitude: float) -> float:
    """
    Returns the 3D distance in meters between the drone and the given location.
    
    This function uses a simplified approximation where the differences in 
    latitude and longitude are converted to meters based on the current 
    drone latitude.
    """
    
    # Earth's radius in meters (mean value)
    R = 6371000.0  
    
    # Get the current drone position
    async for pos in drone.telemetry.position():
        
        # 1. Calculate the difference in latitude and longitude
        lat_diff_deg = pos.latitude_deg - latitude
        lon_diff_deg = pos.longitude_deg - longitude
        alt_diff_m = pos.absolute_altitude_m - altitude
        
        # 2. Convert degrees to radians for trigonometric functions
        # The average latitude is used for the longitude-to-meter conversion
        lat_rad = radians(pos.latitude_deg) 
        lat_diff_rad = radians(lat_diff_deg)
        lon_diff_rad = radians(lon_diff_deg)
        
        # 3. Convert differences (degrees) to approximate distance in meters (flat Earth approximation for short distances)
        
        # a) Latitude conversion (approx 111.32 km per degree)
        # 1 degree of latitude is roughly constant in meters
        lat_dist_m = R * lat_diff_rad 
        
        # b) Longitude conversion (varies with latitude)
        # 1 degree of longitude is shorter at the poles: (111.32 km) * cos(latitude)
        lon_dist_m = R * lon_diff_rad * cos(lat_rad)
        
        # 4. Use the 3D Pythagorean theorem: distance = sqrt(dx² + dy² + dz²)
        # dx = lat_dist_m, dy = lon_dist_m, dz = alt_diff_m
        distance = sqrt(lat_dist_m**2 + lon_dist_m**2 + alt_diff_m**2)
        
        return distance

async def low_battery_checker(drone: System, drone_current_state: DroneState):
    async for battery in drone.telemetry.battery():
        if battery.remaining_percent <= 20:
            logger.warning(f"Low Battery: {battery.remaining_percent}%")
            logger.warning(f"Returning to home.")
            await drone.action.return_to_launch()
            drone_current_state = DroneState.LOW_BATTERY
            break
