# Terrain-relative reward + flat-floor curriculum — design

**Date:** 2026-07-20
**Status:** approved (design review done, incl. Fable pass — gaps 1–3 folded in)
**Scope:** `sim/nova_mjx/env.py`, `sim/nova_mjx/rollout.py`, one new test file. No changes to `train.py` accounting, obs layout, or action space.

## Problem

The reward was written for flat ground and reads **absolute world z** everywhere it means
**height above local ground**. On the tier-2 staircase terrain (which rises radially from the
spawn pad) this creates four instances of the same bug:

| # | Site | Code today | Effect on stairs |
|---|------|-----------|------------------|
| 1 | contact | `(foot_z - FOOT_RADIUS) < CONTACT_EPS` (env.py:269) | foot planted on a 0.24 m step reads AIRBORNE → `slip_pen` (gated on contact) vanishes → scraping feet against risers is **cost-free** |
| 2 | clearance | `\|foot_z - FOOT_TARGET_Z\| * sqrt(foot_xy_speed)` (env.py:382) | every swing pays ∝ absolute elevation → swinging is taxed exactly where stepping up is needed |
| 3 | done | `height < 0.08` with `height = x.pos[0,2]` (env.py:250,465) | can never fire on elevated terrain → face-plants on step 3 don't terminate; episode-length and `climb` metrics count corpses |
| 4 | height reward | `height_pen = (height - STAND_HEIGHT)**2`, weight **−1.5** (env.py:337,446) | **quadratic** tax on elevation: 0.086/step on the 3rd step, 0.35/step on the 6th — plausibly the dominant anti-climb gradient, and it was never logged per stage |

Observed consequence (2026-07-20 rollouts of `nova_policy_stairs_final.pkl`): the policy
wiggles feet against the riser until one catches, rather than stepping up; `airT` ~0.4 (loitering
near the pad); at vx 0.25 it survives 8 cm staircases (601/601 frames) yet **falls on flat ground
at step 554, deterministically** — flat is ~5% of stage-4 envs, so PPO correctly trades it away
(the fall costs ~2% of batch return).

