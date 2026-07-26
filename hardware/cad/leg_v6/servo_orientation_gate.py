#!/usr/bin/env python3
"""Prove the hfe/kfe servos can only be seated ONE way round.

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

RESULT (2026-07-26): flipped is BLOCKED at both joints -- hfe 0.97mm over 88
sample points, kfe 1.65mm over 106 -- while the derived orientation is clean at
both. The derivation survived.

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

R_EXCLUDE = 13.0  # designed disc interfaces, per check_fit doctrine
SPLINE_OFFSET = -12.5  # sts3215_real(): moves the spline to the origin

# preview_leg_assembly.scad, RIGHT leg
HFE_AT = (33.8, 11.6, -9.5)  # coax frame; axis along coax +X
KFE_AT = (106.9, 0.0, 0.0)  # femur frame; axis along femur +Z
KNEE_ARM_AT = (59.0, 0.0, 17.75)


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
    """Sample points inside `mesh`, outside the designed disc interface."""
    p = trimesh.transform_points(pts, xform)
    hit = p[mesh.contains(p)]
    if not len(hit):
        return 0, 0.0
    d = hit - np.asarray(axis_pt, float)
    radial = np.linalg.norm(d - np.outer(d @ axis, axis), axis=1)
    keep = hit[radial >= R_EXCLUDE]
    if not len(keep):
        return 0, 0.0
    return len(keep), float(trimesh.proximity.signed_distance(mesh, keep).max())


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

    pts, _ = trimesh.sample.sample_surface(servo, args.samples)
    spline = tr([SPLINE_OFFSET, 0, 0])
    flip = rot(180, 0, 0)  # 180 deg about the servo CASE axis

    hfe_base = tr(HFE_AT) @ rot(0, 0, 180) @ rot(0, 90, 0)
    cases = [
        ("HFE", "coax arms", coax, hfe_base, HFE_AT, np.array([1.0, 0, 0])),
        ("KFE", "femur yoke + knee_arm", yoke, tr(KFE_AT), KFE_AT, np.array([0, 0, 1.0])),
    ]

    ok = True
    for joint, against, mesh, base, axis_pt, axis in cases:
        print(f"{joint}  (servo clamped by {against})")
        results = {}
        for tag, extra in (("derived  horn INBOARD", np.eye(4)), ("flipped  horn OUTBOARD", flip)):
            n, pen = interference(
                mesh, pts, base @ extra @ rot(0, 0, 180) @ spline, axis_pt, axis
            )
            results[tag] = n
            verdict = "BLOCKED" if n else "FITS"
            print(f"  {tag:24} r>={R_EXCLUDE:g}: {n:5d} pts  maxpen={pen:5.2f}mm  -> {verdict}")

        derived_fits = results["derived  horn INBOARD"] == 0
        flipped_blocked = results["flipped  horn OUTBOARD"] > 0
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
