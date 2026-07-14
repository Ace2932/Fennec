#!/usr/bin/env python3
"""Generate nova.xml (MuJoCo MJCF) for the NOVA 12-DOF quadruped from the same
measured link lengths + CAD inertials the URDF uses (nova_description).

MJX/Brax train on an MJCF, not a URDF. This emits a clean, RL-ready model:
floating trunk + 4 legs (haa/hfe/kfe), position-servo actuators sized to the
STS3215, primitive collision (feet + trunk only, for fast stable contacts),
an IMU + joint sensor suite, and a standing keyframe.

Numbers (SI, m/kg): link offsets + joint limits from nova.urdf.xacro (MEASURED);
per-link mass/inertia from tools/compute_inertials.py. Inertials are DIAGONAL
here (first pass) with a physically-reasoned CoM sign (CoM follows the femur/
servo). Rationale: the femur/tibia STL->link transforms validate against the
URDF landmarks, but the hip's coax CAD frame is mirror-handed vs its link frame,
so the hip off-diagonals + CoM-z sign are unreliable — diagonal + reasoned CoM
is robust, and domain randomization covers the products of inertia. Refine with
the full validated tensor + weighed masses later (backlog #5).

Run:  python build_mjcf.py   # writes nova.xml
Deps: none (pure string emit). Validate with validate_model.py (needs mujoco).
"""

# ---- measured kinematics (m) — nova.urdf.xacro ----------------------------
MOUNT = dict(x=0.1412, y=0.0390, z=0.0380)     # base -> haa (half hip grid)
HAA_TO_HFE = (0.0, 0.0338, -0.0095)            # y scaled by reflect
HFE_TO_KFE = (0.0, 0.0, -0.1069)               # femur length
KFE_TO_FOOT = (0.0, 0.0305, -0.1290)           # tibia length; y by reflect

# joint limits (rad) — chassis gate ROM
HAA_IN, HAA_OUT = 0.262, 0.698
HFE_FOLD, HFE_EXT = 0.873, 1.501
KFE = 1.9
EFF_HIP, EFF_LEG = 2.9, 1.8                     # N*m stall torque (datasheet)
# No-load speed caps (rad/s): leg 7.5V bench (peak 1800 raw = 2.76), hip 12V
# datasheet 45 RPM. Enforced as the motor torque-speed slope via per-joint
# damping d = stall/no_load -> available torque hits 0 at no-load speed, so the
# joint can't exceed it even on a ballistic swing (docs/bench/README.md).
VMAX_HIP, VMAX_LEG = 4.71, 2.80                 # rad/s no-load
DAMP_HIP, DAMP_LEG = EFF_HIP / VMAX_HIP, EFF_LEG / VMAX_LEG   # 0.616, 0.643

# ---- inertials — tools/compute_inertials.py (diagonal, reasoned CoM sign) --
# (mass kg, com (x, |y|, z) m, diag inertia (ixx,iyy,izz) kg*m^2). y-sign set
# by reflect at emit time so the CoM follows the femur/servo side.
LINK_I = {
    "hip":   (0.0836, (0.0071, 0.0200, -0.0080), (4.099e-5, 2.120e-5, 3.255e-5)),
    "upper": (0.1219, (0.0000, 0.0065, -0.0507), (7.486e-5, 6.649e-5, 2.667e-5)),
    "lower": (0.1110, (-0.0005, 0.0101, -0.0656), (1.006e-4, 9.150e-5, 2.321e-5)),
    "foot":  (0.0039, (0.0, 0.0, 0.0), (2.116e-7, 5.602e-7, 5.763e-7)),
}
BASE_I = (2.83, (0.0, 0.0, 0.0), (8.7e-3, 2.46e-2, 2.65e-2))

# capsule half-geometry for collision/visual (radius m)
R_THIGH, R_SHANK, R_FOOT = 0.013, 0.011, 0.014

