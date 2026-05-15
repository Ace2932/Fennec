# Jetson Orin Nano Super — Setup

Step-by-step bring-up for the Jetson Orin Nano Super 8GB Dev Kit (P3766).

## Will cover
- Firmware update procedure (pre-JetPack 6.x)
- JetPack 6.x microSD flash via Balena Etcher
- First-boot Ubuntu setup
- Built-in WiFi 5 (802.11ac) verification + BT presence check
- NVMe install (Crucial P3 Plus 1TB) + rootfs migration to SSD
- Power mode selection (MAXN for dev, 7W/15W for battery)
- ROS 2 Humble install (apt + source)
- librealsense2 ARM64 build + `realsense2_camera` install
- unilidar_sdk2 + `unitree_lidar_ros2` (discodyer fork) clone + colcon build
- POINT-LIO and/or RTAB-Map install
- Sanity tests: `realsense-viewer`, rviz2 with L2 cloud, ROS 2 talker/listener

> **Status:** placeholder — populate as bring-up happens.
