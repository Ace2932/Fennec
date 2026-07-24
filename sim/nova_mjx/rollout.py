"""Roll out a trained NOVA policy in MuJoCo and save a video.

  python rollout.py --policy nova_policy.pkl --vx 0.5 --steps 400 --out walk.mp4

Steps the policy in the MJX env with a FIXED velocity command, records the qpos
trajectory, then renders it in plain MuJoCo (follow-cam) to an mp4/gif. Runs on
CPU (slow but fine for a few-hundred-step clip) or GPU.

With no --policy it rolls out zero actions (a stand/settle) so you can test the
render path before training.

Headless (Colab/servers): auto-uses EGL (set below) — no display needed.
Deps: + imageio imageio-ffmpeg  (mp4; .gif needs no ffmpeg).
"""
import argparse
import functools
import os
import pickle

# Headless OpenGL for the render (Colab / servers have no X display). MUST be
# set before `import mujoco`. setdefault so an explicit MUJOCO_GL still wins
# (e.g. MUJOCO_GL=osmesa if EGL is unavailable).
os.environ.setdefault("MUJOCO_GL", "egl")

import imageio
import jax
import jax.numpy as jp
import mujoco
import numpy as np

from env import NovaJoystick


def load_policy(path, obs_size, act_size):
    from brax.training.acme import running_statistics
    from brax.training.agents.ppo import networks as ppo_networks
    # ⚠ MUST match training: train.py runs normalize_observations=True, so the
    # policy was trained on NORMALIZED obs. make_ppo_networks DEFAULTS to an
    # identity preprocessor, which silently IGNORES the pickled normalizer params
    # and feeds the net raw obs -> out-of-distribution inputs -> degraded, wrong
    # behavior. (Same gotcha already fixed in export_policy.py; this file was
    # missed — every earlier rollout video rendered a mis-driven policy.)
    net = ppo_networks.make_ppo_networks(
        obs_size, act_size,
        preprocess_observations_fn=running_statistics.normalize,
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
    ap.add_argument("--heightmap", action="store_true",
                    help="build the height-map env (obs +HM_N^2) for a tier-2 teacher")
    ap.add_argument("--stair-level", type=float, default=0.0,
                    help="inject a STAIRCASE (rise STAIR_RISE*level) into the single-env "
                         "terrain so you can watch the teacher climb. Needs --heightmap.")
    ap.add_argument("--cmd-c", type=float, default=None,
                    help="force the commanded footswing height info['cmd_c'] (lift-v5) to "
                         "this fixed value, re-pinned every step so the env's 250-step "
                         "resample can't drift it. Omit = env's own random schedule "
                         "(U(0.015,0.06) at reset/resample) — needed so a stair probe isn't "
                         "judged at a randomly-low lift command.")
    args = ap.parse_args()

    env = NovaJoystick(heightmap=args.heightmap)
    if args.stair_level > 0:            # inject stairs into this env's hfield
        import jax.numpy as _jp
        from terrain import terrain_field
        hf = terrain_field(jax.random.PRNGKey(0), args.stair_level, 0.0, 1.0)
        env.sys = env.sys.tree_replace({"hfield_data": _jp.asarray(hf)})
    cmd = jp.array([args.vx, 0.0, args.wz])
    cmd_c_j = jp.asarray(args.cmd_c) if args.cmd_c is not None else None

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
    if cmd_c_j is not None:          # force the commanded footswing (lift-v5)
        state = state.replace(info={**state.info, "cmd_c": cmd_c_j})

    # base z at spawn, to report net climb (world z) alongside x travel — the
    # eyeball check that a stair teacher actually gained elevation, not just
    # translated across a flat.
    z0 = float(state.pipeline_state.x.pos[0, 2])
    qpos = [np.array(state.pipeline_state.q)]
    for _ in range(args.steps):
        rng, k = jax.random.split(rng)
        if act_fn is not None:
            action, _ = act_fn(state.obs, k)
        else:
            action = jp.zeros(env.action_size)
        state = jit_step(state, action)
        state = state.replace(info={**state.info, "cmd": cmd})  # hold command
        if cmd_c_j is not None:      # re-pin: survives the env's 250-step resample
            state = state.replace(info={**state.info, "cmd_c": cmd_c_j})
        qpos.append(np.array(state.pipeline_state.q))
        if float(state.done) > 0.5:
            print(f"  fell at step {len(qpos)}")
            break

    # render the qpos trajectory in plain MuJoCo
    m = mujoco.MjModel.from_xml_path("nova.xml")
    if args.stair_level > 0:            # show the SAME terrain the policy was driven on
        import numpy as _np
        from terrain import terrain_field as _tf
        m.hfield_data[:] = _np.asarray(_tf(jax.random.PRNGKey(0), args.stair_level, 0.0, 1.0))
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
    climbed = float(state.pipeline_state.x.pos[0, 2]) - z0
    print(f"wrote {args.out}  ({len(frames)} frames, {len(frames)/fps:.1f}s, "
          f"traveled {x_travel:+.2f} m in x, climbed {climbed:+.2f} m in z)")


if __name__ == "__main__":
    main()
