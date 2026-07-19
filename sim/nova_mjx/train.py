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


def print_fingerprint(env, terrain=0.0, dr_scale=1.0, step_frac=0.0, stair_frac=0.0):
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
    if step_frac > 0:
        import terrain as _terr
        print(f"  step terrain : {step_frac:.2f} of envs quantized to discrete steps "
              f"(STEP_M={_terr.STEP_M}m)   [blind curb/step, needs terrain>0]")
    if stair_frac > 0:
        import terrain as _terr
        print(f"  STAIRCASE    : {stair_frac:.2f} of envs (rise {_terr.STAIR_RISE}m*level) "
              f"[tier-2 teacher, needs terrain>0 + --heightmap]")
    if getattr(env, "_heightmap", False):
        import env as _e
        print(f"  HEIGHT MAP   : ON — obs +{_e.HM_N**2} ({_e.HM_N}x{_e.HM_N} grid, +-{_e.HM_EXTENT}m) "
              f"= {env.observation_size}. PRIVILEGED (perfect) teacher map; NOT the "
              f"real D456/L2 view. Needs a grafted init + heightmap runner to deploy.")
    print("  Sanity: resuming the stage-1 walk evals ~2100-2500. cmd stage 2")
    print("  (reverse+lateral+turn) transiently DIPS reward as it generalizes;")
    print("  judge by a probe, not by eval_reward. A ~2700 start = stale code.")
    print("--------------------------------------------------------------")


