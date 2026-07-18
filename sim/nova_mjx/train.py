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

from env import NovaJoystick, make_domain_randomize


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


def print_fingerprint(env, terrain=0.0, dr_scale=1.0):
    """Print WHAT is about to be trained, before a single GPU-hour burns.

    A 60M-step run was once launched against a stale checkout: Colab's `git clone`
    fails with "destination path already exists" when the repo is already there,
    the following `%cd` succeeds anyway, and training silently proceeds on old
    code. It cost an hour, and the only reason it was caught is that eval_reward
    sat ~1000 points above what the new reward could possibly produce.

    Reads the real module constants, the real git SHA, and the LIVE env instance
    (its actual command range) — nothing here is a hand-maintained copy, so it
    cannot drift from what actually runs. `env` is the exact object handed to
    train_fn, so the printed range is the trained range.
    """
    import subprocess
    import env as _env
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL, text=True).strip()
        if subprocess.call(["git", "diff", "--quiet"], stderr=subprocess.DEVNULL) != 0:
            sha += " (+uncommitted changes)"
    except Exception:
        sha = "UNKNOWN — not a git checkout?"
    lo, hi = [float(v) for v in env._cmd_lo], [float(v) for v in env._cmd_hi]
    print("--- reward fingerprint ---------------------------------------")
    print(f"  code         : {sha}")
    print(f"  contact      : (foot_z - {_env.FOOT_RADIUS}) < {_env.CONTACT_EPS}"
          "   [radius-corrected]")
    print(f"  clearance    : COST, target foot z = {_env.FOOT_TARGET_Z}")
    print(f"  cmd stage {env._cmd_stage}  : vx[{lo[0]:+.2f},{hi[0]:+.2f}] "
          f"vy[{lo[1]:+.2f},{hi[1]:+.2f}] wz[{lo[2]:+.2f},{hi[2]:+.2f}]")
    print(f"  terrain      : {terrain:.2f}   ({'FLAT' if terrain == 0 else 'rough — sim2real robustness'})")
    print(f"  dr scale     : {dr_scale:.2f}   ({'default DR' if dr_scale == 1.0 else 'widened — transfer-conservative' if dr_scale > 1 else 'tightened'})"
          " [+torque-headroom +mass/inertia]")
    print("  Sanity: resuming the stage-1 walk evals ~2100-2500. cmd stage 2")
    print("  (reverse+lateral+turn) transiently DIPS reward as it generalizes;")
    print("  judge by a probe, not by eval_reward. A ~2700 start = stale code.")
    print("--------------------------------------------------------------")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="nova_ckpt",
                    help="checkpoint dir — put on mounted Drive on Colab")
    ap.add_argument("--timesteps", type=int, default=40_000_000,
                    help="steps to train THIS invocation (re-run to add more)")
    ap.add_argument("--num_envs", type=int, default=2048)
    ap.add_argument("--out", default="nova_policy.pkl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cmd-stage", type=int, default=2, choices=(1, 2),
                    help="command curriculum: 1 = forward-only (builds the gait "
                         "from scratch), 2 = omnidirectional (resume a stage-1 walk)")
    ap.add_argument("--terrain", type=float, default=0.0,
                    help="rough-terrain ceiling in [0,1] (per-env difficulty is "
                         "sampled [0,terrain]). 0 = flat. Resume the flat walk and "
                         "ramp gently (~0.3-0.5) for sim-to-real robustness; obs "
                         "unchanged so it stays deploy-compatible.")
    ap.add_argument("--dr-scale", type=float, default=1.0,
                    help="global domain-randomization width multiplier (1.0 = "
                         "measured-grounded defaults, >1 = wider/more conservative "
                         "for safer sim-to-real transfer). Resume a trained walk "
                         "into it like terrain; obs unchanged, deploy-compatible.")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="permit a CPU run (smoke-test only; ~100x too slow for real training)")
    args = ap.parse_args()

    env = NovaJoystick(cmd_stage=args.cmd_stage)
    print(f"JAX backend {jax.default_backend()}  devices {jax.devices()}")
    print_fingerprint(env, args.terrain, args.dr_scale)
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
        # entropy back to 1e-2: 2e-2 was too noisy (run 8 plateaued ~1050, below
        # the wiggle). The forward-only command curriculum now forces walking, so
        # heavy exploration isn't needed — clean exploitation is better.
        entropy_cost=1e-2, normalize_observations=True,
        num_evals=max(4, args.timesteps // 2_000_000),
        network_factory=net,
        randomization_fn=make_domain_randomize(args.terrain, args.dr_scale),
        save_checkpoint_path=str(run_dir),
        restore_checkpoint_path=restore, seed=args.seed)

    _, params, _ = train_fn(environment=env, progress_fn=progress,
                            policy_params_fn=save_policy)
    with open(args.out, "wb") as f:
        pickle.dump(params, f)
    logf.close()
    print(f"done ({time.time()-t0:.0f}s). policy -> {args.out}, checkpoints -> {run_dir}")


if __name__ == "__main__":
    main()
