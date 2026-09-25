"""Open-loop probe: does the IK swing reference lift every foot, and what does the
firmware's servo profile (TORQUE_LIMIT / GOAL_ACC) leave of it?

1. KINEMATIC GATE (exit 1 on fail): pose each leg at the reference's peak
   offsets with mj_forward and require the foot to move +REF_HEIGHT straight up
   in the TRUNK frame (+-1 mm). This is the sign/frame test — the dominant bug
   class here — isolated from dynamics.
2. DYNAMIC TABLE: drive the blind env with ZERO residual under ref_gait (trot,
   1.4 Hz), pushes off, latency pinned to 0, and report per leg the knee's
   achieved / commanded excursion — joint space, because foot height is
   confounded by body rocking and stance-leg sag. Once on a stand (g=0: the
   actuator alone) and once loaded. What a row loses is actuator authority.

  JAX_PLATFORMS=cpu python probe_servo_profile.py
"""
import sys

import jax
import jax.numpy as jp
import mujoco
import numpy as np

from env import (NovaJoystick, goal_acc_rad, LEG_NAMES, REF_HEIGHT, REF_DZ_MAX,
                 REF_N, DEFAULT_POSE, ref_lift_table)


def kinematic_gate():
    m = mujoco.MjModel.from_xml_path("nova.xml")
    d = mujoco.MjData(m)
    tab = np.asarray(ref_lift_table())
    k = int(round(REF_HEIGHT / REF_DZ_MAX * (REF_N - 1)))
    dp = np.asarray(DEFAULT_POSE)

    def feet(q):
        d.qpos[:] = m.qpos0
        d.qpos[7:] = q
        mujoco.mj_forward(m, d)
        R = d.xmat[1].reshape(3, 3)
        return np.array([R.T @ (d.xpos[m.body(f"{n}_foot").id] - d.xpos[1])
                         for n in LEG_NAMES])

    base, ok = feet(dp), True
    for li, n in enumerate(LEG_NAMES):
        q = dp.copy()
        q[3 * li + 1] += tab[k, 0]
        q[3 * li + 2] += tab[k, 1]
        dxyz = feet(q)[li] - base[li]
        good = abs(dxyz[2] - REF_HEIGHT) < 1e-3 and np.hypot(*dxyz[:2]) < 1e-3
        ok &= good
        print(f"  kinematic {n}: dxyz {np.round(dxyz * 100, 2)} cm  {'ok' if good else 'FAIL'}")
    return ok

STEPS = 150            # 3 s, ~4 gait cycles at 1.4 Hz
SETTLE = 25

CASES = [
    # label, torque_limit, GOAL_ACC register
    ("no profile, full torque", 1.0, 0),
    ("torque 0.6 (fw)", 0.6, 0),
    ("torque 0.6 + acc 254", 0.6, 254),
    ("torque 0.6 + acc 150", 0.6, 150),
    ("torque 0.6 + acc 50 (fw today)", 0.6, 50),
]


def run(tl, acc, gravity=True):
    """Per-leg achieved kfe peak-to-peak / commanded peak-to-peak (joint space, so
    no frame or stance-compliance confound). gravity=False = robot 'on a stand':
    the actuator alone, no load."""
    env = NovaJoystick(push_mag=0.0, ref_gait=True, torque_limit=tl,
                       goal_acc=goal_acc_rad(acc))
    if not gravity:
        env.sys = env.sys.replace(opt=env.sys.opt.replace(gravity=jp.zeros(3)))
    reset, step = jax.jit(env.reset), jax.jit(env.step)
    s = reset(jax.random.PRNGKey(0))
    s = s.replace(info={**s.info, "delay": jp.asarray(0, s.info["delay"].dtype),
                        "cmd": jp.array([0.2, 0.0, 0.0])})
    zero = jp.zeros(env.action_size)
    q, ref = [], []
    for i in range(SETTLE + STEPS):
        ref.append(np.asarray(env._ref_offset(s.info["gait_phase"])))
        s = step(s, zero)
        q.append(np.asarray(s.pipeline_state.q[7:]))
        if gravity and float(s.done) > 0.5:
            return None, i
    q, ref = np.array(q)[SETTLE:], np.array(ref)[SETTLE:]
    kfe = [3 * li + 2 for li in range(4)]
    return np.ptp(q[:, kfe], axis=0) / np.ptp(ref[:, kfe], axis=0), None


def main():
    if not kinematic_gate():
        print("FAIL: the reference does not lift a foot straight up -> frame/sign bug")
        sys.exit(1)
    print(f"\nreference peak lift {REF_HEIGHT*100:.1f} cm, trot 1.4 Hz, zero residual.\n"
          "kfe excursion achieved / commanded (1.00 = tracks the reference)\n")
    for grav, title in ((False, "ON A STAND (g=0, actuator only)"),
                        (True, "LOADED (standing on the floor)")):
        print(title)
        print(f"  {'case':32s} " + " ".join(f"{n:>5s}" for n in LEG_NAMES))
        for label, tl, acc in CASES:
            r, fell = run(tl, acc, grav)
            if r is None:
                print(f"  {label:32s} FELL at step {fell}")
                continue
            print(f"  {label:32s} " + " ".join(f"{v:5.2f}" for v in r))


if __name__ == "__main__":
    main()
