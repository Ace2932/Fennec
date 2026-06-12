# nova_calibration

Calibration routines for NovaSM3. v1 ships **servo home auto-detect** via
mechanical hard-stop probing using STS3215 load feedback. Sibling of
`nova_ops`; nothing here is on the gait critical path.

## What it does

Drives each leg joint slowly toward a known mechanical hard stop, detects the
stop from the servo's load (`/joint_states.effort`), records the stop position,
and computes the logical home offset:

    home_raw = stop_pos_raw - search_dir * stop_to_home_raw

Offsets persist to `~/.nova/calibration/servo_offsets_<stamp>.yaml` with a
stable `servo_offsets_latest.yaml` symlink the gait layer loads on start.

## Wire contract (Teensy firmware)

| Topic | Type | Use |
|-------|------|-----|
| `/joint_states` (sub) | `sensor_msgs/JointState` | `position[i]`=raw 0..4095, `effort[i]`=raw load 0..1000 (servo id=i+1) |
| `/safety_state` (sub) | `std_msgs/Int32` | `0`=NORMAL; probe only runs when NORMAL |
| `/joint_commands` (pub) | `sensor_msgs/JointState` | `position[i]`=raw goal, all 12 every msg |

## Run

```bash
ros2 launch nova_calibration servo_homing.launch.py
# in another shell:
ros2 service call /nova_servo_homing/calibrate_homes std_srvs/srv/Trigger
ros2 topic echo /nova_calibration_status
```

## ⚠️ Before first real run

1. **Fill `servo_homing/config.py` from CAD.** Every joint ships
   `placeholder=True` and is **skipped** until you set its real `search_dir`
   (which stop to push) and `stop_to_home_raw` (CAD stop→home, raw counts).
   Set `placeholder=False` per joint once measured. This is deliberate — never
   drive a joint into a stop with a guessed direction.
2. **Gear safety.** There is *no torque-limit passthrough* yet (firmware is a
   raw bus driver). The only protection is the low `load_threshold`, the
   `load_ceiling` hard abort, and the slow host step rate in
   `hard_stop.HardStopParams`. Keep them conservative; start with the leg off
   the ground and one joint at a time. A future firmware register-write
   passthrough (STS3215 torque limit = reg 0x30) would let us cap torque in
   hardware — see `docs/notes-virtual-view-autocal.md`.
3. **Travel budget.** A joint farther from its stop than
   `step_raw * tick_hz * timeout_s` (default ~960 raw ≈ 84°) will TIMEOUT.
   Raise `timeout_s` or start nearer the stop.

## Actuator characterization (for sim-to-real)

Separate tool that drives a step on one joint through the live firmware path
and logs the response, to fit the STS3215 actuator model the sim needs (see
[`docs/sim-training.md`](../../../docs/sim-training.md) — actuator model is the
#1 sim-to-real lever). Runs through ROS on purpose: captures the *deployed*
path (Teensy 40 Hz + slew + ~17 Hz telemetry), not the bare servo.

```bash
ros2 launch nova_calibration actuator_char.launch.py joint_id:=1 amplitude_raw:=200
ros2 service call /nova_actuator_char/characterize std_srvs/srv/Trigger
# CSV -> ~/.nova/calibration/actuator/ ; fit with actuator_char.fit.fit_step()
```

Outputs latency, max velocity, first-order time constant, steady gain — the
parameters for a MuJoCo `position` actuator + velocity limit + lag.

## Layout

```
servo_homing/
  config.py     per-joint search_dir + stop_to_home_raw (FILL FROM CAD)
  hard_stop.py  pure algorithm (no ROS) — unit-tested in test/
  node.py       ROS node: ~/calibrate_homes Trigger service + sweep worker
  storage.py    YAML persist to ~/.nova/calibration/
actuator_char/
  fit.py        pure step-response fitter (no ROS) — unit-tested in test/
  node.py       ROS node: ~/characterize Trigger service + CSV logger
```

Tests: `pytest test/` (pure logic, no hardware) — `test_hard_stop.py` +
`test_fit.py`.
