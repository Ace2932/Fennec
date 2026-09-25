# nova_description

URDF/xacro for the NovaSM3 12-DOF quadruped. This is the keystone the sim +
planning stack was blocked on (MJX gait training, Isaac/VLA, MoveIt, RViz,
robot_localization, gait COM-compensation all consume it).

## Status: link kinematics are MEASURED; masses/inertias are CALIBRATED estimates, not weighed

~~FIRST-CUT — link kinematics are PLACEHOLDERS~~ — superseded 2026-07-06 onward;
no property in `urdf/nova.urdf.xacro` is tagged `TODO-CAD` any more.

- **Exact / measured:** kinematic tree, joint types/axes, joint names, ID↔name map,
  STS3215 effort/velocity limits, the **visual/collision meshes** (the real carved
  NovaSM3 STLs from `original_body_files/`), **link offsets** (measured 2026-07-02
  from the Assembly_NOVA_SM3 Fusion share; the leg_v6 hip-grid station fixed
  2026-07-27 (#165) — `body_half_x` is the haa station and stays 0.1412, the
  separate `hip_to_upper_x` (0.0116) carries the haa→hfe offset per leg end;
  `test_urdf_sync.py` pins `body_half_x - hip_to_upper_x` against the CAD), and
  **joint position ranges** (set from the CAD fit-gate crouch sweep, 2026-07-06,
  refined by #47's measured hfe sweep, 2026-07-11).
- **Estimated, not weighed:** link masses/inertias are COMPUTED (2026-07-13,
  `tools/compute_inertials.py`) from the real leg_v6 meshes + embedded servos, and
  CALIBRATED against measured print density + a 60 g servo-box allowance — real
  numbers, not a guess, but not a scale reading either. Still owed: weigh every
  printed part and replace these with measured masses (backlog #5/#13); the
  xacro also flags the left/right mirror sign on the inertia tensors as
  "verify in sim".

The kinematics are trustworthy enough to plan/train motion on; the mass/inertia
values are a calibrated estimate, so treat dynamics-sensitive results (torque
margins, balance) with that caveat until the weigh-in above lands.

### How to refine (remaining task)
Weigh every printed part and feed the measured masses back into
`tools/compute_inertials.py`, then update `urdf/nova.urdf.xacro`'s mass/inertia
properties and re-check in RViz.

## Layout
- `urdf/nova.urdf.xacro` — robot: properties + base + 4× leg macro
- `urdf/leg.macro.xacro` — 3-DOF leg (HAA→HFE→KFE→foot)
- `meshes/` — NovaSM3 STLs (mm; scaled ×0.001 in URDF)
- `config/joint_id_map.yaml` — canonical Feetech bus-ID ↔ joint-name map
- `launch/display.launch.py` — robot_state_publisher + JSP GUI + RViz

## Joints (12)
Legs `FL FR RL RR`; per leg `<leg>_haa` (hip ab/ad, coax), `<leg>_hfe`
(hip flex, femur), `<leg>_kfe` (knee, tibia). Bus IDs: HAA 1-4, HFE/KFE 5-12
(see `config/joint_id_map.yaml` — verify against physical servo labels).

## Build + view
```bash
cd ~/codebases/NOVA/proj/ros2_ws
colcon build --packages-select nova_description
source install/setup.bash
ros2 launch nova_description display.launch.py
```
