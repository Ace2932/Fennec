"""Cross-check the Jetson policy runner against the SIM env — the obs the robot
builds must equal the obs the policy trained on, or transfer silently fails.

Needs the sim venv (jax/brax/mujoco). Run from sim/nova_mjx/:
  JAX_PLATFORMS=cpu python deploy/test_policy_runner.py
"""
import os
import pickle
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _export_untrained_npz(path):
    import jax
    import jax.numpy as jp
    from brax.training.acme import running_statistics, specs
    from brax.training.agents.ppo import networks as ppo_networks
    from export_policy import extract
    from env import ACTION_SCALE, DEFAULT_POSE
    from env import HIST, PROP
    obs = HIST * PROP + 3 + 12                          # 105
    net = ppo_networks.make_ppo_networks(
        obs, 12, preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))
    norm = running_statistics.init_state(specs.Array((obs,), jp.float32))
    norm = running_statistics.update(
        norm, jax.random.normal(jax.random.PRNGKey(1), (2048, obs)))
    params = (norm, net.policy_network.init(jax.random.PRNGKey(2)))
    mean, std, W, b = extract(params)
    bundle = {"mean": mean, "std": std,
              "action_scale": np.float32(ACTION_SCALE),
              "default_pose": np.asarray(DEFAULT_POSE, np.float32)}
    for i, (Wi, bi) in enumerate(zip(W, b)):
        bundle[f"W{i}"], bundle[f"b{i}"] = Wi, bi
    np.savez(path, **bundle)
    return params, net


def main():
    import jax
    import jax.numpy as jp
    from brax import math
    from brax.training.agents.ppo import networks as ppo_networks
    from policy_runner import NovaPolicy
    from env import NovaJoystick

    npz = os.path.join(tempfile.mkdtemp(), "p.npz")
    params, net = _export_untrained_npz(npz)

    env = NovaJoystick()
    st = jax.jit(env.reset)(jax.random.PRNGKey(0))
    ps, info = st.pipeline_state, st.info

    # raw quantities exactly as the real robot would report them. The IMU
    # reading is BIASED (the env adds a per-episode gyro bias to the frame) —
    # the runner receives that biased reading, so include it here too.
    quat = ps.q[3:7]
    qinv = math.quat_inv(quat)
    gyro = np.asarray(math.rotate(ps.xd.ang[0], qinv) + info["gyro_bias"])
    proj_grav = np.asarray(math.rotate(jp.array([0., 0., -1.]), qinv))
    jpos = np.asarray(ps.q[7:])
    jvel = np.asarray(ps.qd[6:])
    cmd = np.asarray(info["cmd"])

    # ground-truth CLEAN obs (env formula, no noise): frame tiled x HIST + cmd
    # + last_act (env fills the history with frame 0 on reset).
    default = np.asarray(env._default_pose)
    frame = np.concatenate([gyro * 0.25, proj_grav, jpos - default, jvel * 0.05])
    expected = np.concatenate([
        np.tile(frame, 3), cmd * np.array([2., 2., .25]),
        np.asarray(info["last_act"])])

    pol = NovaPolicy(npz)
    pol.last_action = np.asarray(info["last_act"], np.float32)
    obs = pol.build_obs(gyro, proj_grav, cmd, jpos, jvel)

    err = float(np.max(np.abs(obs - expected)))
    assert obs.shape == (105,), obs.shape
    assert err < 1e-5, f"OBS MISMATCH {err} — deployment obs != training obs!"
    print(f"OK  build_obs matches sim env obs (max|err| {err:.2e}, dim {obs.shape[0]})")

    # numpy inference matches the Brax deterministic policy on that obs
    infer = ppo_networks.make_inference_fn(net)(params, deterministic=True)
    a_brax = np.asarray(infer(jp.asarray(expected), jax.random.PRNGKey(0))[0])
    a_np = pol.infer(expected.astype(np.float32))
    aerr = float(np.max(np.abs(a_brax - a_np)))
    assert aerr < 1e-4, f"INFER MISMATCH {aerr}"
    print(f"OK  numpy infer matches Brax policy (max|err| {aerr:.2e})")

    tgt = pol.joint_targets(gyro, proj_grav, cmd, jpos, jvel)
    assert tgt.shape == (12,) and np.all(np.abs(tgt - default) <= env.action_size)
    print(f"OK  joint_targets shape {tgt.shape}, near default pose")
    print("ALL DEPLOY CROSS-CHECKS PASSED")


if __name__ == "__main__":
    main()
