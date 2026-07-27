#!/usr/bin/env python3
"""Prove each leg servo can only be seated ONE way round.

WHY
---
`nova_ops.safety_envelope.derived_signs` derives the hfe/kfe servo signs from
"the horn faces INBOARD", which was read out of CAD sources (`coax.scad`'s
`ARM_IN_X1 = FEMUR_MID - HORN_Z1`, `knee_arm.scad`'s horn-seat plane). Reading a
constant is weak evidence: it confirms what the author INTENDED, not what the
geometry ALLOWS, and the sign test that consumes it shares its premises, so a
misreading would leave both wrong and both green.

This gate replaces the reading with a physical-fit argument. It seats the real
servo mesh in the derived orientation and in the flipped one -- 180 deg about
the servo's CASE axis, which keeps the case in place and moves only the horn, so
it is the mis-assembly hardest to tell apart -- and asks which orientations the
surrounding parts actually admit.

It is a FALSIFICATION test: it can return "both fit", which would mean the CAD
does not constrain the orientation and the derived hfe/kfe signs are unfounded.
That answer is a valid and useful outcome. Do not tune it away.

RESULT (2026-07-26): flipped is BLOCKED at all three joints, derived clean at
all three, so the derivation survived. But the margins are SMALL:

    joint  clamped by                  flipped blocked by   radial reach
    HFE    coax arms                   0.97mm / 88 pts      16.92mm
    KFE    femur yoke + knee_arm       1.65mm / 106 pts     15.82mm
    HAA    shoulder + shoulder_plate   0.67mm / 17 pts      13.96mm

TWO of the three block by UNDER A MILLIMETRE. Print tolerance is ~0.2-0.3mm and
PA6-CF flexes, so haa and hfe are ~3-4x tolerance at a feature corner -- a
person can force either together without noticing. Treat these as poka-yoke
GAPS, not mechanical keys: the CAD forbids the mistake on paper and barely
resists it in the hand. The gate says so on every run rather than reporting a
flat PASS. HAA is thinnest: its block is the servo's CONNECTOR BAY, which the
flip moves to the horn side, grazing the shoulder arm at r 13.33..13.96. It is
stable across seeds (17/21/23 in three draws, never zero), so it is a real
feature and not mesh noise.

TWO THINGS THIS DOES NOT DO
---------------------------
1. It confirms the MOUNT (which lateral side the horn is on). It says nothing
   about "+tick = CLOCKWISE from horn side", the servo's own convention, which
   no mesh can check. Homing confirmation is still required.
2. The pocket ALONE does not discriminate -- a backwards servo drops into the
   femur/tibia pocket perfectly happily and only refuses later, at the arms, by
   ~1-1.7mm on a printed part. That is forceable and easy to miss by hand. See
   the assembly note in the leg_v6 README.

Sample points landing inside the mating part within r < R_EXCLUDE of the joint
axis are the DESIGNED disc interface (bolted face-to-face contact plus the proud
centre features), not a collision -- the same exclusion `check_fit.py` uses.
Without it the derived orientation reports a spurious ~0.55mm at the horn face.

Note the servo mesh carries an ASSUMED Ø6 wheel hub, not the calipered Ø8.8
(first-article catch, PR #84), so the real flipped interference is LARGER than
what this reports. The error is in the conservative direction.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
SERVO = (
    HERE.parents[3] / "feetech_servo_models" / "converted_stl" / "servo.stl"
)

# Mask the DESIGNED disc interface. Derived from the part, not inherited: the
# horn/wheel discs are Oe20 (r=10), so anything past r=10 cannot be legitimate
# disc-on-seat contact. Measured: the derived orientation is clean at EVERY
# radius down to r>=10 at all three joints, so 10.5 discards nothing real.
# It was 13.0, copied from check_fit's SWEPT-ENVELOPE checks -- a different
# problem. That threw away 3mm of valid evidence, which happened to be exactly
# the band the HAA interference lives in (r 13.33..13.96), leaving that verdict
# sitting 0.96mm from flipping. At 10.5 the margin to the cliff is ~3.5mm.
R_EXCLUDE = 10.5
SPLINE_OFFSET = -12.5  # sts3215_real(): moves the spline to the origin
FORCEABLE_MM = 1.0     # below this a printed part can simply be forced together

# preview_leg_assembly.scad, RIGHT leg
HFE_AT = (33.8, 11.6, -9.5)  # coax frame; axis along coax +X
KFE_AT = (106.9, 0.0, 0.0)  # femur frame; axis along femur +Z
KNEE_ARM_AT = (59.0, 0.0, 17.75)
HIP_STATION = (39.05, 0.0, 0.0)  # haa axis in the shoulder frame (Y line)


def rot(a: float, b: float, c: float) -> np.ndarray:
    """OpenSCAD rotate([a,b,c]) == Rz(c) @ Ry(b) @ Rx(a)."""
    a, b, c = np.radians([a, b, c])
    rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    m = np.eye(4)
    m[:3, :3] = rz @ ry @ rx
    return m


def tr(v) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = v
    return m


def interference(mesh, pts, xform, axis_pt, axis):
    """Sample points inside `mesh`, outside the designed disc interface.

    Returns (n, max_penetration, max_radial_reach). The radial reach is the
    MARGIN indicator: a block whose points sit just outside R_EXCLUDE would
    vanish if that threshold moved a millimetre, and is far weaker evidence
    than one reaching well past it. See the HAA note in the module docstring.
    """
    p = trimesh.transform_points(pts, xform)
    hit = p[mesh.contains(p)]
    if not len(hit):
        return 0, 0.0, 0.0
    d = hit - np.asarray(axis_pt, float)
    radial = np.linalg.norm(d - np.outer(d @ axis, axis), axis=1)
    sel = radial >= R_EXCLUDE
    keep = hit[sel]
    if not len(keep):
        return 0, 0.0, 0.0
    return (
        len(keep),
        float(trimesh.proximity.signed_distance(mesh, keep).max()),
        float(radial[sel].max()),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", type=int, default=15000)
    args = ap.parse_args()

    np.random.seed(0)  # seeded: the gate must be reproducible
    servo = trimesh.load(SERVO)
    femur = trimesh.load(HERE / "femur_R.stl")
    coax = trimesh.load(HERE / "coax_R.stl")
    knee_arm = trimesh.load(HERE / "knee_arm.stl")
    knee_arm.apply_transform(tr(KNEE_ARM_AT))
    yoke = trimesh.util.concatenate([femur, knee_arm])
    shoulder_arms = trimesh.util.concatenate(
        [trimesh.load(HERE / "shoulder.stl"), trimesh.load(HERE / "shoulder_plate.stl")]
    )

    pts, _ = trimesh.sample.sample_surface(servo, args.samples)
    spline = tr([SPLINE_OFFSET, 0, 0])
    flip = rot(180, 0, 0)  # 180 deg about the servo CASE axis

    hfe_base = tr(HFE_AT) @ rot(0, 0, 180) @ rot(0, 90, 0)
    # HAA: servo sits in the coax pocket, yoked by the shoulder. Its own
    # placement already carries the rot(0,0,180) the others need, so it is
    # applied here and cancelled in the loop.
    mir = np.eye(4)
    mir[1, 1] = -1
    haa_base = tr(HIP_STATION) @ mir @ rot(0, -90, 0) @ rot(90, 0, 0) @ rot(0, 0, -180)
    cases = [
        ("HAA", "shoulder + shoulder_plate", shoulder_arms, haa_base,
         HIP_STATION, np.array([0, 1.0, 0]), "FORWARD", "REARWARD"),
        ("HFE", "coax arms", coax, hfe_base,
         HFE_AT, np.array([1.0, 0, 0]), "INBOARD", "OUTBOARD"),
        ("KFE", "femur yoke + knee_arm", yoke, tr(KFE_AT),
         KFE_AT, np.array([0, 0, 1.0]), "INBOARD", "OUTBOARD"),
    ]

    ok = True
    for joint, against, mesh, base, axis_pt, axis, d_lbl, f_lbl in cases:
        print(f"{joint}  (servo clamped by {against})")
        results = {}
        for tag, extra in (
            (f"derived  horn {d_lbl}", np.eye(4)),
            (f"flipped  horn {f_lbl}", flip),
        ):
            n, pen, rmax = interference(
                mesh, pts, base @ extra @ rot(0, 0, 180) @ spline, axis_pt, axis
            )
            results[tag] = n
            verdict = "BLOCKED" if n else "FITS"
            margin = f"  reach={rmax:5.2f}mm" if n else ""
            print(
                f"  {tag:24} r>={R_EXCLUDE:g}: {n:5d} pts  maxpen={pen:5.2f}mm"
                f"{margin}  -> {verdict}"
            )
            # Warn on the PHYSICAL margin, not on distance to the mask -- the
            # mask is a parameter we choose, the interference is the part.
            # Print tolerance runs ~0.2-0.3mm and PA6-CF flexes, so a block of
            # well under a millimetre at a feature corner is something a person
            # can force together without noticing. That is a poka-yoke gap, not
            # a mechanical key, and it is worth saying out loud even on a PASS.
            if n and pen < FORCEABLE_MM:
                print(
                    f"     ^ MARGINAL: blocked by only {pen:.2f}mm over {n} pts. "
                    f"That is ~{pen / 0.25:.0f}x print tolerance -- forceable by "
                    f"hand. Verify horn direction visually; do not rely on fit."
                )

        derived_fits = results[f"derived  horn {d_lbl}"] == 0
        flipped_blocked = results[f"flipped  horn {f_lbl}"] > 0
        if not derived_fits:
            print(f"  !! {joint}: the DERIVED orientation does not seat — placement is wrong")
            ok = False
        elif not flipped_blocked:
            print(
                f"  !! {joint}: BOTH orientations fit — the CAD does NOT constrain this "
                f"servo. The derived {joint} sign is unfounded; downgrade it to "
                f"unknown-pending-homing."
            )
            ok = False
    print("\nPASS: only the derived orientation is buildable" if ok else "\nFAIL: see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
