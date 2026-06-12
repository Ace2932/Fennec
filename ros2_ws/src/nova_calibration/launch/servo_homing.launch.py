"""Launch the servo home-finding node.

    ros2 launch nova_calibration servo_homing.launch.py

Then trigger a sweep:

    ros2 service call /nova_servo_homing/calibrate_homes std_srvs/srv/Trigger

Watch progress:

    ros2 topic echo /nova_calibration_status
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nova_calibration',
            executable='servo_homing_node',
            name='nova_servo_homing',
            output='screen',
        ),
    ])
