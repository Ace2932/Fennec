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
import math
from dataclasses import dataclass, replace
from typing import Dict, Iterator, List, Optional, Tuple

from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    LegParams,
    solve_side,
    within_limits,
)
from nova_ops.safety_envelope.derived_signs import HAA_IDS
from nova_ops.safety_envelope.limits import load_default_limits
from nova_ops.safety_envelope.limp_pose import LIMP_JOINTS_CANONICAL

LEGS = ("FL", "FR", "RL", "RR")
Pose = Dict[str, Tuple[float, float, float]]


@dataclass(frozen=True)
class ChoreoParams:
    leg: LegParams = LegParams()
    dt: float = 0.02  # 50 Hz output (matches feedback rate)
    # 0.190 (#150): follows TrotParams.stand_height so the robot does not change
    # height when it starts walking. Side benefit -- it widens the crouch envelope
    # the translated knee config had collapsed: stand 19.0 -> lie 17.08 is 1.92 cm
    # of travel, up from 0.92.
    # #224: 0.190 -> 0.1995 (+ hip_to_upper_z, 9.5mm) — leg_ik's z fix made
    # the solver honest about the haa->hfe drop it used to omit. Verified
    # the achieved hfe/kfe angles are bit-for-bit unchanged (same physical
    # pose, only the honest z number that reaches it), so every angle in
    # this file's comments below is still accurate.
    stand_z: float = 0.1995  # nominal stand (81% reach)
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
    # #224: crouch_z/lie_z each +0.0095 (hip_to_upper_z) for the same reason
    # as stand_z above — verified the achieved hfe/kfe are unchanged, so the
    # angle figures in the comments (and the envelope numbers below) still hold.
    crouch_z: float = 0.1850  # front hfe +47.0°, kfe -84.3°
    lie_z: float = 0.1803  # deepest inside the +50° skirt cap: front hfe +49.0°


# Canonical foot-space keyframes, PER LEG (2026-07-25). They used to be one
# shared (x, y, z) for all four legs with x = 0 and haa = 0 — "feet under hips".
# That rule is what collapsed the translated-knee crouch envelope to 0.92 cm: with
# the foot pinned under the hip, ALL of a height change has to come out of hfe
# fold, and fold is the one direction the riser skirt caps (+50°). Free the foot
# and the cap stops binding — min hip height goes 16.85 cm -> 2.00 cm, because a
# foot placed FORWARD drives hfe NEGATIVE (phi = atan2(-x, -z)) into the unused
# -86° side. Sim-measured, sim/nova_mjx/probe_lift_envelope.py + probe_standup.py.
#
# SIT / DOWN come from backlog #15's controlled-limp pose and are expressed as
# JOINT angles, not foot targets: they are defined by the chassis gate (belly
# lands on the skid rails) rather than by where the foot goes. See SIT_JOINTS.
def KEYFRAMES(p: ChoreoParams):
    d = p.leg.hip_offset

    def all_legs(z):
        return {leg: (0.0, d, -z) for leg in LEGS}

    return {
        "lie": all_legs(p.lie_z),
        "crouch": all_legs(p.crouch_z),
        "stand": all_legs(p.stand_z),
    }


# backlog #15 controlled-limp SIT, canonical/outboard-positive (haa, hfe, kfe).
# Splaying outboard drops the body via the haa axis instead of folding hfe into
# the skirt: hip height 8.49 cm with 10° of skirt margin, vs 'lie' at 17.08 cm
# with 1°. Verified settled under gravity through the real position servos
# (sim/nova_mjx/render_sit_poses.py) and recoverable — stand-up succeeds from
# both poses, 6/6 (sim/nova_mjx/probe_standup.py).
#
# #145: the firmware's soft-fault controlled limp commands this SAME pose
# (converted to raw counts by nova_ops.safety_envelope.limp_pose, published
# on the `limp_pose` topic) — imported rather than re-declared so the two
# copies cannot silently drift apart the way #163/#154 already have.
SIT_JOINTS: Tuple[float, float, float] = LIMP_JOINTS_CANONICAL  # +40, +40, -90


def joint_keyframes(p: ChoreoParams) -> Dict[str, Pose]:
    """Poses defined directly in JOINT space (canonical), not via foot IK.

    'down' = all four splayed+folded, belly settles on the skid rails (the
             soft-fault controlled-limp target).
    'sit'  = dog sit: REAR splayed+folded, FRONT holding the stand pose, so the
             body pitches nose-up ~24° and the rear belly comes down first.
    """
    stand_leg = pose_for("stand", p)  # physical angles, already side-mirrored
    sit_phys = {}
    for leg in LEGS:
        haa, hfe, kfe = SIT_JOINTS
        sit_phys[leg] = (haa * (-1.0 if LEG_SIDE[leg] == "right" else 1.0), hfe, kfe)
    return {
        "down": sit_phys,
        "sit": {
            leg: (sit_phys[leg] if leg in ("RL", "RR") else stand_leg[leg])
            for leg in LEGS
        },
    }


