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

## ⚠️ Geometry is placeholder (TODO-CAD)
`LegParams` (femur/tibia/hip_offset, joint ranges) and `TrotParams`
(stand_height etc.) default to the same SpotMicro-class placeholders as
`nova_description`. **The math is correct and tested; the numbers need CAD
measurement** before driving real servos. Keep these in sync with the
`nova_description` xacro link lengths (single source once measured).

## Next (Phase-2 integration, not yet built)
- `gait_node`: `cmd_vel`/gait params → `trot.foot_target` → `leg_ik` →
  `/joint_commands`, mapping joint→bus-ID via
  `nova_description/config/joint_id_map.yaml`. The tested pure logic above is
  the core; the node is thin glue + the live `/joint_states` contract.
- Body pose / COM-shift input (Phase-4 arm couples in here).
