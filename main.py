from mavsdk import System
from mavsdk.action import OrbitYawBehavior
from mavsdk.mission import MissionItem, MissionPlan
from asyncio import run, sleep
import paho.mqtt.client as mqtt
from model import GroupPosition
from enum import IntEnum
from util import is_position_reached, get_distance_between

from logging import getLogger, INFO, basicConfig
basicConfig(level=INFO)
logger = getLogger(__name__)

DRONE_START_LOCATION = [18.373417, 42.3781843]
INIT_GROUP_LOCATION = [18.373603,42.3778573]

class DroneState(IntEnum):
    INIT = 0
    MONITOR = 1
    TO_MED_SUPPLY = 2
    TO_GROUP = 3
    LOW_BATTERY = 4


def on_message(client, userdata, msg):
    logger.info(f"Received message on topic {msg.topic}")
    logger.info(f"Payload: {msg.payload.decode()}")
    payload = msg.payload.decode()
    try:
        group_position = GroupPosition(*map(float, payload.split(',')))
        client.user_data_set(group_position)
    except ValueError as e:
        logger.error(f"Invalid group position received: {payload} - {e}")

async def mission():
    drone = System()
    drone_current_state = DroneState.INIT
    await drone.connect(system_address="udp://:14540")
    mqtt_client = mqtt.Client()
    mqtt_client.connect("0.0.0.0", 1883, 60)
    logger.info("Connected to MQTT broker")
    mqtt_client.loop_start()
    mqtt_client.subscribe("flollow/target_location")
    mqtt_client.on_message = on_message
    mqtt_client.user_data_set(
        GroupPosition(INIT_GROUP_LOCATION[0], INIT_GROUP_LOCATION[1], 0)
    )

    home = await drone.telemetry.position().__anext__()
    med_supply_location = home

    med_supply_mission_items = [
        # Fly to medical supply location
        MissionItem(
            med_supply_location.latitude_deg,
            med_supply_location.longitude_deg,
            10,
            5,
            True,
            float('nan'),
            float('nan'),
            MissionItem.CameraAction.NONE,
            float('nan'),
            float('nan'),
            float('nan'),
            float('nan'),
            float('nan'),
            MissionItem.VehicleAction.NONE,
        ),
    ]
    med_supply_mission = MissionPlan(med_supply_mission_items)
    async for upload_data in drone.mission.upload_mission_with_progress(med_supply_mission):
        progress_percent = round(upload_data.progress * 100)
        logger.info(f"Upload progress: {progress_percent}")
    
    while True:
        # TODO: Refactor state machine code
        match drone_current_state:
            case DroneState.INIT:
                logger.info("Taking off and reaching initial altitude")
                await drone.action.set_takeoff_altitude(10)
                await drone.action.arm()
                await drone.action.takeoff()
                while not await is_position_reached(
                    drone,
                    home.latitude_deg,
                    home.longitude_deg,
                    await drone.action.get_takeoff_altitude()
                ):
                    pass
                logger.info("Initial altitude reached")
                drone_current_state = DroneState.TO_GROUP
            case DroneState.TO_GROUP:
                logger.info("Heading to group location")
                group_altitude = mqtt_client._userdata.altitude + (await drone.action.get_takeoff_altitude())
                await drone.action.goto_location(
                    mqtt_client._userdata.latitude,
                    mqtt_client._userdata.longitude,
                    group_altitude,
                    0
                )
                while not await is_position_reached(
                    drone,
                    mqtt_client._userdata.latitude,
                    mqtt_client._userdata.longitude,
                    group_altitude
                ):
                    pass
                drone_current_state = DroneState.MONITOR
            case DroneState.MONITOR:
                logger.info("Monitoring group location")
                await drone.action.do_orbit(
                    2,
                    3,
                    OrbitYawBehavior.HOLD_FRONT_TO_CIRCLE_CENTER,
                    mqtt_client._userdata.latitude,
                    mqtt_client._userdata.longitude,
                    await drone.action.get_takeoff_altitude()
                )
                while True:
                    await sleep(5)
                    group_position: GroupPosition = mqtt_client.user_data_get()
                    distance = await get_distance_between(
                    drone,
                    group_position.latitude,
                    group_position.longitude,
                    await drone.action.get_takeoff_altitude())
                    logger.info(f"Distance => {distance}")
                    if distance > 13:
                        break
                drone_current_state = DroneState.TO_GROUP
            case DroneState.TO_MED_SUPPLY:
                pass
            case DroneState.LOW_BATTERY:
                pass
        



if __name__ == "__main__":
    run(mission())
