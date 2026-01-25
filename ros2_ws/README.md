# ROS2 Workspace — Image MQTT Bridge

This workspace contains the ROS2 package(s) for bridging Gazebo camera images to MQTT for mobile app consumption.

## ROS2 Image MQTT Bridge

The ROS2 Image MQTT Bridge enables streaming camera images from Gazebo to the mobile app via MQTT.

### Prerequisites

Install ROS2 dependencies:
```bash
sudo apt install ros-humble-cv-bridge ros-humble-ros-gz-bridge
pip3 install paho-mqtt opencv-python
```

### Build the Package

```bash
cd /home/nafea/projects/guided-tour-companion-drone/ros2_ws
colcon build --packages-select ros2_image_mqtt_bridge
source install/setup.bash
```

### Launch the Bridge

**Option 1 - Using launch file (recommended):**
```bash
ros2 launch ros2_image_mqtt_bridge image_bridge.launch.py
```

**Option 2 - Manual launch with custom parameters:**

Start ros_gz_bridge:
```bash
ros2 run ros_gz_bridge parameter_bridge \
  /world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image@sensor_msgs/msg/Image@gz.msgs.Image
```

Start the MQTT bridge:
```bash
ros2 run ros2_image_mqtt_bridge image_mqtt_bridge \
  --ros-args \
  -p ros_topic:=/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image \
  -p mqtt_broker:=0.0.0.0 \
  -p mqtt_port:=1883 \
  -p mqtt_topic:=drone/camera/image \
  -p image_quality:=80 \
  -p image_scale:=0.5
```

### What the Bridge Does

- Subscribe to Gazebo camera images via ROS2
- Compress images to JPEG format
- Encode as base64 for transmission
- Publish to MQTT topic for mobile app consumption