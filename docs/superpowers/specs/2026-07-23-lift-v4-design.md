# Lift v4 — remove the three fines on the climb stride

**Date:** 2026-07-23
**Status:** APPROVED (Aiden: "yes ultrathink" on the three-lever design)
**Context:** lift-v3 run: `swing` 0.02 unmoved through 120M; `clear` bill −0.16/step (~7% of
return) paid and ignored. Kinematic probe (`probe_lift_ceiling.py`, reference data in
memory): plant does 3.2 cm sustained / 6.6 cm transient; lift ∝ swing DURATION; trained
gait swings ~0.35 s. Videos: approach ✓, arrival ✓, ascent ✗ (parked at the first riser).

## Root cause (three stacked fines, quantified)

1. **Pose veto (dominant).** `w_pose = 0.5·exp(−2·Σ_8joints(hfe/kfe−default)²)` regularizes
   swing joints STANCE AND SWING alike. A two-leg trot swing flexed for 5 cm lift loses
   ~0.26-0.35/step of pose income; the clearance saving for the same lift is ~0.08/step at
   weight 2 (~0.25 at weight 6). Lifting was NET-PUNISHED — the policy wasn't ignoring the
   clearance bill, it was collecting a bribe to stay low. (Same class as #130 absolute-z:
   flat-era term silently anti-climb.)
2. **Duration fine.** Carry cost bills past `AIR_MAX 0.4 s`; the probe says height needs
   T≈0.5-0.6 s swings. The only lift-producing stride was fined.
3. **Weak incentive.** Even absent 1-2, clearance weight 2.0 undersizes the pull.

## Changes (all cost-side reshapes/gates — ZERO new positive terms)

### 1. Contact-gated pose regularizer (env.py, flagless/structural)

```
legs = [(1,2), (4,5), (7,8), (10,11)]            # (hfe,kfe) per leg, q[7:] indices
dev_i = Σ_(j∈leg i) (q_j − default_j)²
pose_rew = exp(−2 · Σ_i dev_i · contact_i)       # contact_i: 1 planted, 0 airborne
```

- Stance legs stay regularized — the buckle-guard purpose (front-leg collapse = a STANCE
  pathology) survives intact.
- Swing legs flex free — the posture fine on the climb stride is gone.
- Near-no-op on the current flat gait (today's swing legs barely deviate); the small
  during-swing income bump is bounded (pose_rew caps at 1 → max +0.09/step) and
  non-farmable (airborne-leg antics earn nothing here; carry/air/track own that space).
- `contact` is the existing radius-corrected per-foot bool; leg order must match
  `LEG_NAMES`/`_foot_ids` ordering (verify FL/FR/RL/RR ↔ joint-group order in code).

### 2. `AIR_MAX 0.4 → 0.6`, CLI `--air-max` (env kwarg `air_max`)

- Removes the fine on T≤0.6 s strides. Hold-guard asymptotics UNCHANGED: bill still ramps
  to the same 1.5·0.6 = 0.9/step max (AIR_CARRY_CAP untouched), just 0.2 s later.
- The air REWARD cap stays 0.4 (`clip(air−0.2, 0, 0.4)` untouched) — we stop fining long
  swings, we never start PAYING for them (that direction is the ckpt12 farm).
- Kwarg default `AIR_MAX` module const = 0.6; thread like `--foot-target-z`.

### 3. Clearance weight 2.0 → 6.0, CLI `--w-clearance` (env kwarg `w_clearance_scale` or
   direct weight — implementer matches the existing weight-line style: `w_clearance =
   -W·clearance_cost` with W from the kwarg, default `W_CLEARANCE = 6.0` module const)

- ~20% of return at the current 2 cm swing — undodgeable, and pays 0 at target.
- Shuffle-escape (cutting √v instead of lifting) stays dominated by track/progress
  (~2/step at stake vs 0.48 savings); watch `fwd` in stage 1 for partial shuffle.

## Unchanged

FOOT_TARGET_Z 0.07 + one-sided form (#134), all climb-v2 terms (w_climb/beta/PBRS),
asymmetric clip, stage schedule, obs 226, AIR_CARRY_CAP, air-reward window.

## Non-farmability review

- Pose gating: removes a penalty on airborne legs; pose income ceiling unchanged (exp≤1).
  Airborne-leg freedom is already policed by carry (holds), air-cap (no pay past 0.4),
  move_gate (no pay standing), one-sided clearance (cost-only).
- AIR_MAX: pure penalty-onset delay, same asymptote. No positive added.
- w_clearance: scales a cost. No positive added.
- Composed: the climb stride (slow, high, flexed) goes from triple-fined to cost-neutral;
  its PAY still comes only from the existing verified-non-farmable terms (w_climb telescoping
  min-ground-z, PBRS Φ, track/progress).

## Acceptance (TDD)

- Pose gate: manufactured state, one leg airborne + flexed, others planted at default →
  pose_rew ≈ exp(−2·planted-dev only) (airborne dev excluded); all-planted state →
  bit-identical to the old formula.
- AIR_MAX: env default 0.6; kwarg 0.4 reproduces old billing onset (carry fires at 0.4);
  at default no billing for a 0.5 s air time.
- w_clearance: default 6.0; kwarg 2.0 reproduces old weight; metric scales linearly.
- Fingerprint prints all three live (`--air-max`, `--w-clearance` values + pose-gate note).
- Full suite green; climb-term flat no-ops untouched.

## Run success bar (fennec_lift_v4, full 4-stage from HM_GRAFT, beta 20, defaults)

1. `swing` off 0.02 in stage 1 — with the pose veto gone this should move EARLY (eval 2-4).
2. `airT` drifting 0.35 → 0.45-0.55 = the slow-high stride forming (healthy); PINNED at
   0.6+ with `fwd` collapsing = hold pattern (kill; revert --air-max 0.5).
3. `fwd` holding ≥0.13 (shuffle watch).
4. Then the chain: `gzmax` scaling with stage, `wclimb` growing.
Kill signals: swing still 0.02 at stage-1 end (something ELSE fines lift — instrument per-term
swing-conditioned income next, no more const-tuning); fwd < 0.10 sustained (shuffle escape —
drop --w-clearance to 4).
