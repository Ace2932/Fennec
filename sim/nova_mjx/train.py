"""Train a NOVA walking policy with Brax PPO on the MJX env.

Runs on a GPU (Colab free T4 is enough). On a CPU it will import + start but is
too slow for a full run — use it locally only to smoke-test, train on Colab.

  python train.py --timesteps 60_000_000 --out nova_policy.pkl

Outputs a pickled (params) file + prints eval reward as it goes. Convert the
policy to ONNX for Jetson deployment separately (see README).
"""
import argparse
import functools
import pickle
import time

import jax
from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo

from env import NovaJoystick, domain_randomize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timesteps", type=int, default=60_000_000)
    ap.add_argument("--out", default="nova_policy.pkl")
    ap.add_argument("--num_envs", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    print(f"JAX backend: {jax.default_backend()}  devices: {jax.devices()}")
    if jax.default_backend() == "cpu":
        print("⚠ CPU backend — fine for a smoke test, far too slow for a real "
              "run. Train on a GPU (Colab).")

    net = functools.partial(
        ppo_networks.make_ppo_networks,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))

    train_fn = functools.partial(
        ppo.train,
        num_timesteps=args.timesteps,
        num_evals=max(2, args.timesteps // 3_000_000),
        episode_length=1000,
        unroll_length=20,
        num_minibatches=32,
        num_updates_per_batch=4,
        discounting=0.97,
        learning_rate=3e-4,
        entropy_cost=1e-2,
        num_envs=args.num_envs,
        batch_size=256,
        network_factory=net,
        randomization_fn=domain_randomize,
        seed=args.seed,
    )

    t0 = time.time()

    def progress(step, metrics):
        r = metrics.get("eval/episode_reward", float("nan"))
        print(f"[{time.time()-t0:6.0f}s] step {step:>12,}  "
              f"eval_reward {r:8.2f}")

    make_inference_fn, params, _ = train_fn(
        environment=NovaJoystick(), progress_fn=progress)

    with open(args.out, "wb") as f:
        pickle.dump(params, f)
    print(f"saved policy -> {args.out}  ({time.time()-t0:.0f}s total)")


if __name__ == "__main__":
    main()
