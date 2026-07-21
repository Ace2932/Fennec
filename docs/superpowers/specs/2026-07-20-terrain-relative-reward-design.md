# Terrain-relative reward + flat-floor curriculum — design

**Date:** 2026-07-20
**Status:** approved (design review + 2 adversarial pre-implementation reviews — all findings adjudicated and folded in 2026-07-20)
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
| 4 | height reward | `height_pen = (height - STAND_HEIGHT)**2`, weight **−1.5** (env.py:337,446) | **quadratic** tax on elevation, up to 0.06/step at the terrain ceiling (TZ caps relief at 0.20 m — see Terrain ceiling below) — a real anti-climb gradient, never logged per stage |

Observed consequence (2026-07-20 rollouts of `nova_policy_stairs_final.pkl`): the policy
wiggles feet against the riser until one catches, rather than stepping up; `airT` ~0.4 (loitering
near the pad); at vx 0.25 it survives 8 cm staircases (601/601 frames) yet **falls on flat ground
at step 554, deterministically** — flat is ~5% of stage-4 envs, so PPO correctly trades it away
(the fall costs ~2% of batch return).

Secondary candidate (measure, don't pre-fix): `z_pen = vz**2`, weight −0.4 (env.py:338,447) —
taxes the upward velocity climbing requires; ~0.036/step during a lift burst.

## Fix A — terrain-relative geometry (one helper, five consumers)

TWO helpers, not one — empirical review (real-MuJoCo raycasts against the actual stair
hfield) proved bilinear interpolation diverges from MuJoCo's collision surface by up to
~19 mm inside 59% of riser-boundary cells, bidirectionally: one sign reintroduces the
contact bug at tread edges, the other fabricates ghost contacts that poison `slip_pen`
exactly where footholds matter. MuJoCo triangulates each hfield cell along a FIXED
diagonal (v00–v11); bilinear uses all four corners; they agree only on cell edges.

```python
def _terrain_height(self, wx, wy):
    """ABSOLUTE terrain z, BILINEAR — obs path ONLY (the policy was trained on this)."""

def _terrain_ground_z(self, wx, wy):
    """ABSOLUTE terrain z matching MuJoCo's hfield collision surface EXACTLY —
    per-cell fixed-diagonal triangulation. All reward/done consumers use THIS.
        lower = fc >= fr
        z = v00 + where(lower, fc*(v01-v00) + fr*(v11-v01),
                               fr*(v10-v00) + fc*(v11-v10))
    (fr, fc = fractional row/col within the cell; orientation pinned by T3/T8.)"""
```

`_sample_heightmap` keeps bilinear untouched (obs invariant: the 121 trained inputs must
not move). The five reward/done consumers use `_terrain_ground_z`:

```python
ground_z = self._terrain_ground_z(foot_xy[:, 0], foot_xy[:, 1])   # (4,) collision-exact
foot_h   = foot_z - ground_z                                      # height above LOCAL ground
# done/height ground reference: MIN over the four feet's ground_z, NOT a CoM point
# sample. The hip span (~0.28 m) exceeds a tread run (~0.20 m), so a climbing robot
# NORMALLY straddles two treads; a CoM sample past the riser reads the upper tread and
# can under-read base_h by ~0.10 m — enough to spuriously terminate a healthy climb
# against the 0.08 threshold. min() reuses the per-foot array, errs toward NOT
# terminating, and is identical on flat (all zeros).
base_h   = base_z - jp.min(ground_z)

contact        = (foot_h - FOOT_RADIUS) < CONTACT_EPS             # 1
clearance_cost = sum(|foot_h - FOOT_TARGET_Z| * sqrt(foot_xy_speed))  # 2
done           = (base_h < 0.08) | (up[2] < 0.4)                  # 3
height_pen     = (base_h - STAND_HEIGHT) ** 2                     # 4
contact_true   = (foot_h - FOOT_RADIUS) < CONTACT_EPS             # diagnostics twin (env.py:487)
```

`contact_true` moves in lock-step or airT/ghost silently diverge from the reward's view —
the drift those metrics exist to prevent.

**Why this is safe on flat:** flat terrain ⇒ both helpers ≡ 0 (all-zero hfield, `fz = 0`
verified against the real model) ⇒ every expression above is bit-identical to today's. The
blast radius is confined to terrain that is actually elevated.

**Measure-then-decide (applies to BOTH `w_z` and `w_clearance`):** log both in the per-stage
diagnostics. `z_pen` taxes the vz climbing requires (~0.02–0.05/step during a lift);
`clearance_cost` is symmetric about 0.05 m, so clearing an 0.08 m riser pays a ~5–12% headwind
vs `w_progress` (both adversarial reviews priced it independently). If during the probe either
exceeds ~10% of `w_progress` while `climb` stalls, apply the follow-up (one-sided forms) —
NOT in this change: one-sided clearance breaks the bit-identical-on-flat property (the flat
gait was trained under the symmetric cost), so it needs its own validation pass.

**Corrected risk note:** the original draft accepted bilinear edge-smoothing as "sub-centimetre,
errs lenient" — empirically FALSE (up to 19.2 mm, both signs). Hence `_terrain_ground_z`.
The residual approximation is now zero by construction: the reward reads the same surface
physics stands on.

**Obs invariant:** `_sample_heightmap` output is byte-identical after the refactor (helper returns
ABSOLUTE terrain; obs path keeps its own `- bz`). The deployed 226-obs interface does not move.

## Terrain ceiling (adjudicated CRITICAL)

`TZ = 0.20` (terrain.py:17, build_mjcf.py:60, baked into nova.xml `size="2.5 2.5 0.2"`) caps
representable relief at 0.20 m: the level-1.0 staircase is TWO real 0.08 m risers, then a
clipped plateau. Any acceptance bar above +0.20 m demands terrain that does not exist.
The probe bar is therefore **+0.16 m** (both real risers). Raising `TZ` (→0.32) requires
regenerating nova.xml and hands the resumed policy heights it has never seen — a second
variable; it goes in the next-run backlog beside the stair-frac ramp.

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
- `climb_max` — high-water mark (`max(base_z - spawn_z)` over the episode, one more float in
  `info`). Commands resample every 250 steps with random heading on RADIAL stairs, so a policy
  that climbs then gets commanded back down telescopes to `climb ≈ 0` — identical to never
  climbing. The acceptance rollout pins its command and is immune; the TRAINING trend is not.
- `w_height`, `w_z`, `w_clearance` join the per-eval diagnostics line (never logged per stage;
  #4 hid there), plus **`training/v_loss`** — brax computes it and our `eval/` prefix filter
  drops it (verified in brax source). Without it, "policy can't climb" and "critic still
  recalibrating after the reward shock" are indistinguishable: `restore_params` never restores
  Adam state, and the critic was fitted to elevation-taxed returns. Probe reads gate on v_loss
  plateauing.
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
| T7 | face-plant pose on an elevated step → `done == 1`; AND healthy straddle pose (base xy over the riser boundary, feet on two treads) → `done == 0` | bug #3 (fails on current code) + the straddle false-terminate |
| T8 | foot inside a transition-CELL INTERIOR (not a vertex/edge): `contact`/`clearance` agree with MuJoCo's true triangulated surface, NOT bilinear | the 19 mm bilinear divergence — T5–T7 place feet mid-tread and cannot catch it |
| T9 | `ghost_*` ≈ 0 on elevated terrain post-fix | `contact`/`contact_true` moving out of lockstep |

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

**Early kill-switch (~5M steps, ~20 min):** if `swing_h_per_step` hasn't shifted upward on
stair envs AND `w_slip` hasn't engaged (fix not biting / policy not touching risers), with
`v_loss` already plateaued — kill the probe, save the hour. Trend calibration for `climb`:
genuine climbing reads ~0.03–0.08 m aggregate and rising (45% stair envs × mean level 0.5,
diluted); sustained ≤0.02 m oscillation is noise.

**Acceptance (bar amended for the TZ ceiling):**
1. Stairs: rollout `--stair-level 1.0 --vx 0.25 --steps 600` → `climbed ≥ +0.16 m` (both real
   risers ascended; the terrain cannot represent more), full 601 frames.
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
- Splitting `kt` 3-ways shifts the whole per-seed terrain draw stream: `--flat-frac 0` does
  NOT reproduce old runs bit-for-bit. Fine under the fresh-dir protocol; do not assume the
  invariant later.
- `climb` in the TRAINING log (EpisodeWrapper path) inherits one garbage corpse-step delta per
  auto-reset — cosmetic boundary spikes, eval path is masked correctly (verified in brax
  source). Not a bug in the metric; a property of delta metrics under brax auto-reset.