# terrain heightfield (env.domain_randomize fills per-env; flat by default) —
# keep TN/TR/TZ in sync with terrain.py
TN = 40            # hfield resolution (TN x TN cells)
TR = 2.5           # hfield half-size (m)
TR2 = 2 * TR       # full terrain extent (m)
TZ = 0.20          # max terrain height (m); hfield data [0,1] -> [0, TZ]

LEGS = [  # name, mount sign (sx along x, sy along y = reflect)
    ("FL", +1, +1), ("FR", +1, -1), ("RL", -1, +1), ("RR", -1, -1),
]


def inertial(link, reflect):
    m, (cx, cy, cz), (ixx, iyy, izz) = link
    return (f'<inertial pos="{cx:.5f} {reflect*cy:+.5f} {cz:.5f}" mass="{m:.4f}" '
            f'diaginertia="{ixx:.4e} {iyy:.4e} {izz:.4e}"/>')


def haa_range(reflect):
    # URDF: left (reflect +1) lower -in / upper +out ; right mirrored
    lo, hi = (-HAA_IN, HAA_OUT) if reflect == 1 else (-HAA_OUT, HAA_IN)
    return f"{lo:.4f} {hi:.4f}"


def leg_body(name, sx, sy):
    hy = HAA_TO_HFE[1] * sy
    fy = KFE_TO_FOOT[1] * sy
    return f'''
      <body name="{name}_hip" pos="{sx*MOUNT['x']:.4f} {sy*MOUNT['y']:.4f} {MOUNT['z']:.4f}">
        <joint name="{name}_haa" axis="1 0 0" range="{haa_range(sy)}" damping="{DAMP_HIP:.3f}"/>
        {inertial(LINK_I['hip'], sy)}
        <geom type="capsule" fromto="0 0 0 0 {hy:.4f} {HAA_TO_HFE[2]:.4f}" size="{R_THIGH}" class="viz"/>
        <body name="{name}_upper" pos="0 {hy:.4f} {HAA_TO_HFE[2]:.4f}">
          <joint name="{name}_hfe" axis="0 1 0" range="{-HFE_EXT:.4f} {HFE_FOLD:.4f}" damping="{DAMP_LEG:.3f}"/>
          {inertial(LINK_I['upper'], sy)}
          <geom type="capsule" fromto="0 0 0 0 0 {HFE_TO_KFE[2]:.4f}" size="{R_THIGH}" class="viz"/>
          <body name="{name}_lower" pos="0 0 {HFE_TO_KFE[2]:.4f}">
            <joint name="{name}_kfe" axis="0 1 0" range="{-KFE:.4f} {KFE:.4f}" damping="{DAMP_LEG:.3f}"/>
            {inertial(LINK_I['lower'], sy)}
            <geom type="capsule" fromto="0 0 0 0 {fy:.4f} {KFE_TO_FOOT[2]:.4f}" size="{R_SHANK}" class="viz"/>
            <body name="{name}_foot" pos="0 {fy:.4f} {KFE_TO_FOOT[2]:.4f}">
              {inertial(LINK_I['foot'], sy)}
              <geom name="{name}_foot" type="sphere" size="{R_FOOT}" class="foot"/>
            </body>
          </body>
        </body>
      </body>'''


def actuators():
    out = []
    for name, _, _ in LEGS:
        for j, eff in (("haa", EFF_HIP), ("hfe", EFF_LEG), ("kfe", EFF_LEG)):
            # kv=0: control damping folded into the joint's torque-speed damping
            # (DAMP_HIP/DAMP_LEG) — kv and joint damping are both -c*qdot, only the
            # sum matters, and that sum is set to the motor slope for the vel cap.
            out.append(f'    <position name="{name}_{j}" joint="{name}_{j}" '
                       f'kp="35" kv="0" forcerange="{-eff} {eff}"/>')
    return "\n".join(out)


