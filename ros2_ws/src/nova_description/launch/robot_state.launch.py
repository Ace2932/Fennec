"""Headless robot_state_publisher for on-robot bringup.

Xacro-processes nova.urdf.xacro and runs robot_state_publisher — publishes
/robot_description + the /tf tree from /joint_states (from the servo bridge).
No GUI, no RViz (those are dev-desktop — see display.launch.py). This is what
SLAM needs for sensor->base TF, and what gives Foxglove the 3D robot model.

  ros2 launch nova_description robot_state.launch.py
  (auto-included by the nova_ops `walk` / `slam` bringup profiles)

Note: until a /joint_states source exists (servo-state node / gait controller),
the movable joints show at their default pose — the model + static TF still
publish, so Foxglove shows the robot; the joints animate once /joint_states does.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("nova_description")
    xacro_path = os.path.join(pkg, "urdf", "nova.urdf.xacro")
    robot_desc = Command(["xacro ", xacro_path])
    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                output="screen",
                parameters=[{"robot_description": robot_desc}],
            ),
        ]
    )
