"""Standalone launch for the preflight check service node.

Usage:
    ros2 launch nova_ops preflight.launch.py

Or compose into a larger bringup file by including this launch.
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nova_ops',
            executable='preflight_node',
            name='preflight',
            output='screen',
            # Remap the relative service name so users can `ros2 service call
            # /preflight/run` without typing the node name.
            remappings=[
                ('~/run', '/preflight/run'),
                ('~/status', '/preflight/status'),
            ],
        ),
    ])
