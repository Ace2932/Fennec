"""DERIVED servo-direction signs, and the on-robot check that confirms them.

WHY THIS EXISTS
---------------
`HAA_INBOARD_SIGN` and `JointHomeCalib.urdf_sign` were treated as four unknown
bits that only hardware could supply, so haa stayed pinned to a conservative
symmetric +-15 deg — withholding the 40 deg of OUTBOARD splay that is 98.8%
chassis-legal, and blocking the #145 sit poses and the #142 firmware posture
rule with it.

They are not unknown. Every input is already measured and recorded:

  * "+tick = CLOCKWISE from horn side" — MEASURED (leg homing convention),
    with home_tick = 2048 on every joint and RAW_PER_RAD = 4096/2pi = 651.9.
  * "haa horns ALL-FORWARD ... front/rear shoulder = ONE part translated"
    (leg_v6 doctrine, A360-verified). Chosen precisely so the rear legs are
    TRANSLATIONS, not mirrors, keeping solve_side's L/R-only flip valid.
  * left/right parts are true mirrors (coax/coax_L, shoulder_plate R/L).

THE DERIVATION (each step is invertible, so each is stated)
-----------------------------------------------------------
1. Right-hand rule: a positive rotation about +A appears COUNTER-clockwise to a
   viewer positioned at +A looking back along -A. Therefore CLOCKWISE from the
   horn side  =>  NEGATIVE rotation about the shaft axis.
2. Horns all-forward => the shaft (+Z of the servo frame) points along trunk +x
   on ALL FOUR hips. An L/R mirror maps y -> -y and leaves +x fixed, so
   mirroring does not change which way the horn faces.
3. (1)+(2): +tick = NEGATIVE rotation about trunk +x, identically on all four.
4. The URDF/MJCF haa axis is +x on all four legs, so an increasing URDF angle is
   a POSITIVE rotation about +x. With (3), raw counts and URDF angle move in
   OPPOSITE directions => urdf_sign = -1 for every haa. Same on all four, which
   is the payoff of the all-forward choice.
5. Foot geometry: the foot hangs below the hip (z < 0), and a positive rotation
   about +x moves it by dy = -z*sin(theta) > 0, i.e. toward +y. So +tick (a
   negative rotation) moves the foot toward -y.
6. Body geometry: LEFT legs sit at +y, so -y is INBOARD. RIGHT legs sit at -y,
   so -y is OUTBOARD.

    => +tick swings a LEFT leg INBOARD   (HAA_INBOARD_SIGN = +1)
    => +tick swings a RIGHT leg OUTBOARD (HAA_INBOARD_SIGN = -1)

HFE AND KFE
-----------
Same method, different mount. Their shafts run along the LATERAL axis, which an
L/R mirror does flip, so unlike the hips their urdf_sign differs left-to-right.
No "all-forward" statement pins them, so the horn facing comes from CAD:

  * every leg part is a true mirror about its own lateral axis --
    `coax_L = mirror([1,0,0]) coax_v6()` ("lateral axis = X in coax frame"),
    `femur_L`/`tibia_L` = `mirror([0,0,1])`. Each mirror plane is PERPENDICULAR
    to the shaft, so it swaps the horn and wheel seats end-for-end. A real
    (unmirrorable) servo still fits by flipping 180 deg about its case axis --
    the case is symmetric that way, and that rotation moves the connector bay
    exactly where the mirror puts it -- so the mirrored pocket is buildable and
    the shaft points opposite lateral ways on the two sides.
  * `coax.scad`: `ARM_IN_X1 = FEMUR_MID - HORN_Z1  // femur horn seat face`.
    Coax +X is outboard, so the INBOARD arm lands on the HORN seat (the
    outboard arm, `ARM_OUT_X0 = 56.2`, is on the wheel side)
    => the HFE horn faces INBOARD, and femur-frame +Z is inboard.
  * `knee_arm.scad`: "FEMUR-frame: plate spans z 17.75..21.75", the horn-seat
    face (`HORN_Z1`) => the KFE horn also faces INBOARD.
  * confirmed against the authoritative placement,
    `check_fit.coax_to_trunk_bases()`: the hfe/kfe shaft resolves INBOARD on all
    four legs, with det +1 right / -1 left (the sides really are mirror images).

Composing with the same measured convention: +tick is a negative rotation about
the shaft, the shaft points inboard, and the URDF hfe/kfe axis is +y on all four
legs, so

    LEFT  leg (at +y): shaft = -y => +tick is POSITIVE about +y => urdf_sign +1
    RIGHT leg (at -y): shaft = +y => +tick is NEGATIVE about +y => urdf_sign -1

Front and rear share a sign, as for the hips -- corroborated by the MJCF, where
hfe/kfe ranges are identical across all four legs.

The "horn faces INBOARD" premise is no longer just a reading of somebody's
constant. `hardware/cad/leg_v6/servo_orientation_gate.py` seats the real servo
mesh both ways -- the flip being 180 deg about the CASE axis, which keeps the
case put and moves only the horn, the mis-assembly hardest to tell apart -- and
asks which orientations the mating parts admit:

    HFE (coax arms)              derived FITS  |  flipped BLOCKED 0.97mm / 88 pts
    KFE (femur yoke + knee_arm)  derived FITS  |  flipped BLOCKED 1.65mm / 106 pts

That is a falsification test, free to return "both fit" and declare these signs
unfounded; the femur pocket ALONE does exactly that, which is what makes the
PASS meaningful. So the MOUNT half of hfe/kfe now rests on a physical
impossibility proof rather than on documentation -- arguably firmer than haa's,
which rests on reading a placement transform.

What stays unconfirmed is the half hfe/kfe SHARE with haa: "+tick = CLOCKWISE
from horn side". No mesh can check a servo's internal convention. There is also
no independent kinematic cross-check for the pitch joints the way haa has the
mirrored ranges -- the URDF axis is +y on all four with identical ranges, so the
model holds no left/right asymmetry to exploit. Homing confirmation is still
required for every joint.

ASSEMBLY NOTE worth carrying to the bench: the femur/tibia POCKET does not
discriminate. A backwards servo drops in perfectly happily and only refuses
later, at the arms, by ~1-1.7mm on a printed part -- forceable, and easy to miss
by hand.

HOW MUCH OF THIS IS CHECKED
---------------------------
Steps 4-6 (the KINEMATIC half) are CONFIRMED by measurement against the model,
not merely argued — see `test_derived_signs.py`:

  * MJCF haa ranges are exact mirror images, [-0.262, +0.698] on the left vs
    [-0.698, +0.262] on the right, and a leg splays outboard further than it
    tucks inboard, so the generous direction IS outboard: +haa = outboard left,
    inboard right.
  * Forward kinematics measured: +haa moves the foot toward +y on ALL FOUR legs
    (dy = +0.070, +0.075, +0.070, +0.075 m at 0.30 rad).
  * hfe/kfe ranges are IDENTICAL across all four legs — no fore-aft mirroring,
    corroborating "4 identical translated legs" from the CAD side.

Steps 1-3 (the SERVO half — the CW convention and the horn facing) are DERIVED
ONLY. No model can check them; they are facts about a physical part in a
physical bracket. That is exactly what `confirm_haa_sign()` closes, and it is
why the runtime stays conservative until it has run.

STATUS: DERIVED, NOT CONFIRMED. Nothing here is wired into the runtime.
`limits.HAA_INBOARD_SIGN` stays all-None (conservative symmetric +-15) until
`confirm_haa_sign()` has checked each hip against real observed motion. A wrong
sign here would swing a leg INBOARD under the belly pack at 40 deg — the exact
outcome the conservative default exists to prevent — so the derivation buys a
fast, loud CONFIRMATION at homing, not a shortcut around it.
"""

