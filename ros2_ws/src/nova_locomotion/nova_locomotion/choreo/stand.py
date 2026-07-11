"""Stand/sit choreography — min-jerk pose sequencer (pure math, no ROS).

Clean-movement lane 2026-07-06: basic motion quality comes from three
layers — the firmware anti-snap ramp (seeds slew from present position),
this module's MIN-JERK interpolation between keyframe poses (zero
velocity + zero acceleration at both ends, no trapezoid corners), and
the safety-envelope wrapper's clamps as the backstop.

Keyframes live in CANONICAL foot space and convert to joint space
through leg_ik with the per-leg X-CONFIG knee branch (KNEE_FORWARD).
Interpolation is JOINT-space (foot paths bow slightly during
transitions; feet slide a little — fine for stand/sit, and it can never
pass through an IK singularity mid-blend).

Deepest keyframe respects the kfe software limit (109° -> minimum
hip-to-foot reach 138 mm): a real E-stop collapse settles deeper (mech
stop 118°), so stand_up() accepts the CURRENT pose as frame 0 — never
assume the robot starts at a keyframe.

LA-13 (2026-07-11): crouch_z/lie_z were re-derived from a *symmetric*
hfe window (+-86 deg for every leg); pose_for() now enforces the real
CAD-authoritative per-leg split (FRONT legs FL/FR cap away-trunk hfe at
-50 deg — head clearance, chassis check_fit HEAD case — vs -86 deg for
REAR), and at x=0 (feet under hips) a 2-link leg needs a LOT of hfe
swing to hold the foot in place while the knee folds deep — the old
0.150/0.140 depths solved to front hfe ~-57/-61 deg, well past the -50
cap, so pose_for() would raise ValueError building "crouch"/"lie" for
FL/FR. Retuned to the deepest depths that still clear the front cap
with a couple degrees of margin (front hfe ~-47/-48 deg here); this
shrinks crouch/lie travel from ~40 mm to ~8 mm below stand and the
"lie" pose no longer reaches the ~108 deg kfe this module used to
target (now ~87 deg) — a real loss of E-stop-collapse depth-testing
fidelity, not just a renumbering. A proper fix needs either a per-leg
(not shared) crouch target or a redesign of how deep this rig can
safely fold at x=0; flagging for follow-up rather than guessing further.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    LegParams,
    solve_side,
    within_limits,
)

LEGS = ("FL", "FR", "RL", "RR")
Pose = Dict[str, Tuple[float, float, float]]


@dataclass(frozen=True)
class ChoreoParams:
    leg: LegParams = LegParams()
    dt: float = 0.02  # 50 Hz output (matches feedback rate)
    stand_z: float = 0.180  # nominal stand (76% reach, knee ~81°)
    # LA-13 (2026-07-11): retuned so FL/FR clear the -50° front hfe cap
    # with margin at x=0 (see module docstring) — was 0.150/0.140.
    crouch_z: float = 0.176  # low crouch (front hfe ~-47°, knee ~84°)
    lie_z: float = 0.172  # deepest commandable (front hfe ~-48°, knee ~87°)


# canonical foot-space keyframes: (x, y, z) per leg — same for all legs
# (X-config lives in the knee branch, not the target)
def KEYFRAMES(p: ChoreoParams):
    d = p.leg.hip_offset
    return {
        "lie": (0.0, d, -p.lie_z),
        "crouch": (0.0, d, -p.crouch_z),
        "stand": (0.0, d, -p.stand_z),
    }


def pose_for(name: str, p: ChoreoParams) -> Pose:
    """Keyframe -> physical joint angles per leg (X-config branches)."""
    foot = KEYFRAMES(p)[name]
    pose: Pose = {}
    for leg in LEGS:
        theta = solve_side(LEG_SIDE[leg], foot, p.leg, KNEE_FORWARD[leg])
        # canonical-frame check (undo the side mirror on haa)
        t_canon = (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta
        if not within_limits(t_canon, p.leg, KNEE_FORWARD[leg], leg=leg):
            raise ValueError(f"keyframe {name!r} out of ROM for {leg}: {theta}")
        pose[leg] = theta
    return pose


def min_jerk(tau: float) -> float:
    """Quintic min-jerk blend: s(0)=0, s(1)=1, zero vel + acc at ends."""
    tau = max(0.0, min(1.0, tau))
    return tau * tau * tau * (10.0 + tau * (-15.0 + 6.0 * tau))


def sequence(
    frames: List[Pose], durations: List[float], p: ChoreoParams
) -> Iterator[Pose]:
    """Yield joint poses at p.dt through min-jerk blends between frames.

    len(durations) == len(frames) - 1. Peak joint velocity of a blend is
    1.875 * |delta| / T — pick durations so that stays under the
    envelope's velocity limits (wrapper clamps as backstop anyway).
    """
    if len(durations) != len(frames) - 1:
        raise ValueError("need one duration per frame transition")
    yield frames[0]
    for a, b, T in zip(frames[:-1], frames[1:], durations):
        n = max(1, int(round(T / p.dt)))
        for i in range(1, n + 1):
            s = min_jerk(i / n)
            yield {
                leg: tuple(a[leg][j] + s * (b[leg][j] - a[leg][j]) for j in range(3))
                for leg in LEGS
            }


def stand_up(
    p: ChoreoParams,
    start_pose: Optional[Pose] = None,
    rise_s: float = 1.5,
    settle_s: float = 1.2,
) -> Iterator[Pose]:
    """CURRENT (or lie) -> crouch -> stand. Feet stay under the hips the
    whole way (keyframes at x=0): the 'feet under knees' stand-up rule —
    no splayed push-up, knee stays <= its stance loading."""
    frames = [
        start_pose or pose_for("lie", p),
        pose_for("crouch", p),
        pose_for("stand", p),
    ]
    return sequence(frames, [settle_s, rise_s], p)


def sit_down(
    p: ChoreoParams, start_pose: Optional[Pose] = None, lower_s: float = 1.5
) -> Iterator[Pose]:
    """CURRENT (or stand) -> crouch -> lie: the controlled version of
    what an E-stop does ballistically."""
    frames = [
        start_pose or pose_for("stand", p),
        pose_for("crouch", p),
        pose_for("lie", p),
    ]
    return sequence(frames, [lower_s, 0.8], p)
