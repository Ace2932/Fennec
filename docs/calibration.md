# Calibration Procedures

Sensor and joint calibration for the modified NovaSM3 platform.

## Servo zero-position calibration — REAL PROCEDURE

Everything below is read out of the code it describes, not written from memory;
each step names the file that implements it.

**Status of the config the old text warned about.** `servo_homing/config.py` no
longer needs filling from CAD for most joints: all **8 hfe/kfe** entries carry
real hard stops and `placeholder=False`. The **4 haa** ids (1, 4, 7, 10) are
still `placeholder=True`, each with a `PLACEHOLDER_REASON` — and that is not a
value anyone can look up. `HAA_INBOARD_SIGN` is the inboard direction *in the
servo command frame*, which is unknowable until a real servo is watched moving.
Step 3 is how it becomes known. **Writing it by hand does not count (#161):**
the recorded confirmation is what unlocks the window, not the number.

### 1. Bring up the bench profile

```
ros2 launch nova_ops bringup.launch.py profile:=bench
```

`bench` starts `firmware_tables` and requires a preflight PASS. That node is
what publishes `joint_limits` / `hfe_envelope` / `limp_pose` to the Teensy —
until it has, the firmware's per-joint clamp is wide open (0..4095) and the
#145 controlled limp falls back to instant torque release.

### 2. Home the 8 hfe/kfe joints

```
ros2 launch nova_calibration servo_homing.launch.py
```

Drives each joint to its self-collision hard stop under STS3215 load feedback
and records the offset. Joints still marked `placeholder=True` are **skipped**,
so the 4 haa are untouched here — if you see *"done — 0 joints homed
(all skipped/failed)"* (`servo_homing/node.py:167`), the config is not what this
document describes and you should stop.

Writes `~/.nova/calibration/servo_offsets_<stamp>.yaml` and refreshes the
`servo_offsets_latest.yaml` symlink (`servo_homing/storage.py`).

### 3. Confirm each haa sign — ON HARDWARE, ONE LEG AT A TIME

```
ros2 run nova_calibration confirm_haa_sign \
    --joint FL --observed inboard \
    --assembly 'leg_v6 rev2 / FL / servo 1'
```

- `--joint` — `FL/FR/RL/RR` or the haa bus id (1/4/7/10)
- `--observed` — **which way the FOOT actually swung, as you watched it**
- `--assembly` — which physical leg/servo this was seen on; it is recorded
- `--probe-deg` — defaults to `MAX_PROBE_DEG`, which is **half** the runtime
  ±15° clamp. The tool **refuses** a larger value rather than silently
  clamping it.
- `--reverse` — probe toward decreasing raw counts instead of increasing

Repeat for all four. Each run appends through the same write path as step 2.

**Why haa is the one that carries hardware risk:** inboard tucks a leg under the
belly where the LiPo sits. That is why the runtime clamp is a conservative
symmetric ±15° until confirmation, and why the probe is bounded to half of it.

### 4. What unlocks, and how to check

`confirmed_haa_sign()` (`nova_ops/safety_envelope/limits.py:173`) reads the
artifact; `load_default_limits()` builds the per-bus-ID table from it. Once all
four are recorded:

- the haa window widens from symmetric ±15° to the asymmetric
  15-inboard / 40-outboard envelope,
- `choreo.stand.pose_for('sit'|'down')` stops raising and returns the splay
  poses (they need ~40° outboard),
- `safety_envelope.limp_pose.build_limp_pose_data()` stops returning `None`, so
  the Teensy finally receives a real `limp_pose` table and the #145 controlled
  limp arms instead of falling back to instant release.

Quick check without moving anything:

```
python -c "from nova_ops.safety_envelope.calibration_io import read_calibration; \
           from nova_ops.safety_envelope.limp_pose import build_limp_pose_data; \
           print(build_limp_pose_data(read_calibration()))"
```

`read_calibration()` defaults to `DEFAULT_CALIBRATION_PATH`, the same artifact
`tables_node` reads (`calibration_io.py:36,124`).

`None` means at least one leg is still unconfirmed or uncalibrated — that is the
fail-safe, not a bug.

## Will cover
- Leg kinematic calibration (link lengths, joint offsets in URDF/xacro)
- IMU calibration: D456 IMU intrinsics + L2 IMU bias estimation (MPU-6050 cut per BOM v3.5)
- RealSense ↔ Unitree L2 extrinsic calibration (hand-eye or target-based)
- Arm tool-tip calibration (when arm is mounted)
- EKF tuning (`robot_localization` covariance matrices)
- Calipers — used for direct link-length measurement during leg redesign

> **Status:** placeholder — populate during Phase 2.
