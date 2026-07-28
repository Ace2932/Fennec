"""POSTURE-AWARE chassis hfe bounds (2026-07-25).

REGENERATED 2026-07-26 (#164) against the corrected rear hip placement (#163:
the rear hip is the front placement YAWED 180 deg about Z, not a translation).
The FRONT rows reproduce the previous table bit-for-bit — the front placement
did not change — which is what validates the regeneration. The REAR rows now
mirror the front to within 2.5 deg (the residual is real fore-aft asymmetry:
the head is front-only, the skid rails span x -55..75) and are kfe-dependent
again; the stale rows were flat across all ten kfe values, the tell that the
knee was folding away from the chassis.

CONVENTIONS
  * haa/hfe/kfe are CANONICAL (leg_ik frame): +haa = OUTBOARD for every leg.
  * Bounds are returned in RADIANS.
  * Lookup is CONSERVATIVE: a query between grid cells takes the TIGHTEST bound
    of the enclosing cells (max of the lows, min of the highs), and a query
    outside the grid is clamped to the edge cell. Never interpolate toward a
    looser bound — the sampled surface is not guaranteed monotonic between cells.
  * Unknown leg -> the intersection of the FRONT and REAR envelopes.
  * The table is a CLEARANCE boundary, not first contact: it was swept with a
    proximity test at rom_envelope_table.CLEARANCE_MM, so the required gap is
    already inside the stored numbers. MARGIN_DEG is an extra hook, now 0.

⚠ This is the KINEMATIC truth. The scalars derived from it downstream —
LegParams.hfe_max, nova.urdf.xacro hfe_fold, sim/nova_mjx/build_mjcf.HFE_FOLD and
nova_ops.safety_envelope.limits — are still set to the worst case, so the runtime
will still clamp to +50 until they are regenerated from this table. Raising them
is a hardware-affecting change and is deliberately NOT done here.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from nova_ops.rom_envelope_table import ENVELOPE, HAAS, KFES

# The required gap now lives in the MEASUREMENT, not here (issue #146 / S4).
# hfe_envelope.py sweeps the boundary with a proximity test — "the leg comes
# within CLEARANCE_MM of the chassis" — instead of a containment flip, so the
# stored bounds already stand off the geometry by a real physical distance.
#
# That fixes two things an angular back-off could not. Containment only trips
# once a SAMPLED point is inside the solid, which is late twice over: the cloud
# is sparse (a tangential graze can register zero points while surfaces touch)
# and a 2.5 deg scan step is ~6.5 mm of arc at the tibia flank, enough to step
# over a boss entirely. Proximity sees a feature from CLEARANCE_MM away. And a
# degree is not a distance: the retired 5 deg was worth ~5 mm at haa +40 but
# noticeably more at haa 0, so it silently varied by posture.
#
# Kept at 0 as a deliberate hook — set it only to add margin ON TOP of the
# measured gap, never as a substitute for regenerating the table.
MARGIN_DEG = 0.0

#: The ONE front/rear partition in this module. Everything end-keyed reads it —
#: a second copy of this split is how a frame convention drifts out of sync with
#: the sign that depends on it.
REAR_ENDS = frozenset({"RL", "RR"})


def _bracket(vals, x):
    """Indices of the grid cells enclosing x (clamped at the edges)."""
    if x <= vals[0]:
        return (0, 0)
    if x >= vals[-1]:
        return (len(vals) - 1, len(vals) - 1)
    for i, v in enumerate(vals):
        if v == x:
            return (i, i)  # exact grid hit — no need to widen the bracket
    hi = next(i for i, v in enumerate(vals) if v >= x)
    return (hi - 1, hi)


def _to_canonical(leg: str, lo: float, hi: float) -> Tuple[float, float]:
    """Table hfe (LEG-LOCAL) -> canonical/URDF hfe. Degrees in, degrees out.

    The table's hfe axis is the coax frame hfe_envelope.py sweeps in, where
    +hfe means "fold TOWARD THE TRUNK" for whichever leg it is. The rear hip is
    the front placement YAWED 180 deg about Z (#163), so toward-the-trunk is
    REARWARD at the front and FORWARD at the rear -- while canonical/URDF +hfe
    is uniformly rearward on all four (leg.macro.xacro axis "0 1 0").

    MEASURED, not assumed: a leg-local +hfe of +10 deg moves the foot -x at the
    front legs and +x at the rear ones, through the corrected bases; URDF +hfe
    of +10 deg moves it -x on all four. Hence front is identity and rear is a
    negate-and-swap. Endpoints must SWAP because negating an interval reverses
    which end is the low one -- forgetting that yields lo > hi and a gate that
    refuses every pose.

    Exactly ONE side of the pipeline may do this. hfe_envelope.py deliberately
    emits leg-local and says so in the generated header; if a future
    regeneration also negates, the rear bound lands back on the WRONG SIDE --
    permitting the folds that reach the riser and forbidding the harmless ones,
    which is strictly worse than the stale rows this replaced.
    """
    if leg in REAR_ENDS:
        return -hi, -lo
    return lo, hi


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
    # PER-LEG since the 2026-07-25 review (S3): all four legs are swept, so a
    # known leg gets its own measured envelope rather than an assumed mirror.
    # (Measured L/R asymmetry is 0.0 deg, so the old assumption held — but it is
    # now verified rather than assumed.) Unknown leg -> intersect all four.
    ends = (leg,) if leg in ENVELOPE else tuple(ENVELOPE)
    lo, hi = -1e9, 1e9
    for end in ends:
        e_lo, e_hi = _end_bounds(end, haa_deg, kfe_deg)
        e_lo, e_hi = _to_canonical(end, e_lo, e_hi)  # leg-local -> canonical
        lo, hi = max(lo, e_lo), min(hi, e_hi)
    # BACK OFF from the measured FIRST-CONTACT boundary. The table is raw
    # geometry — the angle at which the leg TOUCHES. A gate that permits poses
    # right up to first contact permits grazing, and the point of the gate is
    # that a posture is refused because it would come NEAR the body.
    # 5 deg matches the convention the project already used: the chassis gate
    # measured front skirt contact at ~+55 and the published cap was +50.
    # Policy lives here, not in the table, so the margin is tunable and the
    # measurement stays a measurement.
    lo, hi = lo + MARGIN_DEG, hi - MARGIN_DEG
    if lo > hi:  # margin swallowed the cell — refuse it all
        mid = 0.5 * (lo + hi)
        lo = hi = mid
    return math.radians(lo), math.radians(hi)
