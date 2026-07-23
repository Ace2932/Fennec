"""Train a NOVA walking policy with Brax PPO on the MJX env — CHECKPOINTED so a
Colab disconnect / crash mid-run costs nothing.

  python train.py --ckpt /content/drive/MyDrive/nova_ckpt --timesteps 40_000_000

Resilience:
  * Brax writes a full-state checkpoint (params + normalizer) every eval to
    --ckpt. Put --ckpt on PERSISTENT storage (mounted Google Drive) — Colab's
    /content is wiped on disconnect, so a local checkpoint dies with the run.
  * On (re)start it finds the LATEST checkpoint under --ckpt — via the pointer
    each training dir records for itself (PROGRESS), not filesystem mtime — and
    CONTINUES from it. So after any dropout you just re-run the same cell; it
    picks up where the last checkpoint left off, and a resumed curriculum stage
    is charged only the steps it still owes.
  * Each run saves to its own subdir (no step-number collisions between runs),
    plus a flat nova_policy.pkl (latest policy, for rollout.py) and a CSV log —
    both survive a dropout.

Re-run to keep training; watch eval_reward climb. GPU (Colab) for real runs.
"""
import argparse
import functools
import pickle
import time

import jax
from etils import epath

from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo

from env import (NovaJoystick, make_domain_randomize, W_PBRS,
                 FOOTSWING_MAX, PBRS_LOOKAHEAD, AIR_MAX, W_CLEARANCE)
# stdlib-only helpers (importable without JAX, so they're unit-tested on a
# laptop — see test_resume_budget.py). Re-exported here: callers that already
# do `from train import find_latest_checkpoint` keep working.
from ckpt_utils import (EvalMetricsCsv, atomic_write, checkpoint_named,
                        find_latest_checkpoint, read_progress, record_progress,
                        stage_done_steps, steps_per_second)


def print_fingerprint(env, terrain=0.0, dr_scale=1.0, step_frac=0.0, stair_frac=0.0, flat_frac=0.0,
                      w_climb=40.0, w_pbrs=W_PBRS, footswing_max=FOOTSWING_MAX,
                      air_max=AIR_MAX, w_clearance=W_CLEARANCE):
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
    print(f"  clearance    : ONE-SIDED COST w={w_clearance:g}, footswing cmd c∈[0.015,{footswing_max:g}] (lift-v5)")
    print(f"  stride       : air_max {air_max:g}s carry onset, pose STANCE-GATED, upright deadzone 15°, w_air 1.0 (lift-v4)")
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
    if flat_frac > 0:
        print(f"  FLAT FLOOR   : {flat_frac:.2f} of envs at level 0 (flat-gait retention)")
    print(f"  climb reward : w_climb {w_climb:.0f} (signed Δ min ground_z, 0 on flat)")
    _beta = float(getattr(env, "_beta_climb", 0.0))
    print(f"  climb density: beta_climb {_beta:.1f} (PBRS signed Δ mean ground_z; "
          f"{'OFF — min-only' if _beta == 0.0 else 'ON — density aid'})")
    print(f"  approach Φ   : w_pbrs {w_pbrs:g} (PBRS lookahead {PBRS_LOOKAHEAD} m — climb-v2)")
    if getattr(env, "_heightmap", False):
        import env as _e
        print(f"  HEIGHT MAP   : ON — obs +{_e.HM_N**2} ({_e.HM_N}x{_e.HM_N} grid, +-{_e.HM_EXTENT}m) "
              f"= {env.observation_size}. PRIVILEGED (perfect) teacher map; NOT the "
              f"real D456/L2 view. Needs a grafted init + heightmap runner to deploy.")
    print("  Sanity: post terrain-relative reward (2026-07-20) eval levels are NOT")
    print("  comparable to pre-fix runs. cmd stage 2")
    print("  (reverse+lateral+turn) transiently DIPS reward as it generalizes;")
    print("  judge by a probe, not by eval_reward. A ~2700 start = stale code.")
    print("--------------------------------------------------------------")


