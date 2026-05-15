# ROS 2 Workspace — `src/`

Colcon workspace for ROS 2 Humble packages.

## Planned packages
- `nova_description` — URDF/xacro for quadruped + arm
- `nova_bringup` — launch files for full stack
- `nova_servo_bus` — micro-ROS bridge node (Jetson side). Topics paired with the Teensy firmware (see [`firmware/teensy/`](../../firmware/teensy/)). v1 uses Pattern B (Teensy is bus master); no direct FE-URT-1 driver path in this package.
- `nova_gait` — 8-phase walk gait controller
- `nova_ik` — 3-DOF-per-leg inverse kinematics solver
- `nova_perception` — RealSense + L2 fusion launch
- `nova_slam` — POINT-LIO and/or RTAB-Map configs
- `nova_nav` — Nav2 params for legged platform
- `nova_vla` — VLA policy node (Phase 4)

External clones (vendored or `vcs import`):
- `realsense-ros` (Intel)
- `unitree_lidar_ros2` (discodyer fork)
- `micro_ros_setup`

Build: `colcon build --symlink-install`
