from mavsdk import System
from asyncio import run, sleep, create_task
import paho.mqtt.client as mqtt
from model import MQTTTopic
from util import is_position_reached, low_battery_checker
from model import MedicalDroneState

from logging import getLogger, INFO, basicConfig

basicConfig(level=INFO)
logger = getLogger(__name__)

MEDICAL_DRONE_START_LOCATION = [15, 23]
INIT_GROUP_LOCATION = [18.373465, 42.3781875]


medical_drone_state = MedicalDroneState.INIT


def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    global medical_drone_state
    if msg.topic == MQTTTopic.MEDICAL_SUPPLY_ALERT_TOPIC.value:
        logger.info(f"Medical alert received on topic {msg.topic}")
        if medical_drone_state == MedicalDroneState.WAIT_FOR_ALERT:
            medical_drone_state = MedicalDroneState.TO_GROUP
            logger.info("State changed to TO_GROUP")


async def mission():
    """Main mission logic for medical supply drone."""
    global medical_drone_state

    drone = System(port=14541)
    logger.info("Connecting to medical drone with system ID 2 on port 14541")
    await drone.connect(system_address="udp://:14541")

    logger.info("Waiting for system ID 2 to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            logger.info("Medical drone system ID 2 connected!")
            break

    home = await drone.telemetry.position().__anext__()
    takeoff_altitude = 5  # meters
    await drone.action.set_takeoff_altitude(takeoff_altitude)
    await drone.action.set_return_to_launch_altitude(takeoff_altitude)

    # Initialize MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.connect("0.0.0.0", 1883, 60)
    logger.info("Connected to MQTT broker")
    mqtt_client.loop_start()
    mqtt_client.subscribe(MQTTTopic.MEDICAL_SUPPLY_ALERT_TOPIC.value)
    mqtt_client.on_message = on_message

    # Get home position

    # Create battery check task
    create_task(low_battery_checker(drone, medical_drone_state))

    while True:
        match medical_drone_state:
            case MedicalDroneState.INIT:
                logger.info("Initializing: Taking off to initial altitude")
                await drone.action.arm()
                await drone.action.takeoff()

                # Wait until takeoff altitude is reached
                while not await is_position_reached(
                    drone,
                    home.latitude_deg,
                    home.longitude_deg,
                    home.absolute_altitude_m + takeoff_altitude,
                    0.009,
                ):
                    await sleep(0.5)
                logger.info("Waiting for medical supply alert...")
                medical_drone_state = MedicalDroneState.WAIT_FOR_ALERT

            case MedicalDroneState.WAIT_FOR_ALERT:
                await sleep(1)

            case MedicalDroneState.TO_GROUP:
                logger.info("Flying to group location")
                await drone.action.goto_location(
                    INIT_GROUP_LOCATION[0], INIT_GROUP_LOCATION[1], takeoff_altitude, 0
                )
                # Wait until close to group location
                while not await is_position_reached(
                    drone,
                    INIT_GROUP_LOCATION[0],
                    INIT_GROUP_LOCATION[1],
                    takeoff_altitude,
                    0.009,
                ):
                    await sleep(0.5)
                logger.info("Arrived at group location")

                medical_drone_state = MedicalDroneState.WAIT_AT_GROUP

            case MedicalDroneState.WAIT_AT_GROUP:
                logger.info("Delivering medical supplies... ")
                await sleep(15)
                logger.info("Medical supplies delivered!")
                medical_drone_state = MedicalDroneState.RETURN_TO_LAUNCH

            case MedicalDroneState.RETURN_TO_LAUNCH:
                logger.info("Returning to launch location")
                await drone.action.goto_location(
                    home.latitude_deg, home.longitude_deg, takeoff_altitude, 0
                )

                # Wait until close to home
                while True:
                    async for pos in drone.telemetry.position():
                        distance_to_home = (
                            (pos.latitude_deg - home.latitude_deg) ** 2
                            + (pos.longitude_deg - home.longitude_deg) ** 2
                        ) ** 0.0009

                        if distance_to_home < 0.0009:  # Very close to home
                            logger.info("Returned to home location")
                            medical_drone_state = MedicalDroneState.WAIT_FOR_ALERT
                            break
                        break

                    if medical_drone_state == MedicalDroneState.WAIT_FOR_ALERT:
                        await sleep(5)
                        break

                    await sleep(1)

            case MedicalDroneState.LOW_BATTERY:
                logger.warning("Low battery - landed at home")
                await sleep(5)


if __name__ == "__main__":
    run(mission())
