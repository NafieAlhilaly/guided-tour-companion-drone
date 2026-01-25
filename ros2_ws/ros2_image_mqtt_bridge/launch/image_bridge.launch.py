#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Launch file to start the image bridge with ros_gz_bridge."""
    
    # Declare launch arguments
    ros_topic_arg = DeclareLaunchArgument(
        'ros_topic',
        default_value='/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image',
        description='ROS2 topic to subscribe to'
    )
    
    gz_topic_arg = DeclareLaunchArgument(
        'gz_topic',
        default_value='/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image',
        description='Gazebo topic to bridge from'
    )
    
    mqtt_broker_arg = DeclareLaunchArgument(
        'mqtt_broker',
        default_value='0.0.0.0',
        description='MQTT broker address'
    )
    
    mqtt_port_arg = DeclareLaunchArgument(
        'mqtt_port',
        default_value='1883',
        description='MQTT broker port'
    )
    
    mqtt_topic_arg = DeclareLaunchArgument(
        'mqtt_topic',
        default_value='drone/camera/image',
        description='MQTT topic to publish to'
    )
    
    image_quality_arg = DeclareLaunchArgument(
        'image_quality',
        default_value='80',
        description='JPEG compression quality (0-100)'
    )
    
    image_scale_arg = DeclareLaunchArgument(
        'image_scale',
        default_value='0.5',
        description='Image scale factor (e.g., 0.5 for half size)'
    )
    
    # Launch ros_gz_bridge to connect Gazebo and ROS2
    gz_bridge = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
            [LaunchConfiguration('gz_topic'), '@sensor_msgs/msg/Image@gz.msgs.Image']
        ],
        output='screen',
        name='gz_image_bridge'
    )
    
    # Launch the image MQTT bridge node
    image_mqtt_node = Node(
        package='ros2_image_mqtt_bridge',
        executable='image_mqtt_bridge',
        name='image_mqtt_bridge',
        output='screen',
        parameters=[{
            'ros_topic': LaunchConfiguration('ros_topic'),
            'mqtt_broker': LaunchConfiguration('mqtt_broker'),
            'mqtt_port': LaunchConfiguration('mqtt_port'),
            'mqtt_topic': LaunchConfiguration('mqtt_topic'),
            'image_quality': LaunchConfiguration('image_quality'),
            'image_scale': LaunchConfiguration('image_scale'),
        }]
    )
    
    return LaunchDescription([
        ros_topic_arg,
        gz_topic_arg,
        mqtt_broker_arg,
        mqtt_port_arg,
        mqtt_topic_arg,
        image_quality_arg,
        image_scale_arg,
        gz_bridge,
        image_mqtt_node,
    ])
