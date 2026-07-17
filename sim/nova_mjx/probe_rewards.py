"""Dump the per-term reward decomposition for a trained NOVA policy.

  python probe_rewards.py --policy nova_policy.pkl --vx 0.25 --steps 400

Answers "WHICH term is the policy actually being paid by?" — the question the
rollout VIDEO can't. Steps the policy exactly like rollout.py (same normalizer
fix), averages every WEIGHTED reward term over the episode, and ranks them.

Reads terms straight out of `state.metrics`, which env.py builds from the same
named variables it sums into `reward` — so this can't drift from the real
reward. No reward logic lives here.

Read the output like this:
  * `w_clearance` large and positive while `w_progress` is small
        -> the policy is paid more to wave feet than to travel. Farm.
  * `air_RR` ~1.0 while air_FL/FR/RL cycle ~0.3-0.5
        -> the rear-right leg is CARRIED, not stepping.
  * `swing_xy_speed`
        -> the multiplier the clearance term pays on. Everything about the
           clearance farm's magnitude hinges on this number.
"""
import argparse

# NOTE: deliberately does NOT set MUJOCO_GL. This probe never renders — it only
# steps the env — so it needs no GL backend at all, and forcing one (rollout.py
# sets egl for its renderer) just breaks the import on machines without it.

import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick
from rollout import load_policy      # reuse the normalizer-correct loader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=None, help="pickled PPO params; omit = stand")
    ap.add_argument("--vx", type=float, default=0.25, help="fwd command m/s")
    ap.add_argument("--wz", type=float, default=0.0, help="yaw command rad/s")
    ap.add_argument("--steps", type=int, default=400)
    args = ap.parse_args()

    env = NovaJoystick()
    cmd = jp.array([args.vx, 0.0, args.wz])

    if args.policy:
        act_fn = jax.jit(load_policy(args.policy, env.observation_size, env.action_size))
    else:
        print("no --policy -> zero-action stand (baseline)")
        act_fn = None

    jit_reset, jit_step = jax.jit(env.reset), jax.jit(env.step)
    rng = jax.random.PRNGKey(0)
    state = jit_reset(rng)
    state = state.replace(info={**state.info, "cmd": cmd})

    acc, rewards, n = {}, [], 0
    x0 = float(state.pipeline_state.q[0])
    for _ in range(args.steps):
        rng, k = jax.random.split(rng)
        action = act_fn(state.obs, k)[0] if act_fn else jp.zeros(env.action_size)
        state = jit_step(state, action)
        state = state.replace(info={**state.info, "cmd": cmd})   # hold command
        for key, v in state.metrics.items():
            acc[key] = acc.get(key, 0.0) + float(v)
        rewards.append(float(state.reward))
        n += 1
        if float(state.done) > 0.5:
            print(f"  fell at step {n}")
            break

    mean = {k: v / n for k, v in acc.items()}
    x_travel = float(state.pipeline_state.q[0]) - x0

    print(f"\ncmd vx={args.vx} wz={args.wz} | {n} steps ({n/50:.1f}s) | "
          f"traveled {x_travel:+.3f} m | mean reward {np.mean(rewards):+.3f}/step")

    print("\n-- WEIGHTED reward terms, mean per step (ranked by |magnitude|) --")
    terms = {k[2:]: v for k, v in mean.items() if k.startswith("w_")}
    total_pos = sum(v for v in terms.values() if v > 0)
    for k, v in sorted(terms.items(), key=lambda kv: -abs(kv[1])):
        share = f"{100*v/total_pos:5.1f}% of + " if v > 0 and total_pos > 0 else " " * 12
        print(f"  {k:>10}: {v:+8.4f}   {share}")
    print(f"  {'SUM':>10}: {sum(terms.values())+0.1:+8.4f}   (+0.1 alive bonus)")

    print("\n-- per-foot airborne fraction (1.0 = never touches down) --")
    for f in ("FL", "FR", "RL", "RR"):
        v = mean[f"air_{f}"]
        flag = "  <-- CARRIED?" if v > 0.85 else ("  <-- barely lifts" if v < 0.05 else "")
        print(f"  {f}: {v:.3f}{flag}")

    print(f"\n-- diagnostics --")
    print(f"  swing_xy_speed : {mean['swing_xy_speed']:.3f} m/s   "
          f"(the clearance term's multiplier)")
    print(f"  fwd_speed      : {mean['fwd_speed']:.3f} m/s   (along command)")
    print(f"  move_gate      : {mean['move_gate']:.3f}       (0=shapers off, 1=full)")


if __name__ == "__main__":
    main()
