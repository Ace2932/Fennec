"""Display NovaSM3 in RViz with joint_state_publisher_gui sliders.

  ros2 launch nova_description display.launch.py

Loads nova.urdf.xacro via robot_state_publisher, brings up the JSP GUI so you
can sweep the 12 joints, and opens RViz. Use this to eyeball the kinematic tree
+ visuals (and to SEE where the placeholder link offsets are wrong).
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("nova_description")
    xacro_path = os.path.join(pkg, "urdf", "nova.urdf.xacro")
    robot_desc = Command(["xacro ", xacro_path])

    gui = LaunchConfiguration("gui")
    rviz_cfg = os.path.join(pkg, "rviz", "nova.rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gui",
                default_value="true",
                description="launch joint_state_publisher_gui",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                output="screen",
                parameters=[{"robot_description": robot_desc}],
            ),
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                condition=IfCondition(gui),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                output="screen",
                arguments=(["-d", rviz_cfg] if os.path.exists(rviz_cfg) else []),
            ),
        ]
    )
