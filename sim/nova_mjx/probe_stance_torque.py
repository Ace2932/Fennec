"""Can the knees HOLD a trot's stance at the firmware torque limit?

Static hold, nominal model, pushes off, latency 0, 2 s per case:
  4-leg   all feet down, zero action (the stand)
  2-leg   FR + RL lifted 2 cm by the IK lift table -> FL + RR carry the robot,
          which is the load every trot stance phase puts on a diagonal pair
at TORQUE_LIMIT fractions 1.0 / 0.8 / 0.6 (firmware today) / 0.45.

Prints the settled base height (stand = 0.176 m) and each leg's kfe torque as a
fraction of its CAPPED forcerange (1.00 = saturated, the leg is sagging). Also
prints the hand estimate the sim should agree with:
  knee torque = (m g / n_stance) * horizontal knee->foot distance at the stand.

Gate (exit 1): at full torque the 4-leg stand must hold (base >= 0.165 m). If
it doesn't, the model is broken and the other rows mean nothing.

  JAX_PLATFORMS=cpu python probe_stance_torque.py
"""
import sys

import jax
import jax.numpy as jp
import mujoco
import numpy as np

from env import NovaJoystick, ref_lift_table, ACTION_SCALE, LEG_NAMES, DEFAULT_POSE

LIMITS = (1.0, 0.8, 0.6, 0.45)
STEPS = 100
KNEE_BODY = "FL_lower"      # its origin is the kfe joint


def hand_estimate():
    m = mujoco.MjModel.from_xml_path("nova.xml")
    d = mujoco.MjData(m)
    d.qpos[:] = m.qpos0
    d.qpos[7:] = np.asarray(DEFAULT_POSE)
    mujoco.mj_forward(m, d)
    R = d.xmat[1].reshape(3, 3)
    knee = R.T @ (d.xpos[m.body(KNEE_BODY).id] - d.xpos[1])
    foot = R.T @ (d.xpos[m.body("FL_foot").id] - d.xpos[1])
    arm = abs(foot[0] - knee[0])
    mg = float(m.body_mass.sum()) * 9.81
    return float(m.body_mass.sum()), arm, mg / 4 * arm, mg / 2 * arm


def hold(tl, lifted):
    env = NovaJoystick(push_mag=0.0, torque_limit=tl)
    s = jax.jit(env.reset)(jax.random.PRNGKey(0))
    s = s.replace(info={**s.info, "delay": jp.asarray(0, s.info["delay"].dtype)})
    step = jax.jit(env.step)
    tab = np.asarray(ref_lift_table())
    a = np.zeros(12, np.float32)
    for li in lifted:
        a[3 * li + 1], a[3 * li + 2] = tab[8] / ACTION_SCALE      # 2 cm lift
    lim = np.asarray(env.sys.actuator_forcerange[:, 1])
    util = []
    for _ in range(STEPS):
        s = step(s, jp.asarray(a))
        util.append(np.abs(np.asarray(s.pipeline_state.qfrc_actuator[6:])) / lim)
    u = np.array(util)[STEPS // 2:].mean(0)
    return float(s.pipeline_state.x.pos[0, 2]), u[[2, 5, 8, 11]], lim[2]


def main():
    mass, arm, t4, t2 = hand_estimate()
    print(f"robot {mass:.2f} kg, knee->foot horizontal arm at the stand {arm*100:.1f} cm")
    print(f"hand estimate: 4-leg {t4:.2f} N*m/knee ({t4/1.8:.0%} of 1.8 stall), "
          f"2-leg {t2:.2f} N*m/knee ({t2/1.8:.0%})\n")
    print(f"{'case':7s} {'TL':>5s} {'cap N*m':>8s} {'base z':>7s}   kfe util  "
          + " ".join(f"{n:>4s}" for n in LEG_NAMES))
    ok = True
    for name, lifted in (("4-leg", ()), ("2-leg", (1, 2))):
        for tl in LIMITS:
            z, u, cap = hold(tl, lifted)
            if name == "4-leg" and tl == 1.0 and z < 0.165:
                ok = False
            print(f"{name:7s} {tl:5.2f} {cap:8.2f} {z:7.3f}             "
                  + " ".join(f"{v:4.2f}" for v in u))
    if not ok:
        print("FAIL: the full-torque 4-leg stand does not hold -> model broken")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