JOINT_POSES = ("sit", "down")  # defined in joint space, not by a foot target


def _check_rom(name: str, leg: str, theta, leg_params: LegParams) -> None:
    # canonical-frame check (undo the side mirror on haa)
    t_canon = (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta
    if not within_limits(t_canon, leg_params, KNEE_FORWARD[leg], leg=leg):
        raise ValueError(f"keyframe {name!r} out of ROM for {leg}: {theta}")


def _haa_gate(leg: str) -> Tuple[float, float]:
    """Legal PHYSICAL (per-leg-mirrored) haa window for one leg, straight from
    the SAME per-bus-ID table nova_ops.safety_envelope.wrapper's
    SafeJointCommandPublisher already clamps every published /joint_commands
    goal against (wrapper.py's per-joint soft-limit clamp) — reused rather
    than re-derived, so this cannot disagree with the runtime clamp about
    what "legal" means.

    Conservative symmetric ±15° (limits.JointLimit from _hip_abduction) until
    nova_ops.safety_envelope.limits.record_haa_confirmation() has an OBSERVED
    sign on record for this leg's haa bus ID (HAA_IDS, #194) — the asymmetric
    15-inboard/40-outboard window unlocks from there.
    """
    lim = load_default_limits().get(HAA_IDS[leg])
    return lim.lower, lim.upper


def pose_for(name: str, p: ChoreoParams) -> Pose:
    """Keyframe -> physical joint angles per leg (translated knee config).

    Foot-space keyframes (lie/crouch/stand) carry a target PER LEG, so a pose is
    free to be front/rear asymmetric. sit/down are joint-space (JOINT_POSES) —
    they are defined by where the chassis lands, not by a foot position.
    """
    if name in JOINT_POSES:
        pose = joint_keyframes(p)[name]
        for leg in LEGS:
            # SPLAY POSES ARE GATED ON HOMING CALIBRATION, BY DESIGN.
            # They need ~40° OUTBOARD haa; the gate window is a deliberate
            # conservative SYMMETRIC ±15° (the chassis gate's INBOARD cap —
            # belly-pack contact from ~18°) until
            # nova_ops.safety_envelope.limits.HAA_INBOARD_SIGN is filled. That
            # sign is the INBOARD direction in the SERVO COMMAND frame and is
            # genuinely unknowable until homing watches a real servo move —
            # limits.py says so and says splay choreography is why to fill it.
            # Fail LOUD and specific rather than emit a pose the runtime would
            # silently clamp (the exact failure mode that put choreo's lie/crouch
            # 27 mm off target under the translated knee config).
            lo, hi = _haa_gate(leg)
            haa = pose[leg][0]
            if not (lo - 1e-9 <= haa <= hi + 1e-9):
                raise ValueError(
                    f"keyframe {name!r} needs haa={math.degrees(haa):+.0f}° on "
                    f"{leg}, outside the gate window "
                    f"[{math.degrees(lo):+.0f}°, {math.degrees(hi):+.0f}°] until "
                    f"nova_ops.safety_envelope.limits.record_haa_confirmation() "
                    f"records an OBSERVED inboard sign for {leg} at homing "
                    f"calibration. Splay poses unlock there. Writing "
                    f"HAA_INBOARD_SIGN by hand will not do it (#161) — the "
                    f"confirmation is what unlocks the window, not the number."
                )
            # within_limits()'s own haa check is p.leg.haa_range, a SYMMETRIC
            # scalar — widen it to match the (possibly asymmetric) gate window
            # just proven above, or every JOINT_POSES leg would fail THAT
            # check instead (canonical haa is always the same +40° splay
            # magnitude here — see joint_keyframes/LIMP_JOINTS_CANONICAL).
            leg_params = replace(p.leg, haa_range=max(abs(lo), abs(hi)))
            _check_rom(name, leg, pose[leg], leg_params)
        return pose
    feet = KEYFRAMES(p)[name]
    pose = {}
    for leg in LEGS:
        theta = solve_side(LEG_SIDE[leg], feet[leg], p.leg, KNEE_FORWARD[leg], leg=leg)
        _check_rom(name, leg, theta, p.leg)
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
