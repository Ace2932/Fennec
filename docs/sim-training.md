# Simulation & Policy Training

Decision record + plan for training NovaSM3 locomotion (and later VLA) policies
in simulation, then transferring to the real robot.

> **Status:** decision captured 2026-06-06. Not yet on the active schedule —
> training work begins once `nova_description` URDF and `/joint_states` are
> stable (Phase 2 / locomotion). See [`work-schedule.md`](./work-schedule.md).

---

## Decision: MuJoCo Playground (MJX) for v1 locomotion, Isaac Lab for VLA

Two-stage plan, not either/or. The URDF and the servo home offsets from
[`../ros2_ws/src/nova_calibration`](../ros2_ws/src/nova_calibration) feed both,
so no wasted work switching later.

| Stage | Engine | Why |
|-------|--------|-----|
| **v1 — blind locomotion** | **MuJoCo Playground (MJX)** | JAX GPU-parallel, fast iteration, runs on modest GPU (laptop / Colab). MuJoCo contact model best-in-class for legged. Crucially: MuJoCo `position` actuators (kp/damping) map directly to the STS3215 position servos — no fighting a torque-control framework. Current go-to for quadruped sim-to-real. |
| **v2 — vision / VLA** | **Isaac Lab (Isaac Sim)** | photoreal rendering + camera/LiDAR sensors + massive-scale domain randomization. Worth the weight only once vision is in the loop. Needs an RTX workstation (Jetson can't host it — see [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md)). |

### Engines considered

| Engine | Verdict |
|--------|---------|
| MuJoCo Playground / MJX | ✅ chosen for v1 — best fidelity-to-effort, cheap to run, actuator match |
| Isaac Lab / Isaac Sim | ✅ deferred to VLA — photoreal + sensors + scale; RTX-only, torque-default fights position servos |
| Genesis | ⏸ watch — very fast, clean API, but young; thin sim-to-real track record |
| Brax | ❌ skip — fast pure-JAX but weaker contact model for legged |

---

## Sim-to-real: the things that actually decide transfer

The engine is the *secondary* variable. For a hobby quadruped on cheap serial
servos, transfer success is dominated by:

1. **Actuator model (biggest lever).** STS3215 = position-controlled serial
   servo, not a torque actuator. Measure its real step response — kp, damping,
   latency, max velocity, deadband — or train an actuator net from real
   `/joint_states` logs. Model this in sim or the policy won't transfer.
2. **Control-loop match.** Firmware broadcasts goals at 40 Hz with a slew limit
   (`NOVA_SLEW_MAX_DELTA=50` raw / 25 ms, see
   `firmware/teensy/firmware/src/main.cpp`). Sim control dt + slew must match.
3. **Domain randomization.** Mass, friction, motor strength, **latency**, and
   random push perturbations during training.
4. **Observation noise.** Match real sensor rates and noise — round-robin servo
   telemetry is ~17 Hz/joint, IMU from D456 + Unitree L2.
5. **Calibration consistency.** Sim URDF joint zeros + directions must equal the
   real home offsets produced by `nova_calibration`. That package is the bridge
   between sim radians and real raw 0..4095 counts.

## Deploy path (sim → robot)

```
trained policy (ONNX / TorchScript)
   → runs on Jetson
   → outputs 12 joint targets (radians)
   → convert to raw 0..4095 via ~/.nova/calibration/servo_offsets_latest.yaml
   → publish /joint_commands (sensor_msgs/JointState, position[] raw)
   → Teensy sync_writes to the STS3215 chain
```

Observation pipeline on robot: `/joint_states` (have), IMU (D456 + L2, have),
base-velocity estimate (EKF — on roadmap).

## Open questions

- Measure STS3215 actuator params on the bench vs. fit an actuator net from
  logged real motion — decide once a leg is assembled.
- Where the policy node lives: extend `nova_ops` or a new `nova_control`
  package. Lean toward a dedicated package (policy inference is on the gait
  critical path; `nova_ops` is explicitly off it).
