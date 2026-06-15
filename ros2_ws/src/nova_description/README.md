# nova_description

URDF/xacro for the NovaSM3 12-DOF quadruped. This is the keystone the sim +
planning stack was blocked on (MJX gait training, Isaac/VLA, MoveIt, RViz,
robot_localization, gait COM-compensation all consume it).

## ⚠️ Status: FIRST-CUT — link kinematics are PLACEHOLDERS

- **Exact:** kinematic tree, joint types/axes, joint names, ID↔name map, STS3215
  effort/velocity limits, and the **visual/collision meshes** (the real carved
  NovaSM3 STLs from `original_body_files/`).
- **NOT exact (every value tagged `TODO-CAD` in `urdf/nova.urdf.xacro`):** link
  offsets (axis-to-axis distances), joint position ranges, masses, inertias.
  These live in the mesh geometry / leg_v5 assembly and were not measured (no
  mesh tool in the authoring env).

**Do NOT train a gait or plan motion on this until the `TODO-CAD` values are
replaced with measurements from CAD** — the link offsets are SpotMicro-class
guesses and the kinematics will be wrong. The visuals are correct, so loading it
in RViz immediately shows where the offsets need fixing.

### How to refine (the one remaining task)
Measure from the leg_v5 assembly / `original_body_files/SM3_Frame_*` meshes:
`body_half_x/y`, `mount_z`, `hip_to_upper_*`, `upper_to_lower_z` (femur length),
`lower_to_foot_z` (tibia length), per-joint `*_range`, and link masses/inertias.
Replace the matching xacro properties, then re-check in RViz.

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
