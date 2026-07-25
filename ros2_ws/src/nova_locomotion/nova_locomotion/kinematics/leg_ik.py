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

from nova_ops.rom_envelope import hfe_bounds
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
    # -86°). FRONT legs (FL/FR) used to be capped tighter by hfe_min_front
    # (URDF hfe_ext_front) on the theory that a -86 front reach hits the
    # D456 face / L2 crown. #47 (2026-07-11, MEASURED — hardware/cad/
    # chassis/head_cap_sweep.py): a fine hfe sweep of the front leg vs the
    # REAL head assembly found ZERO contact anywhere in the front leg's
    # structurally-reachable hfe range (min clearance ~34mm) — the -50 cap
    # was stale (set the same day the head moved forward onto the
    # front-shoulder deck, never re-validated after that move). FRONT and
    # REAR now share the same real governing constraint (leg self-collision,
    # leg_v6/check_fit.py LA-19: clean to 92.5°, first contact 93°), so
    # hfe_min_front == hfe_min today. Pass leg=<"FL"|"FR"|"RL"|"RR"> to
    # within_limits() (and solve_side(), which CLAMPS on it — see below) to
    # select the correct window; an omitted/unrecognized leg name defaults
    # to this permissive rear value — see within_limits' docstring.
    hfe_min: float = -1.501  # −86° away-trunk (gate), REAR legs (+ default)
    hfe_min_front: float = -1.501  # −86° away-trunk (gate), FRONT legs — #47: not head-limited (measured); matches hfe_min
    hfe_max: float = 1.501  # +86° toward-trunk MECHANICAL travel (2026-07-25).
    # Was +50 (the riser-skirt graze). That is the bound at ONE posture — full
    # outboard splay with the knee fully folded — not everywhere: measured
    # (hardware/cad/chassis/hfe_envelope.py) the front leg reaches +70.6 at
    # haa 0, which is where trot and crawl actually run. A scalar cannot
    # express a bound that depends on the other two joints, so the chassis
    # constraint now lives in kinematics/rom_envelope.py and is applied per
    # posture by within_limits()/solve_side(). This value is the LINKAGE limit:
    # self-collision 93° (leg_v6 LA-19, clean to 92.5) minus the same 7° margin
    # hfe_min already uses -> a symmetric ±86° mechanical window.
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


def solve_side(
    side: str,
    foot,
    p: LegParams,
    knee_forward: bool = True,
    leg: Optional[str] = None,
):
    """IK for a physical leg. `side` = 'left' | 'right'.

    THE ONE MIRRORING BOUNDARY. foot_target() and inverse_kinematics()
    both work in the CANONICAL (left-leg) hip frame — +y is outboard for
    every leg. Right legs are physical mirrors: same canonical target,
    haa sign flipped on the way out. Do NOT mirror anywhere else
    (researched failure: SpotMicro-class builds crash hips on silent
    left/right reversals).

    #47 RUNTIME SAFETY CLAMP: pass leg=<"FL"|"FR"|"RL"|"RR"> to engage it.
    solve_side() is THE single choke point every commanded pose funnels
    through — choreo (choreo/stand.py pose_for), the gait controller
    (controller.gait_pose, covers trot AND crawl's body-pose-composed
    targets), and any future raibert/body_pose caller that follows the
    same pattern. When leg is a FRONT leg (FL/FR — always knee_forward=
    True in the X-config, so the physical hfe output t2 needs no
    side/knee-branch correction), the physical hfe is clamped to
    [p.hfe_min_front, p.hfe_max]. This is a coarse backstop — it does
    NOT re-solve kfe/haa for the clamped hfe, so a clamped pose is not
    IK-consistent with the original foot target (the foot lands
    somewhere else, not nowhere). That's intentional: crude-but-safe
    beats kinematically-pure-but-unsafe. Real prevention is tuning gait/
    pose params to stay inside the cap in the first place (see choreo/
    stand.py, gait/trot.py, gait/crawl.py); this clamp only needs to
    engage as a last resort, and should rarely if ever fire given #47's
    measured cap (see LegParams.hfe_min_front).
    """
    t1, t2, t3 = inverse_kinematics(foot, p, knee_forward)
    if side == "right":
        t1 = -t1
    elif side != "left":
        raise ValueError(f"side must be 'left'|'right', got {side!r}")
    if leg in FRONT_LEGS or leg in REAR_LEGS:
        # POSTURE-AWARE CLAMP (2026-07-25) — matches within_limits. Clamping every
        # posture to one worst-case scalar cost real stride: the trot's +59.4 deg
        # front excursion is chassis-clear at haa 0 (bound +70.6) and was being
        # pulled back to +50, a bound that only applies at full outboard splay.
        env_lo, env_hi = hfe_bounds(leg, t1, t3)
        hfe_lo = max(env_lo, p.hfe_min_front if leg in FRONT_LEGS else p.hfe_min)
        hfe_hi = min(env_hi, -p.hfe_min)
        t2 = max(hfe_lo, min(hfe_hi, t2))
    elif False:
        # REAR CLAMP ADDED 2026-07-25. The rear pair previously had NO runtime
        # backstop: only FRONT_LEGS were clamped, on the belief that the +50
        # riser-skirt cap was the rear's cap too. It is not — the rear's
        # toward-trunk fold is NEGATIVE canonical hfe, and the corrected
        # check_fit crouch sweep cuts the riser at rear hfe -86/-45 while
        # +45..+86 is clean. Same mirror as within_limits; see its docstring.
        t2 = max(-p.hfe_max, min(-p.hfe_min, t2))
    return (t1, t2, t3)


