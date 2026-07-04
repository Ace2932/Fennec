"""Analytic 3-DOF kinematics for one NovaSM3 leg (pure math, no ROS/hardware).

Chain matches nova_description: HAA (hip ab/ad, roll about +x) -> lateral hip
offset d along the leg's +y -> HFE (hip flex, pitch about +y) -> femur a1 ->
KFE (knee, pitch about +y) -> tibia a2 -> foot. All in the hip (HAA-axis) frame,
metres / radians.

Convention (matches FK below): at angles (0,0,0) the leg points straight down,
foot at (0, d, -(a1+a2)).

FK is the unambiguous reference; IK is the closed-form inverse and is validated
by FK(IK(p)) == p round-trips in test_leg_kinematics.py — so a sign error in IK
fails the tests rather than silently shipping bad kinematics.

All targets are in the CANONICAL (left-leg) hip frame; use solve_side()
to get physical joint angles — it owns the left/right mirror (haa sign).
"""

from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LegParams:
    hip_offset: float = 0.0643  # d — HAA axis to FOOT plane along leg +y.
    # v6 = stock stance: 33.8 (haa→femur mid) + 0 + 30.5 (toe tab outboard)
    # = 64.3mm — straight vertical legs, semi-wide track. URDF splits it
    # per joint; test_urdf_sync checks the SUM equals this. (Inboard
    # variant d=3.3 shelved until a balance controller exists.)
    femur: float = 0.1069  # a1 — HFE to KFE   MEASURED 2026-07-01 (STL bores, 106.9 mm)
    tibia: float = 0.1290  # a2 — KFE to foot  MEASURED 2026-07-01 (STL foot-post ctr)
    # joint limits (rad), conservative placeholders (TODO-CAD mechanical travel)
    haa_range: float = 0.7
    hfe_range: float = 1.5
    kfe_range: float = 1.9  # sweep-gate: mech stop ~118deg; see URDF note


class Unreachable(ValueError):
    """Foot target is outside the leg's workspace (or inside the hip offset)."""


def forward_kinematics(theta, p: LegParams):
    """(haa, hfe, kfe) radians -> foot (x, y, z) in hip frame (metres)."""
    t1, t2, t3 = theta
    a1, a2, d = p.femur, p.tibia, p.hip_offset
    # planar (sagittal) reach, pitch about +y; straight-down at t2=t3=0
    px = -a1 * math.sin(t2) - a2 * math.sin(t2 + t3)
    pz_plane = -(a1 * math.cos(t2) + a2 * math.cos(t2 + t3))  # negative = down
    # HAA roll about +x rotates (y, z); x carries the sagittal reach
    x = px
    y = d * math.cos(t1) - pz_plane * math.sin(t1)
    z = d * math.sin(t1) + pz_plane * math.cos(t1)
    return (x, y, z)


def inverse_kinematics(foot, p: LegParams, knee_forward: bool = True):
    """foot (x, y, z) in hip frame -> (haa, hfe, kfe) radians.

    knee_forward selects the knee elbow (the two FK-equivalent solutions).
    Raises Unreachable if outside the workspace. Does NOT enforce joint limits
    (caller checks against p.*_range); see within_limits().
    """
    x, y, z = foot
    a1, a2, d = p.femur, p.tibia, p.hip_offset

    # --- HAA (roll) ---
    yz2 = y * y + z * z
    if yz2 < d * d:
        raise Unreachable(f"foot inside hip offset: |yz|={math.sqrt(yz2):.4f} < d={d}")
    r = math.sqrt(yz2 - d * d)  # = -pz_plane (>=0)
    pz_plane = -r
    t1 = math.atan2(z, y) - math.atan2(pz_plane, d)
    t1 = math.atan2(math.sin(t1), math.cos(t1))  # wrap to [-pi, pi]

    # --- planar 2-link (femur a1, tibia a2) for HFE/KFE ---
    px = x
    reach2 = px * px + pz_plane * pz_plane
    cos_k = (reach2 - a1 * a1 - a2 * a2) / (2 * a1 * a2)
    if cos_k < -1.0 - 1e-9 or cos_k > 1.0 + 1e-9:
        raise Unreachable(
            f"planar reach {math.sqrt(reach2):.4f} outside [{abs(a1 - a2):.3f},{a1 + a2:.3f}]"
        )
    cos_k = max(-1.0, min(1.0, cos_k))
    k = math.acos(cos_k)  # interior knee bend, >=0
    t3 = k if knee_forward else -k
    # direction to target (straight down = 0): phi about +y.
    # FK has px = -(a1 sinθ2 + a2 sin(θ2+θ3)), so the 2R "u" axis is -px.
    phi = math.atan2(-px, -pz_plane)
    # offset of femur from the target line
    beta = math.atan2(a2 * math.sin(t3), a1 + a2 * math.cos(t3))
    t2 = phi - beta
    t2 = math.atan2(math.sin(t2), math.cos(t2))
    return (t1, t2, t3)


def solve_side(side: str, foot, p: LegParams, knee_forward: bool = True):
    """IK for a physical leg. `side` = 'left' | 'right'.

    THE ONE MIRRORING BOUNDARY. foot_target() and inverse_kinematics()
    both work in the CANONICAL (left-leg) hip frame — +y is outboard for
    every leg. Right legs are physical mirrors: same canonical target,
    haa sign flipped on the way out. Do NOT mirror anywhere else
    (researched failure: SpotMicro-class builds crash hips on silent
    left/right reversals).
    """
    t1, t2, t3 = inverse_kinematics(foot, p, knee_forward)
    if side == 'right':
        return (-t1, t2, t3)
    if side != 'left':
        raise ValueError(f"side must be 'left'|'right', got {side!r}")
    return (t1, t2, t3)


LEG_SIDE = {"FL": "left", "FR": "right", "RL": "left", "RR": "right"}


def within_limits(theta, p: LegParams) -> bool:
    t1, t2, t3 = theta
    return (
        abs(t1) <= p.haa_range + 1e-9
        and abs(t2) <= p.hfe_range + 1e-9
        and abs(t3) <= p.kfe_range + 1e-9
    )
