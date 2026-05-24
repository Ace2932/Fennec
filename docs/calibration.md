# Calibration Procedures

Sensor and joint calibration for the modified NovaSM3 platform.

## Will cover
- Servo zero-position calibration (per-joint home offsets)
- Leg kinematic calibration (link lengths, joint offsets in URDF/xacro)
- IMU calibration: D456 IMU intrinsics + L2 IMU bias estimation (MPU-6050 cut per BOM v3.5)
- RealSense ↔ Unitree L2 extrinsic calibration (hand-eye or target-based)
- Arm tool-tip calibration (when arm is mounted)
- EKF tuning (`robot_localization` covariance matrices)
- Calipers — used for direct link-length measurement during leg redesign

> **Status:** placeholder — populate during Phase 2.
