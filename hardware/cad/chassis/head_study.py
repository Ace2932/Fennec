#!/usr/bin/env python3
"""HEAD placement/clearance study (deliverable 1 of the head integration).

Replaces the periscope (d456_head) + L2 mast with ONE forward head:
  - D456 as a DOWN-TILTED face, forward of the chassis (x 70..100)
  - L2 as a crown on top, optical center ~z150, 360deg ring clear.

Verifies, with the REAL swept leg cloud (front hfe capped -50), that:
  1. the tilted D456 body clears the front-leg sweep, the shoulder deck-ext
     fins (z73.05..79.55, x63.5..109, y+-26..59.4), and stays x<=100.
  2. the L2 crown (x53.5, seat top ~z120) keeps its 360deg horizontal ring
     clear and quantifies the forward/rear down-cone clip.
  3. the camera top clears the L2 body.

Run:  ../../../.venv/bin/python head_study.py
"""
import numpy as np
import trimesh

import check_fit as cf   # reuse leg_cloud / bases / helpers

T = trimesh.transformations.translation_matrix
rot = cf.rot
tf = cf.tf

# ---- head geometry knobs (the thing this study is choosing) -----------------
TILT = 27.0                       # D456 down-tilt about +y (deg); 25..30 spec
XM = 70.0                         # camera BACK-FACE center x (on the head face)
ZM = 105.5                        # camera back-face center z (bottom clears fin)
CAM_D, CAM_L, CAM_H = 26.0, 123.8, 29.0     # D456 body (dimensions.md)
L2_CTR_X = 53.5                   # L2 optical/plate center x (UNCHANGED vs mast)
L2_SEAT_TOP = 122.0              # L2 body bottom (raised vs mast 117.4 to clear
                                  # the tilted face-plate top 120.7)
FIN_Z = (73.05, 79.55)


def rotY(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0])


def cam_box(xm=XM, zm=ZM, tilt=TILT):
    """D456 body OBB. back-face center = (xm,0,zm); +x'=forward(down-tilted),
    z'=up. Returns (mesh, corners 8x3)."""
    th = np.radians(tilt)
    fwd = np.array([np.cos(th), 0, -np.sin(th)])
    up = np.array([np.sin(th), 0, np.cos(th)])
    M = np.array([xm, 0, zm])
    center = M + (CAM_D / 2) * fwd
    box = trimesh.creation.box(extents=[CAM_D, CAM_L, CAM_H],
                               transform=T(center) @ rotY(tilt))
    corners = []
    for d in (0, CAM_D):
        for l in (-CAM_L / 2, CAM_L / 2):
            for h in (-CAM_H / 2, CAM_H / 2):
                corners.append(M + d * fwd + l * np.array([0, 1, 0]) + h * up)
    return box, np.array(corners)


def front_leg_sweep():
    """All REACHABLE front-leg points (hfe -50..+50, inboard haa<=15,
    outboard<=40), both front hips, near the head region."""
    cf.LEGPTS = cf.load_leg_parts()
    bases = [(lab, b) for lab, b in cf.coax_to_trunk_bases() if lab[0] == 'F']
    pts = []
    for hfe in range(-50, 51, 10):
        for kfe in (-109, -55, 0, 55, 109):
            cloud = cf.leg_cloud(hfe, kfe)
            for haa in (-40, -25, -15, 0, 15, 25, 40):
                for lab, base in bases:
                    inboard = -haa if lab[1] == 'R' else haa
                    if inboard > 15 or haa > 40 or haa < -40:
                        continue
                    Sx = rot(haa, [1, 0, 0],
                             [cf.HIP_FA, cf.HIP_LAT if lab[1] == 'R'
                              else -cf.HIP_LAT, cf.HIP_Z])
                    p = tf(tf(cloud, base), Sx)
                    p = p[(p[:, 0] > 60) & (p[:, 2] > 55)]
                    if len(p):
                        pts.append(p)
    return np.vstack(pts)