Secondary candidate (measure, don't pre-fix): `z_pen = vz**2`, weight −0.4 (env.py:338,447) —
taxes the upward velocity climbing requires; ~0.036/step during a lift burst.

## Fix A — terrain-relative geometry (one helper, five consumers)

Factor the world-xy → terrain-height lookup that `_sample_heightmap` already contains
(env.py:555-563) into:

```python
def _terrain_height(self, wx, wy):
    """ABSOLUTE terrain z at world (wx, wy), bilinear from this env's hfield."""
```

Consumers:

```python
ground_z = self._terrain_height(foot_xy[:, 0], foot_xy[:, 1])   # (4,)
foot_h   = foot_z - ground_z                                    # height above LOCAL ground
base_h   = base_z - self._terrain_height(base_x, base_y)        # scalar

contact        = (foot_h - FOOT_RADIUS) < CONTACT_EPS           # 1
clearance_cost = sum(|foot_h - FOOT_TARGET_Z| * sqrt(foot_xy_speed))  # 2
done           = (base_h < 0.08) | (up[2] < 0.4)                # 3
height_pen     = (base_h - STAND_HEIGHT) ** 2                   # 4
contact_true   = (foot_h - FOOT_RADIUS) < CONTACT_EPS           # diagnostics twin (env.py:487)
```

`contact_true` moves in lock-step or airT/ghost silently diverge from the reward's view —
the drift those metrics exist to prevent.

**Why this is safe on flat:** flat terrain ⇒ `_terrain_height ≡ 0` ⇒ every expression above is
bit-identical to today's. The blast radius is confined to terrain that is actually elevated.

**`z_pen` decision rule:** log `w_z` in the per-stage diagnostics; if during the probe's climbs
it exceeds ~10% of `w_progress`'s magnitude, exempt upward velocity (`z_pen = clip(vz, None, 0)**2`)
in a follow-up — not in this change.

**Known approximation:** bilinear interpolation smooths riser edges into short ramps; a foot at
an edge reads a blended height. Sub-centimetre, errs lenient. Accepted.

**Obs invariant:** `_sample_heightmap` output is byte-identical after the refactor (helper returns
ABSOLUTE terrain; obs path keeps its own `- bz`). The deployed 226-obs interface does not move.

## Fix B — flat-floor curriculum (one line + flag)

`env.py` `make_domain_randomize.rand()` (env.py:653-655):

```python
kt1, kt2, kt3 = jax.random.split(kt, 3)
is_flat = jax.random.uniform(kt3, ()) < flat_frac
level   = jp.where(is_flat, 0.0, jax.random.uniform(kt2, (), 0.0, tmax))
```

`level = 0` provably flattens both branches (`height_m = field·pad·(BUMP_M·0) = 0`,
`stair_m = step_idx·(STAIR_RISE·0) = 0`), so no `terrain.py` change. Exposed as
`--flat-frac`, **default 0.25**, threaded through `make_domain_randomize(...)` and
`print_fingerprint`. Flat envs keep full DR (mass/friction/kp/kv) — only terrain flattens.

**Rationale:** flat is ~5% of stage-4 envs today; a deterministic fall there costs ~2% of batch
return — beneath PPO's notice. At 25% the same failure costs ~11%. Also matches deployment:
NOVA lives mostly on floors.

**Deliberately NOT included:** the stair-frac ramp (reviewer rec). Its motivating evidence
(stage 1 flat-reward) predates the discovery of Fix A's bugs, which are sufficient to explain it.
One variable at a time; ramp stays in the backlog for the run after this one.

## Metrics (phase 1 of the acceptance bar)

- `climb` — per-step `base_z - info["last_base_z"]` (absolute z, NOT base_h: net ascent is the
  quantity). Brax sums non-`per_step` metrics masked by `active_episodes`, so the episode value
  telescopes exactly to (z at first done − z at spawn). One float of new state in `info`.
- `swing_h_per_step` — mean `foot_h` over swinging feet (`~contact`); `_per_step` suffix ⇒ brax
  divides by episode length ⇒ reads in metres. This is most of the future scrape detector: swing
  height pinned at 5 cm vs 8 cm risers = physically cannot step up, visible in the training log.
- `w_height`, `w_z` join the per-eval diagnostics line (they were never logged per stage; #4
  hid there).
- `rollout.py` prints `climbed +X.XX m in z` next to `traveled` (final − initial base z).

Phase 2 (deferred until it climbs): explicit riser-scrape detector.

## Validation

Geometry code fails silently (cf. `test_heightmap.py`), so red-then-green on every bug:

| T | Test | Catches |
|---|------|---------|
| T1 | flat terrain → `_terrain_height ≡ 0`, `foot_h == foot_z` | blast-radius claim |
| T2 | constant 0.10 m field → query returns 0.10 | `* ztop + fz` scale/offset |
| T3 | **asymmetric ramp** (rises in x only), query at known x | **row/col transpose — invisible on the radially-symmetric staircase, so T1/T2/T5-7 all pass transposed** |
| T4 | `_sample_heightmap` output unchanged by refactor | obs regression / relative-vs-absolute inversion |
| T5 | foot planted on 0.24 m step → `contact == True` | bug #1 (fails on current code) |
| T6 | same foot → clearance cost ≈ 0 | bug #2 (fails on current code) |
| T7 | face-plant pose on 0.24 m step → `done == 1` | bug #3 (fails on current code) |

Tests need jax → try CPU-only `jax==0.6.0 + mujoco-mjx + brax==0.14.2` into `proj/.venv`
(arm64 wheels exist) so they run on the Mac; Colab like `test_heightmap.py` as fallback.

## Probe protocol (decision gate, ~1.3 h GPU)

Per the approved staging: cheap probe first, then decide continue-vs-restart.

- **Fresh** `--ckpt /content/drive/MyDrive/nova_stairs_fix` — never reuse `nova_stairs_curr`
  (its PROGRESS/DONE describe the old objective; fresh dir also gives the new metrics a fresh
  `eval_metrics.csv` header — the column set is frozen per file).
- Init `--restore-params-pkl /content/drive/MyDrive/nova_policy_stairs_final.pkl` (obs 226 matches).
- Single stage, no `--curriculum`: `--heightmap --terrain 1.0 --stair-frac 0.6 --flat-frac 0.25
  --timesteps 25_000_000`.
- **Reading `climb`:** aggregate is diluted (~45% of envs are stairs after the flat floor) — use
  as a TREND (lifts off ~0, keeps rising). Acceptance is measured on a pure-stairs rollout.

**Acceptance (approved bar):**
1. Stairs: rollout `--stair-level 1.0 --vx 0.25 --steps 600` → `climbed ≥ +0.24 m` (three 8 cm
   risers ascended), full 601 frames.
2. Flat: rollout `--stair-level 0.0 --vx 0.35 --steps 600` → 601 frames, ≥80% speed tracking
   (today: falls at step 470).

**Decision:** pass → continue this policy. Climb trending but short → extend probe once.
Flat still failing OR climb flat-lined → restart curriculum clean from the flat ckpt12 graft with
fixes in (the 120M-step scrape habit won).

**Attribution:** Fix A is a provable no-op on flat; Fix B never touches the reward. Stairs
outcome ⇒ Fix A; flat outcome ⇒ Fix B. No confounding.

## Risks

- `eval_reward` shifts level on terrain (clearance + height stop billing altitude) — old-run
  comparisons invalid. The fingerprint's "resuming the stage-1 walk evals ~2100-2500" sanity
  line is stale → update in the same commit.
- One XLA recompile (~300 s) from the new metric keys + reward graph. Expected, once.
- 25M steps may not undo a 120M-step habit — that is the probe's question, priced at 1.3 h.
- `height_pen` becoming terrain-relative removes a (buggy) regulariser the terrain gait was
  trained under; transient wobble on resume is expected and is why the probe exists.
