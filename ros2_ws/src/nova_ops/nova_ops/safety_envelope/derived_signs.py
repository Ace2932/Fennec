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

hfe/kfe are NOT included here. Their shafts run along the lateral axis, which an
L/R mirror DOES flip, so their urdf_sign differs left-to-right — and unlike the
hips there is no "all-forward" statement pinning them. Derive those separately
or observe them; do not guess.

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
