# nova_locomotion

Phase-2 locomotion groundwork: **analytic 3-DOF leg kinematics + a scripted trot
gait**, as pure hardware-independent math (tested without ROS, like
`nova_calibration`). This is the scripted baseline; the MJX sim-learned policy is
a separate Phase-2 path.

## Modules
- `kinematics/leg_ik.py` — `forward_kinematics`, `inverse_kinematics`,
  `within_limits`, `LegParams`. FK is the reference; IK is the closed-form
  inverse, validated by FK∘IK round-trips. Chain matches `nova_description`
  (HAA roll → hip offset → HFE pitch → femur → KFE pitch → tibia → foot).
- `gait/trot.py` — `foot_target(phase, leg, TrotParams)` / `all_feet(phase)`.
  Diagonal trot (FL+RR vs FR+RL), stance slide + half-sine swing arch.

## Tests (pure, run anywhere)
```bash
cd ros2_ws/src/nova_locomotion && PYTHONPATH=. python -m pytest test/ -q
```
- `test_leg_kinematics.py` — neutral pose, FK∘IK round-trip grid (125 cases),
  exact angle recovery on normal poses, unreachable guards, workspace reach.
- `test_trot.py` — periodicity, stance/swing, diagonal sync, swing apex, stride
  span, and **every gait foot target over a full cycle is IK-reachable + within
  joint limits**.

## Modules (added 2026-07-06, clean-movement lane)
- `choreo/stand.py` — min-jerk stand/sit sequencer: keyframes (lie/crouch/
  stand, feet under hips) -> joint-space quintic blends, zero vel+acc at
  ends; `stand_up(start_pose=...)` accepts the real current pose (post-
  E-stop recovery never assumes a keyframe). 50 Hz output.
- `KNEE_FORWARD` (leg_ik) — **TRANSLATED, corrected 2026-07-25**: every
  knee bends BACKWARD (all four `False`). The robot as built is the
  translated layout and the MJX sim always matched it (`sim/nova_mjx`
  `DEFAULT_POSE` kfe −1.2 on all four). The previous "X-CONFIG decided
  2026-07-06" value `{FL: True, FR: True, RL: False, RR: False}` was
  never built and commanded the FRONT knees FORWARD — `gait_pose` would
  have driven the front legs to a mirrored stance on first stand.
  Verified: `sim/nova_mjx/render_knee_configs.py`.
  ⚠ **Two open consequences (see docs/knee-config-analysis.md):**
  (1) `within_limits` flips the hfe window whenever `knee_forward` is
  False, so it now flips for ALL legs — correct for the REAR pair (whose
  toward-trunk fold is negative canonical) but WRONG for the FRONT pair,
  which needs the unflipped `[hfe_min, hfe_max]`. `solve_side`'s
  FRONT_LEGS clamp is the runtime backstop and does apply the right
  bound, so this bites gait-quality tests, not hardware.
  (2) the `lie`/`crouch` choreo keyframes need front hfe +61°/+57°,
  past the +50° riser-skirt cap — `test_keyframe_feet_under_hips` fails
  on this and is left failing deliberately.

## Modules (added 2026-07-06, pre-hardware locomotion work package)
Roadmap: `docs/roadmap-trot-balance.md`. All pure-math, no rclpy in tests.
- `kinematics/body_pose.py` — body-pose IK (stage 1.2): BodyPose(rpy+dxyz)
  + world foot anchors -> canonical hip-frame targets; `neutral_anchors()`
  reproduces the trot/choreo stance. Owns the body->canonical y-mirror
  (frame); solve_side still owns the joint mirror.
- `gait/crawl.py` — statically-stable crawl (stage 2): duty 0.8, lateral-
  sequence order FL->RL->FR->RR, at most one leg in swing; `body_shift()`
  min-jerk CoM pre-shift, composes through body_pose.
- `balance/raibert.py` — Raibert touchdown stepper + attitude PD deltas
  (stage 4.3/4.4) as pure logic; max_step + reachable-disc clamps built in.
- `gait/backlash.py` — half-backlash bias with reversal hysteresis (stage
  3.3); default 0.5 deg table MEASURE-AT-STAGE-1.
- `controller.py` — gait-node core (stage 1.1): mode machine (idle/
  stand_up/sit/crawl/trot) -> solve_side -> bus-ID ordering (nova_ops
  joint_map) -> backlash comp. `node.py` = the thin rclpy glue
  (`ros2 run nova_locomotion gait_node`; radians end-to-end,
  counts_per_rad/home_offset identity params WIRE-AT-CALIBRATION).
- `tools/trot_metrics.py` — stage-3 tuning score (lower = better) +
  CSV CLI: `python -m nova_locomotion.tools.trot_metrics run.csv`.

## Modules (added 2026-08-06, sim->real policy bridge, #289)
- `policy_runner.py` — moved here verbatim from `sim/nova_mjx/deploy/`
  (pure numpy, no ROS deps): the 105-d obs assembly + numpy MLP inference
  the sim-trained RL policy needs. One copy; `sim/nova_mjx/deploy`'s own
  tests still run against it (path-inserted at the new location).
- `policy_node.py` — the rclpy glue (`ros2 run nova_locomotion policy_node`
  / `ros2 launch nova_locomotion policy.launch.py`): `/joint_states` +
  `/imu` + `/cmd_vel` -> policy_runner -> `/joint_commands`, through the
  SAME `SafeJointCommandPublisher`/`_CountsAdapter` path `gait_node` uses.
  Replaces the old `sim/nova_mjx/deploy/policy_node.py` scaffold, which
  published to `/joint_goal_ticks` (zero subscribers) from outside the
  buildable workspace. `PolicyGate` (pure, in this file) refuses inference
  unless preflight has PASSed (reuses `controller.PreflightGate`), all 12
  joints are calibrated, `/imu` is live, and `/nova/policy_enable` is
  explicitly True — never auto-arms. Ramps from the measured pose to the
  policy's own output over the first `ramp_ticks` after enable (anti-snap).

## ⚠️ Geometry status (updated 2026-07-06)
Link lengths + hip offset MEASURED (106.9/129.0/64.3). Joint limits =
the CAD gate ROM (haa ±15 conservative until homing fills the inboard
signs; hfe −86..+50 leg-local; kfe ±109). Masses still CAD estimates.

## old note (superseded)
`LegParams` (femur/tibia/hip_offset, joint ranges) and `TrotParams`
(stand_height etc.) default to the same SpotMicro-class placeholders as
`nova_description`. **The math is correct and tested; the numbers need CAD
measurement** before driving real servos. Keep these in sync with the
`nova_description` xacro link lengths (single source once measured).

## Next (hardware-blocked)
- IMU firmware driver + `/imu` topic (stage 4.1), homing calibration
  (fills counts_per_rad/home_offset + the HAA inboard signs), backlash
  measurement (stage 1.3), rosbag->CSV export for trot_metrics.
- MuJoCo scene from the URDF (stage 4.5 tuning lane) — skipped in this
  pass, `mujoco` not installed in `.venv`.