def run_stage(env, args, terrain, stair_frac, timesteps, ckpt_dir, restore,
              restore_params, t0, logf):
    """One PPO training segment at a FIXED difficulty. Brax freezes per-env terrain
    at env construction, so an auto-ramp curriculum = several of these chained, each
    resuming the previous stage's full checkpoint (policy+value+normalizer) at a
    higher `terrain`. Writes the flat nova_policy.pkl every eval so a mid-stage
    dropout still leaves a usable policy. Returns the final params."""
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    net = functools.partial(
        ppo_networks.make_ppo_networks,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))

    def progress(step, metrics):
        r = float(metrics.get("eval/episode_reward", float("nan")))
        print(f"[{time.time()-t0:6.0f}s] step {step:>11,}  eval_reward {r:8.2f}")
        logf.write(f"{time.time():.0f},{step},{r}\n"); logf.flush()

    def save_policy(step, make_policy, params):
        with open(args.out, "wb") as f:      # latest policy for rollout.py
            pickle.dump(params, f)

    train_fn = functools.partial(
        ppo.train,
        num_timesteps=timesteps, episode_length=1000,
        num_envs=args.num_envs, batch_size=256,
        num_minibatches=32, num_updates_per_batch=4,
        unroll_length=20, discounting=0.97, learning_rate=3e-4,
        # entropy back to 1e-2: 2e-2 was too noisy (run 8 plateaued ~1050, below
        # the wiggle). The forward-only command curriculum now forces walking, so
        # heavy exploration isn't needed — clean exploitation is better.
        entropy_cost=1e-2, normalize_observations=True,
        num_evals=max(4, timesteps // 2_000_000),
        network_factory=net,
        randomization_fn=make_domain_randomize(terrain, args.dr_scale,
                                               args.step_frac, stair_frac),
        save_checkpoint_path=str(ckpt_dir),
        restore_checkpoint_path=restore, restore_params=restore_params,
        seed=args.seed)

    _, params, _ = train_fn(environment=env, progress_fn=progress,
                            policy_params_fn=save_policy)
    with open(args.out, "wb") as f:
        pickle.dump(params, f)
    return params


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
    ap.add_argument("--step-frac", type=float, default=0.0,
                    help="fraction of envs whose terrain is quantized into DISCRETE "
                         "STEPS (blind tier-1 curb/step robustness). Needs --terrain>0. "
                         "Resume a terrain walk into it; obs unchanged (blind).")
    ap.add_argument("--stair-frac", type=float, default=0.0,
                    help="fraction of envs that are STAIRCASES (tier-2 teacher). Rise "
                         "sweeps with the terrain level to find the max climbable step. "
                         "Needs --terrain>0 AND --heightmap (blind can't climb stairs).")
    ap.add_argument("--curriculum", action="store_true",
                    help="AUTO-RAMP terrain difficulty in stages within one run. Brax "
                         "bakes per-env terrain at env build, so this CHAINS N stages, "
                         "each resuming the last at higher --terrain (one cell instead of "
                         "manual staged resumes). Ramps --curriculum-start -> --terrain "
                         "over --curriculum-stages; --timesteps is the TOTAL (split evenly). "
                         "Resumable: stable stage{i} dirs + DONE markers survive a dropout.")
    ap.add_argument("--curriculum-stages", type=int, default=4,
                    help="number of difficulty stages for --curriculum")
    ap.add_argument("--curriculum-start", type=float, default=0.25,
                    help="terrain level of the FIRST curriculum stage (ramps to --terrain)")
    ap.add_argument("--heightmap", action="store_true",
                    help="add the PRIVILEGED height-map obs (obs 105->105+HM_N^2) for a "
                         "tier-2 stair-climbing TEACHER. Resume a walk via "
                         "graft_obs.py --add-dims HM_N^2 + --restore-params-pkl. NOT "
                         "deployable (privileged map != real D456/L2); train the student next.")
    ap.add_argument("--restore-params-pkl", default=None,
                    help="graft output (.pkl of [norm,policy,value]) to init from, "
                         "bypassing the checkpoint dir. For the FIRST obs-expansion "
                         "resume (e.g. --heightmap via graft_obs.py); later resumes "
                         "read the fresh larger-obs checkpoints.")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="permit a CPU run (smoke-test only; ~100x too slow for real training)")
    args = ap.parse_args()

    env = NovaJoystick(cmd_stage=args.cmd_stage, heightmap=args.heightmap)
    print(f"JAX backend {jax.default_backend()}  devices {jax.devices()}")
    print_fingerprint(env, args.terrain, args.dr_scale, args.step_frac, args.stair_frac)
    if jax.default_backend() == "cpu" and not args.allow_cpu:
        raise SystemExit(
            "✗ JAX is on CPU — real training would take days, not minutes.\n"
            "  Set the Colab runtime to GPU (Runtime > Change runtime type > GPU),\n"
            "  re-run the deps-install cell, then re-run this. If the GPU won't\n"
            "  allocate, you've likely hit the free-tier quota (wait ~24h or use\n"
            "  Colab Pro). Pass --allow-cpu only to force a slow smoke-test.")

    root = epath.Path(args.ckpt)
    root.mkdir(parents=True, exist_ok=True)
    # graft init (obs expansion, e.g. --heightmap): load the padded [norm,policy,
    # value] and hand them to ppo.train as restore_params, which OVERRIDES the
    # checkpoint dir. Skip find_latest so a stale smaller-obs checkpoint can't
    # shape-clash. Use a FRESH --ckpt dir; later resumes read the new checkpoints.
    restore_params = None
    if args.restore_params_pkl:
        with open(args.restore_params_pkl, "rb") as f:
            restore_params = pickle.load(f)
        restore = None
        print(f"GRAFT init from {args.restore_params_pkl} "
              f"(obs {int(restore_params[0].mean.shape[0])}) — checkpoint dir skipped")
    else:
        restore = find_latest_checkpoint(args.ckpt)
        print(f"RESUME from {restore}" if restore else "FRESH start (no checkpoint)")

    logf = (root / "train_log.csv").open("a")
    t0 = time.time()

    if args.curriculum:
        # Brax freezes per-env terrain at env build, so difficulty can't ramp inside
        # one ppo.train. Run STAGES of increasing terrain, each resuming the prior
        # stage's full checkpoint. STABLE stage{i}_t{level} dirs + a DONE marker make
        # it resumable: a plain re-run after a dropout skips finished stages and
        # picks up the interrupted one from its own latest checkpoint.
        s = max(1, args.curriculum_stages)
        lo = min(args.curriculum_start, args.terrain)
        levels = ([args.terrain] if s == 1 else
                  [lo + (args.terrain - lo) * i / (s - 1) for i in range(s)])
        per = max(1, args.timesteps // s)
        print(f"=== AUTO-RAMP CURRICULUM: {s} stages x {per:,} steps, terrain "
              f"{lo:.2f} -> {args.terrain:.2f}, stair-frac {args.stair_frac:.2f} ===")
        prev_ckpt, prev_params = restore, restore_params
        for i, lvl in enumerate(levels):
            sdir = root / f"stage{i}_t{lvl:.2f}"
            if (sdir / "DONE").exists():
                print(f"--- stage {i+1}/{s} (terrain {lvl:.2f}) already DONE — skip ---")
                prev_ckpt, prev_params = find_latest_checkpoint(str(sdir)), None
                continue
            own = find_latest_checkpoint(str(sdir))       # mid-stage dropout resume
            if own is not None:
                r, rp = own, None
            elif i == 0:
                r, rp = prev_ckpt, prev_params            # initial resume / graft
            else:
                r, rp = prev_ckpt, None                   # prior stage's checkpoint
            print(f"--- stage {i+1}/{s}  terrain {lvl:.2f}  ({per:,} steps)  "
                  f"init={'graft' if rp else (r or 'fresh')} ---")
            run_stage(env, args, lvl, args.stair_frac, per, sdir, r, rp, t0, logf)
            (sdir / "DONE").write_text("done")
            prev_ckpt, prev_params = find_latest_checkpoint(str(sdir)), None
        logf.close()
        print(f"done ({time.time()-t0:.0f}s). curriculum complete -> {args.out}, "
              f"checkpoints -> {root}")
    else:
        # unique per-run save subdir -> no step collisions between resumes
        run_dir = root / f"run_{int(time.time())}"
        run_stage(env, args, args.terrain, args.stair_frac, args.timesteps,
                  run_dir, restore, restore_params, t0, logf)
        logf.close()
        print(f"done ({time.time()-t0:.0f}s). policy -> {args.out}, "
              f"checkpoints -> {run_dir}")


if __name__ == "__main__":
    main()
