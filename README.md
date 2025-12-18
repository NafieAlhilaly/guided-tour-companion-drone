# Guided Tour Companion Drone

This project simulates a companion drone for guided tours, enabling tour guides to ensure group safety and regulation-compliant experiences. The tour guide can control the drone using [Companion Mobile App](https://github.com/NafieAlhilaly/guided-tour-companion-app), enhancing overall management and security.

The drone will do the following:
- Monitor group safety and regulation violations.
- Deliver medical supplies to the group from the medical supply location.

## Set up

### Prerequisites
- Make, PX4, and jMAVSim installed
- QGroundControl application
- Python 3.x with pip

### Running Locally

1. **Start PX4 SITL with jMAVSim**
    ```bash
    export PX4_HOME_LON=42.3781843
    export PX4_HOME_LAT=18.373417
    export PX4_HOME_ALT=0
    make px4_sitl jmavsim
    ```

2. **Launch QGroundControl**
    - Open the QGroundControl application to monitor the drone

3. **Set up Python Environment**
    ```bash
    python -m venv env
    source env/bin/activate
    ```

4. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

5. **Run the Application**
    ```bash
    python main.py
    ```

6. **Test with Mosquitto Client** (Optional)
    - To send test notifications to topics, use the scripts in the `scripts/` folder:
    ```bash
    mosquitto_pub -h localhost -t "notification/topic" -m "test message"


    ```
    - Refer to scripts in `scripts/` for pre-configured publish examples

    Or you can use the [Companion App](https://github.com/NafieAlhilaly/guided-tour-companion-app)

## Test

https://github.com/user-attachments/assets/85c33211-5759-46ed-bed0-d3d1d5159017
