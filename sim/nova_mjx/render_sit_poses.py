"""Render the ASYMMETRIC SIT and the belly-DOWN pose, settled under gravity (#142).

WHY: choreo/stand.py can only express symmetric, feet-under-hips poses (KEYFRAMES
returns ONE foot target for all four legs, haa = 0, x = 0). That routes 100% of the
height change into hfe fold — the one direction the riser skirt blocks at +50° — so
the translated-knee crouch envelope collapsed to 0.92 cm. The robot has two ways
down that never approach the cap:

  * LATERAL SPLAY  — backlog #15's controlled-limp sit, haa +40 / hfe +40 / kfe -90:
    hip height 8.49 cm with 10° of skirt margin (vs choreo 'lie' at 17.08 cm and 1°).
  * FOOT PROTRACTION — foot placed forward drives hfe NEGATIVE, into the unused
    -86° side; hip reaches 2.00 cm at foot x +14 cm with hfe -21°.

These are not drawings: each pose is COMMANDED through the real position servos
(kp=35, the MJCF's joint limits and torque envelope) and left to settle under
gravity + contact, so the body pitch, the belly landing and any joint hitting a
stop are the simulator's answer, not mine.

  MUJOCO_GL=cgl ../../.venv/bin/python render_sit_poses.py
"""
import os
import sys

import numpy as np
import mujoco
import imageio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import LEG_NAMES   # noqa: E402
from build_mjcf import HAA_IN, HAA_OUT, HFE_FOLD, HFE_EXT, KFE   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sit_pose_views")
W, H = 640, 480
D = np.radians
SIDE = {"FL": +1.0, "FR": -1.0, "RL": +1.0, "RR": -1.0}     # +1 = left (outboard = +haa)

# backlog #15 controlled-limp SIT angles (canonical/outboard-positive), and the
# sim stand pose for the legs that stay up.
SIT_LEG = (D(40.0), D(40.0), D(-90.0))      # haa outboard, hfe, kfe
STAND_LEG = (0.0, 0.600, -1.200)

POSES = {
    "sit":  {"FL": STAND_LEG, "FR": STAND_LEG, "RL": SIT_LEG, "RR": SIT_LEG},
    "down": {leg: SIT_LEG for leg in LEG_NAMES},
}
J_LO = {leg: np.array([-HAA_IN if SIDE[leg] > 0 else -HAA_OUT, -HFE_EXT, -KFE])
        for leg in LEG_NAMES}
J_HI = {leg: np.array([HAA_OUT if SIDE[leg] > 0 else HAA_IN, HFE_FOLD, KFE])
        for leg in LEG_NAMES}


def target_vector(pose):
    """Canonical per-leg angles -> the 12-vec of PHYSICAL joint targets.
    Canonical +haa is outboard for every leg; a right leg's physical haa is
    the negated canonical one (leg_ik.solve_side, THE ONE MIRRORING BOUNDARY)."""
    q = []
    for leg in LEG_NAMES:
        haa, hfe, kfe = pose[leg]
        q += [haa * SIDE[leg], hfe, kfe]
    return np.array(q)


def settle(m, d, ctrl, n=6000):
    d.qpos[:] = 0.0
    d.qpos[0:7] = [0, 0, 0.24, 1, 0, 0, 0]     # drop it in from above
    d.qpos[7:] = ctrl
    d.qvel[:] = 0.0
    d.ctrl[:] = ctrl
    for _ in range(n):
        mujoco.mj_step(m, d)
    return d


def pitch_deg(d):
    """Nose-UP positive. A positive rotation about body +y tips the nose DOWN
    (it takes +x toward -z), so negate to get the intuitive sign."""
    w, x, y, z = d.qpos[3:7]
    return -np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))


def main():
    os.makedirs(OUT, exist_ok=True)
    m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "nova.xml"))
    m.hfield_data[:] = 0.0
    d = mujoco.MjData(m)

    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.lookat[:] = [0.0, 0.0, 0.07]
    cam.distance = 0.78
    cam.azimuth = 90.0        # +x (HEAD) to the RIGHT
    cam.elevation = -10.0

    panels, names = [], []
    with mujoco.Renderer(m, height=H, width=W) as rnd:
        for name, pose in POSES.items():
            ctrl = target_vector(pose)
            settle(m, d, ctrl)
            trunk_z = d.body("trunk").xpos[2]
            print(f"\n=== {name.upper()} ===")
            print(f"  trunk centre z {trunk_z*100:5.2f} cm   belly z "
                  f"{(trunk_z-0.045)*100:5.2f} cm   pitch {pitch_deg(d):+5.1f} deg (nose-up +)")
            for i, leg in enumerate(LEG_NAMES):
                q = d.qpos[7 + 3 * i: 10 + 3 * i]
                at = ["*" if (abs(q[j] - J_LO[leg][j]) < 2e-3
                              or abs(q[j] - J_HI[leg][j]) < 2e-3) else " " for j in range(3)]
                err = q - ctrl[3 * i:3 * i + 3]
                foot_z = d.body(f"{leg}_foot").xpos[2]
                print(f"    {leg}: q={np.round(np.degrees(q),1)} {''.join(at)} "
                      f"track_err={np.round(np.degrees(err),1)} deg  foot_z={foot_z*100:5.2f} cm")
            ncon = d.ncon
            trunk_touch = any(
                m.geom(d.contact[k].geom1).name == "trunk_c"
                or m.geom(d.contact[k].geom2).name == "trunk_c" for k in range(ncon))
            print(f"  contacts {ncon}, belly(trunk_c) touching ground: {trunk_touch}")

            rnd.update_scene(d, camera=cam)
            panels.append(rnd.render().copy())
            names.append(name)
            imageio.imwrite(os.path.join(OUT, f"{name}.png"), panels[-1])

    try:
        from PIL import Image, ImageDraw
        titles = {"sit": "ASYMMETRIC SIT  — rear splayed+folded, front standing",
                  "down": "BELLY DOWN — all four splayed+folded (#15 limp pose)"}
        lab = []
        for img, nm in zip(panels, names):
            im = Image.fromarray(img)
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, 0, W, 26], fill=(12, 16, 24))
            dr.text((8, 8), titles[nm], fill=(255, 255, 255))
            dr.text((8, H - 20), "HEAD / +x  ---->", fill=(120, 220, 255))
            lab.append(np.asarray(im))
        panels = lab
    except ImportError:
        pass

    out = os.path.join(OUT, "sit_poses.png")
    imageio.imwrite(out, np.concatenate(panels, axis=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