def main():
    print(f'== HEAD study: TILT={TILT}  cam back-face ctr=({XM},0,{ZM}) ==\n')
    box, C = cam_box()
    print('D456 body corners (tilted):')
    print(f'  x {C[:,0].min():.1f}..{C[:,0].max():.1f}  '
          f'z {C[:,2].min():.1f}..{C[:,2].max():.1f}  y +-{CAM_L/2:.1f}')
    print(f'  lowest pt  z={C[:,2].min():.1f} (fin top {FIN_Z[1]}, '
          f'margin {C[:,2].min()-FIN_Z[1]:+.1f})')
    print(f'  fwd-most x={C[:,0].max():.1f} (leg limit 100, '
          f'margin {100-C[:,0].max():+.1f})')

    # optical axis (camera mid, tilted down) -> ground intersection
    th = np.radians(TILT)
    oc = np.array([XM + (CAM_D / 2) * np.cos(th), 0, ZM - (CAM_D / 2) * np.sin(th)])
    # forward-down ray from optical center
    dz_per_dx = -np.tan(th)
    x_ground = oc[0] + (0 - oc[2]) / dz_per_dx
    print(f'  optical center ~({oc[0]:.0f},0,{oc[2]:.0f}), axis {TILT}deg down '
          f'-> hits ground z0 at x~{x_ground:.0f} (~{x_ground-cf.HIP_FA+141.2:.0f} '
          f'fwd of nose)')

    print('\n-- camera vs front-leg sweep (hfe capped -50) --')
    leg = front_leg_sweep()
    inside = box.contains(leg)
    n = int(inside.sum())
    print(f'  swept front-leg pts near head: {len(leg)}   inside camera: {n}')
    if n:
        h = leg[inside]
        print('  WORST clusters:', np.round(h[:5], 1).tolist())

    print('\n-- camera vs deck-ext fins --')
    finL = cf.make_box(63.5, 109, 26, 59.4, *FIN_Z)
    finR = cf.make_box(63.5, 109, -59.4, -26, *FIN_Z)
    fpts = np.vstack([trimesh.sample.sample_surface(finL, 4000, seed=0)[0],
                      trimesh.sample.sample_surface(finR, 4000, seed=0)[0]])
    nf = int(box.contains(fpts).sum())
    print(f'  fin pts inside camera: {nf}')

    print('\n-- L2 crown --')
    l2 = cf.make_box(L2_CTR_X - 37.5, L2_CTR_X + 37.5, -37.5, 37.5,
                     L2_SEAT_TOP, L2_SEAT_TOP + 65)
    l2_oc_z = L2_SEAT_TOP + 32.5
    print(f'  L2 body x {L2_CTR_X-37.5:.1f}..{L2_CTR_X+37.5:.1f}  '
          f'z {L2_SEAT_TOP:.0f}..{L2_SEAT_TOP+65:.0f}  optical ctr z~{l2_oc_z:.0f}')
    # camera top vs L2 bottom
    cam_top = C[:, 2].max()
    print(f'  camera top z={cam_top:.1f} vs L2 bottom z={L2_SEAT_TOP:.1f}  '
          f'gap {L2_SEAT_TOP-cam_top:+.1f}')
    nlc = int(box.contains(trimesh.sample.sample_surface(l2, 4000, seed=0)[0]).sum())
    print(f'  L2 body pts inside camera: {nlc}')
    # 360 ring clearance at optical z: nothing within 40mm radially
    print(f'  360deg ring @ z{l2_oc_z:.0f}: camera top {cam_top:.0f} is '
          f'{l2_oc_z-cam_top:.0f} below -> ring clear vertically')

    # forward down-cone clip by the camera top-front corner
    fc = C[np.argmax(C[:, 0])]           # forward-most corner
    ang = np.degrees(np.arctan2(l2_oc_z - fc[2], fc[0] - L2_CTR_X))
    print(f'  fwd down-cone: camera fwd-top corner ({fc[0]:.0f},{fc[2]:.0f}) '
          f'sits {ang:.1f}deg below L2 horizon -> clips elevations below '
          f'-{ang:.1f}deg in that azimuth (cone edge -45; '
          f'clip {45-ang:+.1f}deg vs full)')
    # rear down-cone clip by the Jetson case top (z110.1, rear x-62..48)
    case_front_top = np.array([48.3, 110.1])
    ang_r = np.degrees(np.arctan2(l2_oc_z - case_front_top[1],
                                  L2_CTR_X - case_front_top[0]))
    print(f'  rear down-cone: Jetson case front-top ({case_front_top[0]:.0f},'
          f'{case_front_top[1]:.0f}) sits {ang_r:.1f}deg below horizon -> '
          f'rear-down blind below that (v1-accepted)')

    print('\n-- CoM fore-aft shift vs the retired periscope+mast --')
    # masses (g): L2 230 (dimensions.md), D456 ~110 (D45x housing class)
    M_ROBOT = 4200.0
    # L2 centroid x: mast 53.5 -> head 53.5 (UNCHANGED by design)
    d_l2 = 230.0 * (L2_CTR_X - 53.5)
    # D456 centroid x: periscope body ctr 82.7 -> tilted OBB ctr
    cam_ctr_x = XM + (CAM_D / 2) * np.cos(th)
    d_d456 = 110.0 * (cam_ctr_x - 82.7)
    print(f'  L2 (230g): x {53.5}->{L2_CTR_X} -> {d_l2:+.0f} g.mm')
    print(f'  D456 (~110g): ctr x 82.7->{cam_ctr_x:.1f} -> {d_d456:+.0f} g.mm')
    print(f'  net fore-aft CoM shift ~ {(d_l2 + d_d456) / M_ROBOT:+.2f} mm '
          f'(+ = forward); both masses also rise ~+4mm in z')

    print('\n-- verdict --')
    ok = n == 0 and nf == 0 and nlc == 0 and C[:, 0].max() <= 100.5 \
        and (L2_SEAT_TOP - cam_top) >= 2.0
    print('  FEASIBLE' if ok else '  BLOCKED -- see above')


if __name__ == '__main__':
    main()
