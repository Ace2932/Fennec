"""Launch the gait controller node standalone.

    ros2 launch nova_locomotion gait.launch.py

gait_node refuses to leave idle (no motion commands published) until it
observes a preflight PASS on /preflight/status — start that first:

    ros2 launch nova_ops preflight.launch.py

Bench debugging without a Teensy/preflight chain up can bypass the gate
(logs a loud warning on the node):

    ros2 launch nova_locomotion gait.launch.py require_preflight:=false
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'require_preflight', default_value='true',
            description='refuse motion modes until a preflight PASS is observed '
                        'on /preflight/status; false bypasses the gate '
                        '(bench debugging only, logs a loud warning)'),
        Node(
            package='nova_locomotion',
            executable='gait_node',
            name='gait_node',
            output='screen',
            parameters=[{'require_preflight': LaunchConfiguration('require_preflight')}],
        ),
    ])
