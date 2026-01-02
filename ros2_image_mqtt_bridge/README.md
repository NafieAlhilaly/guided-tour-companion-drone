# ROS2 Image MQTT Bridge

Bridge Gazebo camera images to MQTT for Flutter app visualization.

## Features

- Subscribes to ROS2 image topics from Gazebo via `ros_gz_bridge`
- Compresses images to JPEG format
- Encodes images as base64 for easy transmission
- Publishes to MQTT with metadata (timestamp, dimensions, etc.)
- Configurable image quality and scaling for bandwidth optimization

## Dependencies

```bash
sudo apt install ros-humble-cv-bridge ros-humble-ros-gz-bridge
pip3 install paho-mqtt opencv-python
```

## Build

```bash
cd /home/nafea/projects/test_mavsdk
colcon build --packages-select ros2_image_mqtt_bridge
source install/setup.bash
```

## Usage

### Option 1: Launch file (recommended)
```bash
ros2 launch ros2_image_mqtt_bridge image_bridge.launch.py
```

### Option 2: Manual with custom parameters
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

## Parameters

- `ros_topic`: ROS2 image topic to subscribe to
- `mqtt_broker`: MQTT broker address (default: 0.0.0.0)
- `mqtt_port`: MQTT broker port (default: 1883)
- `mqtt_topic`: MQTT topic to publish images (default: drone/camera/image)
- `image_quality`: JPEG quality 0-100 (default: 80)
- `image_scale`: Image resize factor (default: 0.5 = half size)

## MQTT Message Format

```json
{
  "image": "<base64_encoded_jpeg>",
  "timestamp": 1704200000.123,
  "width": 640,
  "height": 480,
  "frame_id": "camera_link",
  "encoding": "jpeg"
}
```

## Flutter Integration

In your Flutter app:

```dart
import 'package:mqtt_client/mqtt_client.dart';
import 'dart:convert';

// Subscribe to MQTT topic
final client = MqttClient('broker_address', 'flutter_client');
await client.connect();

client.updates!.listen((List<MqttReceivedMessage<MqttMessage>> messages) {
  final message = messages[0].payload as MqttPublishMessage;
  final payload = utf8.decode(message.payload.message);
  final data = jsonDecode(payload);
  
  // Decode base64 image
  final bytes = base64Decode(data['image']);
  
  // Display in Image widget
  Image.memory(bytes);
});

client.subscribe('drone/camera/image', MqttQos.atMostOnce);
```

## Performance Tips

- Reduce `image_scale` (e.g., 0.3-0.5) for lower bandwidth
- Lower `image_quality` (e.g., 60-70) for faster transmission
- Use QoS 0 for real-time streaming (some frame loss acceptable)
- Consider throttling frame rate if needed
