"""Body-pose IK — world-fixed feet, moving body (pure math, no ROS).

Roadmap stage 1 item 2 (docs/roadmap-trot-balance.md): THE missing
primitive every later stage uses — weight shift (stage 1.4), crawl CoM
coupling (stage 2), attitude trim (stage 3.5), attitude regulation
(stage 4). Given a body pose (roll, pitch, yaw, dx, dy, dz) and four
world-frame foot anchors, return each leg's foot target in its
CANONICAL hip frame, ready for leg_ik.solve_side().

Frames (URDF/ROS convention, right-handed):
  world  = body frame at the zero pose: x forward, y LEFT, z up.
  body   = rigid frame carrying the hip grid; BodyPose is its pose in
           world (R = Rz(yaw)·Ry(pitch)·Rx(roll), t = (dx, dy, dz)).
           +dz raises the body; lowering onto the feet is dz < 0.
           +roll (about +x) raises the LEFT side; +pitch (about +y)
           lowers the nose.
  hip    = body-axis-aligned frame at each leg's HAA mount (hip grid
           ±half_x fore-aft, ±half_y lateral — MEASURED, nova.urdf.xacro).

Mirroring: right legs' hip frames mirror in y. leg_ik.solve_side() is
THE ONE mirroring boundary for JOINT angles (haa sign); the FRAME
conversion body→canonical (+y outboard for every leg) has to happen
exactly once too, and it happens here on the way out: canonical
y = SIDE_SIGN_Y[leg] · body y. Downstream code never mirrors again —
it hands canonical targets to solve_side and is done.

Foot target math: with foot anchor A fixed in world and the body at
(R, t), the foot in the body-aligned hip frame is

    q_body = Rᵀ · (A − t) − h        (h = hip mount, body frame)

foot_world() is the exact inverse (used by the round-trip tests).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple

from nova_locomotion.kinematics.leg_ik import LegParams

LEGS = ("FL", "FR", "RL", "RR")
# hip-grid corner signs in the BODY frame (x forward, y LEFT)
SIDE_SIGN_X = {"FL": 1.0, "FR": 1.0, "RL": -1.0, "RR": -1.0}
SIDE_SIGN_Y = {"FL": 1.0, "FR": -1.0, "RL": 1.0, "RR": -1.0}

Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class BodyPose:
    """Body pose in the world frame. Radians / metres. Zero = neutral."""

    roll: float = 0.0  # about +x: positive raises the LEFT side
    pitch: float = 0.0  # about +y: positive lowers the nose
    yaw: float = 0.0  # about +z: positive turns nose left
    dx: float = 0.0  # forward shift
    dy: float = 0.0  # left shift
    dz: float = 0.0  # up shift (+ raises body off the feet)


@dataclass(frozen=True)
class BodyPoseParams:
    leg: LegParams = LegParams()
    # hip grid: HAA axes 282.4 x 78.1 mm (MEASURED 2026-07-02, A360
    # instance-tree; nova.urdf.xacro body_half_x/_y — the xacro rounds
    # the lateral half to 0.0390, the measured value is 39.05 mm).
    half_x: float = 0.1412
    # #175: leg_ik.solve_side() solves the planar IK from the HFE (pitch) axis,
    # not the HAA station — nova.urdf.xacro's hip_to_upper_x (0.0116) runs
    # TOWARD THE TRUNK from the haa station at BOTH ends (front and rear,
    # per the rear's 180° yaw — see nova.urdf.xacro comments ~lines 72-100).
    # half_x above is honestly the haa station (name-matched to body_half_x);
    # this is the extra step to the pitch axis that hip_mounts()/
    # neutral_anchors() must subtract fore-aft.
    hip_to_upper_x: float = 0.0116
    half_y: float = 0.03905
    stand_height: float = 0.18  # hip-to-foot drop (matches TrotParams/ChoreoParams)
    stand_y: float = (
        0.0643  # foot outboard of HAA = LegParams.hip_offset (stock stance)
    )


def hip_mounts(p: BodyPoseParams) -> Dict[str, Vec3]:
    """{leg: leg-plane anchor (x, y, z)} in the BODY frame (hip-row plane z=0).

    Fore-aft anchored at the HFE (pitch) axis — where leg_ik.solve_side()
    actually solves from — not the HAA station: #175. hip_to_upper_x is
    toward the trunk at both ends, so SIDE_SIGN_X handles the per-end flip
    automatically (see BodyPoseParams.hip_to_upper_x)."""
    x = p.half_x - p.hip_to_upper_x
    return {
        leg: (SIDE_SIGN_X[leg] * x, SIDE_SIGN_Y[leg] * p.half_y, 0.0) for leg in LEGS
    }


def neutral_anchors(p: BodyPoseParams) -> Dict[str, Vec3]:
    """World-frame foot anchors of the neutral stand: feet straight
    under the leg columns (stock stance, ~207 mm track), stand_height
    below the hip row. foot_targets(BodyPose(), anchors) returns the
    identity stance (0, stand_y, -stand_height) canonical — the same
    target trot.py and choreo/stand.py use.

    Fore-aft anchored at the pitch axis, matching hip_mounts(): #175."""
    x = p.half_x - p.hip_to_upper_x
    return {
        leg: (
            SIDE_SIGN_X[leg] * x,
            SIDE_SIGN_Y[leg] * (p.half_y + p.stand_y),
            -p.stand_height,
        )
        for leg in LEGS
    }