def sensors():
    s = ['    <framequat name="trunk_quat" objtype="site" objname="imu"/>',
         '    <gyro name="trunk_gyro" site="imu"/>',
         '    <velocimeter name="trunk_vel" site="imu"/>',
         '    <accelerometer name="trunk_acc" site="imu"/>',
         '    <framepos name="trunk_pos" objtype="site" objname="imu"/>']
    for name, _, _ in LEGS:
        for j in ("haa", "hfe", "kfe"):
            s.append(f'    <jointpos name="{name}_{j}_p" joint="{name}_{j}"/>')
            s.append(f'    <jointvel name="{name}_{j}_v" joint="{name}_{j}"/>')
    return "\n".join(s)


def home_keyframe():
    # base at z0, identity quat, then per-leg (haa, hfe, kfe) folded to stand.
    # foot_z_below_haa = -0.0095 -0.1069 cos(hfe) -0.1290 cos(hfe+kfe).
    hfe, kfe = 0.6, -1.2
    q = []
    for _, _, sy in LEGS:
        q += [0.0, hfe, kfe]
    joints = " ".join(f"{v:.3f}" for v in q)
    return (f'    <key name="stand" qpos="0 0 0.17 1 0 0 0 {joints}"\n'
            f'         ctrl="{" ".join("0 %.3f %.3f" % (hfe, kfe) for _ in LEGS)}"/>')


MJCF = f'''<mujoco model="nova_sm3">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.004" iterations="10" ls_iterations="10">
    <flag eulerdamp="disable"/>
  </option>

  <default>
    <!-- damping is overridden per-joint (DAMP_HIP/DAMP_LEG = torque-speed slope,
         the velocity cap). frictionloss 0.20 N*m = gearbox Coulomb drag: the
         1:345 gearbox is ~non-backdrivable, so it bounds gravity-driven overspeed
         (motor-driven speed already capped by damping). Tuned so no joint exceeds
         its no-load cap even gravity-assisted, without eating motor speed. -->
    <joint damping="0.5" armature="0.008" frictionloss="0.20"/>
    <default class="viz">
      <geom contype="0" conaffinity="0" group="1" density="0" rgba="0.5 0.6 0.7 1"/>
    </default>
    <default class="foot">
      <geom contype="1" conaffinity="1" friction="1.2 0.02 0.001" rgba="0.2 0.2 0.2 1"/>
    </default>
  </default>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="512"/>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.1 0.2 0.3" rgb2="0.2 0.3 0.4" width="300" height="300"/>
    <material name="grid" texture="grid" texrepeat="8 8" reflectance="0.2"/>
    <!-- TERRAIN heightfield: flat by default (0 data); env.domain_randomize sets
         per-env terrain (terrain.py). {TN}x{TN} cells over {TR2:.0f}x{TR2:.0f} m, z up to {TZ} m.
         Robot spawns on a flat center pad, terrain roughens outward. -->
    <hfield name="terrain" nrow="{TN}" ncol="{TN}" size="{TR} {TR} {TZ} 0.02"/>
  </asset>

  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="hfield" hfield="terrain" material="grid" contype="1" conaffinity="1" friction="1.2 0.02 0.001"/>

    <body name="trunk" pos="0 0 0.17">
      <freejoint name="root"/>
      <site name="imu" pos="0 0 0"/>
      <camera name="track" mode="trackcom" pos="0 -1.3 0.6" xyaxes="1 0 0 0 0.45 1"/>
      {inertial(BASE_I, 1)}
      <geom type="box" size="0.14 0.055 0.045" class="viz" rgba="0.4 0.4 0.45 1"/>
      <geom name="trunk_c" type="box" size="0.14 0.055 0.045" contype="1" conaffinity="1" group="3" rgba="0 0 0 0"/>
{''.join(leg_body(n, sx, sy) for n, sx, sy in LEGS)}
    </body>
  </worldbody>

  <actuator>
{actuators()}
  </actuator>

  <sensor>
{sensors()}
  </sensor>

  <keyframe>
{home_keyframe()}
  </keyframe>
</mujoco>
'''

if __name__ == "__main__":
    with open("nova.xml", "w") as f:
        f.write(MJCF)
    print(f"wrote nova.xml ({len(MJCF)} bytes, {len(LEGS)} legs, "
          f"{3*len(LEGS)} actuated DOF)")
