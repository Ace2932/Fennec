"""Pure trot-gait foot-trajectory generator (no ROS/hardware).

Diagonal trot: legs FL+RR move together, FR+RL a half-cycle out of phase. For a
normalized gait phase in [0,1) this returns each foot's target (x,y,z) in that
leg's hip frame — feed straight into nova_locomotion.kinematics.leg_ik.

Stance = foot planted, sliding backward (-x) at stand height. Swing = foot
lifted on a half-sine arch, returning forward (+x). This is the scripted Phase-2
baseline gait; the MJX-learned policy (Phase 2 sim) is a separate path.

Distances in metres. Uses placeholder geometry defaults — refine with CAD.
"""

from __future__ import annotations
import math
from dataclasses import dataclass

LEGS = ("FL", "FR", "RL", "RR")
# diagonal trot phase offsets
PHASE_OFFSET = {"FL": 0.0, "RR": 0.0, "FR": 0.5, "RL": 0.5}


@dataclass(frozen=True)
class TrotParams:
    step_length: float = 0.06  # total fore-aft foot travel (m)
    step_height: float = 0.03  # swing apex lift (m)
    # 0.190, RAISED from 0.180 2026-07-25 (issue #150). At 0.180 the trot's front
    # fold peaks at +59.4 deg and the chassis envelope allows +57.0 as soon as the
    # hip rolls 1 deg INBOARD -- i.e. the gait had ZERO haa headroom and fitted
    # only because every pose commands haa exactly 0.00. Any lateral hip motion (a
    # balance loop, CoM sway, Raibert foot placement) would have had its fold
    # silently clamped by the posture gate.
    #
    # Measured haa headroom vs stand height: 18.0 -> 0.0 deg, 18.5 -> 0.0,
    # 19.0 -> 11.5, 19.5 -> 11.5. 19.0 is the KNEE -- taller buys nothing more,
    # because past ~12 deg inboard the belly-pack cliff dominates regardless of
    # fold. Stride is the wrong lever: halving step_length buys only 1.5 deg.
    #
    # Not a trade: the straighter stance IMPROVES capacity (hold 2.80 -> 3.03x
    # the per-leg share, lift power 0.692 -> 0.744 W at 2 cm/s). At 73 deg of knee
    # bend it is nowhere near the singular region.
    stand_height: float = 0.190  # nominal hip-to-foot drop (m) — 81% of measured
    # full reach (femur 106.9 + tibia 129.0 = 235.9 mm), knee bent ~81°. OK.
    stand_y: float = 0.0643  # lateral foot offset = hip_offset (m), stock stance
    duty: float = 0.5  # fraction of cycle in stance (0.5 = trot)


def _wrap01(p: float) -> float:
    return p - math.floor(p)


def foot_target(phase: float, leg: str, p: TrotParams):
    """Foot (x, y, z) in the leg's CANONICAL (left) hip frame, phase [0,1).

    +y is outboard for EVERY leg (right legs included). Convert to
    physical joint angles ONLY via leg_ik.solve_side(LEG_SIDE[leg], ...),
    which owns the left/right mirror. Never negate y here.
    """
    if leg not in PHASE_OFFSET:
        raise KeyError(f"unknown leg {leg!r}")
    lp = _wrap01(phase + PHASE_OFFSET[leg])
    half = p.step_length / 2.0
    y = p.stand_y
    if lp < p.duty:
        # stance: planted, sliding from +half (front) to -half (back)
        s = lp / p.duty  # 0..1
        x = half - p.step_length * s
        z = -p.stand_height
    else:
        # swing: lifted arch, returning from -half to +half
        s = (lp - p.duty) / (1.0 - p.duty)  # 0..1
        x = -half + p.step_length * s
        z = -p.stand_height + p.step_height * math.sin(math.pi * s)
    return (x, y, z)


def all_feet(phase: float, p: TrotParams):
    """{leg: (x,y,z)} for all four legs at `phase`."""
    return {leg: foot_target(phase, leg, p) for leg in LEGS}
