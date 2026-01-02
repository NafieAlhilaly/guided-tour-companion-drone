# Guided Tour Companion Drone

This project simulates a companion drone system for guided tours, enabling tour guides to ensure group safety and maintain regulation-compliant experiences. The tour guide can control the drone fleet using the [Companion Mobile App](https://github.com/NafieAlhilaly/guided-tour-companion-app), enhancing overall management and security.

## Features

The drone system provides the following capabilities:
- **Safety Monitoring**: Continuously monitor group safety and detect regulation violations
- **Medical Supply Delivery**: Autonomously deliver medical supplies from designated locations to the tour group
- **Real-time Control**: Remote monitoring and control via mobile application

## Setup

### Prerequisites

Ensure you have the following installed:
- Make, PX4, and jMAVSim
- QGroundControl application
- Python 3.x with pip
- Gazebo (optional, for advanced simulation)

### Running Locally

#### Option 1: Start PX4 SITL with jMAVSim

```bash
export PX4_HOME_LON=42.3781843
export PX4_HOME_LAT=18.373417
export PX4_HOME_ALT=0
make px4_sitl jmavsim
```

#### Option 2: Start PX4 SITL with Gazebo

```bash
PX4_UXRCE_DDS_NS=px4_0 PX4_GZ_WORLD=forest make px4_sitl gz_x500_depth
```

Launch the medical drone (second drone instance):
```bash
./scripts/spawn_medical_drone.sh
```

#### Launch QGroundControl

Open the QGroundControl application to monitor and control the drone fleet.

#### Python Environment Setup

Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate
```

Install required dependencies:
```bash
pip install -r requirements.txt
```

#### Run the Drone Instances

**Monitor Drone (Primary Instance)**
```bash
python main.py
```

**Medical Drone (Secondary Instance)**

In a separate terminal:
```bash
python medical_drone.py
```

### Testing

#### Test with Mosquitto Client (Optional)

Send test notifications using the MQTT broker:
```bash
mosquitto_pub -h localhost -t "notification/topic" -m "test message"
```

Pre-configured publish examples are available in the `scripts/` directory.

Alternatively, use the [Companion Mobile App](https://github.com/NafieAlhilaly/guided-tour-companion-app) for integrated testing.

#### Configure Gazebo World

To use the custom forest environment (`PX4_GZ_WORLD=forest`):
1. Modify the `forest.sdf` file as needed
2. Copy the world file to the PX4 directory:
```bash
./scripts/copy_world_to_px4_dir.sh
```

## Demo

### jMAVSim Simulation

Testing core drone functionality including takeoff and group monitoring (orbit pattern):

https://github.com/user-attachments/assets/85c33211-5759-46ed-bed0-d3d1d5159017

### Gazebo Simulation

Comprehensive testing of all drone capabilities including takeoff, group monitoring (orbit pattern), and medical supply delivery missions.


https://github.com/user-attachments/assets/53e6caaf-3b80-4540-befc-173b95956abb



https://github.com/user-attachments/assets/efd97c0b-e035-4b7b-aa13-62483de3fde4



