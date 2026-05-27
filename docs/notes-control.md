# Feature Notes — Control Layer

Forward-looking notes on the *control* side of the stack — per-servo PID, gait controller architecture, body stabilization, and the diagnostics that tell you when control quality is degrading. Captured 2026-05-25. Sibling to [`notes-qol-features.md`](./notes-qol-features.md) (ops) and [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md) (viewing + auto-cal).

None of this is on the active schedule. Phase 2 is the natural pickup window — most items only matter once a real gait controller is publishing to `/joint_commands` and you can measure tracking quality.

The boundary with other docs:

- §3 of `notes-qol-features.md` covers the **safety envelope** (refuse commands that would harm the robot). This doc covers **control quality** (commands that respect the envelope but still track poorly).
- `notes-virtual-view-autocal.md` covers calibration of *sensors*. This doc adds calibration of *actuators* (PID gain tuning).

---

## Servo-level (STS3215 internals)

### 1. Per-servo PID gain management

**Goal:** the STS3215 runs an internal P/I/D position controller per servo, with gains stored in EEPROM. Today every joint runs factory defaults — fine for bench testing, suboptimal once the leg has real mass on it. A reproducible, version-controlled gain set is the foundation everything else here builds on.

**What the servo gives you:**

- Position-P, Position-I, Position-D gain registers in the EEPROM area. **Exact addresses to be confirmed against the SMS_STS register map** (around 0x15-0x18 per common Feetech docs; the firmware doesn't currently define them — see `firmware/teensy/firmware/src/feetech_protocol.h`). Add `REG_POS_KP`, `REG_POS_KI`, `REG_POS_KD` defs there once verified.
- Per-servo persistence: writes to these registers stick across power cycles. Reads work even with torque disabled.

**Scope:**

- New file `firmware/teensy/firmware/config/gains.yaml` — single source of truth, version-controlled. Schema:
  ```yaml
  defaults: { kp: 32, ki: 0, kd: 0 }
  joints:
    1:  { kp: 40, ki: 0, kd: 4 }   # hip FL — stiffer (load-bearing)
    5:  { kp: 24, ki: 0, kd: 8 }   # femur FL — softer (swing dominated)
    # ...
  ```
- New Teensy firmware path: on boot, after the servo ping sweep (already in `main.cpp::ping_servo_sweep()`), apply the gain table from a compiled-in C++ struct generated from `gains.yaml` at build time. Skip writes if the read-back already matches (EEPROM has finite write cycles — STS3215 docs cite ~100k, conservative).
- ROS 2 service `/servo_set_gain` (Teensy-side, takes joint_id, kp, ki, kd) for live tuning without a rebuild. Service writes to RAM only — operator is responsible for committing to `gains.yaml` + reflashing for persistence.

**Open questions:**

- Whether to gate the boot-time apply on a checksum, so a corrupted yaml doesn't half-write the table.
- Whether to publish `/servo_gain_state` (read-back gains per joint) at low rate (0.1 Hz) so the dashboard shows what's actually running. Lean yes; cheap insurance against "I changed the yaml but never flashed."

---

### 2. PID auto-tune routine

**Goal:** systematically derive a reasonable gain set instead of hand-tuning twelve joints. Pairs with [§1](#1-per-servo-pid-gain-management).

**Scope:**

- New ROS 2 service `nova_calibration/auto_tune_pid` (lives in the `nova_calibration` package proposed in `notes-virtual-view-autocal.md`). Operates on one joint at a time; operator picks the joint and confirms the leg is unloaded / safe to step.
- Procedure per joint (relay-feedback / Åström-Hägglund style — works without a process model):
  1. Disable I and D (set to 0). Sweep Kp until the joint *just* sustains oscillation around a setpoint when commanded a step.
  2. Record period T_u and amplitude. The classic Ziegler-Nichols rule gives Kp = 0.6 K_u, Ti = T_u / 2, Td = T_u / 8 — convert to integer register units.
  3. Apply, command a 30° step, log 5 s of `/joint_states`, report settling time + overshoot + RMS error.
  4. Operator decides keep / iterate / abort.
- All four numbers (K_u, T_u, derived Kp/Ki/Kd, measured response) get written to `~/.nova/calibration/pid-tune-<joint>-<ts>.yaml` for inspection before they land in the source-controlled `gains.yaml`.

**Open questions:**

- Auto-tuning under load vs unloaded — unloaded gives a clean response but real gait conditions differ a lot. Probably tune unloaded, sanity-check by replaying a recorded gait bag and comparing tracking error before/after.
- Relay-feedback can run away on the wrong joint (one with hard mechanical limits a few degrees from neutral). The service must reject if URDF position limits aren't loaded + the joint isn't near mid-range.

---

### 3. Per-joint following-error monitor

**Goal:** sustained `goal_position - present_position` divergence is a control-quality signal distinct from load or temperature. A high-gain servo on a binding bearing will saturate load without crossing the temperature line; following-error catches it sooner.

**Scope:**

- New node `nova_ops/following_error` subscribing to `/joint_commands` and `/joint_states`. For each joint:
  - Maintain a rolling window (1 s) of `(command - measured)`.
  - Publish `/following_error_rms` (Float32MultiArray, 12 joints) at 5 Hz.
  - Threshold per joint (from URDF or a tuned table): if window mean exceeds threshold for >500 ms, emit on `/safety_envelope_events` (the topic introduced in qol §3) with `joint=N, error=X°, kind="tracking"`.
- Threshold tuning lands in the same `gains.yaml` (per-joint `tracking_threshold_deg` field), so the gain change and the alarm move together.

**Where this differs from §3 of qol doc:** safety envelope rejects bad *commands*; following-error catches bad *execution* of acceptable commands. Both can fire on the same physical fault, but the second usually fires first.

**Open questions:**

- Whether to use absolute error or % of velocity. At high commanded velocity, larger absolute error is expected; relative measure is more stable.
- Whether to gate the alarm on commanded velocity being below a threshold (so high-speed slewing doesn't false-alarm). Lean yes.

---

### 4. Acceleration / max-velocity register tuning

**Goal:** STS3215's `REG_GOAL_ACC` (0x29) lets the servo do internal trajectory shaping between successive position commands. Today the firmware writes goals at ~40 Hz via SYNC_WRITE; setting `REG_GOAL_ACC` to a sane value lets the servo interpolate cleanly, reducing the bus's responsibility to ship fine-grained intermediate setpoints.

**Scope:**

- Extend `gains.yaml` schema with per-joint `accel` (0-254 STS units, where 0 = "as fast as possible") and `max_velocity` (0-1023).
- Same boot-time apply as [§1](#1-per-servo-pid-gain-management).
- Conservative starting point: `accel: 40` (≈ smooth, doesn't lurch); revisit per-joint after first walk.

**Tradeoff:**

- Higher accel → more responsive, more jerk, more bus load (the servo finishes moves between bus updates, then sits idle).
- Lower accel → smoother motion, slower response to gait phase transitions, but compensates for sparse setpoint streams.

Pairs with [§6](#6-trajectory-smoother-in-the-gait-controller) below — they solve the same problem at different layers; do one or the other, not both at max settings.

---

## Gait-controller-level (Jetson)

### 5. Per-gait-phase gain profiles

**Goal:** a leg in **stance** (supporting the robot) wants high Kp / low compliance — anything else and the body sinks under its own weight. A leg in **swing** (clearing forward) wants the opposite — soft, so an unexpected foot contact doesn't fight the gait. Today there's one gain set for all phases.

**Scope:**

- Two gain sets in `gains.yaml`:
  ```yaml
  joints:
    5:
      stance: { kp: 32, ki: 0, kd: 8 }
      swing:  { kp: 16, ki: 0, kd: 12 }
  ```
- Gait controller publishes `/joint_gain_phase` (Int8MultiArray, 12 entries, one of `STANCE | SWING | TRANSITION`) at gait-state-machine rate (50-100 Hz).
- Teensy subscribes; on phase change, issues a `WRITE_DATA` to the relevant Kp/Ki/Kd registers (RAM, not EEPROM — these are runtime swaps, must not burn through write cycles).
- TRANSITION = blend; ramp gains over ~50 ms to avoid stepping the controller.

**Why this lives partly on Teensy:** the gain write is a bus transaction. Doing it from Jetson would compete with the gait-command stream. Letting Teensy own the swap keeps the bus serialized cleanly.

**Open questions:**

- Whether to use RAM-only writes (lost on servo power cycle) or also persist to EEPROM occasionally. Lean RAM-only; on every boot the firmware applies the stance defaults from §1 anyway.
- Phase-detection robustness: if the gait state machine is wrong about which leg is in stance, gain swap is wrong too. Maybe cross-check against measured foot contact (load > threshold).

---

### 6. Trajectory smoother between waypoints

**Goal:** IK gives discrete joint setpoints per gait tick. Sending them raw produces step-shaped reference for the servo PID to chase, which spikes following error every tick. Interpolating between waypoints produces a continuous reference, much easier to track.

**Scope:**

- New `nova_gait/trajectory_smoother` node sitting between the IK solver and `/joint_commands`. Subscribes to `/joint_waypoints` (raw IK output @ 50-100 Hz), publishes `/joint_commands` (smoothed @ 200 Hz).
- Cubic spline between consecutive waypoints, with velocity at waypoint boundaries matched. Quintic if jerk matters more (Phase 3 stair-climbing).
- Compute cost negligible — twelve joints × a polynomial evaluation @ 200 Hz is microseconds on Jetson.
- Bonus: smoother output means [§4](#4-acceleration--max-velocity-register-tuning) can run with higher accel (since the servo gets continuous targets, internal shaping isn't doing the heavy lifting).

**Open questions:**

- Whether to do the smoothing on Teensy instead (it already runs at 200 Hz, sees `/joint_commands` directly). Pros: fewer round-trips. Cons: Teensy doesn't see future waypoints, needs lookahead protocol. Lean Jetson-side for v1.
- Whether to also smooth `/cmd_vel` upstream of IK. Probably yes if teleop is jerky — but solve IK→servo path first.

---

### 7. Gravity-compensation feedforward

**Goal:** the femur/tibia servos are constantly fighting gravity in static stance — Kp alone holds the joint roughly in place, but with steady-state error proportional to gravity torque. Adding a feedforward term (compute expected gravity torque from current joint angles → add to commanded position as a bias) reduces steady-state error to near zero.

**STS3215 reality:** the servo doesn't expose direct torque control. The hack is to bias the **position setpoint** by an amount that produces the desired correcting torque under the current Kp. Less clean than a true torque-mode servo (Dynamixel X-series, e.g.) but it works.

**Scope:**

- Compute gravity vector in body frame from IMU (already present in EKF output).
- For each joint, project gravity onto the joint's lever arm using URDF link masses + CoM positions. Pre-compute the Jacobian transpose at IK time (≈ 100 µs per leg).
- Add the resulting position bias to the gait controller's commanded position before publishing.

**Phase:** 2+, not before the gait controller has a stable IK path.

**Open questions:**

- Mass estimates from CAD vs. actual measured mass. CAD gets you started; refine after a first walk if static lean is visible.
- Whether to gate on stance phase only (don't compensate during swing — swing leg's gravity is what carries it forward).

---

### 8. Control architecture document

**Goal:** there's currently no written explanation of the `/cmd_vel → gait phase → leg targets → 3-DOF IK → /joint_commands` path. Once code lands, this is the doc that saves the next agent 2 hours of code-spelunking.

**Scope:**

- New `docs/control-architecture.md` — block diagram + topic-by-topic data flow + node responsibility list. Same format as `README.md`'s "Software Architecture" section, but specifically for the locomotion control path.
- Sections to cover:
  - Reference frame conventions (body, world, foot)
  - `/cmd_vel` interpretation (m/s body-frame X-Y + yaw)
  - 8-phase walk gait state machine (already mentioned in README) — phase timing, stride length param, body height param
  - IK solver — analytic 3-DOF closed-form per leg (reference: mogar/spot_micro); singular configurations + how the controller handles them
  - Output rate, units, frame of `/joint_commands`
  - How [§5](#5-per-gait-phase-gain-profiles), [§6](#6-trajectory-smoother-between-waypoints), [§7](#7-gravity-compensation-feedforward) plug in
- Update once per significant rework. **Write it the same week as the first walking gait commit, not before** — pre-implementation architecture docs rot fastest.

---

## Body-level

### 9. IMU-feedback body stabilization

**Goal:** referenced in README Phase 2 ("MPU-6050 body stabilization feedback"). Closing the loop: tilt sensed by IMU → adjust per-leg hip pitch / roll offsets to keep torso level. Lets the robot walk over uneven ground without falling.

**Scope:**

- New node `nova_gait/body_stabilizer`. Subscribes to fused IMU output from `robot_localization` (not raw IMU — fused is denoised), publishes a small additive offset onto each leg's hip/femur targets.
- Gain pair: `Kp_roll`, `Kp_pitch`, both small (~0.5 rad/rad). Empirically tuned; start very conservative.
- Bandwidth: the loop has to run fast enough to react before the robot falls but slow enough not to chase IMU noise. 50 Hz is a sane start.

**Open questions:**

- Whether to gate on stance (don't stabilize via a swinging leg). Yes.
- Whether to integrate with [§7](#7-gravity-compensation-feedforward) (gravity comp uses gravity direction; stabilizer outputs adjust posture vs that direction — same math, different intent). Probably keep separate for clarity, merge if it makes sense once both are running.

---

### 10. CoM-shift compensation for arm

**Goal:** README Open Decision row 12, Phase 4 — arm extension + payload mass shifts the center of mass outside the support polygon, robot falls. Gait controller needs the arm-state input to pre-shift body posture before the CoM moves.

**Scope:** see README row 12 — fully Phase 4 work, captured here to anchor it in the control taxonomy. Lives in the same `nova_gait/body_stabilizer` node as [§9](#9-imu-feedback-body-stabilization); CoM offset becomes another input alongside IMU tilt.

---

## Diagnostics

### 11. PID step-response harness

**Goal:** quick visual diagnostic when a joint *feels* wrong — sluggish, oscillating, etc. — without needing to run an auto-tune.

**Scope:**

- CLI tool `ros2 run nova_ops pid_step --joint=5 --step-deg=30` does:
  1. Confirms E-stop disengaged and joint within URDF limits.
  2. Records `/joint_states` for that joint at 200 Hz.
  3. Sends one step command.
  4. After 2 s, computes rise time, settling time, % overshoot, RMS error.
  5. Writes a `.png` plot + a row in `~/.nova/pid-steps/<joint>-<ts>.csv`.
- Operator stares at the plot.
- Same plumbing the auto-tune routine ([§2](#2-pid-auto-tune-routine)) uses — share code.

---

### 12. Tracking-quality metric on the dashboard

**Goal:** per-joint RMS following error logged per gait cycle. Drifts upward over weeks = something's wearing. Drifts upward in one session = thermal effect or developing fault.

**Scope:**

- The `/following_error_rms` topic from [§3](#3-per-joint-following-error-monitor) is already there. Add to the §7 telemetry CSV (qol doc) and the Grafana dashboard if/when v2 telemetry happens.
- Annotated with `gait_cycle_id` so per-cycle comparison is straightforward.

---

## Suggested rollout order

Ordered by "needed before the next item works."

1. **§1 PID gain management** — foundational. Without the yaml + boot-time apply path, every subsequent item is editing live gains by hand.
2. **§11 step-response harness** — even before auto-tune, the visual diagnostic is what tells you whether a manual tweak helped. Same code base as §2 so build it first.
3. **§2 auto-tune** — once §11 plots are in hand, automating the tune is incremental.
4. **§3 following-error monitor** — sits in front of any walk attempt; tells you whether tracking is acceptable.
5. **§6 trajectory smoother** — pairs with the first real gait commit. Big quality win for small effort.
6. **§4 servo accel register** — tune after §6 lands; values depend on whether the smoother is doing the work or the servo is.
7. **§5 per-phase gains** — once stance / swing detection is solid (mid-Phase 2).
8. **§8 control architecture doc** — write it the same week the first walking gait commits.
9. **§9 IMU stabilization** — Phase 2 second half, after stand/sit/walk are solid.
10. **§7 gravity-comp feedforward** — Phase 2-3 polish; ROI depends on whether static lean is a problem.
11. **§12 tracking dashboard panel** — Phase 2-3 alongside the §7-telemetry-doc work.
12. **§10 CoM compensation** — Phase 4, with the arm install.

---

## Tie-in to other notes

- [`notes-qol-features.md`](./notes-qol-features.md) §3 — *safety* envelope (rejects unsafe commands). This doc's §3 — *quality* envelope (catches poor tracking of safe commands). Different alarms, different fixes, both publish on `/safety_envelope_events`.
- [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md) §2 — *sensor* calibration. This doc's §1-§2 — *actuator* calibration. Same `nova_calibration` package, same `~/.nova/calibration/` storage convention.
- README `Build Roadmap` Phase 2 — most of this doc lands there. The auto-tune (§2), step harness (§11), gain yaml (§1) are good Phase 1-end deliverables since they don't need a working gait.

---

> **Status:** notes only, not on the active schedule. Promote items to checklist entries when Phase 2 starts.
