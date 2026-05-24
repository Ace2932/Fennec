"""Standalone launch for the dashcam node.

Usage:
    ros2 launch nova_ops dashcam.launch.py

Override retention:
    ros2 launch nova_ops dashcam.launch.py retention_mb:=10240
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'retention_mb', default_value='2048',
            description='rolling buffer cap in MB (default 2 GB)'),
        DeclareLaunchArgument(
            'max_bag_seconds', default_value='60',
            description='bag split duration'),

        Node(
            package='nova_ops',
            executable='dashcam_node',
            name='dashcam',
            output='screen',
            parameters=[{
                'retention_mb': LaunchConfiguration('retention_mb'),
                'max_bag_seconds': LaunchConfiguration('max_bag_seconds'),
            }],
            remappings=[
                ('~/freeze', '/dashcam/freeze'),
            ],
        ),
    ])
