# !/bin/bash

# Using ros_gz_bridge to connect ROS2 and Gazebo
GZ_IMAGE_TOPIC="/world/forest/model/x500_depth_0/link/camera_link/sensor/IMX214/image"
ros2 run ros_gz_bridge parameter_bridge $GZ_IMAGE_TOPIC@sensor_msgs/msg/Image@gz.msgs.Image