# Crawl-gait v8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Checkbox (`- [ ]`) steps.

**Goal:** Add a terrain-selected slow CRAWL gait (one foot at a time, 3-leg support) alongside the existing trot, so the policy trots on flat and crawls on stairs — the gait tall risers need. Reuses the v7 tracking reward + v6 gait cost unchanged (both read the schedule, which becomes gait-parameterized). Crawl-ceiling probe already PASSED (6.7cm stable, ~2× trot).

**Architecture:** Task 1 = gait-parameterize `_gait_schedule` + crawl params + terrain selection + F_MIN + per-foot schedule obs (env.py + tests). Task 2 = fingerprint + probe crawl-gate + suite. Spec: `docs/superpowers/specs/2026-07-24-crawl-gait-v8-design.md` — READ FIRST. Builds on v7 (branch off sim/swingref-v7). Obs 230→234, regraft `--add-dims 4` (run-time).

**Tech Stack:** JAX/Brax MJX; tests `JAX_PLATFORMS=cpu` from `sim/nova_mjx/`, foreground, 600000 ms, one file per call.

## Global Constraints

- Crawl consts: `CRAWL_OFFSETS` (one-foot-at-a-time, per LEG_NAMES FL,FR,RL,RR — use the STABLE order the crawl probe validated: READ `sim/nova_mjx/probe_crawl_ceiling.py` for the exact sequence + offsets it used with no falls, and match it), `CRAWL_DUTY = 0.75`. Trot stays `GAIT_OFFSETS`/`GAIT_DUTY` (0.5).
- `_gait_schedule(theta, offsets, duty)` — gait-parameterized (offsets+duty were module consts, now per-env args threaded from info). Trot call (offsets=GAIT_OFFSETS, duty=0.5) must reproduce v6/v7 BYTE-IDENTICAL (regression pin — the whole v7 tracking chain depends on it).
- Per-env gait stored in `info` (offsets+duty, or a gait-id scalar 0=trot/1=crawl the schedule maps): stair-terrain envs → crawl, flat/rough → trot. Set in `domain_randomize` alongside the terrain-type draw (read how is_stair/flat_frac are drawn there). Teacher only; blind → trot (no behavior change, byte-pinned).
- `F_MIN 1.0 → 0.3` (crawl slow-swing band); crawl envs sample `cmd_f` low (0.3-0.6), trot envs 1.0-2.0. Trot cmd_f distribution on flat unchanged where possible (or documented).
- Obs teacher += 4 per-foot `swing_sched` values → 230→234 (append AFTER the v6 clock dims 227-229; heightmap+cmd_c+clock unmoved for regraft safety). Blind 105 byte-unchanged.
- Reuse v7 tracking (`swingref`) + v6 gait cost (`w_gait`) UNCHANGED — they read swing_sched/swing_frac, now gait-correct for free. NO new reward terms.
- Blind reward byte-pinned (BLIND_REWARD_PIN 0.892089664936 @1e-6). NO touch: climb/PBRS/pose/upright/carry/air/clip.
- Commits: `sim/env: …`, `sim: …`.

---

### Task 1: Crawl schedule + terrain-select + obs (env.py)

**Files:** Modify `sim/nova_mjx/env.py`; extend `sim/nova_mjx/test_gait_clock.py`.

**Interfaces:** `CRAWL_OFFSETS`/`CRAWL_DUTY` consts; `_gait_schedule(theta, offsets, duty)` signature; per-env gait in info; obs 234.

Steps (TDD):
```python
def test_gait_schedule_trot_unchanged():   # _gait_schedule(θ, GAIT_OFFSETS, 0.5) == old v6 output, bit-identical
def test_crawl_one_foot_at_a_time():       # crawl schedule: stance_sched sums to ~3 for all θ (3-leg support); exactly one foot's swing_sched≈1 at a time
def test_crawl_duty_075():                 # each foot swing-scheduled ~25% of the cycle
def test_terrain_selects_gait():           # stair env → crawl offsets/duty in info; flat env → trot (probe domain_randomize output)
def test_f_min_extended():                 # crawl envs sample cmd_f in [0.3,0.6]; F_MIN=0.3
def test_obs_234_teacher_last4_swingsched(): # obs 234, last 4 = per-foot swing_sched; blind 105
def test_blind_reward_pin_holds():         # BLIND_REWARD_PIN @1e-6 (v8 doesn't touch blind)
```
Implement: consts (match probe's stable crawl order); `_gait_schedule` gait-parameterized (offsets+duty args), reuse the raised-cosine circular-distance body (just parameterize duty + offsets); thread per-env gait through info (reset seeds it from terrain type, resample-safe); domain_randomize selects gait by terrain; F_MIN 0.3 + gait-dependent cmd_f band; obs append 4 swing_sched. Comment: crawl = 3-leg support for tall lift (probe 6.7cm), reuses v7 tracking for height.

Run test_gait_clock.py, test_lift_clearance.py, test_climb_reward.py, test_heightmap.py. Commit: `sim/env: v8 crawl gait — parameterized schedule, terrain-selected trot/crawl, F_MIN 0.3, obs 234`.

---

### Task 2: Fingerprint + probe crawl-gate + suite

**Files:** `sim/nova_mjx/train.py`, `sim/nova_mjx/probe_crawl_ceiling.py` (extend to a reward-gate).

Steps:
- Fingerprint: add a `gait` line showing terrain-selected trot/crawl + crawl offsets/duty + F range; note obs 234. Resume-stub: add CRAWL consts if imports need.
- Probe gate: extend `probe_crawl_ceiling.py` — with the v8 env + v7 tracking reward active, drive the IK crawl at the reference height (cmd_c on crawl envs) and confirm total reward is MAXIMIZED at the crawl reference lift (4-6cm), w_swingref minimized there, w_gait ≈0 for the compliant crawl schedule. PASS = the v8 landscape pays for the tall crawl lift. (This is the v7 IK-gate logic on the crawl schedule.)
- Full suite one file per call (test_gait_clock, test_lift_clearance, test_heightmap, test_climb_reward, test_curriculum_resume, test_resume_budget, test_terrain_relative).
- Commit: `sim: v8 crawl fingerprint + IK crawl-reward gate`.

## Run (GATED — after v7 confirms tracking lifts swing)

Regraft flat-walker → 234, resume from v7's policy, fresh 4-stage. Do NOT run until v7's run shows the tracking reward moves swing off 0.02 (else amplitude × gait-type confound). Success: crawl swing lifts to 4-6cm on stair envs, gzmax scales, climbs 4-6cm risers. 8cm = stretch (learned CoM-shift).
