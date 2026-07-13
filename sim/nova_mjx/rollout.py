"""Roll out a trained NOVA policy in MuJoCo and save a video.

  python rollout.py --policy nova_policy.pkl --vx 0.5 --steps 400 --out walk.mp4

Steps the policy in the MJX env with a FIXED velocity command, records the qpos
trajectory, then renders it in plain MuJoCo (follow-cam) to an mp4/gif. Runs on
CPU (slow but fine for a few-hundred-step clip) or GPU.

With no --policy it rolls out zero actions (a stand/settle) so you can test the
render path before training.

Headless (Colab/servers): set MUJOCO_GL=egl before running.
Deps: + imageio imageio-ffmpeg  (mp4; .gif needs no ffmpeg).
"""
import argparse
import functools
import pickle

import imageio
import jax
import jax.numpy as jp
import mujoco
import numpy as np

from env import NovaJoystick


def load_policy(path, obs_size, act_size):
    from brax.training.agents.ppo import networks as ppo_networks
    net = ppo_networks.make_ppo_networks(
        obs_size, act_size,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))
    make_policy = ppo_networks.make_inference_fn(net)
    with open(path, "rb") as f:
        params = pickle.load(f)
    return make_policy(params, deterministic=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=None, help="pickled PPO params; omit = stand")
    ap.add_argument("--vx", type=float, default=0.5, help="fwd command m/s")
    ap.add_argument("--wz", type=float, default=0.0, help="yaw command rad/s")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--out", default="rollout.mp4")
    args = ap.parse_args()

    env = NovaJoystick()
    cmd = jp.array([args.vx, 0.0, args.wz])

    if args.policy:
        policy = load_policy(args.policy, env.observation_size, env.action_size)
        act_fn = jax.jit(policy)
    else:
        print("no --policy -> zero-action stand rollout (render-path test)")
        act_fn = None

    jit_reset, jit_step = jax.jit(env.reset), jax.jit(env.step)
    rng = jax.random.PRNGKey(0)
    state = jit_reset(rng)
    state = state.replace(info={**state.info, "cmd": cmd})

    qpos = [np.array(state.pipeline_state.q)]
    for _ in range(args.steps):
        rng, k = jax.random.split(rng)
        if act_fn is not None:
            action, _ = act_fn(state.obs, k)
        else:
            action = jp.zeros(env.action_size)
        state = jit_step(state, action)
        state = state.replace(info={**state.info, "cmd": cmd})  # hold command
        qpos.append(np.array(state.pipeline_state.q))
        if float(state.done) > 0.5:
            print(f"  fell at step {len(qpos)}")
            break

    # render the qpos trajectory in plain MuJoCo
    m = mujoco.MjModel.from_xml_path("nova.xml")
    d = mujoco.MjData(m)
    cam = m.camera("track").id
    with mujoco.Renderer(m, height=480, width=640) as r:
        frames = []
        for q in qpos:
            d.qpos[:] = q
            mujoco.mj_forward(m, d)
            r.update_scene(d, camera=cam)
            frames.append(r.render())

    fps = 50
    if args.out.endswith(".gif"):
        imageio.mimsave(args.out, frames, fps=fps)
    else:
        imageio.mimsave(args.out, frames, fps=fps, macro_block_size=None)
    x_travel = qpos[-1][0] - qpos[0][0]
    print(f"wrote {args.out}  ({len(frames)} frames, {len(frames)/fps:.1f}s, "
          f"traveled {x_travel:+.2f} m in x)")


if __name__ == "__main__":
    main()
