# Climb incentive — design (post-adversarial-review)

**Date:** 2026-07-21
**Status:** DRAFT for Aiden's decision. Two adversarial reviews (RL-reward + sim/terrain lens) redirected the first draft — this is the corrected design. Real task-design decisions remain (marked ⟐); do not build until chosen.
**Context:** PR #130 (terrain-relative reward) merged + validated. The clean 4-stage re-run (`nova_climb_v1`, ~104M) does NOT climb: `climb_max` flat 0.02 all stages; stair-level-1.0 rollout frames show the robot parked on the flat pad, orbiting, never stepping up. `len ~990` — survives by not engaging.

## Finding

#130 was **necessary but not sufficient**. It removed the *penalties* for climbing (contact/clearance/done/height_pen terrain-relative — correct, flat gait preserved). To actually climb, two things must both be true, and neither is:

- **(PAY)** A non-farmable reward for the ascent. `progress` reads *horizontal* velocity only (`lin_vel[:2]`); surmounting a 58° riser is mostly vertical, so the ascent stride *loses* ~0.30/step of progress. Nothing pays it back.
- **(FORCE)** The task must require ascending. A **body-frame velocity command is position-invariant** — no velocity command's satisfaction can require being higher, because velocity is a rate; there is always a flat contour that satisfies it. On radial stairs the robot orbits the center at constant radius, collecting full `progress` with zero climb.

## Two rejected fixes (one naive, one mine)

**Naive positive bonus `+w·clip(base_z − spawn_z)` — REJECTED (farmable).** `base_z` moves with posture: rear up / stand tall / pogo all bank height with no locomotion. This is the "run 13" additive-proxy trap the reward's 12-run history documents (env.py:438-465).

**First-draft Approach A+B — REJECTED by review:**
- *A (shrink pad, lean on existing progress)* does **not** force climbing. On radial stairs the refuge is every contour, not the pad; the robot orbits. "Bias the command outward" is not a body-frame velocity — it's a world-frame/goal command, the change the draft deferred.
- *B (3D velocity-projection progress)* is **worse than run 13**: the vertical axis is untracked by `track` and `progress` clips the downstroke at 0, so vertical bouncing pays ~+0.7/step for zero locomotion — a bigger farm than the clearance farm the whole reward was rebuilt to kill.

## The corrected design — PAY with a potential, FORCE with the command

### PAY — potential-based climb shaping (the clean positive the rule's dichotomy misses)

The "no positive shaper" rule is true for additive proxies on a *level/rate*; it is **false for potential-based reward shaping** (Ng et al. 1999): `r_shape = w·(Φ_t − Φ_{t−1})` is provably policy-invariant — it cannot create a new optimum, so it cannot be farmed by any closed posture loop (every loop telescopes to 0). Every farm in the history (clearance+, gait+, air+) was an additive proxy; **none was potential-based.**

