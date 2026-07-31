#!/usr/bin/env python3
"""HFE inboard-arm MOUTH study (#221) — builds and validates the fit coupon.

THE IDEA (Aiden's, 2026-07-31): SO-101 arms capture the STS3215 horn with a
lowered lip you slide into sideways — open-end wrench, not socket. NOVA's coax
instead closes a full ring around the horn via a bolt-on cap (coax_hfe_plate),
the weakest joint on the leg (#61). This study asks: can the inboard arm be a
front half-C with a rear MOUTH, so femur+servo+horn slide in from behind and
the cap stops existing?

MEASURED ANSWER (three failed hypotheses on the way — see #221 for the full
trail): yes, geometrically. The transiting body is the SERVO HORN DISC (mesh
radius ~12.8, so Ø~25.6 — NB coax.scad's HORN_OD=20 does not describe the mesh
horn; the mesh is authority). The validated mouth: rear sector ±92 deg about
+Y, radial r 10.4 -> rim, through the full cap x-extent 11.8..19.4. All four
horn-bolt bosses (r=7) survive; the margin variant shrunk 0.8 mm BLOCKS, so
the mouth floor clears the metal horn rim by <1 mm — a first-article
measurement, not a foregone conclusion.

THE COUPON THIS EXPORTS IS NOT A ROBOT PART. It is boolean'd from the two
committed STLs (cap fused on, then the mouth cut), so it carries cap remnants
and has no driver bores — bolt0 is physically undrivable on it. It exists to
answer with hands what no sweep can: does the real unit glide past the mouth
lips or scrape, and does the seated horn feel captive. Print PA6-CF, same
orientation as coax_R (rear face +Y down, supports under the yoke bridge).

CONVENTIONS THIS ENCODES (each was violated once during the study and produced
a confident wrong answer — do not "simplify" them away):
  * the servo mesh INCLUDES the mounted horn + bottom wheel; the horn is
    always on the servo, so every sweep must run horn-on
  * designed contact (horn/wheel discs, r<=10.0 about the HFE axis) must be
    excluded or every direction reads blocked at t=2mm
  * sweep the COMBINED femur+servo assembly along the real insertion axis
    (+Y withdraw), not the servo alone in six directions

Run:  ../../../.venv/bin/python hfe_mouth_study.py
Writes coax_hfe_mouth_coupon.stl next to this file (gitignored — regenerable
here in seconds; the committed sources are the .scad-fresh STLs it reads).
"""

import os
import pathlib
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HFE_YZ = np.array([11.6, -9.5])   # HFE axis in (y, z); axis runs along X
R_EXCL = 10.3                     # designed contact is r<=10.0 exactly
OUT = HERE / "coax_hfe_mouth_coupon.stl"

# The validated candidate ("F" in #221). G = F shrunk 0.8mm/4deg BLOCKS, so
# these values carry <1mm of margin — change them only with the sweep rerun.
MOUTH_R_IN = 10.4
MOUTH_HALF_DEG = 92.0
MOUTH_X0, MOUTH_X1 = 11.8, 19.4


def rz180():
    return trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])


def seat_transform():
    """femur-local -> coax frame, exactly check_fit.insertion_checks()."""
    return (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
            @ rz180()
            @ trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))


def mouth_wedge():
    angs = np.radians(np.linspace(-MOUTH_HALF_DEG, MOUTH_HALF_DEG, 91))
    outer = HFE_YZ + 28.0 * np.c_[np.cos(angs), np.sin(angs)]
    inner = HFE_YZ + MOUTH_R_IN * np.c_[np.cos(angs[::-1]), np.sin(angs[::-1])]
    wedge = trimesh.creation.extrude_polygon(
        Polygon(np.vstack([outer, inner])), height=MOUTH_X1 - MOUTH_X0)
    # polygon plane (a,b)=(y,z), extrusion c = x-depth -> (x,y,z)=(c+x0, a, b)
    wedge.apply_transform(np.array([[0., 0., 1., MOUTH_X0],
                                    [1., 0., 0., 0.],
                                    [0., 1., 0., 0.],
                                    [0., 0., 0., 1.]]))
    return wedge


def assembly_points(cf):
    femur = trimesh.load('femur_R.stl')
    arm = trimesh.load('knee_arm.stl')
    arm.apply_transform(
        trimesh.transformations.translation_matrix([59, 0, 17.75]))
    pts = np.vstack([
        trimesh.sample.sample_surface(femur, 30000, seed=0)[0],
        trimesh.sample.sample_surface(arm, 6000, seed=0)[0],
        trimesh.transform_points(cf.sample_points(cf.servo_mesh()), rz180()),
    ])
    return trimesh.transform_points(pts, seat_transform())


def main() -> int:
    os.chdir(HERE)   # meshes load by bare name; do not depend on caller cwd
    import check_fit as cf

    base = trimesh.boolean.union([trimesh.load('coax_R.stl'),
                                  trimesh.load('coax_hfe_plate.stl')])
    assert base.is_watertight, "coax+plate union not watertight"
    coupon = trimesh.boolean.difference([base, mouth_wedge()])
    assert coupon.is_watertight, "coupon not watertight"

    asm = assembly_points(cf)
    bad = 0
    for t in range(2, 72, 2):
        p = asm.copy()
        p[:, 1] += t
        p = p[np.linalg.norm(p[:, 1:] - HFE_YZ, axis=1) > R_EXCL]
        bad += int(coupon.contains(p).sum())
    # 35 pts = the 0.1mm sliver between R_EXCL and MOUTH_R_IN; anything well
    # beyond that means the candidate regressed.
    print(f"insertion sweep residue: {bad} pts (validated baseline ~35)")
    if bad > 120:
        print("FAIL: mouth no longer admits the femur+servo unit")
        return 1

    for ang in (45, 135, -135, -45):
        b = HFE_YZ + 7.0 * np.array([np.cos(np.radians(ang)),
                                     np.sin(np.radians(ang))])
        ring = np.array([[x, b[0] + rr * np.cos(a), b[1] + rr * np.sin(a)]
                         for x in np.arange(13.2, 15.8, 0.4)
                         for rr in (2.2, 2.6, 3.0)
                         for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)])
        n = int(coupon.contains(ring).sum())
        print(f"horn-bolt boss @{ang:+4d}deg: {n}/{len(ring)}")
        if n < len(ring) * 0.8:
            print("FAIL: mouth ate a horn-bolt boss")
            return 1

    # negative control: the un-mouthed base must block the same sweep, or this
    # harness proves nothing (a sweep that cannot fail is not a check).
    ctrl = 0
    for t in range(2, 30, 2):
        p = asm.copy()
        p[:, 1] += t
        p = p[np.linalg.norm(p[:, 1:] - HFE_YZ, axis=1) > R_EXCL]
        ctrl += int(base.contains(p).sum())
    print(f"control (un-mouthed base): {ctrl} pts blocked")
    if ctrl == 0:
        print("FAIL: control did not block — harness broken")
        return 1

    coupon.export(OUT)
    print(f"wrote {OUT.name}  ({coupon.volume/1000:.1f} cm3, watertight)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
