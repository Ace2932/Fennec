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
    # URDF-derived (nova.urdf.xacro hfe_fold/hfe_ext/hfe_ext_front): fold
    # (+, toward-trunk) caps at +50 deg for ALL four legs (hfe_fold=0.873
    # rad — tibia flank grazes the riser skirt from ~+55).
    # LA-12 FIX 2026-07-11: was a flat -30..+90 placeholder, ~40 deg beyond
    # the true +50 fold cap on every leg and blind to the front/rear split.
    #
    # Away-trunk (-, forward protraction): LA-13 (2026-07-11) introduced a
    # tighter -50 deg FRONT cap (hfe IDs 2=FL, 5=FR) on the theory that a
    # -86 front reach hits the forward integrated head (D456 face / L2
    # crown). #47 (2026-07-11, MEASURED — hardware/cad/chassis/
    # head_cap_sweep.py): a FINE hfe sweep of the front leg vs the REAL
    # head assembly (head.stl, l2_adapter.stl, head_ear.stl/_L.stl, plus
    # convex hulls of the non-watertight l2_ref.stl/d456_ref.stl) found
    # ZERO contact anywhere in the front leg's structurally-reachable hfe
    # range (past leg_v6's own measured ~93deg self-collision mech stop),
    # min clearance ~34mm at legal haa. The -50 cap was set the SAME DAY
    # the head moved forward onto the front-shoulder deck and was never
    # re-validated after that move — stale, not conservative-by-design.
    # FRONT and REAR now share the same real governing constraint (leg
    # self-collision, LA-19: clean to 92.5deg, first contact 93deg) —
    # `front` is kept as a parameter (not collapsed away) so a future
    # head-position change has one obvious place to reintroduce a split.
    # LOOSENED TO MECHANICAL 2026-07-25 — the +50 fold cap moved OUT of this
    # scalar and into the posture-aware gate.
    #
    # +50 is the riser-skirt bound at ONE posture: full outboard splay with the
    # knee fully folded. It is not the bound anywhere else — measured
    # (hardware/cad/chassis/hfe_envelope.py) the front leg reaches +70.6 at
    # haa 0, which is exactly where trot and crawl run. A per-joint scalar
    # CANNOT express a limit that depends on the other two joints, so holding
    # +50 here clipped every gait to another posture's worst case.
    #
    # The chassis constraint is now enforced upstream, per posture, by
    # nova_ops.safety_envelope.rom_envelope, applied by wrapper.publish().
    # THIS limit is now purely MECHANICAL: leg self-collision is measured at
    # 93 deg (leg_v6 LA-19, clean to 92.5), and 86 deg keeps the same 7 deg
    # margin the away-trunk side already used — so the window is symmetric.
    #
    # ⚠ CONSEQUENCE: this clamp is no longer a backstop against a riser-skirt
    # strike. It only stops a command from exceeding what the LINKAGE can do.
    # A skirt strike is now prevented solely by the posture gate upstream.
    lower = -86.0 if front else -86.0
    return JointLimit(
        lower=math.radians(lower),
        # DECIDED 2026-07-25 (issue #142): this stays MECHANICAL. The host posture
    # gate is the sole chassis protection pre-homing.
    #
    # A firmware posture rule was evaluated and rejected -- not on effort, on
    # measurement. The chassis tightness is entirely INBOARD (the belly pack: the
    # bound drops from +66.3 at haa 0 to +57.0 at 1 deg inboard, +13.8 at 15),
    # while outboard stays roomy (+66.1 at 1 deg, +46.8 at full 40 splay). The
    # firmware reads /joint_commands in the SERVO frame, where which haa direction
    # is inboard is exactly what HAA_INBOARD_SIGN leaves None until homing. So any
    # firmware rule must key on |haa| and assume the inboard value BOTH ways --
    # capping hfe at +57.0 from 1 deg onward, which clips the trot. A scalar and a
    # sign-agnostic posture rule are forced to the same worst case, so neither can
    # be simultaneously safe and non-clipping. Mechanical is the only option that
    # is neither.
    #
    # ACCEPTED COST: a host-side bug that publishes a deep fold reaches the
    # chassis with nothing beneath it. The Teensy protects the LINKAGE only.
    # REVISIT AT HOMING: once HAA_INBOARD_SIGN is filled the firmware can tell
    # inboard from outboard and a real posture rule becomes worthwhile -- same
    # unlock as #145, do them together.
    #
    # RE-LOOSENED to mechanical once the precondition was actually met:
        # wrapper.publish() now applies rom_envelope.hfe_bounds() per leg BEFORE
        # these per-joint scalars, so the chassis constraint is enforced at the
        # choke point every publisher passes through -- including
        # nova_calibration's servo_homing and actuator_char, which publish
        # /joint_commands directly and never touch nova_locomotion.solve_side.
        # Locked by test_safety_envelope.test_posture_gate_* .
        upper=math.radians(86.0),
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
    # SIGN CORRECTED 2026-07-25. This window was [+5, +109] — kfe treated as a
    # positive bend MAGNITUDE. It is not: leg_ik/URDF kfe is SIGNED, and the
    # built TRANSLATED knee config puts every commanded knee NEGATIVE.
    #
    # Nothing converts between them. solve_side() returns physical angles,
    # pose_to_positions() is a pure slot remap, and the node publishes that
    # verbatim — so the envelope was clamping EVERY knee command to the +5 floor:
    #
    #     trot FL kfe commanded -73.1  ->  published +7.0   (soft lower)
    #     trot RL kfe commanded -95.1  ->  published +7.0
    #
    # i.e. the robot would have been commanded to near-straight knees under load
    # on its first stand. Never caught because no test crossed the gait ->
    # publish frame boundary; solve_side, within_limits and limits.py were each
    # tested in isolation. test_end_to_end_gait_survives_the_envelope now does.
    #
    # Everything the robot commands lives in -95.1 .. -71.1 (trot, crawl, all
    # three choreo poses), so [-109, -5] clears it by 11.9 / 64.1 deg. -109 is
    # the URDF kfe_range; -5 keeps the original "never lock the knee straight"
    # intent, now on the correct side of zero.
    return JointLimit(
        lower=math.radians(-109.0),
        upper=math.radians(-5.0),
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
