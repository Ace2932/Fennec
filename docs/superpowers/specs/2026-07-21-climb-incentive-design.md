# Climb incentive — ascent-mode design (v2, post-2-reviews + Aiden's direction)

**Date:** 2026-07-21
**Status:** DRAFT — architecture chosen (ascent-mode-as-task, Aiden's call). Undergoing a 3rd adversarial review before an implementation plan. Two open decisions marked ⟐.
**Context:** #130 (terrain-relative reward) merged + validated. Clean 4-stage re-run (`nova_climb_v1`, ~104M) does NOT climb — parks on the flat pad, orbits, never ascends. #130 removed the climb *penalties* but nothing made ascending the task.

## The decision: ascent is a MODE whose OBJECTIVE is climbing (not a bonus)

The robot walks autonomously (normal velocity command). When its own stair-detector / nav recognizes stairs in the path, it enters **ascend mode**: a distinct commanded mode whose *task* is to climb. This is set by a flag in the observation — during training on stair envs, at deploy by perception ("recognizes stairs, tells itself").

### Why a MODE dissolves the knot the first two reviews hit

- A *non-farmable* climb reward is potential-based → policy-invariant → cannot make climbing optimal if orbiting already is.
- A climb reward that *does* force climbing is a farmable level (rear-up/pogo).
- **Escape:** make climbing the *objective in ascend mode*, not shaping on top. Then climbing is optimal *because it is the task*, and it stays non-farmable because the objective is real terrain traversal.

### The ascend-mode objective

`reward_ascend = w_climb · Δ(min over feet of ground_z)` where `ground_z` = per-foot `_terrain_ground_z(foot_xy)` (#130's terrain-height-under-foot).

- Telescopes over the episode to (terrain under the lowest foot at end − at spawn) = net ascent.
- **Non-farmable:** rear-up / stand-tall / pogo / lift-one-foot leave terrain-under-foot unchanged → Δ=0. To bank it the *lowest* foot must step onto a higher tread — a real climbing stride, un-postureable, un-bounceable.
- **Direction-free:** "gain terrain height" is intrinsically uphill; the policy reads which way is up from the heightmap. No command-hack needed.

### This SUPERSEDES the F1/F2 terrain/command hacks

The prior draft needed to *force* climbing (shrink the pad, outward-radial command) because a velocity command lets the robot orbit a flat contour. The ascend objective kills that directly: **orbiting a stair contour stays at constant height → Δ min(ground_z) = 0.** Sitting on the pad → 0. Only ascending pays. So:
- **No `FLAT_R_STAIR`, no outward-radial / heading-lock command needed.** Keep the existing terrain + pad.
- Sitting still in ascend mode earns only the alive bonus (+0.1); climbing earns `w_climb·gain − energy`. As long as `w_climb·gain > energy cost`, climbing dominates sitting — a tuning question, not a topology problem.

### Modes

| | Normal mode (flag 0) | Ascend mode (flag 1) |
|---|---|---|
| trigger | default | robot's stair-detector / nav (training: stair envs) |
| objective | track velocity command (`progress`/`track`/`yaw`) | `w_climb·Δ min(ground_z)` |
| stability costs | all active | all active (pose/upright/slip/energy/jerk/done — climb without falling) |
| flat gait | unchanged — **#130 flat no-op holds** | n/a |

Normal mode is byte-identical to today (flag 0 gates the ascend term to 0). The flat gait cannot be corrupted by the climb behavior and vice-versa; the modes are distinguished by the flag.

## Mechanism / plumbing

- **Obs:** add the ascend flag (obs 226→227). Graftable with zeroed weight, exactly like the heightmap graft.
- **Reward:** `reward = (1−flag)·[track+yaw+progress] + flag·[w_climb·Δ min(ground_z)] + alive + (all costs)`. The costs (pose/upright/slip/energy/jerk/actrate/splay/z + terrain-relative done) stay active in BOTH modes so the robot climbs stably.
- **State:** re-point the existing `last_base_z`/`climb_delta` plumbing (env.py:557) to track `min(ground_z)` for the reward; keep the base_z-based `climb`/`climb_max` METRICS for judging.
- **Command in ascend mode ⟐:** likely ignore vx/vy/wz for the objective (climb what's in front); nav aims the robot in normal mode then flips ascend on. Optionally a mild heading-hold so it doesn't drift sideways off the stairs.

## Training

- **Flag correlates with terrain:** ascend on for the stair-env slice, off for flat/rough. So the policy learns "flag on + heightmap-shows-stairs → climb," "flag off → track velocity." Enough ascend data (stair_frac 0.6) to learn climbing; flat-frac (0.25) retains the flat gait in normal mode.
- **Curriculum handles the sparsity:** min(ground_z) pays once per completed stride; stage-1 2cm risers make strides complete fast → dense early signal → the climbing gait forms, then scales up 0.25→1.0. Reuse the existing 4-stage curriculum, graft the flat walker.
- Build ON #130 (terrain-relative done/contact/clearance) — the prerequisite that makes climbing un-penalized.

## Deployment

Walk (flag 0) → perception/nav recognizes a staircase in the path → flag 1 → climb → flag 0 at the top. Nav keeps the choice to go around (flag 0, route around) vs climb (flag 1). Matches the autonomous-with-ascent-mode intent exactly.
**Unchanged gap:** obs 227 still includes the PRIVILEGED perfect heightmap — a teacher, not Jetson-deployable until distilled onto the real D456/L2 elevation view. The flat 105-d policy remains the only deployable one.

## 3rd review — 2 blockers + farm traps found and RESOLVED

**BLOCKER A (plumbing): the flag can't reach the obs as written.** `is_stair` is a local in the vmapped `rand()` (terrain.py:88), used then discarded — never in `info`/`_get_obs`. **Fix:** write `is_stair` into a sentinel hfield corner cell (`hfield_data` IS per-env) in `domain_randomize`; read `flag = sys.hfield_data[sentinel]` in `_get_obs`. Sentinel cell outside the ±0.4 m heightmap window and unreachable by feet. **Unit-test flag==is_stair across a vmapped batch before writing the plan.**

**BLOCKER B (cold-start bootstrap): do NOT ignore the command in ascend mode.** The ascend objective deletes the velocity reward; the graft's zeroed flag-weight makes the robot ignore the flag at step 0; `min(ground_z)` only pays once the trailing foot climbs. With no command drive the flat walker never leaves the pad → re-parks, now with no reward to escape. **Fix:** keep `progress`/`track` partly active in ascend mode (annealed as climbing takes over) so the command drives the robot onto the stairs — this also KEEPS nav steering (resolves the old ⟐2). Plus a policy-invariant **PBRS density potential on `mean(ground_z)`** to thicken the sparse early gradient.

**Farm traps (all fixed in the corrected objective below):**
- **Signed delta, NEVER clip≥0** — a positive-clipped delta is an *unbounded* climb-descend/thrash farm. Signed telescopes → oscillation nets 0. (Re-point `climb_delta` to `min(ground_z)` and keep its existing unsigned discipline.)
- **`w_climb ≈ 25-60, not ~1e4`** — sizing it to match the velocity mode's ~2200 episode return spikes the shared value head and ROTS the flat gait (the original failure). Tune for comparable advantage *variance*, not return; watch `training/v_loss`; budget 2-3 `w_climb` tuning runs. Handle the value-scale gap with a PBRS densifier / per-mode advantage-norm, NOT by inflating `w_climb`.
- **Non-farmability leans on an EXISTING coupling:** `base_h = height − min(ground_z)` (env.py:285) ties the reward's `min` to `height_pen` + `done`. The one real exploit (swing a foot's xy over higher terrain without climbing) is bounded (~one riser, one-time) AND self-limited — inflating `min` drives `base_h` down → `height_pen` up → death. **KEEP `height_pen`/`done` active on the SAME `min` — that coupling is the lock.**
- **Aggregate:** use **`softmin` over feet** (non-farmable like min, denser gradient, less identity-switch noise) OR **min over CONTACTING feet** (closes the airborne channel outright). NOT mean/sum as the objective (farmable); `mean` is fine as the PBRS *potential*.
- **Rebase `last_min` at the flag 0→1 edge** so the first ascend Δ is 0 (no double-count spike).
- **Decouple `is_flat`/`is_stair` draws** so ascend envs always have a real riser (15% were degenerate flat-with-flag → diluted the climb signal).
- Append flag as the **LAST** obs dim (`graft_obs.py --add-dims 1`; NOT in `_prop_frame` or it ×HIST → 229). Add an obs-size assert on the restore pkl.

### Corrected ascend-mode reward

```
last_min := min_i ground_z_i        # maintained EVERY step, both modes
on flag 0→1: last_min := min_i ground_z_i          # rebase, first Δ = 0
reward_ascend = w_climb · (softmin_i ground_z_i − last_min)     # SIGNED, never clip

reward = (1−flag)·[track+yaw+progress]
       + flag·[ reward_ascend + α·(track+progress) ]   # α anneals 1→~0 as climbing forms (bootstrap drive)
       + β·PBRS(mean ground_z)                          # policy-invariant density
       + 0.1 alive + ALL costs                          # height_pen + terrain-relative done on the SAME min = the lock
```
`w_climb ≈ 25-60`, verify `w_climb·STAIR_RISE·level > per-stride cost` at each curriculum level before scaling level up.

## DECIDED: unidirectional (real) staircases — and it's strictly better

Re-checked the farm both prior reviews flagged for the switch: on stairs rising in +x, `min(ground_z)` = terrain under the lowest-x foot; raising it requires that foot to step to higher x = climb. Lateral (+y) = same height = Δ0 (earns nothing, correct); backward = negative Δ. **No bypass to high ground** — height depends only on x, so high x is reachable only by traversing the stairs; the TZ-cap edge is reached by climbing; the airborne-foot exploit stays bounded + `base_h`-locked. **Farm-safe.**

Why unidirectional beats radial here:
- **Better bootstrap:** spawned facing uphill, a forward-biased command drives +x = straight up. Radial let "forward" (body-frame) rotate → orbit (Blocker B's root). The annealed-command bootstrap now works *with* the geometry.
- **Heading-invariant for free:** the obs is a *yaw-aligned* heightmap + body-frame proprioception — no world-frame info — so fixed-+x terrain teaches "rising terrain ahead → climb," which generalizes to any-direction approach at deploy. **No need to randomize stair direction.**
- Cleaner perception (stairs "ahead" not "all around"); real-staircase sim2real.

**Terrain change (localized to the `is_stair` branch of terrain.py):**
- Radial `r = |cell − center|` → directional `d = (cell − center)·x̂` in `step_idx`. Flat for `d < FLAT_R`, risers for `d > FLAT_R`, plateau at TZ.
- Full-width in y (height depends only on x → no side cliffs).
- Spawn UNCHANGED — center (0,0,0.17) is in the flat bottom zone facing +x. No spawn-position plumbing.
- smooth/step/flat envs keep the radial pad; only stair envs go directional.
- All v3 fixes (flag-sentinel, signed δ, w_climb 25-60, softmin, base_h lock, last_min rebase, decoupled draws) are geometry-independent and hold. Blocker B gets *easier*.
- **Verify in TDD (like #130):** no div-by-zero, no spawn-into-geometry, no bypass corridor to high terrain, min(ground_z) rises only by forward climbing.

## Open decisions ⟐ (only tuning remains)

1. **`α` anneal schedule and `w_climb`/`β` starting values** — tuning, 2-3 runs; not blocking the plan.

## Still-open feasibility notes

- 120M is a reasonable first attempt ONLY with the bootstrap drive (annealed command) + PBRS density present; without them it parks (the 104M non-climber says nothing — it had no objective).
- Flat-gait forgetting is well-protected: flag=0 gets ~40% of the batch (8× the ~5% that caused the original rot), byte-identical to today.
- Still a privileged-heightmap teacher → distillation gap unchanged.

## Retracted / out of scope

- Naive `+base_z` bonus (farmable); first-draft A+B (A can't force on radial, B is a pogo farm); the F1/F2 terrain/command hacks (superseded — the ascend objective removes the need). `TZ`→0.32 and stair-frac ramp are separate backlog. Descent is a future mode. #130 geometry + the flat 105-d policy untouched.