from __future__ import annotations

from typing import Dict, Optional

# bus IDs of the four haa joints (joint_id_map: per-leg sequential, FL 1-3 ...)
HAA_IDS: Dict[str, int] = {"FL": 1, "FR": 4, "RL": 7, "RR": 10}

#: Step 6. +1 = increasing raw counts swings that leg INBOARD.
DERIVED_HAA_INBOARD_SIGN: Dict[int, int] = {
    HAA_IDS["FL"]: +1,
    HAA_IDS["FR"]: -1,
    HAA_IDS["RL"]: +1,
    HAA_IDS["RR"]: -1,
}

#: Step 4. Same for all four hips — raw up = URDF angle down.
DERIVED_HAA_URDF_SIGN: Dict[int, int] = {jid: -1 for jid in HAA_IDS.values()}

# joint_id_map is PER-LEG SEQUENTIAL: FL 1-3, FR 4-6, RL 7-9, RR 10-12,
# each leg ordered haa -> hfe -> kfe.
HFE_IDS: Dict[str, int] = {"FL": 2, "FR": 5, "RL": 8, "RR": 11}
KFE_IDS: Dict[str, int] = {"FL": 3, "FR": 6, "RL": 9, "RR": 12}

LEFT_LEGS = ("FL", "RL")
RIGHT_LEGS = ("FR", "RR")