def _rot(roll: float, pitch: float, yaw: float):
    """Row-major 3x3 of R = Rz(yaw) · Ry(pitch) · Rx(roll)."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def _rt_vec(R, v: Vec3) -> Vec3:
    """Rᵀ · v (world -> body)."""
    return (
        R[0][0] * v[0] + R[1][0] * v[1] + R[2][0] * v[2],
        R[0][1] * v[0] + R[1][1] * v[1] + R[2][1] * v[2],
        R[0][2] * v[0] + R[1][2] * v[1] + R[2][2] * v[2],
    )


def _r_vec(R, v: Vec3) -> Vec3:
    """R · v (body -> world)."""
    return (
        R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
        R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
        R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2],
    )


def foot_targets(
    pose: BodyPose, anchors: Dict[str, Vec3], p: BodyPoseParams
) -> Dict[str, Vec3]:
    """{leg: CANONICAL hip-frame foot target} for world-fixed anchors.

    +y is outboard for every leg (solve_side contract). Feed each
    target to solve_side(LEG_SIDE[leg], ..., KNEE_FORWARD[leg]); may
    raise Unreachable for extreme poses — callers own ROM validation
    (within_limits), same as the gait generators."""
    R = _rot(pose.roll, pose.pitch, pose.yaw)
    t = (pose.dx, pose.dy, pose.dz)
    mounts = hip_mounts(p)
    out: Dict[str, Vec3] = {}
    for leg in LEGS:
        ax, ay, az = anchors[leg]
        q = _rt_vec(R, (ax - t[0], ay - t[1], az - t[2]))
        h = mounts[leg]
        qb = (q[0] - h[0], q[1] - h[1], q[2] - h[2])
        out[leg] = (qb[0], SIDE_SIGN_Y[leg] * qb[1], qb[2])
    return out


def foot_world(pose: BodyPose, leg: str, canonical: Vec3, p: BodyPoseParams) -> Vec3:
    """Inverse of foot_targets for one leg: canonical hip-frame target
    -> world position. foot_world(pose, leg, foot_targets(pose, A)[leg])
    == A[leg] — the round-trip the tests pin."""
    h = hip_mounts(p)[leg]
    qb = (canonical[0], SIDE_SIGN_Y[leg] * canonical[1], canonical[2])
    body = (h[0] + qb[0], h[1] + qb[1], h[2] + qb[2])
    R = _rot(pose.roll, pose.pitch, pose.yaw)
    w = _r_vec(R, body)
    return (w[0] + pose.dx, w[1] + pose.dy, w[2] + pose.dz)
