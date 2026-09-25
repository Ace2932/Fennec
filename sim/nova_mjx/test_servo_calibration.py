"""#463: the sim's position-mode servo must track a goal sine the way the REAL
STS3215 does (docs/bench/leg_sine15_*.csv, 2026-09-25 hardware test: ±15 deg,
no load — ratio 0.53 at 1.4 Hz, 0.27 at 2 Hz, whatever GOAL_ACC says).

Robot hung (g = 0, like the unloaded bench servo), FL knee driven with a ±15 deg
goal sine at 50 Hz, achieved/commanded peak-to-peak over the second half.

  JAX_PLATFORMS=cpu python test_servo_calibration.py

Fails if POSITION_MODE_ACC_REG drifts off the bench, AND checks that the plain
actuator (no profile) is clearly distinguishable — so deleting the accel limit
cannot pass.
"""
import jax
import jax.numpy as jp
import numpy as np

from env import (NovaJoystick, goal_acc_rad, POSITION_MODE_ACC_REG,
                 POSITION_MODE_R85_254_ACC_REG)

A = np.radians(15)
BENCH = {1.4: 0.53, 2.0: 0.27}          # leg_sine15_1.4hz.csv / _2hz.csv headers
BENCH_R85_254 = {1.4: 0.97, 3.0: 0.55}  # leg_sine15_r85_254_*.csv (#466)
# known gap: at 2 Hz the bench (r85=254) reads 0.99, the sim plain actuator 0.84
# (sim no-load speed 2.8 rad/s vs ~3.8 measured) — pessimistic, not asserted.
TOL = 0.08


def ratio(reg, f):
    env = NovaJoystick(push_mag=0.0, goal_acc=goal_acc_rad(reg))
    env.sys = env.sys.replace(opt=env.sys.opt.replace(gravity=jp.zeros(3)))
    step = jax.jit(env.step)
    s = jax.jit(env.reset)(jax.random.PRNGKey(0))
    s = s.replace(info={**s.info, "delay": jp.asarray(0, s.info["delay"].dtype)})
    q = []
    for i in range(int(6 / f / 0.02) + 50):
        a = np.zeros(12, np.float32)
        a[2] = A * np.sin(2 * np.pi * f * i * 0.02) / 0.4
        s = step(s, jp.asarray(a))
        q.append(float(s.pipeline_state.q[9]))
    q = np.array(q[len(q) // 2:])
    return np.ptp(q) / (2 * A)


def main():
    for f, want in BENCH.items():
        got = ratio(POSITION_MODE_ACC_REG, f)
        assert abs(got - want) < TOL, f"{f} Hz: sim {got:.2f} vs bench {want:.2f}"
        print(f"ok  {f} Hz: sim {got:.2f} vs bench {want:.2f} (reg {POSITION_MODE_ACC_REG})")
    for f, want in BENCH_R85_254.items():
        got = ratio(POSITION_MODE_R85_254_ACC_REG, f)
        assert abs(got - want) < TOL, f"r85=254 {f} Hz: sim {got:.2f} vs bench {want:.2f}"
        print(f"ok  r85=254 {f} Hz: sim {got:.2f} vs bench {want:.2f}")
    plain = ratio(0, 1.4)
    assert plain > BENCH[1.4] + 0.25, f"plain actuator {plain:.2f} indistinguishable from bench"
    print(f"ok  plain actuator (no limit) tracks {plain:.2f} at 1.4 Hz — the limit is what matches")
    print("ALL SERVO CALIBRATION CHECKS PASSED")


if __name__ == "__main__":
    main()