LEG_SIDE = {"FL": "left", "FR": "right", "RL": "left", "RR": "right"}

# Knee configuration — TRANSLATED (knees BACKWARD on both pairs).
#
# CORRECTED 2026-07-25 (Aiden, ground truth): the robot as built is the
# TRANSLATED layout — every knee bends backward — and the MJX sim
# (sim/nova_mjx: DEFAULT_POSE hfe +0.6 / kfe -1.2 on all four legs, and
# nova.xml's stand keyframe) has always matched it. The previous value
# {FL: True, FR: True, RL: False, RR: False} recorded an "X-CONFIG
# DECIDED 2026-07-06" (docs/knee-config-analysis.md) that was never
# built, and it commanded the FRONT knees FORWARD — controller.gait_pose
# would have driven the front legs to a mirrored stance on first stand.
# Verified by sim/nova_mjx/render_knee_configs.py, which measures each
# knee against the hip->foot chord: translated = -66.0 mm (backward) on
# all four legs.
#
# Pure software: this is the IK elbow branch per leg; foot targets stay
# canonical. Knee config is NOT a build property — CAD femur/tibia are
# mirrored left/right only, never front/rear.
KNEE_FORWARD = {"FL": False, "FR": False, "RL": False, "RR": False}

# LA-13 introduced these as "legs whose away-trunk hfe reach is capped
# tighter than the rear default" (chassis check_fit HEAD case — a -86
# front reach was believed to hit the D456 face / L2 crown). #47
# (2026-07-11, MEASURED): that belief was stale — see LegParams.hfe_min_
# front and hardware/cad/chassis/head_cap_sweep.py — front and rear now
# share the same value. FRONT_LEGS/REAR_LEGS stay as the SELECTOR
# (solve_side's clamp + within_limits' bound choice both key off them),
# matching LegParams.hfe_min_front and the URDF's hfe_ext_front property
# (nova.urdf.xacro), so a future head-position change has one real split
# to reintroduce instead of re-deriving this plumbing from scratch.
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
    "FR") use p.hfe_min_front; an omitted/unrecognized leg name — same as
    REAR_LEGS — falls back to p.hfe_min. This is a deliberate OPT-IN, not
    fail-safe. #47 (2026-07-11, MEASURED): hfe_min_front == hfe_min today
    (see LegParams.hfe_min_front) — the LA-13 audit that found trot.py/
    crawl.py/raibert.py/body_pose.py commanding front hfe past the old
    -50° cap turned out to be flagging a STALE cap value, not bad gait
    tuning: hardware/cad/chassis/head_cap_sweep.py found every one of
    those modules' worst-case front hfe excursions (trot ~-59°, crawl
    ~-59°, body_pose weight-shift ~-66°) comfortably inside the true
    -86° cap. solve_side()'s leg= clamp is the runtime backstop either
    way (see its docstring) — this function is what gait-quality tests
    assert against pre-clamp.
    """
    t1, t2, t3 = theta
    hfe_min = p.hfe_min_front if leg in FRONT_LEGS else p.hfe_min
    # WINDOW KEYS ON LEG POSITION, NOT THE KNEE BRANCH — corrected 2026-07-25.
    #
    # The asymmetric window exists because ONE END of it is the riser-skirt
    # graze (toward-trunk fold) and the other is free space (away-trunk). Which
    # SIGN of canonical hfe points toward the trunk depends on where the leg is
    # mounted, not on which elbow branch the IK picked: with the built
    # TRANSLATED layout (all four knees backward, leg_ik.KNEE_FORWARD) a
    # positive canonical hfe swings the knee BACKWARD, which is toward the
    # trunk at the FRONT and away from it at the REAR.
    #
    # MEASURED, hardware/cad/chassis/check_fit.py crouch sweep after its rear
    # hip placement was corrected from a reflection to a real rotation
    # (2026-07-25 — the old mirror made front and rear sweep identical volumes,
    # so the gate reported ONE window as if it were two):
    #     FRONT  clean at -86/-45,  riser contact from +55  -> [hfe_min, +50]
    #     REAR   riser contact at -86/-45, clean +45..+86   -> [-50, -hfe_min]
    # an exact mirror pair. Keying this on knee_forward silently gave every leg
    # the REAR window once KNEE_FORWARD became all-False, i.e. it certified
    # front-leg poses out to +86 against a skirt that contacts at +55.
    #
    # `leg` omitted -> the end is unknown, so use the CONSERVATIVE INTERSECTION
    # of the two windows rather than guessing an end. Pass leg= to get the real
    # one (solve_side already threads it through).
    # POSTURE-AWARE (2026-07-25): the chassis bound is a function of (haa, kfe),
    # not a scalar. rom_envelope carries the MEASURED contact-free hfe interval
    # per leg END and posture cell; intersect it with the leg's own mechanical
    # travel (+-|hfe_min|, the gate's away-trunk figure) so a chassis-clear pose
    # still cannot exceed what the linkage can physically do.
    #     FRONT  haa +40 / kfe -109 -> +51.7   (this is where the old +50 came from)
    #     FRONT  haa   0 / kfe -109 -> +70.6   (where trot and crawl actually run)
    #     REAR   haa   0            -> -80.1
    env_lo, env_hi = hfe_bounds(leg, t1, t3)
    lo, hi = max(env_lo, hfe_min), min(env_hi, -hfe_min)
    return (
        abs(t1) <= p.haa_range + 1e-9
        and lo - 1e-9 <= t2 <= hi + 1e-9
        and abs(t3) <= p.kfe_range + 1e-9
    )
