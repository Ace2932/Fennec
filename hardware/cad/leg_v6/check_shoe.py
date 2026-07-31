#!/usr/bin/env python3
"""toe_v2 <-> SM3_Foot shoe fit gate — REAL-mesh check, both directions.

Places the actual SM3_Foot mesh at its mount pose on the tibia toe
(M = T(129,0,-30.5) . rotZ(54) . T(0,-7,0): shoe band ctr 270 -> tibia
stance-plumb -36 deg; keyed by the toe_v2 pockets) and gates:

  1. INTERFERENCE — sampled shoe points (surface + volume) inside the tibia
     solid. ANY hit = the toe cuts the shoe = won't seat.  FAIL.
  2. SEAT CONTACT — the shoe's inner-face points (core band, r<13 about the
     crescent ctr, |z_local|<6) must sit CLOSE to the toe surface: median
     gap must be < 0.4 (designed 0.18). A sloppy ring like the retired
     stock-outline toe (gaps 2..6) fails here.

Run after tibia geometry changes:  ../../../.venv/bin/python check_shoe.py
Exit 0 = clean, 1 = fail. Called from build_all.sh.
"""
import pathlib
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cad_assets import asset  # noqa: E402  (path insert must come first)
import cad_contains  # noqa: E402  (#195 -- installed in main())

# The stock foot, already vendored for the URDF at nova_description/meshes.
# Was an absolute /Users path into the ROOT repo, which is a different git
# repo — so this gate could only ever run on one laptop (#166).
SHOE = str(asset('SM3_Foot.stl'))
THETA = 54.0        # shoe band ctr 270 + 54 = 324 = -36 (stance-plumb)
GAP_MEDIAN_MAX = 0.4


def T(v):
    return trimesh.transformations.translation_matrix(v)


def rz(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])


def mirror_z():
    m = np.eye(4); m[2, 2] = -1
    return m


def shoe_pose():
    return T([129, 0, -30.5]) @ rz(THETA) @ T([0, -7.0, 0])


def sample(m, n_surface=15000, n_volume=6000):
    surf, _ = trimesh.sample.sample_surface(m, n_surface, seed=0)
    lo, hi = m.bounds
    vol = np.random.default_rng(0).uniform(lo, hi, (n_volume * 6, 3))
    vol = vol[m.contains(vol)][:n_volume]
    return np.vstack([surf, vol])


def main():
    cad_contains.install()   # #195 -- reproducible containment
    shoe = trimesh.load(SHOE)
    pts_local = sample(shoe)
    # inner-face points, in SHOE frame: core band about crescent ctr (0,7)
    q = pts_local[:, :2] - [0.0, 7.0]
    r = np.linalg.norm(q, axis=1)
    az = np.degrees(np.arctan2(q[:, 1], q[:, 0])) % 360
    inner = (r < 13.0) & (np.abs(pts_local[:, 2]) < 6.0) \
        & (az > 215) & (az < 325)          # clear of tabs + horns
    bad = False
    for stl, M in [('tibia_R.stl', shoe_pose()),
                   ('tibia_L.stl', mirror_z() @ shoe_pose())]:
        tib = trimesh.load(stl)
        pts = trimesh.transform_points(pts_local, M)
        hits = tib.contains(pts)
        q_gap = trimesh.proximity.ProximityQuery(tib)
        gaps = np.abs(q_gap.signed_distance(pts[inner]))
        med = np.median(gaps)
        print(f'{stl}: shoe pts inside part: {hits.sum()}/{len(pts)}   '
              f'inner-face gap median {med:.3f} p90 '
              f'{np.percentile(gaps, 90):.3f} (n={inner.sum()})')
        if hits.sum():
            c = pts[hits]
            print(f'  INTERFERENCE bbox {c.min(0).round(1)}..{c.max(0).round(1)}')
            bad = True
        if med > GAP_MEDIAN_MAX:
            print(f'  SLOPPY SEAT: median gap {med:.3f} > {GAP_MEDIAN_MAX}')
            bad = True
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
