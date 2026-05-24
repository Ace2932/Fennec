"""Canonical dashcam topic list.

Matches docs/notes-qol-features.md §2 "Topic set (start narrow, expand
as warranted)". Names match the firmware contract in
firmware/teensy/firmware/README.md.

Cameras + lidar are deliberately omitted — too much bandwidth for
always-on. A future dashcam_perception profile will add them.
"""

# v1 default topic set — recorded continuously to the rolling buffer.
V1_TOPICS = [
    # Joint I/O (firmware contract)
    '/joint_states',
    '/joint_commands',
    '/joint_cmd_rx_count',
    '/servo_present_mask',

    # Bus diagnostics
    '/servo_read_err_count',
    '/servo_err_timeout',
    '/servo_err_bad_frame',
    '/servo_err_servo',

    # Loop quality
    '/loop_max_us',
    '/loop_p99_us',
    '/loop_exec_max_us',
    '/loop_exec_p99_us',
    '/tick_missed_count',

    # Power telemetry
    '/power_rails',

    # Safety
    '/estop',
    '/battery_low',
    '/safety_state',

    # Identity (for incident reconstruction)
    '/firmware_version',

    # Velocity command (whatever the gait controller publishes)
    '/cmd_vel',

    # TF for replay-time URDF reconstruction
    '/tf',
    '/tf_static',
]

# Perception / camera topics — separate profile, NOT recorded by default.
# Enabled via `--profile perception` in the launch when you want them.
PERCEPTION_TOPICS = [
    '/camera/camera/color/image_raw',
    '/camera/camera/depth/image_rect_raw',
    '/camera/camera/accel/sample',
    '/camera/camera/gyro/sample',
    '/unilidar/cloud',
    '/unilidar/imu',
]

# Future topics (gated on firmware stubs landing — per
# notes-qol-features.md "Per-joint voltage + temperature are not yet
# on a topic; add them to this list when the stub lands.")
PENDING_TOPICS = [
    '/joint_voltages',    # firmware stub
    '/joint_temperatures',  # firmware stub
    '/imu/d456/data',     # once realsense2_camera launches with imu enabled
    '/imu/mpu6050/data',  # once Nano-side IMU node lands
]
