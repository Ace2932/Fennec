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
from typing import Optional


@dataclass(frozen=True)
class LegParams:
    hip_offset: float = 0.0643  # d — HAA axis to FOOT plane along leg +y.
    # v6 = stock stance: 33.8 (haa→femur mid) + 0 + 30.5 (toe tab outboard)
    # = 64.3mm — straight vertical legs, semi-wide track. URDF splits it
    # per joint; test_urdf_sync checks the SUM equals this. (Inboard
    # variant d=3.3 shelved until a balance controller exists.)
    femur: float = 0.1069  # a1 — HFE to KFE   MEASURED 2026-07-01 (STL bores, 106.9 mm)
    tibia: float = 0.1290  # a2 — KFE to foot  MEASURED 2026-07-01 (STL foot-post ctr)
    # joint limits (rad) = the CAD fit-gate ROM (2026-07-06, replaces the
    # TODO-CAD placeholders; single source: nova.urdf.xacro + limits.py):
    haa_range: float = 0.262  # ±15° conservative symmetric — the chassis
    # gate's INBOARD cap (belly-pack contact from ~18°). The asymmetric
    # 15-inboard/40-outboard range unlocks when HAA_INBOARD_SIGN is
    # filled at homing calibration (nova_ops limits.py).
    # LA-13 FIX 2026-07-11: hfe_min below is the REAR value (URDF hfe_ext,
    # -86°). FRONT legs (FL/FR) are capped tighter by hfe_min_front (URDF
    # hfe_ext_front, -50°): the chassis check_fit HEAD case, a -86 front
    # reach hits the D456 face / L2 crown. Pass leg=<"FL"|"FR"|"RL"|"RR">
    # to within_limits() to select the correct window (an omitted/
    # unrecognized leg name defaults to this permissive rear value — see
    # within_limits' docstring for which callers still rely on that).
    hfe_min: float = -1.501  # −86° away-trunk (gate), REAR legs (+ default)
    hfe_min_front: float = -0.873  # −50° away-trunk (gate), FRONT legs (head cap)
    hfe_max: float = 0.873  # +50° toward-trunk fold cap (riser graze), all legs.
    # ⚠ leg-local→canonical sign mapping VERIFY IN SIM (URDF note).
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
    if side == "right":
        return (-t1, t2, t3)
    if side != "left":
        raise ValueError(f"side must be 'left'|'right', got {side!r}")
    return (t1, t2, t3)


LEG_SIDE = {"FL": "left", "FR": "right", "RL": "left", "RR": "right"}

# Knee configuration — X-CONFIG (DECIDED 2026-07-06, docs/knee-config-
# analysis.md): rear knees mirrored (dog layout). Pure software: this is
# the IK elbow branch per leg; foot targets stay canonical. Rear crouch
# margin 46° vs 10°, robot-level fore/aft symmetry. Gait planners must
# keep a >=40 mm front<->rear foot exclusion (X worst-case convergence).
KNEE_FORWARD = {"FL": True, "FR": True, "RL": False, "RR": False}

# LA-13: legs whose away-trunk hfe reach is capped tighter than the rear
# default (chassis check_fit HEAD case — a -86 front reach hits the D456
# face / L2 crown). Matches LegParams.hfe_min_front and the URDF's
# hfe_ext_front property (nova.urdf.xacro).
FRONT_LEGS = frozenset({"FL", "FR"})
REAR_LEGS = frozenset({"RL", "RR"})


def within_limits(
    theta, p: LegParams, knee_forward: bool = True, leg: Optional[str] = None
) -> bool:
    """Check CANONICAL-frame angles against the gate ROM.

    The asymmetric hfe window (−86 away-trunk .. +50 toward-trunk) is
    LEG-LOCAL: a mirrored-knee leg (X-config rear, knee_forward=False)
    maps canonical pitch to leg-local NEGATED, so its canonical window
    flips to [−hfe_max, −hfe_min]. Pass the leg's KNEE_FORWARD flag.

    `leg` selects the away-trunk (hfe lower) bound: FRONT_LEGS ("FL"/
    "FR") use the tighter p.hfe_min_front (-50°, head clearance); an
    omitted/unrecognized leg name — same as REAR_LEGS — falls back to
    the more permissive p.hfe_min (-86°), matching this function's
    behavior before LA-13. This is a deliberate OPT-IN, not fail-safe:
    stand.py's pose_for() (the one runtime command-generating path that
    calls this) passes leg= and is correctly gated. LA-13 AUDIT
    (2026-07-11): trot.py/crawl.py/raibert.py/body_pose.py compute foot
    targets that, run through solve_side() + within_limits(..., leg=leg),
    DO exceed the front -50° cap at some phases/poses (see
    test_trot.py/test_crawl.py/test_body_pose.py, where the front-cap
    check is deliberately NOT wired in for this reason) — those modules
    were tuned against the old, wrong, symmetric ±86 assumption and need
    a real retune (stand height / stride / weight-shift authority) plus
    hardware or sim validation before the front cap can be enforced
    there too. Out of scope for this pass; flagging so it isn't lost.
    """
    t1, t2, t3 = theta
    hfe_min = p.hfe_min_front if leg in FRONT_LEGS else p.hfe_min
    lo, hi = (hfe_min, p.hfe_max) if knee_forward else (-p.hfe_max, -hfe_min)
    return (
        abs(t1) <= p.haa_range + 1e-9
        and lo - 1e-9 <= t2 <= hi + 1e-9
        and abs(t3) <= p.kfe_range + 1e-9
    )
