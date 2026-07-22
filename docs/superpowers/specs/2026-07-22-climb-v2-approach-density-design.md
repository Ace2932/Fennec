# Climb v2 — approach density + joint pad curriculum

**Date:** 2026-07-22
**Status:** APPROVED (Aiden: world-frame approach force + joint pad/riser expand; "build it")
**Context:** climb-v1 (#131 reward, `nova_climb_reward_v1` run) failed to bootstrap: `wclimb`
dead +0.000 through ~9.7M steps even under `--beta-climb 20`. Frames (stair-level 1.0):
robot walks the flat beside the staircase, never engages. Root: **nothing pays for crossing
the pad toward the stairs** — `min`/`mean ground_z` are 0 until a foot is already ON a riser,
and body-frame velocity tracking (env.py:516) + wz commands (±0.5) let any heading satisfy
the command. Non-farmable ≠ discoverable.

## Review corrections baked in (2026-07-22 code re-read)

1. Per-env difficulty is **already U[0, tmax]** (env.py:826-827) — every stage always
   contains near-zero-riser envs. No warmup stage needed; no stage-schedule change.
2. climb-v1's kill-rollout ran stair-level 1.0 against a policy trained only to level 0.25
   (4× OOD), and `+.3f` display floors sub-riser climbing → v1 was *probably* parked, not
   provably. v2 adds observability so this ambiguity can't recur.
3. PBRS lookahead points must sit inside the ±0.4 m heightmap obs window so the policy can
   perceive what the reward reads.

## The three changes

### 1. PBRS approach potential Φ (env.py) — the v1 fix

`Φ = mean(_terrain_ground_z at 3 points 0.15/0.25/0.35 m ahead of base along body-frame +x
heading)`. Reward term `w_pbrs·(Φ_t − Φ_{t−1})`, **signed, never clipped**, `last_phi` in
info seeded at reset (rebase — no cross-episode delta).

- **Pays for turning toward + closing on rising terrain BEFORE any foot touches it** — the
  pad-crossing gradient v1 lacked.
- **Non-farmable by construction:** PBRS telescopes; any cycle (heading wiggle, advance-
  retreat) nets exactly 0. This is the provable form of "positive shaper" the reward-farm
  history rule permits (precedent: `--beta-climb`, same discipline).
- **Flat no-op:** Φ≡0 on flat/all-zero hfield → term is exactly 0. Sacred flat gait
  untouched. On rough envs Φ>0 exists (bumps ahead) — telescoping bounds episode net to
  (Φ_end−Φ_start) ≈ 0 mean; accepted + documented, same scope note as #131's ungated climb.
- **Default ON** (`W_PBRS = 30.0`, `--w-pbrs` to override, 0 disables). This is the fix, not
  an experiment flag; flat no-op holds regardless.
- γ=1 delta form (matches `beta_climb`); policy-invariance approximate under discounting,
  farm-safety (telescoping) exact.
- Magnitude: full approach+face ≈ ΔΦ 0.2 m → ~6 total, spread over the crossing; per-step
  ≪ track (~1). A densifier, not a dominator — command-following still wins where commanded
  away (correct deploy behavior; nav commands uphill at real stairs). Escalation if
  bootstrap still stalls: sentinel-flag uphill command bias on stair envs (deferred, YAGNI).

### 2. Joint pad+riser curriculum (terrain.py)

`flat_r_stair = STAIR_PAD_MIN + (FLAT_R − STAIR_PAD_MIN)·level`, `STAIR_PAD_MIN = 3` cells.
Stair branch only; rough/step/flat keep `FLAT_R = 12`.

- Low-level envs (always present via U[0,tmax]) get tiny risers ~15-20 cm from spawn — a
  first climb the flat gait's 2 cm swing can discover by walking forward. Lookahead Φ > 0
  **at spawn** there (0.35 m > pad) — density from step 0.
- `flat_r_stair(1.0) = FLAT_R` exactly → **top-difficulty geometry unchanged**.
- Spawn-fit gate (TDD): stance must fit the 3-cell pad with margin; if not, STAIR_PAD_MIN→4.

### 3. Observability (env.py + train.py) — never fly blind again

- `phi` metric (per-step Φ; eval sum ÷ len = mean engagement height).
- `gz_max` metric: running-peak delta of `max(ground_z)` over feet (mirrors `climb_max`
  pattern) → "deepest stair engagement" per episode. Distinguishes not-reaching (=0) from
  reaching-not-climbing (>0, wclimb 0) — the split v1 couldn't make.
- Diagnostics line: `wclimb` at 4 decimals (sub-riser climbing visible), add `wpbrs`, `gzmax`.
- Kill-rollouts must use stage-matched `--stair-level`, not 1.0 (run doctrine, in notebook cmd).

## Unchanged

#131 `w_climb` min-term, `beta_climb`, asymmetric clip, base_h lock, stage schedule
(0.25→1.0, 4×30M), stair_frac 0.6, flat_frac 0.25, obs 226. Graft/restore path: new info
keys (`last_phi`, `gz_peak`) live in env state only — checkpoint restore (network params)
unaffected; resumes from the flat graft as before.

## Acceptance

- Full test suite green (4 existing files + new tests).
- Flat no-op: `w_pbrs_climb ≡ 0` on flat env with w_pbrs ON (exact).
- Telescope: Σ per-step `w_pbrs_climb` == `w_pbrs·(Φ_N − Φ_0)` (structural, ~1e-4).
- Level-1.0 stair field bit-identical to pre-change formula.
- Spawn Φ > 0 on a level-0.125 stair env (density live from step 0).
- Run success bar (Colab, later): `gzmax` lifts off 0 within stage 1 (reaching), then
  `wclimb` > 0 sustained (climbing). Judged at 4-decimal precision, stage-matched rollouts.
