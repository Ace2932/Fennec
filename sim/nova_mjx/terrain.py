"""Procedural terrain for the MJX heightfield — the blind-locomotion curriculum
foundation. Each parallel env gets its own terrain via env.domain_randomize.

`level` in [0,1] = difficulty. The robot always spawns on a FLAT CENTER PAD
(spawn zone) and the ground roughens outward, so it learns to walk from flat
into uneven terrain. Smooth rough (slopes/bumps) + optional DISCRETE STEPS
(quantized terraces — tier-1 curb/step robustness, still BLIND). Foot-precise
real STAIRCASES need the LiDAR height-map perception in the obs (Phase 3), not
just this — see [[project-sim-roadmap-perception-nav]].

Keep TN / TZ in sync with build_mjcf.py.
"""
import jax
import jax.numpy as jp

TN = 40            # hfield resolution (TN x TN), matches build_mjcf
TZ = 0.20          # hfield max height (m); data in [0,1] -> [0, TZ]
FLAT_R = 5         # flat center-pad radius (cells) — the spawn zone
BUMP_M = 0.12      # max bump height (m) at level 1
# DISCRETE STEP height at level 1 (m). Quantizing the smooth field into terraces
# of this height gives edge/step-reactivity the smooth terrain can't. 0.05 = 5cm
# at level 1 (~a small step / tall curb for a 17cm robot; scales down with level).
# NOTE: at 40 cells / 5m the edge spans ~1 cell (12.5cm horizontal), so steps are
# STEEP RAMPS, not razor-sharp — a good tier-1 curb proxy; sharp stairs need a
# finer hfield (higher TN + build_mjcf sync). Blind reactive climbing tops out
# ~3-5cm on this robot; full 17cm building stairs need perception (Phase 3).
STEP_M = 0.05
# STAIRCASE (tier-2 teacher): radial concentric steps rising OUTWARD from the pad,
# so any forward command climbs them (the policy is velocity-commanded, not goal-
# directed). Rise per step = STAIR_RISE * level, so `level` sweeps the step height
# ACROSS envs — that's how the privileged teacher finds NOVA's max climbable step
# (it succeeds up to some rise, fails above). STAIR_RUN_CELLS = tread depth.
# ⚠ At 40cell/5m, a riser spans ~1 cell (12.5cm) -> RAMP-steps not vertical, so
# this UNDER-estimates difficulty (a ramp is easier than a wall). An honest sharp-
# stair test needs a finer hfield (higher TN + build_mjcf sync); this is the first
# feasibility pass. Needs the HEIGHT-MAP obs to be climbable (blind can't see it).
STAIR_RISE = 0.08          # m per step at level 1 (brackets the ~8-12cm expected max)
STAIR_RUN_CELLS = 2        # tread depth in cells (2 = 25cm)
# curriculum knob: per-env difficulty is sampled in [0, TERRAIN_MAX].
# STAGE 1 = FLAT (0.0) to get basic forward walking — this is what the reference
# MuJoCo Playground Go1 JoystickFlatTerrain env trains on, and every legged-RL
# curriculum starts flat. It was 1.0 (up to 12 cm blind bumps from step 0, robot
# is ~17 cm tall) — nearly impossible from scratch, which is a big reason runs
# 1-9 STOOD. Raise to 1.0 for STAGE 2 (rough-terrain robustness) once flat
# forward walking is solid.
TERRAIN_MAX = 0.0


def terrain_field(rng, level, step_frac=0.0, stair_frac=0.0, n=TN):
    """Per-env hfield data, shape (n*n,) in [0,1]. Smooth rough bumps rising from
    a flat center pad, amplitude scaled by difficulty `level`. Per-env terrain TYPE
    (mutually exclusive, by probability): `stair_frac` -> a STAIRCASE (radial steps
    rising outward, rise STAIR_RISE*level — tier-2 teacher), else `step_frac` -> a
    QUANTIZED terrace (tier-1 curb/step), else smooth rough. Flat spawn pad stays
    flat in every case (0 quantizes/floors to 0)."""
    k1, ksl, kstep, kstair = jax.random.split(rng, 4)
    # low-frequency noise upsampled -> smooth body-scale bumps
    low = jax.random.uniform(k1, (6, 6))
    rough = jax.image.resize(low, (n, n), method="linear")
    rough = jp.clip(rough - 0.4, 0.0, None)            # bumps up from 0

    # gentle random slope (adds directional grade)
    a = jax.random.uniform(ksl, (2,), minval=-1.0, maxval=1.0)
    t = jp.linspace(-1.0, 1.0, n)
    slope = jp.clip(a[0] * t[None, :] + a[1] * t[:, None], 0.0, None)

    field = 0.7 * rough + 0.3 * slope                  # unit-ish

    # flat center pad: 0 inside FLAT_R, ramps to 1 outside (spawn stays flat)
    c = (n - 1) / 2.0
    yy, xx = jp.mgrid[0:n, 0:n]
    r = jp.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    pad = jp.clip((r - FLAT_R) / FLAT_R, 0.0, 1.0)

    height_m = field * pad * (BUMP_M * level)          # meters, 0 at center

    # DISCRETE STEPS (tier-1): quantize to terraces of STEP_M*level for a step_frac
    # slice. round(0)=0 so the flat pad stays flat.
    step_h = jp.maximum(STEP_M * level, 1e-4)          # guard level->0
    stepped = jp.round(height_m / step_h) * step_h
    is_step = jax.random.uniform(kstep, ()) < step_frac
    height_m = jp.where(is_step, stepped, height_m)

    # STAIRCASE (tier-2): radial concentric steps rising outward from the pad edge,
    # rise = STAIR_RISE*level per step. floor(0)=0 keeps the pad flat.
    step_idx = jp.floor(jp.clip((r - FLAT_R) / STAIR_RUN_CELLS, 0.0, None))
    stair_m = step_idx * (STAIR_RISE * level)
    is_stair = jax.random.uniform(kstair, ()) < stair_frac
    height_m = jp.where(is_stair, stair_m, height_m)

    return jp.clip(height_m / TZ, 0.0, 1.0).reshape(-1)   # -> [0,1] hfield data
