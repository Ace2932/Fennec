"""Canonical controlled-limp pose + its firmware raw-count table (#145).

WHY THIS EXISTS. #145 replaces the firmware's instant `set_fleet_torque(false)`
on a soft fault (battery-low) with: command a known pose, hold torque ~1 s,
then release (see firmware/teensy/firmware/src/limp_controller.h for the
per-fault-type decision). The pose is backlog #15's controlled-limp angles
(haa +40, hfe +40, kfe -90, canonical/outboard-positive) — the SAME pose
`nova_locomotion.choreo.stand`'s joint-space 'down' keyframe already uses and
that module has sim-verified as settled + recoverable (sim/nova_mjx/
render_sit_poses.py, probe_standup.py).

WHY THE CANONICAL ANGLES LIVE HERE, NOT IN nova_locomotion. nova_locomotion
already depends on nova_ops (package.xml); nova_ops importing back would be
the package cycle calibration_io.py's docstring already guards against. The
pose is genuinely a nova_ops/firmware-safety concept (it is what the Teensy
falls back to on a fault with no gait node involved at all), so
nova_locomotion.choreo.stand imports LIMP_JOINTS_CANONICAL from here instead
of re-declaring its own copy — one number, not two that can silently drift
apart the way #163 (inverted rear hips) and #154 (kfe sign) already have.

WHY A SEPARATE MODULE FROM firmware_limits.py. firmware_limits.py's two
tables (joint_limits, hfe_envelope) are pure per-joint / per-leg-posture
math with no notion of "a pose". This is a third, different shape (12
absolute per-joint targets, not windows) built from the SAME `rad_to_raw`
conversion and the SAME calibration dict — reusing the conversion, not the
table shape.

WHY None ON ANYTHING UNCONFIRMED (fail safe). build_limp_pose_data() returns
None unless EVERY leg is both fully calibrated (rad_to_raw has a defined
conversion) AND its haa sign CONFIRMED — the exact gate
nova_locomotion.choreo.stand.pose_for('down') already enforces before it
will emit this same pose, because it needs the same 40 deg outboard splay.
None means "the pose is not known yet"; the firmware's contract (main.cpp)
is to fall back to the pre-#145 instant-release behaviour when no valid
`limp_pose` table has ever arrived — a guessed pose commanded during a fault
is a worse hazard than no controlled limp at all.
"""

import math
from typing import Dict, List, Optional, Tuple

from .firmware_limits import N_JOINTS, JointHomeCalib, RAW_MAX, RAW_MIN, is_calibrated, rad_to_raw
from .limits import confirmed_haa_sign

#: backlog #15 controlled-limp angles, canonical/outboard-positive
#: (haa, hfe, kfe). Single source of truth — see module docstring.
LIMP_JOINTS_CANONICAL: Tuple[float, float, float] = (
    math.radians(40.0),
    math.radians(40.0),
    math.radians(-90.0),
)

# leg -> (haa_id, hfe_id, kfe_id, mirror_haa). mirror_haa negates the
# canonical haa angle for RIGHT-side legs. This is CLAUDE.md's joint-naming
# convention (haa's axis is fore-aft, so an L/R mirror leaves the shared
# sign alone and only the inboard DIRECTION flips by side) — the same fact
# nova_locomotion.kinematics.leg_ik.LEG_SIDE encodes, named again rather
# than imported (package-cycle guard, see module docstring): it is a fixed
# physical convention, not a derived/CAD number that could drift.
_LIMP_LEGS: Tuple[Tuple[str, int, int, int, bool], ...] = (
    ("FL", 1, 2, 3, False),
    ("FR", 4, 5, 6, True),
    ("RL", 7, 8, 9, False),
    ("RR", 10, 11, 12, True),
)


def limp_pose_canonical() -> Dict[str, Tuple[float, float, float]]:
    """Per-leg PHYSICAL (side-mirrored) joint angles for the limp pose."""
    haa, hfe, kfe = LIMP_JOINTS_CANONICAL
    return {
        leg: (-haa if mirror else haa, hfe, kfe)
        for leg, _haa_id, _hfe_id, _kfe_id, mirror in _LIMP_LEGS
    }


def _clip(v: float) -> float:
    return max(RAW_MIN, min(v, RAW_MAX))


def build_limp_pose_data(calib: Dict[int, JointHomeCalib]) -> Optional[List[float]]:
    """12 raw counts (bus ID 1..12 order) for the `limp_pose` topic, or None.

    None unless every leg is BOTH fully calibrated AND its haa CONFIRMED —
    see the module docstring for why. Otherwise, `rad_to_raw`, bus-ID
    ordered, clipped to the servo's 0..4095 range like every other firmware
    table this package publishes.
    """
    pose = limp_pose_canonical()
    out: List[float] = [0.0] * N_JOINTS
    for leg, haa_id, hfe_id, kfe_id, _mirror in _LIMP_LEGS:
        if confirmed_haa_sign(haa_id) is None:
            return None
        ids = (haa_id, hfe_id, kfe_id)
        cals = [calib.get(jid) for jid in ids]
        if not all(is_calibrated(c) for c in cals):
            return None
        for jid, c, theta in zip(ids, cals, pose[leg]):
            out[jid - 1] = _clip(rad_to_raw(theta, c))
    return out
