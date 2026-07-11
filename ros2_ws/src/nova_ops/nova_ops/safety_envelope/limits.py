"""Joint limit storage.

Per docs/notes-qol-features.md §3 the limits come from the URDF
`<limit lower upper effort velocity>` tags. Until the URDF exists,
this file provides hand-tuned conservative defaults keyed to the canonical
PER-LEG-SEQUENTIAL bus-ID map (nova_description/config/joint_id_map.yaml,
decided 2026-06-27 — each leg = haa,hfe,kfe in ID order):

  ID%3==1  (1,4,7,10)  = haa  hip abduction (coxa, 30 kg STS3215)
  ID%3==2  (2,5,8,11)  = hfe  thigh flexion (femur, 19 kg)
  ID%3==0  (3,6,9,12)  = kfe  knee (tibia, 19 kg)
  IDs 13..18           = arm (Phase 4 reserved)

WARNING: this was previously type-grouped (1-4 hip / 5-8 thigh / 9-12 knee),
which applied the WRONG joint-type limit to most IDs under the per-leg map
(e.g. ID2 got a ±45° hip limit but is actually a femur). Fixed 2026-06-27.
"""

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass
class JointLimit:
    """URDF-style joint limit. Angles in radians, velocity in rad/s,
    effort dimensionless (% of STS3215 stall, 0..1)."""

    lower: float
    upper: float
    velocity: float
    effort: float

    #: position margin inside the URDF limits (~2 deg per notes spec)
    margin: float = math.radians(2.0)

    @property
    def soft_lower(self) -> float:
        return self.lower + self.margin

    @property
    def soft_upper(self) -> float:
        return self.upper - self.margin


# Conservative defaults — REPLACE with URDF-derived values when URDF lands.
# Angles in radians. STS3215 supports ±180° physically but the leg
# kinematics constrain a much smaller range; pick ranges that won't
# crash linkages at first walk.
# Per-haa-ID INBOARD sign in the *servo command frame* (the frame
# /joint_commands positions are expressed in): +1 = increasing command
# swings that leg toward the belly, -1 = decreasing does. UNKNOWN until
# homing calibration observes real motion — the config.py search_dirs
# are placeholders and encode "safe stop direction", NOT inboard.
# While a sign is None its haa gets the CONSERVATIVE SYMMETRIC ±15 deg
# (the chassis gate's inboard cap: belly-pack contact from ~18 deg at
# any hfe fold >= 30). Filling the sign unlocks the asymmetric
# 15-inboard / 40-outboard gate ROM. Splay choreography needs >15
# outboard, so fill these AT homing calibration (firmware-limits lane,
# closed 2026-07-06; signs pending hardware).
HAA_INBOARD_SIGN: Dict[int, Optional[int]] = {1: None, 4: None, 7: None, 10: None}

_HAA_INBOARD_CAP = math.radians(15.0)  # chassis-gate inboard cap
_HAA_OUTBOARD_CAP = math.radians(40.0)  # chassis-gate outboard cap


def _hip_abduction(joint_id: int) -> JointLimit:
    sign = HAA_INBOARD_SIGN.get(joint_id)
    if sign is None:
        # unknown direction -> both ways get the inboard cap
        lower, upper = -_HAA_INBOARD_CAP, _HAA_INBOARD_CAP
    elif sign > 0:
        lower, upper = -_HAA_OUTBOARD_CAP, _HAA_INBOARD_CAP
    else:
        lower, upper = -_HAA_INBOARD_CAP, _HAA_OUTBOARD_CAP
    return JointLimit(
        lower=lower,
        upper=upper,
        velocity=math.radians(180.0),
        effort=0.70,
    )


def _thigh_flexion(front: bool) -> JointLimit:
    # URDF-derived (nova.urdf.xacro hfe_fold/hfe_ext/hfe_ext_front, chassis
    # check_fit HEAD case, 2026-07-07): fold (+, toward-trunk) caps at +50 deg
    # for ALL four legs (hfe_fold=0.873 rad — tibia flank grazes the riser
    # skirt from ~+55). Away-trunk (-, forward protraction) is LEG-DEPENDENT:
    # FRONT legs (hfe IDs 2 = FL, 5 = FR) cap at -50 deg (hfe_ext_front=0.873
    # rad) because the forward integrated head (head.scad: D456 face + L2
    # crown, x70..100 z80..120) occupies the space a -86 front reach would
    # sweep; REAR legs (IDs 8, 11) keep -86 deg (hfe_ext=1.501 rad).
    # LA-12 FIX 2026-07-11: was a flat -30..+90 placeholder, ~40 deg beyond
    # the true +50 fold cap on every leg and blind to the front/rear split.
    lower = -50.0 if front else -86.0
    return JointLimit(
        lower=math.radians(lower),
        upper=math.radians(50.0),
        velocity=math.radians(220.0),
        effort=0.70,
    )


def _knee() -> JointLimit:
    # URDF-derived (nova.urdf.xacro kfe_range=1.9 rad = 108.86 deg ~= 109 deg,
    # matching leg_ik.LegParams.kfe_range and the chassis/leg_v6 check_fit
    # sweep gates, which test kfe software limit at +-109 and treat +-118 as
    # the measured mechanical stop). LA-11 FIX 2026-07-11: was 130 deg, above
    # the ~113-115 deg CAD plastic-contact sweep and the 109 sw ROM used
    # everywhere else — would have crashed the knee into its hard stop.
    # Never lock to 0 (lower margin unchanged).
    return JointLimit(
        lower=math.radians(5.0),
        upper=math.radians(109.0),
        velocity=math.radians(240.0),
        effort=0.70,
    )


def _arm_placeholder() -> JointLimit:
    # Phase 4 — wide-open default until arm install
    return JointLimit(
        lower=math.radians(-150.0),
        upper=math.radians(150.0),
        velocity=math.radians(180.0),
        effort=0.60,
    )


class JointLimits:
    """Bus-ID-indexed limit table."""

    def __init__(self, by_id: Dict[int, JointLimit]):
        self.by_id = dict(by_id)

    def get(self, joint_id: int) -> Optional[JointLimit]:
        return self.by_id.get(joint_id)

    def __contains__(self, joint_id: int) -> bool:
        return joint_id in self.by_id

    def ids(self) -> Iterable[int]:
        return self.by_id.keys()


def load_default_limits(include_arm: bool = False) -> JointLimits:
    """Return the v1 active leg limits (IDs 1..12). Pass include_arm=True
    to also populate IDs 13..18 with placeholders (Phase 4)."""
    table: Dict[int, JointLimit] = {}
    # PER-LEG-SEQUENTIAL: each leg = (haa, hfe, kfe) in ID order (FL,FR,RL,RR).
    for leg in range(4):
        base = 1 + leg * 3
        front = leg < 2  # leg 0=FL, 1=FR, 2=RL, 3=RR (joint_id_map.yaml)
        table[base] = _hip_abduction(base)  # haa  (IDs 1,4,7,10)
        table[base + 1] = _thigh_flexion(front)  # hfe  (IDs 2,5,8,11)
        table[base + 2] = _knee()  # kfe  (IDs 3,6,9,12)
    if include_arm:
        for i in range(13, 19):
            table[i] = _arm_placeholder()
    return JointLimits(table)
