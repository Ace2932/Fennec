"""Statically-stable crawl gait + CoM pre-shift (pure math, no ROS).

Roadmap stage 2 (docs/roadmap-trot-balance.md): crawl before trot — the
de-risk most people skip. One foot in swing at a time, body CoM
pre-shifted over the remaining support triangle, statically stable at
every instant. Exercises the whole pipeline (timing, IK, envelope,
cabling, thermals) where falling is impossible. If crawl isn't clean,
trot won't be.

Same generator style as trot.py: stance slide + half-sine swing arch,
CANONICAL hip-frame outputs (+y outboard, solve_side owns mirroring).
duty 0.8 with offsets {FL:0, RR:.25, FR:.5, RL:.75} gives swing windows
FL[.80,1) / RL[.05,.25) / FR[.30,.50) / RR[.55,.75) — a LATERAL-
SEQUENCE walk (front leg, then same-side hind: FL→RL→FR→RR) with a
0.05-cycle four-stance gap before each lift. That gap is exactly where
body_shift() ramps the CoM away from the leg about to swing (min-jerk
eased, so shift velocity is zero at the hold).

body_shift() returns BODY-frame (dx, dy) — feed it to
body_pose.BodyPose/foot_targets, which owns the canonical-y mirror.
X-config note: step_length/2 = 25 mm keeps the >=40 mm front<->rear
foot exclusion trivially (hips are 282 mm apart).
"""

from __future__ import annotations
import math
from dataclasses import dataclass

from nova_locomotion.choreo.stand import min_jerk

LEGS = ("FL", "FR", "RL", "RR")
# lateral-sequence crawl: one swing leg at a time (see module docstring)
PHASE_OFFSET = {"FL": 0.0, "RR": 0.25, "FR": 0.5, "RL": 0.75}
# body-frame corner signs (x forward, y LEFT) — shift is AWAY from these
_SIGN_X = {"FL": 1.0, "FR": 1.0, "RL": -1.0, "RR": -1.0}
_SIGN_Y = {"FL": 1.0, "FR": -1.0, "RL": 1.0, "RR": -1.0}


@dataclass(frozen=True)
class CrawlParams:
    step_length: float = 0.05  # total fore-aft foot travel (m)
    step_height: float = 0.025  # swing apex lift (m)
    stand_height: float = 0.190  # nominal hip-to-foot drop (m), = trot/choreo (#150)
    stand_y: float = 0.0643  # lateral foot offset = hip_offset (stock stance)
    duty: float = 0.8  # stance fraction — 4x0.2 swing + 4x0.05 four-stance gaps
    shift_amp: float = 0.018  # CoM pre-shift amplitude per axis (m), 15-20 mm class
    shift_ramp: float = 0.05  # shift ease in/out width (cycles) = the 4-stance gap


def _wrap01(p: float) -> float:
    return p - math.floor(p)


def foot_target(phase: float, leg: str, p: CrawlParams):
    """Foot (x, y, z) in the leg's CANONICAL (left) hip frame, phase [0,1).

    Same contract as trot.foot_target: +y outboard for EVERY leg;
    convert via leg_ik.solve_side(LEG_SIDE[leg], ..., KNEE_FORWARD[leg])
    only. Never negate y here."""
    if leg not in PHASE_OFFSET:
        raise KeyError(f"unknown leg {leg!r}")
    lp = _wrap01(phase + PHASE_OFFSET[leg])
    half = p.step_length / 2.0
    y = p.stand_y
    if lp < p.duty:
        # stance: planted, sliding from +half (front) to -half (back)
        s = lp / p.duty
        x = half - p.step_length * s
        z = -p.stand_height
    else:
        # swing: lifted arch, returning from -half to +half
        s = (lp - p.duty) / (1.0 - p.duty)
        x = -half + p.step_length * s
        z = -p.stand_height + p.step_height * math.sin(math.pi * s)
    return (x, y, z)


def all_feet(phase: float, p: CrawlParams):
    """{leg: (x,y,z)} for all four legs at `phase`."""
    return {leg: foot_target(phase, leg, p) for leg in LEGS}


def in_swing(phase: float, leg: str, p: CrawlParams) -> bool:
    return _wrap01(phase + PHASE_OFFSET[leg]) >= p.duty


def _shift_weight(lp: float, p: CrawlParams) -> float:
    """Per-leg CoM-shift weight over local phase: min-jerk ramp UP during
    the four-stance gap before the lift ([duty-ramp, duty)), hold 1
    through swing ([duty, 1)), min-jerk ramp DOWN just after touchdown
    ([0, ramp)). Cyclically continuous with zero end velocities."""
    r = p.shift_ramp
    if p.duty - r <= lp < p.duty:
        return min_jerk((lp - (p.duty - r)) / r)
    if lp >= p.duty:
        return 1.0
    if lp < r:
        return 1.0 - min_jerk(lp / r)
    return 0.0


def body_shift(phase: float, p: CrawlParams):
    """CoM pre-shift (dx, dy) in the BODY frame (x forward, y LEFT).

    Shift points AWAY from the leg that is lifting — toward the
    diagonal corner of its support triangle. Adjacent legs' ramps
    crossfade inside the four-stance gaps, so the sum is smooth and
    periodic. Feed to body_pose (which owns the canonical-y mirror);
    do NOT subtract from canonical targets directly."""
    dx = 0.0
    dy = 0.0
    for leg in LEGS:
        w = _shift_weight(_wrap01(phase + PHASE_OFFSET[leg]), p)
        dx -= w * p.shift_amp * _SIGN_X[leg]
        dy -= w * p.shift_amp * _SIGN_Y[leg]
    return (dx, dy)
