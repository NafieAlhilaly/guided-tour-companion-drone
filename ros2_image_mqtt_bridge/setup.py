from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'ros2_image_mqtt_bridge'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Nafea',
    maintainer_email='nafea@todo.com',
    description='ROS2 package to bridge Gazebo camera images to MQTT for Flutter app',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'image_mqtt_bridge = ros2_image_mqtt_bridge.image_mqtt_bridge_node:main',
        ],
    },
)
