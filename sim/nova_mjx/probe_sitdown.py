"""HOW LONG DOES THE CONTROLLED-LIMP SIT ACTUALLY TAKE? (#142)

The fault path is meant to drive to backlog #15's sit and THEN cut torque, so the
pack lands on the skid rails instead of the robot collapsing on it. That means an
E-stop is followed by a bounded window of powered motion, and the window has to be
justified rather than guessed.

Bounds, before simulating anything:
  * firmware slew limiter (NOVA_SLEW_MAX_DELTA 20 raw / broadcast @ 100 Hz)
    = 175.8 deg/s, and the haa travel 0 -> 40 deg dominates -> 227 ms floor.
  * free fall over the same 11.2 cm drop = 151 ms.
So the slew floor is only ~1.5x slower than gravity: at the limiter the "controlled"
sit is very nearly a drop. The useful number is the shortest blend that still LANDS
SOFTLY, which is what this measures — peak descent speed, peak contact force, and
torque saturation vs blend duration, through the real position servos.

  MUJOCO_GL=cgl ../../.venv/bin/python probe_sitdown.py
"""
import os
import sys

import numpy as np
import mujoco

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import LEG_NAMES   # noqa: E402
from build_mjcf import EFF_HIP, EFF_LEG   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
D = np.radians
SIDE = {"FL": +1.0, "FR": -1.0, "RL": +1.0, "RR": -1.0}
DT = 0.004
SIT_LEG = (D(40.0), D(40.0), D(-90.0))
STAND_LEG = (0.0, 0.600, -1.200)
TAU = np.array([EFF_HIP, EFF_LEG, EFF_LEG] * 4)
SLEW_DPS = 20 * (360.0 / 4095.0) * 100.0        # firmware limiter, deg/s
WEIGHT = (2.83 + 4 * (0.0836 + 0.1219 + 0.1110 + 0.0039)) * 9.81


def vec(pose):
    return np.array([v * (SIDE[leg] if j == 0 else 1.0)
                     for leg in LEG_NAMES for j, v in enumerate(pose[leg])])


def min_jerk(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (10.0 + t * (-15.0 + 6.0 * t))


def total_contact_force(m, d):
    tot = 0.0
    buf = np.zeros(6)
    for k in range(d.ncon):
        mujoco.mj_contactForce(m, d, k, buf)
        tot += abs(buf[0])                      # normal component
    return tot


def main():
    m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "nova.xml"))
    m.hfield_data[:] = 0.0
    d = mujoco.MjData(m)
    stand, sit = vec({l: STAND_LEG for l in LEG_NAMES}), vec({l: SIT_LEG for l in LEG_NAMES})

    print("=" * 100)
    print("CONTROLLED-LIMP SIT — descent quality vs commanded blend duration")
    print(f"firmware slew floor 227 ms | free fall 151 ms | static weight {WEIGHT:.1f} N")
    print("=" * 100)
    print(f"{'blend':>7} {'slew-capped?':>13} {'peak descent':>13} {'peak contact':>13} "
          f"{'x static':>9} {'sat pk':>7}  landing")

    for blend_s in (0.227, 0.35, 0.5, 0.75, 1.0, 1.5, 3.0):
        # settle standing
        d.qpos[:] = 0.0
        d.qpos[0:7] = [0, 0, 0.20, 1, 0, 0, 0]
        d.qpos[7:] = stand
        d.qvel[:] = 0.0
        d.ctrl[:] = stand
        for _ in range(3000):
            mujoco.mj_step(m, d)

        n = int(blend_s / DT)
        prev = d.ctrl.copy()
        max_rate, vz_min, f_max, sat_max = 0.0, 0.0, 0.0, 0.0
        for k in range(n + int(2.0 / DT)):
            s = min_jerk(k / max(n, 1))
            want = stand + s * (sit - stand)
            # emulate the firmware slew limiter on the commanded goal
            step_cap = D(SLEW_DPS) * DT
            delta = np.clip(want - prev, -step_cap, step_cap)
            d.ctrl[:] = prev + delta
            max_rate = max(max_rate, np.degrees(np.abs(delta).max()) / DT)
            prev = d.ctrl.copy()
            mujoco.mj_step(m, d)
            vz_min = min(vz_min, d.qvel[2])
            f_max = max(f_max, total_contact_force(m, d))
            sat_max = max(sat_max, np.mean(np.abs(d.actuator_force) >= 0.99 * TAU))
        capped = "YES" if max_rate >= SLEW_DPS - 1 else "no"
        ratio = f_max / WEIGHT
        land = ("HARD" if ratio > 3.0 else "firm" if ratio > 2.0 else "soft")
        print(f"{blend_s*1000:6.0f}ms {capped:>13} {vz_min*100:10.1f} cm/s "
              f"{f_max:10.1f} N {ratio:8.2f}x {sat_max*100:6.1f}%  {land}")

    print("\npeak contact / static weight: 1.0x = resting, >2x = firm, >3x = slam")


if __name__ == "__main__":
    main()
