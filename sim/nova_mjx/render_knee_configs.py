"""Render the three knee configurations side by side so the real robot's layout can
be identified by eye (#142).

WHY: nova_locomotion.KNEE_FORWARD and docs/knee-config-analysis.md disagree about
which leg pair carries the mirrored (elbow-forward) knee, and the canonical-frame
fold-margin arithmetic is ambiguous enough that deriving it keeps giving different
answers. Looking at the pose is unambiguous: in a SIDE view the knee either points
forward (+x, toward the head) or backward (-x).

Renders a strict side view (camera on -y looking at the x-z plane, +x = FORWARD =
image right) of each config's stand pose, plus a per-leg knee-direction readout
computed from the geometry rather than from the picture.

  MUJOCO_GL=cgl ../../.venv/bin/python render_knee_configs.py
"""
import os
import sys

import numpy as np
import mujoco
import imageio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import KNEE_CONFIGS, knee_pose, LEG_NAMES   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "artifacts", "knee_config_views")
W, H = 640, 480      # MuJoCo's default offscreen framebuffer; larger needs <global offwidth>



def knee_report(m, d, cfg):
    """Per-leg: is the KNEE (kfe joint) forward or behind the hip->foot line?

    Geometric, not visual: compare the knee body's world x against the straight
    line from the hip to the foot. A knee ahead of that chord = knee points FORWARD.
    """
    out = []
    for leg in LEG_NAMES:
        hip = d.body(f"{leg}_upper").xpos      # hfe pivot (top of femur)
        knee = d.body(f"{leg}_lower").xpos     # kfe pivot
        foot = d.body(f"{leg}_foot").xpos
        # chord hip->foot, at the knee's height, gives the "straight leg" x
        t = ((knee[2] - hip[2]) / (foot[2] - hip[2])) if abs(foot[2] - hip[2]) > 1e-9 else 0.5
        chord_x = hip[0] + t * (foot[0] - hip[0])
        dx = knee[0] - chord_x
        out.append((leg, dx, "FORWARD" if dx > 0 else "BACKWARD"))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "nova.xml"))
    m.hfield_data[:] = 0.0                     # flat ground: pure posture comparison
    d = mujoco.MjData(m)

    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.lookat[:] = [0.0, 0.0, 0.095]
    cam.distance = 0.62     # tight: the knee direction is the whole point
    cam.azimuth = 90.0      # eye on -y, looking toward +y -> +x (FORWARD) is to the RIGHT
    cam.elevation = -6.0

    panels, names = [], []
    with mujoco.Renderer(m, height=H, width=W) as rnd:
        for cfg in ("elbow_back", "xconfig_code", "xconfig_doc"):
            pose = np.asarray(knee_pose(cfg))
            d.qpos[:] = 0.0
            d.qpos[0:7] = [0, 0, 0.17, 1, 0, 0, 0]
            d.qpos[7:] = pose
            mujoco.mj_forward(m, d)
            rnd.update_scene(d, camera=cam)
            img = rnd.render().copy()
            panels.append(img)
            names.append(cfg)

            flags = dict(zip(LEG_NAMES, KNEE_CONFIGS[cfg]))
            print(f"\n=== {cfg} ===   elbow-forward flags: {flags}")
            for leg, dx, which in knee_report(m, d, cfg):
                print(f"    {leg}: knee {which:8} of the hip->foot line "
                      f"(offset {dx*1000:+6.1f} mm)")
            p = os.path.join(OUT, f"{cfg}.png")
            imageio.imwrite(p, img)

    # label each panel + mark the forward direction, so the strip is self-describing
    try:
        from PIL import Image, ImageDraw
        titles = {
            "elbow_back":   "elbow_back  (sim today)      front BACK  / rear BACK",
            "xconfig_code": "xconfig_code (KNEE_FORWARD)  front FWD   / rear BACK",
            "xconfig_doc":  "xconfig_doc  (analysis .md)  front BACK  / rear FWD",
        }
        lab = []
        for img, cfg in zip(panels, names):
            im = Image.fromarray(img)
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, 0, W, 26], fill=(12, 16, 24))
            dr.text((8, 8), titles[cfg], fill=(255, 255, 255))
            dr.text((8, H - 20), "HEAD / +x  ---->", fill=(120, 220, 255))
            dr.line([(4, 3), (W - 4, 3), (W - 4, H - 3), (4, H - 3), (4, 3)],
                    fill=(70, 90, 110), width=2)
            lab.append(np.asarray(im))
        panels = lab
    except ImportError:
        print("(PIL unavailable — panels unlabelled; order is printed below)")

    strip = np.concatenate(panels, axis=1)
    out = os.path.join(OUT, "knee_configs_side_by_side.png")
    imageio.imwrite(out, strip)
    print(f"\nside view, +x (FORWARD/head) is to the RIGHT in every panel")
    print(f"panels left->right: {'  |  '.join(names)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
