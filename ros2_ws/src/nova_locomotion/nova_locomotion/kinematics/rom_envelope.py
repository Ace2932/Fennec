"""POSTURE-AWARE chassis hfe bounds (2026-07-25).

The chassis ROM was carried as a single scalar — "hfe toward-trunk fold +50 deg"
— but the constraint is 3-dimensional: how far the leg can fold before the tibia
flank reaches the riser skirt (or the belly pack / rails / head) depends on how
far the hip is splayed and how far the knee is folded at the same time.

MEASURED (hardware/cad/chassis/hfe_envelope.py, against riser_bay / battery_pocket
/ pack / skid rails / head, with check_fit's rear hip placement corrected from a
reflection to a real rotation):

    FRONT hfe_max    haa +40 (full outboard splay), kfe -109  ->  +51.7 deg
                     haa   0                      , kfe -109  ->  +70.6 deg
                     haa   0                      , kfe  -25  ->  +76.9 deg
    REAR  hfe_min    haa   0                                  ->  -80.1 deg

So +50 is very nearly the true worst case over the LEGAL haa range (+51.7) — the
scalar was right, it was just applied at every posture. Both primary gaits run
the front legs at haa 0 with kfe ~-98.8, where the real bound is +70.6; the trot's
+59.4 deg excursion has ~11 deg of margin there and only failed because it was
being checked against another posture's worst case.

CONVENTIONS
  * haa/hfe/kfe are CANONICAL (leg_ik frame): +haa = OUTBOARD for every leg.
  * Bounds are returned in RADIANS.
  * Lookup is CONSERVATIVE: a query between grid cells takes the TIGHTEST bound
    of the enclosing cells (max of the lows, min of the highs), and a query
    outside the grid is clamped to the edge cell. Never interpolate toward a
    looser bound — the sampled surface is not guaranteed monotonic between cells.
  * Unknown leg -> the intersection of the FRONT and REAR envelopes.

⚠ This is the KINEMATIC truth. The scalars derived from it downstream —
LegParams.hfe_max, nova.urdf.xacro hfe_fold, sim/nova_mjx/build_mjcf.HFE_FOLD and
nova_ops.safety_envelope.limits — are still set to the worst case, so the runtime
will still clamp to +50 until they are regenerated from this table. Raising them
is a hardware-affecting change and is deliberately NOT done here.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from nova_locomotion.kinematics.rom_envelope_table import ENVELOPE, HAAS, KFES

FRONT_ENDS = frozenset({"FL", "FR"})
REAR_ENDS = frozenset({"RL", "RR"})


def _bracket(vals, x):
    """Indices of the grid cells enclosing x (clamped at the edges)."""
    if x <= vals[0]:
        return (0, 0)
    if x >= vals[-1]:
        return (len(vals) - 1, len(vals) - 1)
    for i, v in enumerate(vals):
        if v == x:
            return (i, i)          # exact grid hit — no need to widen the bracket
    hi = next(i for i, v in enumerate(vals) if v >= x)
    return (hi - 1, hi)


def _end_bounds(end: str, haa_deg: float, kfe_deg: float) -> Tuple[float, float]:
    ia, ib = _bracket(HAAS, haa_deg)
    ka, kb = _bracket(KFES, kfe_deg)
    lo, hi = -1e9, 1e9
    for k in (KFES[ka], KFES[kb]):
        row = ENVELOPE[end][k]
        for i in (ia, ib):
            cell_lo, cell_hi = row[i]
            lo = max(lo, cell_lo)  # tightest low
            hi = min(hi, cell_hi)  # tightest high
    return lo, hi


def hfe_bounds(leg: Optional[str], haa: float, kfe: float) -> Tuple[float, float]:
    """Chassis-safe hfe interval (radians) for this leg at this (haa, kfe) posture.

    haa/kfe in radians, canonical frame. `leg` may be FL/FR/RL/RR; anything else
    (including None) yields the conservative intersection of both ends.
    """
    haa_deg, kfe_deg = math.degrees(haa), math.degrees(kfe)
    if leg in FRONT_ENDS:
        ends = ("FRONT",)
    elif leg in REAR_ENDS:
        ends = ("REAR",)
    else:
        ends = ("FRONT", "REAR")
    lo, hi = -1e9, 1e9
    for end in ends:
        e_lo, e_hi = _end_bounds(end, haa_deg, kfe_deg)
        lo, hi = max(lo, e_lo), min(hi, e_hi)
    return math.radians(lo), math.radians(hi)
