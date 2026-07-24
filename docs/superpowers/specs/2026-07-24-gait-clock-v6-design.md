# Gait clock v6 — scheduled swings (WTW port, cost-form, teacher-only)

**Date:** 2026-07-24
**Status:** APPROVED (Aiden: "build v6")
**Context:** ROOT CAUSE (in-distribution σ probe, 2026-07-24): exploration was always alive
(σ 0.42, effective post-tanh noise 0.36) — but white per-step noise through the actuation
lowpass (deadband/slew/latency/PD) cannot produce the ~15-step correlated 2-joint sequences a
lift requires, at any σ. Five runs of stasis explained. WTW's footswing command (our v5) is
inert without its partner: the gait clock that SCHEDULES swings; the command then shapes
amplitude of swings that already exist. Research pass flagged this verbatim ("clearance reward
nearly useless without a phase signal"); the probe made it causal.

**Why the clock beats the noise problem:** the walker already alternates contacts at ~1.4 Hz
(airT 0.36 → period ~0.72 s). The clock phase-locks an EXISTING rhythm (timing drift is
low-frequency — within white-noise reach), then `cmd_c` shapes amplitude at known scheduled
times. The correlated structure comes from the clock; noise only modulates. This is why
WTW/ANYmal train schedule-locked gaits reliably from scratch.

## Mechanism

### 1. One trot clock per env (teacher-only)

- `info["gait_phase"]` θ ∈ [0,1), advances `θ += cmd_f · dt` each step (wraps). Seeded
  RANDOM at reset (decorrelates envs). `info["cmd_f"]` ~ U(F_MIN=1.0, F_MAX=2.0) Hz at reset,
  resampled at the cmd cadence (`step % 250`, same jp.where pattern as cmd_c; fold_in for RNG).
  1-2 Hz at duty 0.5 spans 0.25-0.5 s swings = the probe's climb band; 1.4 Hz current gait
  is interior → easy lock. Phase is continuous across f-resample (rate changes, no jump).
- Foot phases: FL,RR at θ; FR,RL at θ+0.5 (mod 1) — fixed trot offsets, fixed DUTY = 0.5.
  No commanded gait-shape zoo.
- Blind (heightmap=False): NO clock — `cmd_f` fixed 1.4 (unused), gait cost OFF (weight
  effectively 0 via the schedule indicators being disabled — implementer picks the cleanest
  static-branch form mirroring cmd_c's `if self._heightmap`). Blind 105-d obs and reward
  byte-unchanged. Deploy path protected, third time, same pattern.

### 2. Schedule indicators (smoothed)

`stance_sched_i(θ)` = raised-cosine smoothed indicator of `frac(θ + offset_i) < DUTY`,
transition half-width `GAIT_SMOOTH = 0.05` phase units on each edge (no reward cliffs).
`swing_sched_i = 1 − stance_sched_i`.

### 3. Schedule enforcement — COST form (deliberate deviation from WTW's positive pair)

```
gait_cost = Σ_i [ contact_i · swing_sched_i  +  (1 − contact_i) · stance_sched_i ]
w_gait    = −W_GAIT · gait_cost · cmd_moving          (W_GAIT = 0.15, --w-gait)
```

- Farm doctrine: "every positive shaper got farmed, no cost ever did." WTW's shaped-force/vel
  REWARDS are replaced by an equivalent-pressure cost: a cost maxes at 0 — unfarmable. A
  standing robot bills ~2·W_GAIT/step (two feet always violating) → rhythm mandatory.
- `cmd_moving` gate: idle command still means STAND (no step-in-place forcing; stand cost
  keeps its job).
- Sizing: W_GAIT 0.15 → standing pressure ~0.3/step (binding on flat); a 0.5 s mid-climb
  schedule break ≈ 7·0.15·2 ≈ 2 < one riser's w_climb 3.2 — climbing may break rhythm when
  it pays. Slow f is the intended stair regime anyway.
- Contact-threshold note: rhythm satisfied at foot_h 1.6 cm is BY DESIGN — the clock owns
  timing, `cmd_c` owns height (division of labor).

### 4. Clearance goes phase-native (WTW's exact form, our one-sided cost kept)

```
target_i  = cmd_c · envelope_i        envelope_i = sin(π · swing_frac_i)  (0 at edges, 1 mid-swing)
clearance = Σ_i max(target_i − foot_h_i, 0) · sqrt(v_i) · swing_sched_i
```
- Billed ONLY during scheduled swing (stance feet fully exempt — √v mostly did this already).
- Blind path: keeps the v5 form (always-on, flat target BLIND_FOOTSWING) — byte-unchanged.

### 5. Obs +3 (teacher): append after cmd_c → [sin 2πθ, cos 2πθ, cmd_f scaled]

Obs 227 → **230**. Regraft `--add-dims 3` (heightmap block dims 105-225 and cmd_c dim 226
unchanged; clock dims 227-229). Blind stays 105.

### 6. Unchanged

w_climb / beta_climb / w_pbrs, carry/air, pose/upright (v5 forms), stage schedule, terrain,
clip. `--footswing-max`, `--w-clearance` etc. all stand.

## Non-farmability review

- gait_cost: cost, max 0. Gated by cmd_moving (env-chosen commands, not policy-chosen).
- Phase-masked clearance: still one-sided cost. Envelope only LOWERS the target near edges —
  strictly less billing than v5's always-on form. No new positives anywhere in v6.
- Composed: schedule + clearance + air (landing-gated, capped) + carry (holds) — the only
  zero-cost trajectory is stepping on schedule at commanded height. That IS the task.

## Acceptance

- Tests: clock advance/wrap + f-resample continuity; schedule indicators (duty windows,
  smooth edges); gait cost 0 for a perfectly-scheduled contact pattern, >0 for anti-phase,
  gated off at idle cmd; clearance masked (stance foot below target bills 0); envelope 0 at
  swing edges; obs 230 teacher (last 3 = clock) / 105 blind; blind reward byte-unchanged
  vs v5 (regression pin).
- **Probe gate (upgraded, before any run):** probe_reward_landscape reworked to a TEACHER env
  with its scripted trot PHASE-ALIGNED to the clock (set cmd_f = 1/script period, offsets
  matched): (a) compliant script → w_gait ≈ 0 (≥ −0.05) and pose/upright walls hold
  (≥ −0.11 / ≥ −0.15); (b) anti-phase script (offset by half period) → w_gait strongly
  negative (≤ −0.2). Both directions or NO-GO.
- Regraft: `--add-dims 3` on hm227 pkl → hm230.

## Audit amendments (2026-07-24 pre-build review)

- **Latency phase-lead:** 75 ms servo lag = 0.1-0.15 phase at f 1-2 Hz — a purely reactive
  tracker eats an unavoidable schedule bill; the clock obs enables ANTICIPATION (lead the
  clock by the latency, feedforward, learnable). Comment this at the gait-cost term.
- **Watch recalibration:** the enveloped clearance LOWERS the billing baseline — v6
  unadapted `clear` ≈ −0.06 (NOT v5's −0.17). Primary run signal = `w_gait` −0.2 → ~0
  (phase-lock); `clear` → 0 is secondary and subtle.
- **Turns:** strict trot during mixed vx+wz arcs pays a compliance tax (WTW-accepted);
  wz-only turn-in-place is already exempt via the xy-magnitude `cmd_moving` gate. Watch yaw.

## Run plan (fennec_gait_v6)

Fresh 4-stage from the 230-graft, defaults + beta 20. WATCH: (1) w_gait → ~0 within stage 1
(phase-lock — should be FAST, it's a timing nudge); (2) `clear` → 0 (c-tracking now on
scheduled swings); (3) swing/gzmax/wclimb chain. Kill: w_gait stuck ≤ −0.2 at 10M (won't
lock — freq range wrong?); clear frozen after lock (the c-mechanism still dead even with
schedule — would falsify the root-cause story, full stop). Success bar unchanged: 4 cm
probable, 6 cm ambitious, 8 cm ceiling-discovery.
