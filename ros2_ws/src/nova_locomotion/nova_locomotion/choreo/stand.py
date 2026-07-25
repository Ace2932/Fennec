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

LA-13 (2026-07-11) re-derived crouch_z/lie_z from a *symmetric* hfe
window (+-86 deg for every leg) down to a shallower 0.176/0.172 because
pose_for() had just started enforcing a per-leg split with FRONT legs
FL/FR capped at -50 deg away-trunk hfe (chassis check_fit HEAD case) —
at x=0 (feet under hips) a 2-link leg needs a LOT of hfe swing to hold
the foot in place while the knee folds deep, and the original 0.150/
0.140 depths solved to front hfe ~-57/-61 deg, past that -50 cap.

#47 (2026-07-11, MEASURED — hardware/cad/chassis/head_cap_sweep.py): the
-50 front cap was stale (set the same day the head moved forward onto
the front-shoulder deck, never re-validated after that move) — a fine
sweep of the front leg vs the REAL head assembly found zero contact
anywhere in its structurally-reachable hfe range, min clearance ~32mm.
FRONT legs now share REAR's -86 deg cap (see leg_ik.LegParams.
hfe_min_front), so the constraint that forced the shallow retune is
gone. RESTORED to the original 0.150/0.140 depths (front hfe ~-57/-61
deg, comfortably inside -86 deg; kfe ~102/108 deg, inside the 109 deg
software limit with a ~1 deg margin at "lie" — the real binding
constraint at this depth is now kfe, not hfe) — full E-stop-collapse
depth-testing fidelity back, not just a renumbering.
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
    stand_z: float = 0.180  # nominal stand (76% reach, front hfe +45.1°)
    # RAISED 2026-07-25 (knee config corrected to TRANSLATED, leg_ik.KNEE_FORWARD).
    #
    # Under the X-config these were 0.150 / 0.140, where the front legs took the
    # elbow-FORWARD branch and crouching drove front hfe NEGATIVE (~-57°/-61°),
    # away from the trunk into the -86° window — lots of room.
    #
    # Translated flips that: every knee bends backward, so crouching drives front
    # hfe POSITIVE, TOWARD the trunk and into the riser skirt. The skirt caps
    # hfe_max at +50° (chassis gate 2026-07-06; tibia flank contacts from ~+55°),
    # and the old depths need +57.4° (crouch) and +61.3° (lie) — both past it.
    # solve_side's FRONT_LEGS clamp fired and the foot landed 27 mm off target.
    #
    # New depths sit inside the cap with margin: crouch +47°, lie +49°.
    # ⚠ The usable crouch envelope in translated is only ~1.2 cm (stand 18.01 cm
    # at the cap-free +45° down to 16.84 cm at the +50° cap), so lie/crouch/stand
    # are now nearly the same pose. Recovering real sit travel needs either a
    # riser-skirt trim (the same part that caps stair step-up) or a front/rear
    # ASYMMETRIC crouch — only the FRONT pair is skirt-limited; the rear pair
    # folds away from the trunk and keeps its full -86° room, which is also how a
    # dog actually sits. See docs/knee-config-analysis.md.
    crouch_z: float = 0.1755  # front hfe +47.0°, kfe -84.3°
    lie_z: float = 0.1708  # deepest inside the +50° skirt cap: front hfe +49.0°


# canonical foot-space keyframes: (x, y, z) per leg — same for all legs
# (the knee configuration lives in the IK branch, not the target)
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
        theta = solve_side(LEG_SIDE[leg], foot, p.leg, KNEE_FORWARD[leg], leg=leg)
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
