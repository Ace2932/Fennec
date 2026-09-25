"""Scripted-trot swing profile study: does a cycloid swing step better than the
half-sine nova_locomotion's trot uses today, on the servos the robot will have?

Open-loop, nominal model (no DR, no pushes, latency 0), 10 s per case. The
foot path is nova_locomotion.gait.trot's (diagonal trot, duty 0.5, stance slides
the foot back at constant speed) with only the SWING profile swapped:

  sine     x linear, z = h sin(pi s)  — lands with vx = L/T_sw and vz = -pi h/T_sw
  cycloid  x = L (s - sin(2 pi s)/2 pi), z = h (1 - cos(2 pi s))/2
           — zero velocity AND acceleration at lift-off and touchdown

Canonical targets -> VALIDATED leg IK (inverse_kinematics, haa*SIDE for the right
legs exactly as scripted_crawl_climber fix 1) -> env action. Stance height is
the sim's own stand (so action 0 == stance).

Columns: travel (m, +x over 10 s), fell, tilt (mean |roll|+|pitch| deg),
impact (mean |vz| of a foot at touchdown, cm/s), slip (mean xy speed of planted
feet, cm/s), clear (mean peak swing height, cm).

  JAX_PLATFORMS=cpu python probe_swing_profile.py
"""
import itertools
import os
import sys

import jax
import jax.numpy as jp
import numpy as np

_PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in ("nova_locomotion", "nova_ops"):
    sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", _p))
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    LegParams, forward_kinematics, inverse_kinematics)

from env import (NovaJoystick, DEFAULT_POSE, ACTION_SCALE, LEG_NAMES,  # noqa: E402
                 FOOT_RADIUS, CONTACT_EPS, goal_acc_rad, _ELBOW_BACK)

DT, STEPS = 0.02, 500
OFFSET = {"FL": 0.0, "RR": 0.0, "FR": 0.5, "RL": 0.5}
SIDE = np.array([1.0 if n[1] == "L" else -1.0 for n in LEG_NAMES])
PRM = LegParams()
X0, Y0, Z0 = forward_kinematics(_ELBOW_BACK, PRM)


def foot(lp, prof, L, h):
    if lp < 0.5:                                  # stance: slide back
        return L / 2 - L * (lp / 0.5), 0.0
    s = (lp - 0.5) / 0.5
    if prof == "sine":
        return -L / 2 + L * s, h * np.sin(np.pi * s)
    return (-L / 2 + L * (s - np.sin(2 * np.pi * s) / (2 * np.pi)),
            h * (1 - np.cos(2 * np.pi * s)) / 2)


def actions(prof, L, h, f):
    dp = np.asarray(DEFAULT_POSE)
    out = np.zeros((STEPS, 12), np.float32)
    for i in range(STEPS):
        for li, n in enumerate(LEG_NAMES):
            dx, dz = foot((i * DT * f + OFFSET[n]) % 1.0, prof, L, h)
            t = np.array(inverse_kinematics((X0 + dx, Y0, Z0 + dz), PRM, knee_forward=False))
            t[0] *= SIDE[li]
            out[i, 3 * li:3 * li + 3] = (t - dp[3 * li:3 * li + 3]) / ACTION_SCALE
    return out


def run(env, acts):
    s0 = env.reset(jax.random.PRNGKey(0))
    s0 = s0.replace(info={**s0.info, "delay": jp.asarray(0, s0.info["delay"].dtype),
                          "cmd": jp.array([0.2, 0.0, 0.0])})
    fid = env._foot_ids

    def body(s, a):
        s = env.step(s, a)
        x = s.pipeline_state.x
        up = jax.vmap(lambda q: q)(x.rot[:1])[0]
        w, qx, qy, qz = up
        roll = jp.arctan2(2 * (w * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
        pitch = jp.arcsin(jp.clip(2 * (w * qy - qz * qx), -1, 1))
        fz = x.pos[fid, 2]
        fv = s.pipeline_state.xd.vel[fid]
        return s, (x.pos[0, 0], s.done, jp.abs(roll) + jp.abs(pitch), fz, fv)

    _, out = jax.lax.scan(body, s0, acts)
    return out


def metrics(bx, done, tilt, fz, fv):
    fell = bool(done.max() > 0.5)
    n = int(np.argmax(done > 0.5)) if fell else len(done)
    c = (fz[:n] - FOOT_RADIUS) < CONTACT_EPS
    td = c[1:] & ~c[:-1]
    impact = np.abs(fv[1:n, :, 2])[td].mean() if td.any() else np.nan
    slip = np.linalg.norm(fv[:n, :, :2], axis=-1)[c].mean() if c.any() else np.nan
    clear = np.mean([fz[:n, k][~c[:, k]].max() - FOOT_RADIUS
                     for k in range(4) if (~c[:, k]).any()]) if n else np.nan
    return dict(travel=bx[n - 1] - bx[0], fell=fell, tilt=np.degrees(tilt[:n].mean()),
                impact=100 * impact, slip=100 * slip, clear=100 * clear)


def main():
    conds = [("ideal", 1.0, 0), ("fw_acc0", 0.6, 0), ("fw_today", 0.6, 50)]
    grid = list(itertools.product(("sine", "cycloid"), (0.03, 0.02), (1.5, 1.0)))
    acts = jp.asarray(np.stack([actions(p, 0.06, h, f) for p, h, f in grid]))
    print(f"{'actuator':9s} {'profile':8s} {'h':>4s} {'f':>4s}  {'travel':>6s} {'fell':>4s} "
          f"{'tilt':>5s} {'impact':>6s} {'slip':>5s} {'clear':>5s}")
    for cname, tl, acc in conds:
        env = NovaJoystick(push_mag=0.0, torque_limit=tl, goal_acc=goal_acc_rad(acc))
        outs = [np.asarray(o) for o in jax.jit(jax.vmap(lambda a: run(env, a)))(acts)]
        for k, (p, h, f) in enumerate(grid):
            m = metrics(*[o[k] for o in outs])
            print(f"{cname:9s} {p:8s} {h*100:4.0f} {f:4.1f}  {m['travel']:6.2f} "
                  f"{'Y' if m['fell'] else '-':>4s} {m['tilt']:5.1f} {m['impact']:6.1f} "
                  f"{m['slip']:5.1f} {m['clear']:5.2f}")


if __name__ == "__main__":
    main()
