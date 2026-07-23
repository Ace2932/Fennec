# Lift v5 — commanded footswing height + de-fined posture (OSS-verified design)

**Date:** 2026-07-23
**Status:** APPROVED (Aiden: "build v5" after OSS verification pass)
**Context:** v3/v4 reward surgeries failed (swing 0.02 pinned, 240M steps). Landscape probe:
posture fines (w_pose −0.35, w_upright −0.36) are the valley walls; own-eyes audit: walls are
partly open-loop artifacts, but they're exactly what PPO's unstabilized exploration faces.
Research pass (all primary-source verified, see memory 2026-07-23): every v5 mechanism has a
shipping OSS precedent.

## Changes

### 1. Commanded footswing height `c` (walk-these-ways pattern, proven: cmd dim 9, range [0.03,0.35])

- Per-env command `c ~ U(FOOTSWING_MIN=0.015, footswing_max=0.06)`, stored `info["cmd_c"]`,
  resampled alongside `cmd` (same 250-step cadence). **Terrain-independent sampling** (WTW
  samples commands independent of terrain too): no sentinel plumbing; the policy learns
  c→lift obedience from the clearance cost everywhere, and climbing skill develops in the
  (high-c × stair) intersection. w_climb/PBRS make those episodes outperform. At deploy,
  nav commands high c at stairs — the explicit "ascend mode" lever.
- **Reward**: the one-sided clearance target becomes `c`: `max(c − foot_h, 0)·√v` (form
  verified = Playground Go1's, weight −w_clearance unchanged). No telescoping state → no
  rebase needed on resample.
- **Obs**: `c` appended as the LAST dim AFTER the heightmap block → obs 226→**227**
  (heightmap block stays contiguous; `graft_obs.py --add-dims 1` re-grafts the teacher pkl).
  **Teacher-only**: with `heightmap=False` the blind 105-d obs is UNCHANGED (deploy artifact
  protected) and `c` is FIXED at 0.05 (the classic target) — blind path behaves like the
  pre-v3 static-target env, no command noise it can't observe.
- `--footswing-max` (default `FOOTSWING_MAX=0.06`). `--foot-target-z` REMOVED (obsolete —
  the target is commanded now; blind fixed value is a const, not a flag).

### 2. Pose: knee de-weight (Playground pattern: per-joint [1, 1, 0.1])

Per-joint weights inside the (kept) v4 contact gate: hfe dev × **1.0**, kfe dev × **0.1**.
Weight stays 0.5. Rationale: kfe flexion IS the lift dof; we pinned it at full weight while
the reference de-weights it 10×. Buckle-guard: hfe still fully regularized on stance +
height_pen/done unchanged.

### 3. Upright deadzone (ANYmal-rough pattern: orientation −0 on rough; we soften, not zero)

`tilt_sq = up_x² + up_y²` (= sin²θ); `upright_pen = max(0, tilt_sq − sin²(15°)) = max(0,
tilt_sq − 0.067)`. Free below 15° (trot wobble ~5-10°, climb pitch ~15-25° partially freed);
quadratic-ish beyond. Weight unchanged; `done` at `up_z < 0.4` and `ang_vel_xy` damping keep
the tipping guards. Const `UPRIGHT_DEADZONE = 0.067`, no flag (YAGNI).

### 4. `w_air` 0.5 → 1.0

Reference stacks run feet_air_time at 1.0-2.0; underweighted air-time is a documented
shuffle cause. Hardcoded change + comment.

## Non-farmability review

- `c`-targeted clearance: still a one-sided COST (max 0) — commanding low c and shuffling
  earns nothing extra; commanding is the ENV's choice, not the policy's (policy can't pick c).
- Knee de-weight + deadzone: penalty reductions, no new positives.
- w_air 1.0: existing landing-gated, move-gated, window-capped reward, weight ×2. The gates
  that killed the ckpt12 farm all stand. Bounded: max 1.0·0.4/landing.
- Composed: probe re-run is the empirical check (below).

## Acceptance

- Tests (TDD): obs 227 with heightmap (last dim == scaled c) and 105 without (unchanged);
  clearance cost tracks `info["cmd_c"]` (two c values, same state → proportional deficits);
  kfe dev billed at 0.1× hfe dev (manufactured flexions); upright 10° tilt → 0 pen (old form
  billed it), 25° → > 0; blind env c fixed 0.05; resample cadence matches cmd.
- Existing suites green with obs-size updates (test_heightmap 226→227 where teacher).
- **Probe gate (before ANY training run)**: probe_reward_landscape with `cmd_c=0.05`
  overridden: pose+upright deltas ≥ −0.1 at a=0.8-1.0 (walls lowered ~3×), d(total)/d(a)
  reported. The run is a NO-GO until the probe passes.
- Regraft: `graft_obs.py --add-dims 1` (226→227) on the Colab pkl; obs-size assert catches
  mismatch.

## Success bar (recalibrated, no-existence-proof honesty)

fennec_lift_v5 full curriculum: `swing` tracks commanded c on flat (family learned);
`gzmax` scaling; 4cm risers climbed = success, 6cm = ambitious (publishable territory —
no hobby-servo-class robot has a published ≥40%-height RL climb), 8cm = teacher-ceiling
discovery, not a pass/fail bar. v6 reserves (pre-named): gait-clock contact schedule
(WTW's anti-shuffle weapon), spawn-position performance curriculum.
