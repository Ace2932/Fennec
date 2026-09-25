"""IK swing-reference deploy parity (gait study): the numpy runner must produce
the SAME reference offsets and the SAME phase clock as sim env.py under
ref_gait, and must refuse a 107-d policy that doesn't carry the reference.

  JAX_PLATFORMS=cpu python deploy/test_ref_runner.py
"""
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "ros2_ws", "src", "nova_locomotion",
                                "nova_locomotion"))


def _npz(path, obs_dim, ref):
    from env import (ACTION_SCALE, DEFAULT_POSE, HIST, PROP, CMD_OBS_SCALE, REF_HEIGHT,
                     REF_DZ_MAX, BLIND_CMD_F, GAIT_OFFSETS, GAIT_DUTY, ref_lift_table)
    b = {"mean": np.zeros(obs_dim, np.float32), "std": np.ones(obs_dim, np.float32),
         "action_scale": np.float32(ACTION_SCALE),
         "default_pose": np.asarray(DEFAULT_POSE, np.float32),
         "W0": np.zeros((obs_dim, 24), np.float32), "b0": np.zeros(24, np.float32),
         "hist": np.int64(HIST), "prop": np.int64(PROP),
         "cmd_scale": np.asarray(CMD_OBS_SCALE, np.float32)}
    if ref:
        b.update({"ref_table": np.asarray(ref_lift_table(), np.float32),
                  "ref_height": np.float32(REF_HEIGHT), "ref_dz_max": np.float32(REF_DZ_MAX),
                  "ref_freq": np.float32(BLIND_CMD_F),
                  "gait_offsets": np.asarray(GAIT_OFFSETS, np.float32),
                  "gait_duty": np.float32(GAIT_DUTY)})
    np.savez(path, **b)
    return path


def main():
    import jax
    import jax.numpy as jp
    from policy_runner import NovaPolicy
    from env import NovaJoystick

    d = tempfile.mkdtemp()
    pol = NovaPolicy(_npz(os.path.join(d, "ref.npz"), 107, True))
    env = NovaJoystick(ref_gait=True)

    # 1. reference offsets, dense phase sweep
    th = np.linspace(0.0, 1.0, 401, endpoint=False)
    sim = np.asarray(jax.vmap(env._ref_offset)(jp.asarray(th)))
    run = np.stack([pol.ref_offset(t) for t in th])
    err = np.abs(sim - run).max()
    assert err < 1e-5, f"ref_offset mismatch {err}"
    assert np.abs(sim).max() > 0.2, "reference never moves — test is vacuous"
    print(f"ok  ref_offset parity over 401 phases, max|err| {err:.1e}")

    # 2. clock: runner phase advance + obs clock dims == env gait_phase / obs[-2:]
    s = jax.jit(env.reset)(jax.random.PRNGKey(3))
    s = s.replace(info={**s.info, "delay": jp.asarray(0, s.info["delay"].dtype)})
    step = jax.jit(env.step)
    pol.reset()
    pol.phase = float(s.info["gait_phase"])
    for _ in range(60):
        o = np.asarray(s.obs)
        g = np.array([0, 0, -1.0])
        ro = pol.build_obs(np.zeros(3), g, np.asarray(s.info["cmd"]), np.zeros(12), np.zeros(12))
        assert np.allclose(ro[-2:], o[-2:], atol=1e-5), (ro[-2:], o[-2:])
        pol.joint_targets(np.zeros(3), g, np.asarray(s.info["cmd"]), np.zeros(12), np.zeros(12))
        s = step(s, jp.zeros(12))
    assert abs(pol.phase - float(s.info["gait_phase"])) < 1e-4
    print("ok  phase clock + obs clock dims track env over 60 steps")

    # 3. contract: a 107-d policy WITHOUT the reference must be refused
    try:
        NovaPolicy(_npz(os.path.join(d, "noref.npz"), 107, False))
    except ValueError:
        print("ok  107-d policy without reference refused")
    else:
        raise AssertionError("107-d policy without the reference loaded")
    NovaPolicy(_npz(os.path.join(d, "plain.npz"), 105, False))
    print("ok  plain 105-d policy still loads")
    print("ALL REF RUNNER CHECKS PASSED")


if __name__ == "__main__":
    main()
