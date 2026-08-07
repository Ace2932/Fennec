"""Launch the RL policy bridge node standalone (#289).

    ros2 launch nova_locomotion policy.launch.py policy_npz:=/path/to/nova_policy.npz

Refuses to run inference until ALL of: a preflight PASS observed on
/preflight/status, full (12/12) joint calibration, a live /imu stream, and an
explicit True on /nova/policy_enable (default False -- this node never arms
itself). See policy_node.py's module docstring for exactly what each guards
against and the refusal wording.

Bench debugging without a preflight chain up can bypass ONLY the preflight
leg of the gate (logs a loud warning, same convention as gait.launch.py):

    ros2 launch nova_locomotion policy.launch.py require_preflight:=false
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'policy_npz', default_value='',
            description='path to an exported nova_policy.npz (export_policy.py); '
                        'missing/empty refuses to start (#288 -- no checkpoint '
                        'pulled onto the robot yet)'),
        DeclareLaunchArgument(
            'require_preflight', default_value='true',
            description='refuse inference until a preflight PASS is observed '
                        'on /preflight/status; false bypasses only that leg of '
                        'the gate (bench debugging only, logs a loud warning)'),
        Node(
            package='nova_locomotion',
            executable='policy_node',
            name='nova_policy',
            output='screen',
            parameters=[{
                'policy_npz': LaunchConfiguration('policy_npz'),
                'require_preflight': LaunchConfiguration('require_preflight'),
            }],
        ),
    ])
