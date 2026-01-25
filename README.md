# Guided Tour Companion Drone

<img width="1143" height="2048" alt="Untitled design" src="https://github.com/user-attachments/assets/d8fc3c2d-a38a-4187-8391-72cbd982f82d" />

This project simulates a companion drone system for guided tours, enabling tour guides to ensure group safety and maintain regulation-compliant experiences.

## Project Structure

- **companion_drone/** - Python mission logic, drone control scripts, and utilities
- **ros2_ws/** - ROS2 workspace with image-to-MQTT bridge package
- **scripts/** - Helper scripts for deployment and testing
- **buildroot-external/** - For building companion computer Embedded Linux image.

## Quick Links

- [Companion Mobile App](https://github.com/NafieAlhilaly/guided-tour-companion-app)
- [Ultralytics Pose Service](https://github.com/NafieAlhilaly/ultralytics-pose-service)

## Getting Started

For detailed setup and usage instructions, see:
- Python mission setup: [companion_drone/README.md](companion_drone/README.md)
- ROS2 bridge setup: [ros2_ws/README.md](ros2_ws/README.md)

## Features

- **Safety Monitoring**: Continuously monitor group safety and detect regulation violations
- **Medical Supply Delivery**: Autonomously deliver medical supplies from designated locations to the tour group
- **Real-time Control**: Remote monitoring and control via mobile application
- **Camera Streaming**: Live video feed from drone to mobile app via MQTT

## Demo Videos

### jMAVSim Simulation
Testing core drone functionality including takeoff and group monitoring (orbit pattern):

https://github.com/user-attachments/assets/85c33211-5759-46ed-bed0-d3d1d5159017

### Gazebo Simulation
Comprehensive testing of all drone capabilities including takeoff, group monitoring (orbit pattern), and medical supply delivery missions:

https://github.com/user-attachments/assets/53e6caaf-3b80-4540-befc-173b95956abb

https://github.com/user-attachments/assets/efd97c0b-e035-4b7b-aa13-62483de3fde4



