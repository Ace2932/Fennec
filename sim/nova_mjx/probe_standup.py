"""CAN IT GET BACK UP? Stand-up recovery from the sit / belly-down poses (#142).

A controlled-limp SIT is only worth wiring into the fault path if the robot can
LEAVE it. Both poses are deeply SPLAYED (haa +40 outboard, foot y +15.5 cm vs the
+6.4 cm nominal stance), so standing means dragging the feet ~9 cm INBOARD against
mu = 1.2 rubber-on-ground while the legs also un-fold and lift 4.1 kg. Friction may
simply pin the feet, the haa servos may saturate, or the robot may skate.

This does not argue about it — it commands a min-jerk joint-space blend from the
settled pose to the stand pose, through the SAME position servos (kp=35, the MJCF
torque envelope and joint limits), and measures what happens.

VERDICT: stood = trunk reaches >= 90% of stand height AND up_z > 0.9 (never rolled)
AND it stays there after the blend ends.

  MUJOCO_GL=cgl ../../.venv/bin/python probe_standup.py
"""
import os
import sys

import numpy as np
import mujoco
import imageio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import LEG_NAMES   # noqa: E402
from build_mjcf import EFF_HIP, EFF_LEG   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "artifacts", "standup_views")
W, H = 640, 480
D = np.radians
SIDE = {"FL": +1.0, "FR": -1.0, "RL": +1.0, "RR": -1.0}
DT = 0.004                                   # MJCF timestep
STAND_Z = 0.176                              # settled stand trunk height

SIT_LEG = (D(40.0), D(40.0), D(-90.0))       # backlog #15 controlled-limp pose
STAND_LEG = (0.0, 0.600, -1.200)
TAU = np.array([EFF_HIP, EFF_LEG, EFF_LEG] * 4)

POSES = {
    "sit":  {"FL": STAND_LEG, "FR": STAND_LEG, "RL": SIT_LEG, "RR": SIT_LEG},
    "down": {leg: SIT_LEG for leg in LEG_NAMES},
}


def vec(pose):
    return np.array([v * (SIDE[leg] if j == 0 else 1.0)
                     for leg in LEG_NAMES for j, v in enumerate(pose[leg])])


def min_jerk(tau):
    tau = min(max(tau, 0.0), 1.0)
    return tau * tau * tau * (10.0 + tau * (-15.0 + 6.0 * tau))


def settle(m, d, ctrl, n=6000):
    d.qpos[:] = 0.0
    d.qpos[0:7] = [0, 0, 0.24, 1, 0, 0, 0]
    d.qpos[7:] = ctrl
    d.qvel[:] = 0.0
    d.ctrl[:] = ctrl
    for _ in range(n):
        mujoco.mj_step(m, d)


def up_z(d):
    return float(d.body("trunk").xmat[8])       # body z-axis . world z


def run(m, d, start_ctrl, blend_s, hold_s=3.0, rnd=None, cam=None, nframes=6):
    goal = vec({leg: STAND_LEG for leg in LEG_NAMES})
    n_blend, n_hold = int(blend_s / DT), int(hold_s / DT)
    feet0 = np.array([d.body(f"{leg}_foot").xpos[:2] for leg in LEG_NAMES])
    zs, uz, sat, frames = [], [], [], []
    grab = set(np.linspace(0, n_blend + n_hold - 1, nframes).astype(int))
    for k in range(n_blend + n_hold):
        s = min_jerk(k / max(n_blend, 1))
        d.ctrl[:] = start_ctrl + s * (goal - start_ctrl)
        mujoco.mj_step(m, d)
        zs.append(d.body("trunk").xpos[2])
        uz.append(up_z(d))
        sat.append(np.mean(np.abs(d.actuator_force) >= 0.99 * TAU))
        if rnd is not None and k in grab:
            rnd.update_scene(d, camera=cam)
            frames.append(rnd.render().copy())
    feet1 = np.array([d.body(f"{leg}_foot").xpos[:2] for leg in LEG_NAMES])
    slip = np.linalg.norm(feet1 - feet0, axis=1)
    return dict(z=np.array(zs), uz=np.array(uz), sat=np.array(sat),
                slip=slip, frames=frames)


def main():
    os.makedirs(OUT, exist_ok=True)
    m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "nova.xml"))
    m.hfield_data[:] = 0.0
    d = mujoco.MjData(m)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.lookat[:] = [0.0, 0.0, 0.09]
    cam.distance = 0.85
    cam.azimuth, cam.elevation = 90.0, -10.0

    print("=" * 92)
    print(f"STAND-UP RECOVERY — target trunk z {STAND_Z*100:.1f} cm, "
          f"pass = reach 90% ({STAND_Z*0.9*100:.1f} cm) and stay upright")
    print("=" * 92)

    strips = []
    with mujoco.Renderer(m, height=H, width=W) as rnd:
        for name, pose in POSES.items():
            start = vec(pose)
            print(f"\n--- from {name.upper()} ---")
            for blend_s in (1.5, 3.0, 6.0):
                settle(m, d, start)
                z0 = d.body("trunk").xpos[2]
                want_frames = (blend_s == 3.0)
                r = run(m, d, start, blend_s,
                        rnd=rnd if want_frames else None,
                        cam=cam if want_frames else None)
                zf, uzf = r["z"][-1], r["uz"][-1]
                ok = zf >= 0.9 * STAND_Z and r["uz"].min() > 0.9
                print(f"  blend {blend_s:4.1f}s: trunk {z0*100:5.2f} -> {zf*100:5.2f} cm "
                      f"(peak {r['z'].max()*100:5.2f})  up_z min {r['uz'].min():.3f} end {uzf:.3f}  "
                      f"foot slip max {r['slip'].max()*100:5.2f} cm  "
                      f"sat peak {r['sat'].max()*100:4.1f}%  -> "
                      f"{'STOOD' if ok else 'FAILED'}")
                if want_frames and r["frames"]:
                    strips.append((name, np.concatenate(r["frames"], axis=1)))

    for name, strip in strips:
        p = os.path.join(OUT, f"standup_{name}.png")
        imageio.imwrite(p, strip)
        print(f"\nwrote {p}")
    if strips:
        hmin = min(s.shape[0] for _, s in strips)
        wmin = min(s.shape[1] for _, s in strips)
        stack = np.concatenate([s[:hmin, :wmin] for _, s in strips], axis=0)
        p = os.path.join(OUT, "standup_both.png")
        imageio.imwrite(p, stack)
        print(f"wrote {p}  (top row = sit, bottom row = down; time -> right)")


if __name__ == "__main__":
    main()
