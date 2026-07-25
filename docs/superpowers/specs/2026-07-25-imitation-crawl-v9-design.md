# Imitation crawl v9 — behavior-clone a scripted climber, then RL fine-tune

**Date:** 2026-07-25
**Status:** DRAFT — Aiden chose imitation after v8's crawl came out a splayed in-place shuffle
(learning failure, not hardware — the CoM-shift de-confound proved rears reach 5.4cm; the policy
just won't DISCOVER the coordinated forward-crawl). 8 generations of "feasible but undiscovered."
Imitation SHOWS the correlated behavior instead of hoping RL finds it — the direct answer to the
root cause (white noise can't discover correlated multi-step motion).

## Pipeline

1. **Scripted expert** — a whole-body crawl-climb controller (leg IK + crawl schedule + forward
   foothold planning + CoM-shift) that DEMONSTRABLY climbs stairs in sim. THE PREMISE — build +
   validate (video) FIRST; no downstream work until it climbs.
2. **Demo generation** — run the expert across many stair envs + DR, record (obs_234, action_12)
   pairs. Obs = exactly what the policy sees (proprio+heightmap+cmd_c+clock+swing_sched).
3. **Behavior cloning** — supervised-train the policy net (same brax arch) obs→action (MSE/NLL)
   to reproduce the expert. Output a BC policy pkl (obs 234).
4. **RL fine-tune** — PPO from the BC init (`--restore-params-pkl` the BC policy) with the
   existing reward stack (climb/PBRS/tracking/gait/DR). BC gives the correlated crawl; RL refines
   robustness + climbs higher + sim2real. The reward stops being a discovery mechanism (it never
   worked as one) and becomes a refinement/robustness signal (which costs always did well at).

## Step 1 — the scripted expert (this build; the rest gated on it)

`sim/nova_mjx/scripted_crawl_climber.py`:
- Reuse the validated leg IK (nova_locomotion/kinematics/leg_ik.py), the crawl schedule
  (CRAWL_OFFSETS/DUTY from env), the CoM-shift from probe_crawl_comshift.py (gain ~0.5, the
  stable one).
- **Foothold planner:** each foot, during its scheduled swing, targets the NEXT foothold =
  current stance xy + forward step (stride) + UP onto the next tread (read the tread height from
  the terrain/heightmap ahead). Foot arc = lift over the riser edge (>riser height) then down
  onto the tread. Body pitches up naturally as feet land on successive treads.
- CoM-shift: before lifting each foot (esp. rear), shift the body over the 3-leg support
  triangle (the +3.3cm de-confound mechanism).
- **Validate:** rollout on a stair env (stair-level 0.25 first, then 0.5), MEASURE base-z ascent
  + per-foot landing heights + no-fall, and VIDEO it. PASS = base ascends ≥2 risers, feet land
  on successive treads, up_z>0.9. If it can't climb → the expert needs work (foothold/CoM tuning)
  before ANY BC.

## Acceptance (Step 1)

- Scripted controller climbs ≥2 risers at stair-level 0.25 (base-z rises by ≥2·riser, feet on
  successive treads), stable (no fall, up_z>0.9). Video shows a recognizable crawl-climb.
- Reuses validated IK + crawl schedule + CoM-shift (no new IK).
- If it climbs 0.25 cleanly, try 0.5 (4cm) — the real target band.

## Downstream (gated on Step 1 climbing)

- Demo gen: ~10^5-10^6 (obs,action) pairs across stair levels + DR seeds.
- BC: MSE on actions (tanh-Gaussian mean), obs-normalized like PPO; validate the BC policy
  reproduces the climb in a rollout BEFORE RL.
- RL fine-tune: PPO restore-params from BC, existing reward, watch it KEEP the crawl (not regress
  to shuffle — a known BC→RL failure; may need a KL/BC-regularization term or low LR).

## Honesty

This is the campaign's logical endpoint: RL never discovered the correlated crawl in 8 tries;
imitation removes discovery from the critical path. If even the SCRIPTED expert can't climb,
that IS the honest hardware/controls wall (bank the walker). If it climbs, BC+RL is the highest-
odds path to a learned climber. Success bar unchanged: 4-6cm risers (8cm CoM-shift stretch).