def plan_curriculum(root, args):
    """Decide every stage's dir, terrain, seed, budget and skip-or-run, WITHOUT
    training or touching a thing.

    Split out so `--dry-run` prints the plan the loop will actually execute
    rather than a hand-written description of it — the same reason
    print_fingerprint reads live module constants instead of a copy. A plan that
    can drift from execution is worse than no plan at all.

    Four values here used to be trivial and no longer are: the budget depends on
    what a prior attempt banked, skip-or-run on a DONE marker, the init on a
    recorded pointer, the seed on the stage index. Getting the ckpt root wrong
    now means silently skipping to the last stage and training a quarter of what
    you asked for. One second of dry-run buys that back.
    """
    s = max(1, args.curriculum_stages)
    lo = min(args.curriculum_start, args.terrain)
    levels = ([args.terrain] if s == 1 else
              [lo + (args.terrain - lo) * i / (s - 1) for i in range(s)])
    per = max(1, args.timesteps // s)
    plan = []
    for i, lvl in enumerate(levels):
        sdir = root / f"stage{i}_t{lvl:.2f}"
        # Seed: recorded beats formula beats legacy beats fresh.
        #   - A recorded seed (persisted every eval, see record_progress) is the
        #     DR draw this stage actually trained under -- resuming it MUST keep
        #     that exact draw, even across a later --seed typo/change.
        #   - No recorded seed but the stage already has its own checkpoint:
        #     LEGACY, written by pre-seed-persistence code, which always used
        #     plain args.seed (never args.seed+i). Using args.seed (not the
        #     formula) is what keeps a currently-live half-trained stage on the
        #     draw it actually has weights for.
        #   - Otherwise (nothing trained here yet): the formula, so each
        #     untouched stage gets its own distinct draw.
        own = find_latest_checkpoint(str(sdir))     # mid-stage dropout resume
        recorded_seed = read_progress(sdir).get("seed")
        if isinstance(recorded_seed, int):
            seed = recorded_seed
        elif own is not None:
            seed = args.seed
        else:
            seed = args.seed + i
        st = {"i": i, "n": s, "level": lvl, "dir": sdir, "per": per,
              "seed": seed, "done": 0, "budget": per, "own": None}
        if (sdir / "DONE").exists():
            st["action"], st["why"] = "skip", "DONE"
            plan.append(st)
            continue
        # A resumed stage owes only what it hasn't trained yet. Handing it the
        # full `per` again is how one 30M stage silently ran 48M steps.
        done = stage_done_steps(sdir) if own is not None else 0
        st.update(own=own, done=done, budget=per - done)
        if own is not None and st["budget"] <= 0:
            # Finished, but its DONE marker never landed (killed between the last
            # eval and the marker). Don't retrain the whole budget.
            st["action"], st["why"] = "mark-done", f"{done:,} of {per:,} steps"
        else:
            st["action"] = "run"
        plan.append(st)
    return plan


def diagnostics(metrics):
    """The eval line that is actually representative.

    eval_reward is a weighted sum the policy is free to farm — the reason the
    fingerprint says to judge by a probe, not by reward. But the env already
    emits the probe's own terms every step (probe_rewards.py reads the same
    dict), and Brax already averages all of them into eval/episode_*. Reading
    them here changes NOTHING the policy optimizes: it is a Python callback
    outside the jit graph, so no retrace, no reward change, no risk to a gait
    that already works. It was pure waste to compute these and discard them.

    Brax's evaluator SUMS every state.metrics key over the whole episode into
    eval/episode_<name> — only keys already named *_per_step are divided by
    episode length for you. Printing those sums as if they were 0-1 per-step
    fractions was off by roughly the episode length (~1000x). Divide by this
    eval's own episode length (eval/avg_episode_length, NOT episode-prefixed —
    it is the episode count/length itself, not a per-episode metric Brax sums)
    to recover the per-step fractions below.

      fwd    — velocity actually tracked / commanded, PER STEP. 1.0 = on command.
      prog   — payment for TRAVELLING, the term a farm starves. PER STEP (all
               reward terms on this line divide by L so they line up with
               probe_rewards.py's per-step prints; the CSV keeps the RAW sums for
               historical comparison, so nothing is lost).
      clear  — payment for WAVING FEET, the term a farm feeds. PER STEP.
      hgt/z  — posture (base-height) + vertical-velocity costs, PER STEP.
      climb  — net base z climbed this episode / episode peak, in METRES. RAW,
               not per-step: both are end-quantities brax already telescoped from
               per-step deltas (see env.step), so dividing would be nonsense. On
               RADIAL stairs a climb-then-descend nets climb≈0 while climb_max
               still shows the peak reached — the whole reason both are logged.
      swing  — mean swing-foot height above local ground, METRES. Already
               per-step (env names it *_per_step so brax divides it), so RAW here.
      ghost  — fraction where the contact proxy lies (planted, but airborne), PER STEP.
      airT   — radius-corrected airborne fraction; ~1.0 on a leg = carried, PER STEP.
      len    — episode length actually survived this eval. THE fall-rate
               canary: 1000 = ran the full episode, low = falling early — a
               signal the farmable reward terms above cannot fake.
    """
    def m(name):
        return float(metrics.get(f"eval/episode_{name}", float("nan")))
    L = max(1.0, float(metrics.get("eval/avg_episode_length", 1.0)))
    ghost = sum(m(f"ghost_{f}") for f in ("FL", "FR", "RL", "RR")) / 4
    airT = [m(f"airT_{f}") for f in ("FL", "FR", "RL", "RR")]
    return (f"    fwd {m('fwd_speed')/L:5.2f}  prog {m('w_progress')/L:+6.2f}  "
            f"clear {m('w_clearance')/L:+6.2f}  hgt {m('w_height')/L:+6.3f}  "
            f"z {m('w_z')/L:+6.3f}  climb {m('climb'):+5.2f}/{m('climb_max'):.2f}  "
            f"wclimb {m('w_climb')/L:+.4f}  wpbrs {m('w_pbrs_climb')/L:+.4f}  "
            f"gzmax {m('gz_max'):.3f}  "
            f"swing {m('swing_h_per_step'):4.2f}  ghost {ghost/L:4.2f}  "
            f"airT " + "/".join(f"{a/L:.2f}" for a in airT) + f"  len {L:.0f}")


def print_plan(plan, args, rate=None):
    """The whole curriculum, before any of it burns GPU time."""
    lo = min(args.curriculum_start, args.terrain)
    total = sum(p["budget"] for p in plan if p["action"] == "run")
    print(f"=== CURRICULUM PLAN: {plan[0]['n']} stages x {plan[0]['per']:,} steps, "
          f"terrain {lo:.2f} -> {args.terrain:.2f}, "
          f"stair-frac {args.stair_frac:.2f} ===")
    for p in plan:
        head = f"  stage {p['i']+1}/{p['n']}  t{p['level']:.2f}  seed {p['seed']}  "
        if p["action"] == "skip":
            print(f"{head}SKIP (already DONE)")
        elif p["action"] == "mark-done":
            print(f"{head}SKIP (complete: {p['why']}, marking DONE)")
        else:
            init = (f"own ckpt +{p['done']:,} banked" if p["own"]
                    else ("graft/restore" if p["i"] == 0 else
                          f"stage{p['i']-1} final"))
            print(f"{head}RUN  {p['budget']:>12,}  init={init}")
    eta = f"  (~{total / rate / 3600:.1f} h at {rate:,.0f} steps/s observed)" if rate else ""
    print(f"  TOTAL to train: {total:,} steps{eta}")


def run_stage(env, args, terrain, stair_frac, timesteps, ckpt_dir, restore,
              restore_params, t0, logf, evalcsv, done_base=0, stage_label="",
              seed=None):
    """One PPO training segment at a FIXED difficulty. Brax freezes per-env terrain
    at env construction, so an auto-ramp curriculum = several of these chained, each
    resuming the previous stage's full checkpoint (policy+value+normalizer) at a
    higher `terrain`. Writes the flat nova_policy.pkl every eval so a mid-stage
    dropout still leaves a usable policy. Returns the final params.

    `timesteps` is what this INVOCATION runs; `done_base` is what the stage
    already banked in earlier attempts. Their sum is persisted every eval so a
    resume knows how much of the stage budget is left (Brax's own step counter
    restarts at 0 on restore, so it can't answer that)."""
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    net = functools.partial(
        ppo_networks.make_ppo_networks,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256))

    banked = {"step": 0}                     # last step with a checkpoint on disk

    def progress(step, metrics):
        r = float(metrics.get("eval/episode_reward", float("nan")))
        total = done_base + step
        tag = f"  (stage total {total:,})" if done_base else ""
        print(f"[{time.time()-t0:6.0f}s] step {step:>11,}  eval_reward {r:8.2f}{tag}")
        try:
            print(diagnostics(metrics))
            # Keep every eval/* term (prefix stripped for a clean column), AND
            # the brax training/* losses the old eval/-only filter dropped.
            # v_loss especially: it's how the probe tells "policy can't climb"
            # (flat return, converged critic) from "critic still recalibrating"
            # (v_loss high, judgement premature) — indistinguishable without it.
            evalcsv.write(stage_label, total,
                          {(k[5:] if k.startswith("eval/") else k): v
                           for k, v in metrics.items()
                           if k.startswith("eval/") or k in
                           ("training/v_loss", "training/policy_loss",
                            "training/total_loss")})
        except Exception as e:      # noqa: BLE001 — never kill a run over a log
            print(f"  ! diagnostics failed: {type(e).__name__}: {e}")
        logf.write(f"{time.time():.0f},{total},{r}\n"); logf.flush()
        # Record the PREVIOUS eval's step, not this one: whether Brax writes its
        # checkpoint before or after this callback is its business, and claiming
        # steps whose checkpoint may not exist would silently skip training.
        # Undercounting only costs a redo of at most one eval interval, so it is
        # the safe direction. The exact total is written on clean stage exit.
        #
        # This lag is NOT for write-ordering: verified against pinned brax
        # 0.14.2 that checkpoint.save is synchronous and completes before
        # progress_fn fires in the same iteration, so by the time we're here
        # the checkpoint for THIS step is already on local disk. It is kept as
        # insurance against Drive FUSE's asynchronous upload — a local write
        # returning does not mean the bytes are durable in Drive yet, and the
        # VM can die mid-upload.
        prev = banked["step"]
        name = checkpoint_named(ckpt_dir, prev)
        if name is not None or prev == 0:
            # prev == 0 is the initial eval: nothing could have a checkpoint
            # yet, so recording latest=None here is harmless and idempotent.
            # Any OTHER prev with no checkpoint on disk means the write above
            # never landed (or never durably will) -- skip the record entirely
            # rather than let `steps` and `latest` describe different moments;
            # the previous (still-valid) PROGRESS is left exactly as it was.
            record_progress(ckpt_dir, done_base + prev, latest=name, seed=seed)
        banked["step"] = step

    def save_policy(step, make_policy, params):
        # latest policy for rollout.py — atomically, or a dropout mid-pickle
        # leaves a truncated .pkl where the run's only usable output should be
        atomic_write(args.out, pickle.dumps(params), label="policy")

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
                                               args.step_frac, stair_frac,
                                               args.flat_frac),
        save_checkpoint_path=str(ckpt_dir),
        restore_checkpoint_path=restore, restore_params=restore_params,
        # Per-STAGE seed. The DR draw (friction, per-body mass, kp, kv — env.py
        # domain_randomize) is derived from this, so a single seed across the
        # whole curriculum trains all four stages against the SAME 2048
        # randomized robots. Varying it per stage quadruples the distinct
        # hardware the policy has to survive, at zero cost. Constant within a
        # stage, so a resumed stage keeps its own draw.
        seed=args.seed if seed is None else seed)

    _, params, _ = train_fn(environment=env, progress_fn=progress,
                            policy_params_fn=save_policy)
    atomic_write(args.out, pickle.dumps(params), label="policy")
    final = banked["step"]                                  # exact, no lag
    record_progress(ckpt_dir, done_base + final,
                    latest=checkpoint_named(ckpt_dir, final), seed=seed)
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
    ap.add_argument("--flat-frac", type=float, default=0.25,
                    help="fraction of envs forced to LEVEL 0 flat ground (keeps the "
                         "flat gait trained; full DR still applies)")
    ap.add_argument("--w-climb", type=float, default=40.0,
                    help="climb-reward weight (signed Δ min ground_z; 0 on flat). Tune 25-60.")
    ap.add_argument("--beta-climb", type=float, default=0.0,
                    help="PBRS climb-density weight (signed Δ mean ground_z; policy-invariant; "
                         "0=off; flip on if the min-only climb reward doesn't bootstrap by ~5M)")
    ap.add_argument("--w-pbrs", type=float, default=W_PBRS,
                    help="approach-density PBRS weight (Φ lookahead; 0 disables; default env "
                         "W_PBRS). keep <=60: the reward-clip ceiling is not w_pbrs-aware")
    ap.add_argument("--footswing-max", type=float, default=FOOTSWING_MAX,
                    help="upper bound of the per-env commanded footswing height c "
                         "(teacher samples c~U[0.015, footswing_max]; "
                         "lift-v5; default env FOOTSWING_MAX)")
    ap.add_argument("--air-max", type=float, default=AIR_MAX,
                    help="seconds of air a normal stride is allowed penalty-free "
                         "before the carry cost bites (lift-v4; default env AIR_MAX)")
    ap.add_argument("--w-clearance", type=float, default=W_CLEARANCE,
                    help="weight of the one-sided swing-clearance cost "
                         "(lift-v4; default env W_CLEARANCE)")
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
    ap.add_argument("--dry-run", action="store_true",
                    help="print the stage plan (dirs, budgets, seeds, what is "
                         "skipped vs trained, hours estimate) and exit without "
                         "training. Cheap insurance against pointing a "
                         "multi-hour curriculum at the wrong --ckpt root.")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="permit a CPU run (smoke-test only; ~100x too slow for real training)")
    args = ap.parse_args()

    env = NovaJoystick(cmd_stage=args.cmd_stage, heightmap=args.heightmap,
                       w_climb=args.w_climb, beta_climb=args.beta_climb,
                       w_pbrs=args.w_pbrs, footswing_max=args.footswing_max,
                       air_max=args.air_max, w_clearance=args.w_clearance)
    print(f"JAX backend {jax.default_backend()}  devices {jax.devices()}")
    print_fingerprint(env, args.terrain, args.dr_scale, args.step_frac, args.stair_frac,
                      args.flat_frac, args.w_climb, args.w_pbrs, args.footswing_max,
                      args.air_max, args.w_clearance)
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
        # In curriculum mode the stage dirs are OFF LIMITS to this scan: the loop
        # below walks the stages in order and chains each off the previous one, so
        # the only question here is "is there a loose earlier run to start stage 0
        # from". Scanning stage dirs could answer it with stage 3's policy.
        restore = find_latest_checkpoint(
            args.ckpt, skip_prefixes=("stage",) if args.curriculum else ())
        print(f"RESUME from {restore}" if restore else "FRESH start (no checkpoint)")

    # Plan first, print it, and let --dry-run stop here. The loop below executes
    # this exact list, so what you read is what will run.
    plan = plan_curriculum(root, args) if args.curriculum else None
    if plan:
        print_plan(plan, args, steps_per_second(root / "train_log.csv"))
    if args.dry_run:
        print("dry run — nothing trained, nothing written.")
        return

    logf = (root / "train_log.csv").open("a")
    # every eval/episode_* Brax aggregates — the diagnostics were already being
    # computed each eval and thrown away; this is the plottable record of them
    evalcsv = EvalMetricsCsv(root / "eval_metrics.csv")
    t0 = time.time()

    if args.curriculum:
        # Brax freezes per-env terrain at env build, so difficulty can't ramp inside
        # one ppo.train. Run STAGES of increasing terrain, each resuming the prior
        # stage's full checkpoint. STABLE stage{i}_t{level} dirs + a DONE marker make
        # it resumable: a plain re-run after a dropout skips finished stages and
        # picks up the interrupted one from its own latest checkpoint.
        prev_ckpt, prev_params = restore, restore_params
        for p in plan:
            i, sdir, s = p["i"], p["dir"], p["n"]
            if p["action"] == "skip":
                print(f"--- stage {i+1}/{s} (terrain {p['level']:.2f}) "
                      f"already DONE — skip ---")
                prev_ckpt, prev_params = find_latest_checkpoint(str(sdir)), None
                continue
            if p["action"] == "mark-done":
                print(f"--- stage {i+1}/{s} (terrain {p['level']:.2f}) has "
                      f"{p['why']} — complete, marking DONE ---")
                (sdir / "DONE").write_text("done")
                prev_ckpt, prev_params = p["own"], None
                continue
            if p["own"] is not None:
                r, rp = p["own"], None
            elif i == 0:
                r, rp = prev_ckpt, prev_params            # initial resume / graft
            else:
                r, rp = prev_ckpt, None                   # prior stage's checkpoint
            budget_note = (f"{p['budget']:,} left of {p['per']:,}" if p["done"]
                           else f"{p['per']:,} steps")
            print(f"--- stage {i+1}/{s}  terrain {p['level']:.2f}  ({budget_note})  "
                  f"seed {p['seed']}  init={'graft' if rp else (r or 'fresh')} ---")
            run_stage(env, args, p["level"], args.stair_frac, p["budget"], sdir,
                      r, rp, t0, logf, evalcsv, done_base=p["done"],
                      stage_label=sdir.name, seed=p["seed"])
            (sdir / "DONE").write_text("done")
            prev_ckpt, prev_params = find_latest_checkpoint(str(sdir)), None
        logf.close()
        print(f"done ({time.time()-t0:.0f}s). curriculum complete -> {args.out}, "
              f"checkpoints -> {root}")
    else:
        # unique per-run save subdir -> no step collisions between resumes
        run_dir = root / f"run_{int(time.time())}"
        # brax's ppo.train returns before any callback/checkpoint when
        # num_timesteps==0 -- a silent no-op, not an error. Floor it so a
        # --timesteps 0 (or a bug upstream of here) still does something.
        timesteps = max(1, args.timesteps)
        run_stage(env, args, args.terrain, args.stair_frac, timesteps,
                  run_dir, restore, restore_params, t0, logf, evalcsv,
                  stage_label=run_dir.name)
        logf.close()
        print(f"done ({time.time()-t0:.0f}s). policy -> {args.out}, "
              f"checkpoints -> {run_dir}")


if __name__ == "__main__":
    main()
