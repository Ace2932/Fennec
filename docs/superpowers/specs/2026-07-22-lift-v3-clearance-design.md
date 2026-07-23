# Lift v3 — one-sided clearance + raised swing target

**Date:** 2026-07-22
**Status:** APPROVED (Aiden: one-sided + target 0.07, CLI flag)
**Context:** climb-v2 (#132) solved approach: the robot commits onto the staircase (video)
and engages elevation up to its foot lift — `gzmax` saturates at ~0.02 == `swing` 0.02
across all 4 stages; `wclimb` decays as risers outgrow the lift. `clear` has sat at −0.10
for 220M+ steps in every run. **Lift is the binding constraint.**

## Root cause (from code, env.py:509)

`clearance_cost = Σ_feet |foot_h − FOOT_TARGET_Z| · √(foot_xy_speed)`, weight −2.0,
FOOT_TARGET_Z = 0.05.

Two problems:
1. **Two-sided → ceiling.** Above-target lift is *punished*. Stage-3/4 risers (6-8 cm)
   need >6 cm swing → a correct climbing stride pays clearance cost forever. (The
   two-sidedness was the fix for the ckpt12 held-foot farm — but that farm needed the
   old *reward* form; the anti-hold job has since moved to the carry cost
   (`AIR_MAX 0.4 s`, `w_carry −1.5`), which bills held feet directly.)
2. **Equilibrium floor at 0.02.** Below target the 2.0·√v gradient toward 0.05 loses to
   energy/act_rate/stability at ~0.02 — stable attractor across every run.

## The mechanism (why this bootstraps where v2 stalled)

v2's own data: 2 cm risers get climbed *incidentally* by a 2 cm swing — discovery by
default gait, no exploration needed, then `w_climb`/PBRS reinforce. v3 extends that
mechanism to mid stairs: **raise the base swing so 4-6 cm risers become "gravel" too.**
Not terrain-adaptive targets — REJECTED: any cost that rises near stairs creates
avoidance pressure (~0.11/step) that dwarfs PBRS (+0.0003/step); the robot would flee
the stairs. Broken by construction.

## Changes

### 1. One-sided clearance cost (env.py)

```
clearance_cost = jp.sum(jp.maximum(self._foot_target_z - foot_h, 0.0)
                        * jp.sqrt(foot_xy_speed))
```
- Ceiling removed: lift above target is free (a cost can pay at most 0 — not farmable).
- Hold-farm guard: carry cost bills any foot airborne >0.4 s; `airT` metrics watch it.
- Below-target gradient shape unchanged (same 2.0 weight, same √v scaling).

### 2. FOOT_TARGET_Z 0.05 → 0.07, CLI-swept (`--foot-target-z`)

- 0.07 rationale: geometry-scaled reference was 0.057-0.06 (the 0.05 rounded down);
  servo envelope caps gait-speed lift at ~6-7 cm (2.8 rad/s × ~0.2 s swing ≈ 0.56 rad);
  0.07 clears 4-6 cm risers and stays physically reachable. 0.08+ chases the envelope.
- Threaded exactly like `--w-pbrs`: env kwarg `foot_target_z=FOOT_TARGET_Z`, argparse
  default from the env import, fingerprint line, single NovaJoystick site.
- Stage-4 8 cm risers may exceed the actuator envelope at gait speed — acceptable: the
  teacher's job includes *finding* the max climbable rise (likely 5-7 cm).

### 3. Doctrine break — DELIBERATE flat-gait retrain

Raising the global target changes the flat gait (higher-stepping trot). This is chosen,
not rot: 2 cm swing is a real-floor liability (carpet, thresholds; reference quadrupeds
swing 5-9 cm). Consequences owned:
- **Full 4-stage re-run from HM_GRAFT** (~7.2 h) — v2 checkpoints carry the old-clearance
  gait; resume would fight the new cost. Fresh lineage.
- The *climb-term* flat no-ops (PBRS/w_climb/beta ≡ 0 on flat) are untouched and their
  tests must stay green. The clearance change DOES alter flat reward — that is the point.
- flat_frac 0.25 keeps the (new) flat gait trained.

## Non-farmability review

- One-sided cost: max attainable value is 0 → cannot be farmed for profit, only avoided
  by lifting to target while swinging — the desired behavior.
- Held-high foot: clearance contribution 0 (was >0) → the delta is bounded by the carry
  cost taking over at 0.4 s; watch `airT_*` and `ghost_*` in the first evals for a
  reopened hold pattern (kill signal: airT → 0.4+ cap with fwd stalling).
- No new positive terms. w_climb/beta/PBRS unchanged.

## Acceptance (tests, TDD)

- One-sidedness: a foot held ABOVE target while moving contributes 0 clearance cost
  (manufactured state); below-target contribution unchanged vs |·| form (equal when
  foot_h < target).
- Default change: fingerprint prints `foot target : 0.07` (and the flag overrides it).
- Threading: `--foot-target-z 0.05` reproduces the old target (sweep path works).
- Climb-term flat no-ops still green (full climb suite).
- Existing clearance-related tests updated only where they encode the |·| form or 0.05.

## Run success bar (fennec_lift_v3, full curriculum, defaults + beta 20)

1. `swing` lifts off 0.02 → ≥0.04 within stage 1 (the equilibrium moved — the whole bet).
2. `gzmax` scales with stage (≥0.04 by stage 2-3) instead of saturating at swing.
3. `wclimb` grows with stage instead of decaying.
4. Stage 4: found ceiling is a RESULT (max climbable rise), not a failure.
Kill signals: swing still 0.02 at stage-1 end (equilibrium didn't move → sweep
`--foot-target-z` up / raise clearance weight); airT pinned at cap (hold pattern).
