# Crawl-gait v8 — terrain-selected trot/crawl (the tall-stairs gait)

**Date:** 2026-07-24
**Status:** APPROVED — crawl-ceiling probe PASSED (probe_crawl_ceiling.py e6888d5): stable 6.73cm
(~2× the trot's 3.2cm), ≥6cm YES / ≥8cm marginal. Limiter = STANCE-leg torque saturation → 3.7cm
body sag (NOT swing reach); the probe omits CoM pre-shift, so 6.7cm is a PESSIMISTIC floor — a
closed-loop crawl learns CoM-sway coordination (upright/height costs incentivize it) and may push
toward 8cm. Build machinery now (independent of v7); the RUN waits on v7 confirming tracking lifts swing.
**Context:** the ~3-4cm ceiling that scared me was a TROT ceiling (fast, 2-leg diagonal support —
body sags under 2-leg load). Tall stairs are climbed by a slow CRAWL: one foot at a time,
3-leg triangle support (1/3 load/leg, stable), lifting leg UNLOADED (reaches high freely), slow
speed dodges the 2.8 rad/s limit, 8cm = 34% of the 236mm leg (kinematic reach trivial). We only
ever ran trot (clock 1-2Hz, diagonal offsets) — Fennec was never given the gait stairs need.

## Premise gate (MUST pass before building)

`probe_crawl_ceiling.py`: a slow 3-leg-support single-foot IK lift must reach ≥6cm (ideally
8cm) stably (up_z>0.9, no fall). PASSED: 6.73cm stable (2× trot), ≥6cm feasible. 8cm marginal (stance-torque-limited,
CoM-shift-dependent). SUCCESS RECALIBRATED: 4-6cm risers solid (the real capability); 8cm = stretch
the learned CoM-shift may reach, not a pass/fail bar.

## Mechanism — minimal 2-gait (NOT full WTW MoB)

We need exactly two gaits: **trot** (flat/rough — fast, efficient) and **crawl** (stairs — slow,
tall, stable). Not a continuous gait zoo (YAGNI).

### 1. Terrain-selected gait (in domain_randomize)

Per env, alongside the existing terrain-type draw (flat_frac/step_frac/stair_frac): stair envs
→ CRAWL, flat/rough → TROT. (Teacher: terrain-auto via the privileged heightmap. Deploy:
perception/nav picks it. Optionally sample a fraction of stair envs as trot so the policy keeps
both — decide in build.)

### 2. Crawl schedule (extends `_gait_schedule`)

- Crawl offsets: one foot swings at a time — sequence FL→RL→FR→RR (or the probe-confirmed
  stable order), offsets `[0, 0.5, 0.25, 0.75]` (per LEG_NAMES FL,FR,RL,RR — VERIFY the stable
  crawl order against the probe), **duty 0.75** (each foot down 75% → 3-leg support always).
- Trot unchanged: offsets `[0,.5,.5,0]`, duty 0.5.
- `_gait_schedule` takes per-env offsets+duty (was consts) → same raised-cosine stance/swing/
  swing_frac machinery, gait-parameterized.

### 3. Frequency: extend F_MIN 1.0 → 0.3

Crawl needs slow swings for high lift (probe: height ∝ swing duration; 8cm needs ~0.7-1.0s
swing → ~0.3-0.5Hz at duty 0.75). Trot stays 1-2Hz. Command `cmd_f` from a gait-dependent range
(crawl: 0.3-0.6, trot: 1-2) OR one wide range 0.3-2 with the schedule handling both.

### 4. Obs: the policy must see the (gait-varying) schedule

The crawl's per-foot phases aren't simple diagonal pairs, so global-phase alone underdetermines
the schedule. Add the **4 per-foot `swing_sched` values** to obs (the explicit "which feet swing
now, how much") → obs 230 → **234**. Regraft `--add-dims 4` (heightmap+cmd_c+v6-clock dims
unmoved). Blind stays 105. (Explicit schedule > making the policy learn offset patterns from a
scalar — don't repeat the campaign's discovery struggles.)

### 5. Reuse v7 tracking reward + v6 gait cost UNCHANGED

Both already read swing_sched/swing_frac from `_gait_schedule` — now gait-parameterized, they
work for crawl for free. The crawl schedules WHEN (one foot at a time); the v7 tracking reward
sets HOW HIGH (to cmd_c, now reachable up to ~8cm on crawl envs → raise footswing-max on crawl).

### 6. Command coupling (stairs are slow)

Crawling is slow → low forward velocity. The commanded vx on stair/crawl envs must allow low
speed (else track/progress fight the crawl). Bias cmd vx low on crawl envs, or widen the low end.

## Non-farmability

No new positive terms (gait cost + tracking cost are both costs, unchanged forms). The gait
schedule is env-selected (not policy-chosen) → can't be gamed. Per-foot swing_sched in obs is
observation, not reward.

## Acceptance (build, TDD)

- Crawl schedule: one foot swings at a time (stance_sched sums to ~3 for all θ — 3-leg support),
  duty 0.75 windows, stable sequence; trot schedule byte-unchanged (gait=trot reproduces v6/v7).
- Terrain selection: stair env → crawl offsets/duty, flat → trot (verify in domain_randomize).
- Obs 234 teacher (last 4 = swing_sched) / 105 blind byte-unchanged; blind reward pin holds.
- F_MIN 0.3 range; crawl cmd_f in the slow band.
- Probe gate (v8): the crawl-aligned IK-inject probe (extend probe_crawl_ceiling) shows total
  reward maximized at the crawl reference height (~6-8cm) with the tracking reward — the v8
  landscape pays for the tall crawl lift.

## Run (after v7 confirms tracking + probe confirms crawl ceiling)

Regraft → 234, resume from v7's policy (inherits tracking skill), fresh 4-stage. WATCH: on
stair envs, swing lifts toward the crawl reference (6-8cm), gzmax scales to the risers, wclimb
grows, wgait locks the crawl schedule. This is the real tall-stairs attempt. Success = climbing
6-8cm risers via the slow crawl. KILL: crawl swing caps at the trot ceiling (~3cm) despite the
schedule → the crawl doesn't deliver its promised lift closed-loop → the honest hardware wall.