- **Φ = `jp.min(ground_z)`** — terrain height under the *lowest* foot (`ground_z` is the per-foot `_terrain_ground_z` array #130 already computes). To raise the minimum, the lowest foot must physically step onto a higher tread — a climbing stride. Un-leanable (posture doesn't move terrain-under-foot), un-bounceable (vertical hops don't change which tread you're over), un-postureable.
- Reward `w_climb · (Φ_t − Φ_{t−1})`. Telescopes over the episode to (terrain under feet at end − at spawn) = net ascent. ~0 on flat (Φ constant). Pays exactly the ascent stride that `progress` currently drops.
- Plumbing exists: `climb_delta = base_z_now − last_base_z` (env.py:557) — re-point `last_base_z`/`peak_base_z` from `base_z` to `min(ground_z)`, add the weighted delta to the reward sum. The `climb`/`climb_max` **metrics** should stay base_z-based (they measure body ascent for judging); the **reward** uses the ground_z potential.
- ⟐ **`w_climb`**: must outweigh the ~0.05/step energy/jerk headwind but not swamp `track`/`progress`. Start small (e.g. match progress's effective scale) and treat as the one tuning knob. Do NOT cut `w_energy`/`w_jerk` instead — the headwind is 6× smaller than the progress hole and those terms guard the nose-dive/thrash farms.

### FORCE — make the command require ascending

Potential shaping *pays* for climbing but is policy-invariant — it speeds learning toward the optimum, it does not change what the optimum is. If the optimum is still "orbit the flat contour" the robot won't climb. So the command must make ascending the way to satisfy the task. Two ways ⟐ (Aiden's call — this is the real decision):

- **Option F1 — outward-radial progress on stair envs.** Replace/augment the body-frame `cmd_xy` projection with the **world-frame outward-radial** direction `r̂ = (bx,by)/‖(bx,by)‖`: reward `dot(r̂, vel_xy)`. Non-farmable exactly like progress (requires real outward displacement), and on radial stairs outward = up. Keeps the existing radial terrain. **Deployment note:** this changes what the robot is rewarded for on stair envs (go outward, not follow the joystick), so the deployed policy would need a "climb/ascend" command mode distinct from free joystick — think about how the nav layer would drive it.
- **Option F2 — directed course + heading lock.** Switch stair terrain to **unidirectional** stairs (rise monotonic in +x) and lock the command heading uphill (yaw task facing +x, vy≈0). Progress then rewards climbing directly. Cleaner reward semantics, bigger terrain change, and closer to the standard Rudin-style stair curriculum (promotion tied to along-course distance, which on stairs can't grow without climbing).

**Complement (either option):** shrink the stair-env flat pad so "forward soon means up." Sim review verified: use a **stair-only `FLAT_R_STAIR ≈ 3-4 cells`** (flat to ~0.35-0.40 m, feet clear the first riser with margin) — **never** zero it (div-by-zero in the smooth-pad formula) and **never** touch the global `FLAT_R=12` (would spawn smooth/step envs into geometry). This is a complement, not the fix; F1/F2 is what forces climbing.

## Feasibility (sim review, verified against the model)

- Spawn always at pad center (0,0,0.17); with any `FLAT_R_STAIR>0` the center stays flat, spawn clearance preserved — no keyframe change.
- Graft easy-start degraded but not broken: only the `stair_frac` slice loses the pad; smooth/flat envs still soft-land the flat walker. Stage-1 riser is 2 cm (within swing clearance) — it stubs, not faceplants.
- Heightmap obs is fine — the changed spawn view is invisible until the zeroed heightmap weights learn, which is the point.
- `is_stair` gating clean; `flat_frac` envs (level 0) stay flat regardless of pad. **No nova.xml rebuild** (terrain is runtime-generated).
- `done`'s min-over-feet `base_h` won't spurious-fire on a straddled spawn.

## Decisions for Aiden ⟐

1. **F1 (outward-radial reward, keep radial stairs) vs F2 (directed course + heading lock).** F1 is the smaller change and reuses the terrain; F2 has cleaner reward semantics and matches the literature but is a bigger terrain rewrite. This is the load-bearing choice.
2. **Deployment intent:** should stair-climbing be a distinct commanded mode (ascend) vs free joystick? F1 implies a mode; affects the nav layer.
3. **`w_climb`** starting value and whether the PBRS potential is base_z or (recommended) min-over-feet ground_z.
4. Accept "climbs directed stairs" as the target, or hold out for "climbs radial stairs under free joystick" (harder — needs F1's world-frame command).

## Retracted / out of scope

- The naive `+base_z` bonus (farmable) and the first-draft A+B (A can't force climbing on radial stairs; B is a pogo farm).
- `TZ`→0.32 and stair-frac ramp — separate backlog.
- The deployed flat 105-d policy and #130's geometry fix — both validated, untouched.

## Credits to the review

RL lens: PBRS is the non-farmable positive the "no positive shaper" dichotomy can't see; Φ must be min-over-feet ground_z not base_z; 3D-velocity progress is a pogo farm. Sim lens: radial+body-frame command topologically can't force climbing (the crux); `FLAT_R_STAIR` shrink-not-zero, stair-only; graft/obs/spawn all feasible; no MJCF rebuild.