#: hfe/kfe horns face INBOARD on every leg, and the lateral shaft is what an
#: L/R mirror flips -- so unlike haa these differ left-to-right.
DERIVED_PITCH_URDF_SIGN: Dict[int, int] = {
    **{HFE_IDS[leg]: +1 for leg in LEFT_LEGS},
    **{KFE_IDS[leg]: +1 for leg in LEFT_LEGS},
    **{HFE_IDS[leg]: -1 for leg in RIGHT_LEGS},
    **{KFE_IDS[leg]: -1 for leg in RIGHT_LEGS},
}

#: Every joint's raw-vs-URDF sign in one table (all 12).
DERIVED_URDF_SIGN: Dict[int, int] = {
    **DERIVED_HAA_URDF_SIGN,
    **DERIVED_PITCH_URDF_SIGN,
}

#: Homing convention (measured): one-key center at the nominal pose.
HOME_TICK = 2048


class SignMismatch(RuntimeError):
    """Observation disagrees with the derivation. Do NOT proceed to wide ROM."""


def confirm_haa_sign(
    joint_id: int,
    raw_delta: float,
    observed_inboard: Optional[bool],
) -> int:
    """Check one hip's observed motion against the derivation; return the sign.

    Call during homing, per hip: command a SMALL raw delta well inside the
    conservative +-15 deg window, watch which way the leg actually went, and
    pass ``observed_inboard``. Raises rather than returning a guess.

    A mismatch means one of the derivation's six steps is inverted for this
    joint — most likely the servo seated the other way round in a mirrored
    bracket. That is a loud stop, not something to paper over: the wide ROM it
    would unlock is 40 deg of travel toward the LiPo pack.
    """
    if joint_id not in DERIVED_HAA_INBOARD_SIGN:
        raise ValueError(
            f"joint {joint_id} is not a haa joint {sorted(HAA_IDS.values())}"
        )
    if raw_delta == 0 or observed_inboard is None:
        raise SignMismatch(
            f"joint {joint_id}: no usable observation "
            f"(raw_delta={raw_delta}, observed_inboard={observed_inboard})"
        )
    observed = (+1 if observed_inboard else -1) * (+1 if raw_delta > 0 else -1)
    expected = DERIVED_HAA_INBOARD_SIGN[joint_id]
    if observed != expected:
        raise SignMismatch(
            f"joint {joint_id}: derivation says +tick swings "
            f"{'INBOARD' if expected > 0 else 'OUTBOARD'}, but a "
            f"{'+' if raw_delta > 0 else '-'}{abs(raw_delta):.0f}-count move went "
            f"{'INBOARD' if observed_inboard else 'OUTBOARD'}. One of the six "
            f"derivation steps is inverted for this joint — do NOT unlock the "
            f"40 deg outboard ROM until it is understood."
        )
    return expected


def confirm_urdf_sign(
    joint_id: int,
    raw_delta: float,
    urdf_delta_rad: float,
) -> int:
    """Check any joint's observed raw-vs-URDF direction against the derivation.

    `firmware_limits.rad_to_raw` defines
    ``raw = home_raw + urdf_sign * theta * RAW_PER_RAD``, so with RAW_PER_RAD
    positive the observed sign is simply ``sign(raw_delta) * sign(urdf_delta)``.

    Works for all 12 joints. Use at homing alongside `confirm_haa_sign()`, which
    additionally pins the body-relative INBOARD direction that haa needs and a
    pitch joint has no notion of.
    """
    if joint_id not in DERIVED_URDF_SIGN:
        raise ValueError(f"unknown joint id {joint_id} (expected 1..12)")
    if raw_delta == 0 or urdf_delta_rad == 0:
        raise SignMismatch(
            f"joint {joint_id}: no usable observation "
            f"(raw_delta={raw_delta}, urdf_delta={urdf_delta_rad})"
        )
    observed = (1 if raw_delta > 0 else -1) * (1 if urdf_delta_rad > 0 else -1)
    expected = DERIVED_URDF_SIGN[joint_id]
    if observed != expected:
        raise SignMismatch(
            f"joint {joint_id}: derivation says urdf_sign={expected:+d}, "
            f"observed {observed:+d} (raw {raw_delta:+.0f} counts moved the "
            f"joint {urdf_delta_rad:+.4f} rad). An inverted joint drives AWAY "
            f"from target into its stop at full authority — stop and resolve."
        )
    return expected
