"""Train a NOVA walking policy with Brax PPO on the MJX env — CHECKPOINTED so a
Colab disconnect / crash mid-run costs nothing.

  python train.py --ckpt /content/drive/MyDrive/nova_ckpt --timesteps 40_000_000

Resilience:
  * Brax writes a full-state checkpoint (params + normalizer) every eval to
    --ckpt. Put --ckpt on PERSISTENT storage (mounted Google Drive) — Colab's
    /content is wiped on disconnect, so a local checkpoint dies with the run.
  * On (re)start it finds the LATEST checkpoint under --ckpt (by mtime, robust
    across many resumes) and CONTINUES from it. So after any dropout you just
    re-run the same cell — it picks up where the last checkpoint left off.
  * Each run saves to its own subdir (no step-number collisions between runs),
    plus a flat nova_policy.pkl (latest policy, for rollout.py) and a CSV log —
    both survive a dropout.

Re-run to keep training; watch eval_reward climb. GPU (Colab) for real runs.
"""
import argparse
import functools
import os
import pickle
import time

import jax
from etils import epath

from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo

from env import NovaJoystick, domain_randomize


def find_latest_checkpoint(ckpt_dir):
    """Newest Brax checkpoint under ckpt_dir, by mtime — correct even across
    many resumes (each run writes its own run_*/<step>/ dir; Brax restarts its
    step counter on restore, so mtime, not step number, is the right key).
    Brax names each checkpoint dir with the zero-padded step (e.g. 000000006400)
    and stores orbax data inside — so we match all-digit dir names."""
    best, best_m = None, -1.0
    for dirpath, _, _ in os.walk(ckpt_dir):
        if os.path.basename(dirpath).isdigit():
            m = os.path.getmtime(dirpath)
            if m > best_m:
                best_m, best = m, dirpath
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="nova_ckpt",
                    help="checkpoint dir — put on mounted Drive on Colab")
    ap.add_argument("--timesteps", type=int, default=40_000_000,
                    help="steps to train THIS invocation (re-run to add more)")
    ap.add_argument("--num_envs", type=int, default=2048)
    ap.add_argument("--out", default="nova_policy.pkl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--allow-cpu", action="store_true",
                    help="permit a CPU run (smoke-test only; ~100x too slow for real training)")
    args = ap.parse_args()

    print(f"JAX backend {jax.default_backend()}  devices {jax.devices()}")
    if jax.default_backend() == "cpu" and not args.allow_cpu:
        raise SystemExit(
            "✗ JAX is on CPU — real training would take days, not minutes.\n"
            "  Set the Colab runtime to GPU (Runtime > Change runtime type > GPU),\n"
            "  re-run the deps-install cell, then re-run this. If the GPU won't\n"
            "  allocate, you've likely hit the free-tier quota (wait ~24h or use\n"
            "  Colab Pro). Pass --allow-cpu only to force a slow smoke-test.")

    root = epath.Path(args.ckpt)
    root.mkdir(parents=True, exist_ok=True)
    restore = find_latest_checkpoint(args.ckpt)
    print(f"RESUME from {restore}" if restore else "FRESH start (no checkpoint)")
    # unique per-run save subdir -> no step collisions between resumes
    run_dir = root / f"run_{int(time.time())}"

    net = functools.partial(
        ppo_networks.make_ppo_networks,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))

    logf = (root / "train_log.csv").open("a")
    t0 = time.time()

    def progress(step, metrics):
        r = float(metrics.get("eval/episode_reward", float("nan")))
        print(f"[{time.time()-t0:6.0f}s] step {step:>11,}  eval_reward {r:8.2f}")
        logf.write(f"{time.time():.0f},{step},{r}\n"); logf.flush()

    def save_policy(step, make_policy, params):
        with open(args.out, "wb") as f:      # latest policy for rollout.py
            pickle.dump(params, f)

    train_fn = functools.partial(
        ppo.train,
        num_timesteps=args.timesteps, episode_length=1000,
        num_envs=args.num_envs, batch_size=256,
        num_minibatches=32, num_updates_per_batch=4,
        unroll_length=20, discounting=0.97, learning_rate=3e-4,
        entropy_cost=1e-2, normalize_observations=True,
        num_evals=max(4, args.timesteps // 2_000_000),
        network_factory=net, randomization_fn=domain_randomize,
        save_checkpoint_path=str(run_dir),
        restore_checkpoint_path=restore, seed=args.seed)

    _, params, _ = train_fn(environment=NovaJoystick(), progress_fn=progress,
                            policy_params_fn=save_policy)
    with open(args.out, "wb") as f:
        pickle.dump(params, f)
    logf.close()
    print(f"done ({time.time()-t0:.0f}s). policy -> {args.out}, checkpoints -> {run_dir}")


if __name__ == "__main__":
    main()
