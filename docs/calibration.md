# Calibration Procedures

Sensor and joint calibration for the modified NovaSM3 platform.

## Will cover
- Servo zero-position calibration (per-joint home offsets) — **auto path scaffolded** in `ros2_ws/src/nova_calibration` (hard-stop home auto-detect via STS3215 load feedback). Needs per-joint `search_dir` / `stop_to_home_raw` filled from CAD before first run.
- Leg kinematic calibration (link lengths, joint offsets in URDF/xacro)
- IMU calibration: D456 IMU intrinsics + L2 IMU bias estimation (MPU-6050 cut per BOM v3.5)
- RealSense ↔ Unitree L2 extrinsic calibration (hand-eye or target-based)
- Arm tool-tip calibration (when arm is mounted)
- EKF tuning (`robot_localization` covariance matrices)
- Calipers — used for direct link-length measurement during leg redesign

> **Status:** placeholder — populate during Phase 2.
