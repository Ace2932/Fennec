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
    stand_height: float = 0.18  # nominal hip-to-foot drop (m)  (TODO-CAD)
    stand_y: float = 0.045  # lateral foot offset = hip_offset (m) (TODO-CAD)
    duty: float = 0.5  # fraction of cycle in stance (0.5 = trot)


def _wrap01(p: float) -> float:
    return p - math.floor(p)


def foot_target(phase: float, leg: str, p: TrotParams):
    """Foot (x, y, z) in the leg's hip frame at gait `phase` in [0,1)."""
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
