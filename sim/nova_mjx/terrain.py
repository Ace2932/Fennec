"""Procedural terrain for the MJX heightfield — the blind-locomotion curriculum
foundation. Each parallel env gets its own terrain via env.domain_randomize.

`level` in [0,1] = difficulty. The robot always spawns on a FLAT CENTER PAD
(spawn zone) and the ground roughens outward, so it learns to walk from flat
into uneven terrain. This is the BLIND foundation (slopes, bumps, rough ground)
— foot-precise STAIRS need finer terrain + the LiDAR height-map perception
(Phase 3), not just this.

Keep TN / TZ in sync with build_mjcf.py.
"""
import jax
import jax.numpy as jp

TN = 40            # hfield resolution (TN x TN), matches build_mjcf
TZ = 0.20          # hfield max height (m); data in [0,1] -> [0, TZ]
FLAT_R = 5         # flat center-pad radius (cells) — the spawn zone
BUMP_M = 0.12      # max bump height (m) at level 1
# curriculum knob: per-env difficulty is sampled in [0, TERRAIN_MAX].
# STAGE 1 = FLAT (0.0) to get basic forward walking — this is what the reference
# MuJoCo Playground Go1 JoystickFlatTerrain env trains on, and every legged-RL
# curriculum starts flat. It was 1.0 (up to 12 cm blind bumps from step 0, robot
# is ~17 cm tall) — nearly impossible from scratch, which is a big reason runs
# 1-9 STOOD. Raise to 1.0 for STAGE 2 (rough-terrain robustness) once flat
# forward walking is solid.
TERRAIN_MAX = 0.0


def terrain_field(rng, level, n=TN):
    """Per-env hfield data, shape (n*n,) in [0,1]. Smooth rough bumps rising
    from a flat center pad, amplitude scaled by difficulty `level`."""
    k1, ksl = jax.random.split(rng)
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
    return (height_m / TZ).reshape(-1)                 # -> [0,1] hfield data
