# Gait Clock v6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trot clock + schedule-violation cost + phase-native clearance (teacher-only), so swing TIMING is commanded and `cmd_c` finally has scheduled swings to shape. Probe gate proves compliance ≈ free / anti-phase ≈ billed before any run.

**Architecture:** Task 1 = clock state + schedule indicators + gait cost + obs 230 (env.py + tests). Task 2 = phase-native clearance + blind regression pin (env.py + tests). Task 3 = probe rework + train threading + fingerprint + full suite + PROBE GATE. Spec: `docs/superpowers/specs/2026-07-24-gait-clock-v6-design.md` — READ IT FIRST every task; it holds semantics + the causal rationale.

**Tech Stack:** JAX/Brax MJX; tests `JAX_PLATFORMS=cpu` from `sim/nova_mjx/`, foreground, 600000 ms, ONE file per call.

## Global Constraints

- Consts: `F_MIN = 1.0`, `F_MAX = 2.0`, `GAIT_DUTY = 0.5`, `GAIT_SMOOTH = 0.05`, `W_GAIT = 0.15`, `GAIT_OFFSETS = [0.0, 0.5, 0.5, 0.0]` (FL,FR,RL,RR — verify order matches LEG_NAMES/_foot_ids; FL+RR in phase, FR+RL antiphase).
- Teacher-only via the SAME static-branch pattern as cmd_c (`if self._heightmap`); blind 105-d obs AND blind reward byte-unchanged vs v5 (pin with a regression test comparing a stepped blind env's reward to the pre-change value captured in the test).
- Clock: `info["gait_phase"]` random-seeded at reset (fold_in RNG — never add split keys), `θ = frac(θ + cmd_f·dt)` per step; `info["cmd_f"]` U(F_MIN,F_MAX) teacher / fixed 1.4 blind, resample at the `step % 250` site (jp.where pattern, teacher-only).
- Schedule: `stance_sched_i` = raised-cosine smoothed `frac(θ+offset_i) < GAIT_DUTY`, half-width GAIT_SMOOTH per edge; `swing_sched = 1 − stance_sched`.
- Gait cost EXACTLY: `w_gait = -self._w_gait * jp.sum(contact*swing_sched + (1-contact)*stance_sched) * cmd_moving_f` where `cmd_moving_f` is the existing cmd_moving as float. Kwarg `w_gait=W_GAIT`, flag `--w-gait`.
- Clearance (teacher): `envelope_i = jp.sin(jp.pi * swing_frac_i)` (swing_frac = position within the swing window, 0..1); `clearance_cost = Σ max(cmd_c*envelope − foot_h, 0)*sqrt(v)*swing_sched`. Blind keeps the v5 always-on form with BLIND_FOOTSWING.
- Obs teacher: append `[sin(2πθ), cos(2πθ), cmd_f * F_OBS_SCALE]` AFTER cmd_c → 230; pick F_OBS_SCALE ~0.5 (maps 1-2 Hz into the O(1) band, comment the convention). Blind 105.
- NO new positive terms. No touch: climb stack, carry/air, pose/upright, clip, terrain, stage schedule.
- Commits per task; messages `sim/env: …` ×2, `sim: …` for Task 3.

---

### Task 1: Clock + schedule + gait cost + obs (env.py)

**Files:** Modify `sim/nova_mjx/env.py`; create `sim/nova_mjx/test_gait_clock.py`.

**Interfaces produced:** consts above; `info["gait_phase"]`, `info["cmd_f"]`; `_gait_schedule(theta)` helper returning `(stance_sched, swing_sched, swing_frac)` shape (4,); `w_gait` metric; obs 230. Task 2 consumes `_gait_schedule`; Task 3 threads `--w-gait`.

TDD sketches (write full tests; manufacture states like test_lift_clearance does):

```python
def test_clock_advances_and_wraps():        # theta(t+1) == frac(theta + f*dt); wraps past 1
def test_cmd_f_range_and_blind_fixed():     # teacher U(1,2); blind == 1.4 constant
def test_schedule_windows():                # at GAIT_SMOOTH-away-from-edges: FL stance while FR swing (antiphase); duty 0.5
def test_schedule_edges_smooth():           # indicator continuous across the edge (sample θ grid, max step < 0.15)
def test_gait_cost_zero_when_compliant():   # manufacture contact pattern == schedule -> w_gait ≈ 0
def test_gait_cost_bills_antiphase():       # contact pattern inverted -> w_gait ≤ -0.15*4*0.7 (strongly negative)
def test_gait_cost_idle_gated():            # cmd ~0 -> w_gait == 0 regardless of pattern
def test_obs_230_teacher_105_blind():       # last-3 = sin/cos/f-scaled; blind unchanged
```

Manufacturing contact patterns: set θ via info override to a mid-window phase, lift the base (all airborne) or leave planted (all contact) — with duty 0.5 antiphase pairs, ALL-planted at any θ gives cost ≈ 2·W_GAIT·cmd_moving (two feet scheduled swing), ALL-airborne the mirror. Use those two + θ choices to hit the compliant/anti cases without per-foot manufacturing. cmd override for the idle gate (existing `_moving_state`-style helpers).

Implement per Global Constraints (read cmd_c's reset/resample/obs-append blocks and mirror all three; fold_in with a NEW unique data arg). `w_gait` into the reward sum + metrics tuple + update. Run test_gait_clock.py then test_lift_clearance.py then test_heightmap.py (obs 227→230 teacher assertions there — update). Commit: `sim/env: v6 gait clock — trot phase state, schedule indicators, gait-violation cost, obs 230`.

---

### Task 2: Phase-native clearance + blind regression pin (env.py)

**Files:** Modify `sim/nova_mjx/env.py`; extend `sim/nova_mjx/test_gait_clock.py` + reconcile `test_lift_clearance.py`.

- Teacher clearance → the enveloped, swing-masked form (Global Constraints). Blind branch keeps v5 form EXACTLY — implement as a static `if self._heightmap` split at the clearance computation.
- Blind regression pin test: build blind env, manufacture the `_moving_state` case, assert `w_clearance` equals the Task-1-era value to 1e-6 (capture the number by running pre-change — document it in the test comment).
- New tests: stance foot below target bills 0 (masked); mid-swing target == cmd_c (envelope peak); swing-edge target ≈ 0; teacher clearance ≤ v5 form on identical states (envelope only lowers billing).
- Reconcile v5 tests that assumed always-on clearance on TEACHER envs (blind-env tests untouched — most of test_lift_clearance is blind, verify by reading).
- Run test_gait_clock.py + test_lift_clearance.py + test_climb_reward.py. Commit: `sim/env: v6 phase-native clearance (enveloped, swing-masked; blind path pinned unchanged)`.

---

### Task 3: Probe rework + threading + fingerprint + suite + PROBE GATE

**Files:** Modify `sim/nova_mjx/probe_reward_landscape.py`, `sim/nova_mjx/train.py` (+ resume-test stub).

- Probe: switch to `NovaJoystick(heightmap=True)`; override per reset: `cmd_c=0.05`, `cmd_f = 1/(2*T_swing)` — the probe's T is SWING duration; full trot cycle = 2T at duty 0.5 (T=0.4 -> f=1.25 Hz). Getting this wrong double-clocks the schedule and bills a perfectly-aligned script, and `gait_phase` pinned each step to the SCRIPT's phase (compute from step index and T, offset so script-swing aligns with schedule-swing; document the alignment). Add a second measurement mode: anti-phase (phase pinned + 0.5). Report w_gait for both.
- train.py: `--w-gait` (mirror --w-clearance), diagnostics line: add `wgait {m('w_gait')/L:+.3f}` (the run's PRIMARY signal: ~-0.2 unadapted -> ~0 phase-locked); fingerprint lines: clearance line gains `phase-native`, new `gait clock    : trot f∈[{F_MIN:g},{F_MAX:g}]Hz duty 0.5, w_gait {w_gait:g} (v6 schedule cost)`.
- Full suite one file per call (test_gait_clock, test_lift_clearance, test_heightmap, test_climb_reward, test_curriculum_resume, test_resume_budget, test_terrain_relative).
- THE GATE (after committing): run the probe. PASS = compliant w_gait ≥ −0.05 AND pose ≥ −0.11 AND upright ≥ −0.15 at a=0.8/1.0, AND anti-phase w_gait ≤ −0.2. Report raw numbers, PASS/FAIL per criterion, touch nothing on FAIL.
- Commit: `sim: v6 probe rework (phase-aligned + anti-phase modes), --w-gait threading, gait-clock fingerprint`.
