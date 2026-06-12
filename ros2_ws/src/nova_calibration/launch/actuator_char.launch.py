"""Launch the STS3215 actuator characterization node.

    ros2 launch nova_calibration actuator_char.launch.py joint_id:=1 amplitude_raw:=200

Trigger a run (leg OFF the ground, one joint):

    ros2 service call /nova_actuator_char/characterize std_srvs/srv/Trigger

CSV lands in ~/.nova/calibration/actuator/. Fit offline:

    python3 -c "import csv; from nova_calibration.actuator_char.fit import fit_step; \
        rows=[(float(a),int(b),int(c),int(d),int(e)) for a,b,c,d,e in \
        list(csv.reader(open('PATH')))[1:]]; print(fit_step(rows))"
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('joint_id', default_value='1'),
        DeclareLaunchArgument('amplitude_raw', default_value='200'),
        DeclareLaunchArgument('dwell_s', default_value='1.5'),
        DeclareLaunchArgument('cycles', default_value='3'),
    ]
    return LaunchDescription(args + [
        Node(
            package='nova_calibration',
            executable='actuator_char_node',
            name='nova_actuator_char',
            output='screen',
            parameters=[{
                'joint_id': LaunchConfiguration('joint_id'),
                'amplitude_raw': LaunchConfiguration('amplitude_raw'),
                'dwell_s': LaunchConfiguration('dwell_s'),
                'cycles': LaunchConfiguration('cycles'),
            }],
        ),
    ])
