#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import paho.mqtt.client as mqtt
import base64
import json


class ImageMqttBridge(Node):
    """Bridge ROS2 camera images from Gazebo to MQTT for Flutter app."""

    def __init__(self):
        super().__init__('image_mqtt_bridge')
        
        # Declare parameters
        self.declare_parameter('ros_topic', '/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image')
        self.declare_parameter('mqtt_broker', '0.0.0.0')
        self.declare_parameter('mqtt_port', 1883)
        self.declare_parameter('mqtt_topic', 'drone/camera/image')
        self.declare_parameter('image_quality', 80)  # JPEG quality (0-100)
        self.declare_parameter('image_scale', 1.0)   # Scale factor for resizing (1.0 = no resize)
        
        # Get parameters
        ros_topic = self.get_parameter('ros_topic').value
        mqtt_broker = self.get_parameter('mqtt_broker').value
        mqtt_port = self.get_parameter('mqtt_port').value
        self.mqtt_topic = self.get_parameter('mqtt_topic').value
        self.image_quality = self.get_parameter('image_quality').value
        self.image_scale = self.get_parameter('image_scale').value
        
        # Initialize CV Bridge
        self.bridge = CvBridge()
        
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.get_logger().info(f'Connected to MQTT broker at {mqtt_broker}:{mqtt_port}')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to MQTT broker: {e}')
        
        # Subscribe to ROS2 image topic
        self.subscription = self.create_subscription(
            Image,
            ros_topic,
            self.image_callback,
            10
        )
        
        self.get_logger().info(f'Subscribed to ROS2 topic: {ros_topic}')
        self.get_logger().info(f'Publishing to MQTT topic: {self.mqtt_topic}')
        self.get_logger().info(f'Image quality: {self.image_quality}%, Scale: {self.image_scale}')
        
        self.frame_count = 0
    
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when MQTT connects."""
        self.get_logger().info(f'MQTT connected with reason code: {reason_code}')
    
    def on_mqtt_disconnect(self, client, userdata, reason_code, properties):
        """Callback when MQTT disconnects."""
        self.get_logger().warn(f'MQTT disconnected with reason code: {reason_code}')
    
    def image_callback(self, msg: Image):
        """Process incoming ROS2 image and publish to MQTT."""
        try:
            # Convert ROS2 Image message to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Resize image if scale factor is specified
            if self.image_scale != 1.0:
                width = int(cv_image.shape[1] * self.image_scale)
                height = int(cv_image.shape[0] * self.image_scale)
                cv_image = cv2.resize(cv_image, (width, height), interpolation=cv2.INTER_AREA)
            
            # Encode image as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality]
            result, encoded_image = cv2.imencode('.jpg', cv_image, encode_param)
            
            if not result:
                self.get_logger().error('Failed to encode image')
                return
            
            # Convert to base64 for transmission
            image_base64 = base64.b64encode(encoded_image).decode('utf-8')
            
            # Create payload with metadata
            payload = {
                'image': image_base64,
                'timestamp': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                'width': cv_image.shape[1],
                'height': cv_image.shape[0],
                'frame_id': msg.header.frame_id,
                'encoding': 'jpeg'
            }
            
            # Publish to MQTT
            self.mqtt_client.publish(
                self.mqtt_topic,
                json.dumps(payload),
                qos=0
            )
            
            self.frame_count += 1
            if self.frame_count % 30 == 0:  # Log every 30 frames
                self.get_logger().info(
                    f'Published frame {self.frame_count} '
                    f'({cv_image.shape[1]}x{cv_image.shape[0]}, '
                    f'{len(image_base64)} bytes)'
                )
                
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
    
    def destroy_node(self):
        """Cleanup when node is destroyed."""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    node = ImageMqttBridge()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
