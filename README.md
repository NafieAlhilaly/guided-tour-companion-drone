# Guided Tour Companion Drone


<img width="1143" height="2048" alt="Untitled design" src="https://github.com/user-attachments/assets/8a431aed-d231-4a8e-a9c9-8437e39858af" />

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

#### ROS2 Image MQTT Bridge Setup

The ROS2 Image MQTT Bridge enables streaming camera images from Gazebo to the mobile app via MQTT.

**Prerequisites:**

Install ROS2 dependencies:
```bash
sudo apt install ros-humble-cv-bridge ros-humble-ros-gz-bridge
pip3 install paho-mqtt opencv-python
```

**Build the package:**

```bash
cd /home/nafea/projects/test_mavsdk
colcon build --packages-select ros2_image_mqtt_bridge
source install/setup.bash
```

**Launch the bridge:**

Option 1 - Using launch file (recommended):
```bash
ros2 launch ros2_image_mqtt_bridge image_bridge.launch.py
```

Option 2 - Manual launch with custom parameters:
```bash
# Start ros_gz_bridge
ros2 run ros_gz_bridge parameter_bridge \
  /world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image@sensor_msgs/msg/Image@gz.msgs.Image

# Start the MQTT bridge
ros2 run ros2_image_mqtt_bridge image_mqtt_bridge \
  --ros-args \
  -p ros_topic:=/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image \
  -p mqtt_broker:=0.0.0.0 \
  -p mqtt_port:=1883 \
  -p mqtt_topic:=drone/camera/image \
  -p image_quality:=80 \
  -p image_scale:=0.5
```

The bridge will:
- Subscribe to Gazebo camera images via ROS2
- Compress images to JPEG format
- Encode as base64 for transmission
- Publish to MQTT topic for mobile app consumption

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



