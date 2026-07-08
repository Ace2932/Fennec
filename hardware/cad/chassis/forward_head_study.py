#!/usr/bin/env python3
"""FORWARD-HEAD placement study (head re-architecture 2026-07-07).

Moves the integrated head OFF the riser front and FORWARD onto the FRONT
SHOULDER top (the "neck"), projecting ahead like a real fox. Interface =
separate NECK BRACKET (user call) bolting to the front-shoulder deck top
(trunk z79.55, spans x109..158, y+-59.4; center y+-26 free of horn plates).

Method: the OLD head's SENSOR geometry (tilted D456 face + L2 crown) is gate-
proven (head_study.py). We rigidly TRANSLATE it forward by DX and re-verify
against the REAL swept front-leg cloud at the new x, plus the shoulder deck
TOP directly under the new position (x109..158 @ z79.55) and the horn-plate
stack. DX is chosen here; head.scad + neck_bracket.scad track the winner.

Frame: trunk, +x FRONT, z up. Front-shoulder->trunk map (check_fit S2T, end=1):
  trunk = (sy+141.2, sx, sz+38.05);  deck top DECK_Z1 41.5 -> trunk z79.55.

Run:  ../../../.venv/bin/python forward_head_study.py
"""
import numpy as np
import trimesh

import check_fit as cf

T = trimesh.transformations.translation_matrix
rot = cf.rot
tf = cf.tf

# ---- OLD (riser) head sensor references (head_study.py, gate-proven) --------
OLD_L2_X = 53.5
OLD_XM = 70.0                     # D456 back-face center x (old)
OLD_ZM = 105.5                    # back-face center z (old riser head)
TILT = 27.0
CAM_D, CAM_L, CAM_H = 26.0, 123.8, 29.0
OLD_L2_SEAT_TOP = 122.0         # L2 body bottom (crown top); body 65 tall
L2_OPT_DZ = 32.5                 # optical center above seat top
L2_SEAT_TOP = OLD_L2_SEAT_TOP    # (rebound per-DZ in evaluate)

# ---- shoulder deck TOP under the new head (trunk frame) ---------------------
DECK_TOP_Z = 79.55
DECK_X = (109.1, 158.2)          # deck proper fore-aft span
DECK_Y = (-59.4, 59.4)


def rotY(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0])


def cam_box(xm, zm, tilt=TILT):
    """D456 body OBB; back-face center=(xm,0,zm), +x'=fwd(down-tilted)."""
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
    """REACHABLE front-leg points near the FORWARD head region."""
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
                    # forward head region: keep everything above the deck top
                    # and anywhere the shifted head can reach in x.
                    p = p[(p[:, 0] > 90) & (p[:, 2] > 70)]
                    if len(p):
                        pts.append(p)
    return np.vstack(pts) if pts else np.zeros((0, 3))


def horn_plate():
    """The REAL above-deck structure = the horn-plate TOP FLANGE only (the
    servo horn + coax hang BELOW the deck, inside the C-box). Plate flange
    (shoulder_plate.scad FLAN_Z 41.5..44.7, x23..55, y2.0..17.2 shoulder) ->
    trunk x143.2..158.4, y+-23..55, z79.55..82.75; +2 for the M3 bolt heads."""
    b = []
    for sy in (-1, 1):
        b.append(cf.make_box(143.2, 158.4, sy * 23, sy * 55,
                             DECK_TOP_Z, 84.75))
    m = trimesh.util.concatenate(b)
    return trimesh.sample.sample_surface(m, 6000, seed=0)[0]


def evaluate(dx, dz):
    l2x = OLD_L2_X + dx
    xm = OLD_XM + dx
    zm = OLD_ZM + dz
    seat = OLD_L2_SEAT_TOP + dz
    box, C = cam_box(xm, zm)
    leg = front_leg_sweep()
    n_leg = int(box.contains(leg).sum()) if len(leg) else 0
    # deck top directly under the head (a thin slab at z79.55)
    deck = cf.make_box(*DECK_X, *DECK_Y, DECK_TOP_Z - 1.0, DECK_TOP_Z)
    n_deck = int(box.contains(
        trimesh.sample.sample_surface(deck, 6000, seed=0)[0]).sum())
    n_horn = int(box.contains(horn_plate()).sum())
    # L2 body box
    l2 = cf.make_box(l2x - 37.5, l2x + 37.5, -37.5, 37.5, seat, seat + 65)
    n_l2cam = int(box.contains(
        trimesh.sample.sample_surface(l2, 4000, seed=0)[0]).sum())
    cam_top = C[:, 2].max()
    cam_xmax = C[:, 0].max()
    cam_zmin = C[:, 2].min()
    return dict(dx=dx, dz=dz, l2x=l2x, xm=xm, zm=zm, seat=seat, C=C,
                cam_top=cam_top, cam_xmax=cam_xmax, cam_zmin=cam_zmin,
                n_leg=n_leg, n_deck=n_deck, n_horn=n_horn,
                n_l2cam=n_l2cam, l2_gap=seat - cam_top)


def main():
    print('== FORWARD-HEAD study: shift the gate-proven head fwd onto the '
          'front-shoulder deck ==\n')
    print(f'deck top z{DECK_TOP_Z}, x{DECK_X[0]:.0f}..{DECK_X[1]:.0f}, '
          f'y+-{DECK_Y[1]:.0f}  (center y+-26 free of horn plates)\n')
    print(f'{"DX":>5} {"DZ":>4} {"L2x":>6} {"camXmax":>8} {"camZ":>6} '
          f'{"leg":>4} {"deck":>5} {"horn":>5} {"L2cam":>6} {"L2gap":>6}')
    best = None
    for dz in (4, 6, 8):
        for dx in (65, 70, 73, 76):
            r = evaluate(dx, dz)
            ok = (r['n_leg'] == 0 and r['n_deck'] == 0 and r['n_horn'] == 0
                  and r['n_l2cam'] == 0 and r['l2_gap'] >= 2.0
                  and r['cam_xmax'] <= 176 and r['cam_zmin'] >= 86.75)
            flag = '' if ok else '  <-- NG'
            print(f'{dx:5.0f} {dz:4.0f} {r["l2x"]:6.1f} {r["cam_xmax"]:8.1f} '
                  f'{r["cam_zmin"]:6.1f} {r["n_leg"]:4d} {r["n_deck"]:5d} '
                  f'{r["n_horn"]:5d} {r["n_l2cam"]:6d} {r["l2_gap"]:+6.1f}{flag}')
            # prefer the smallest DZ, then DX nearest 73 (deck-centered)
            if ok and (best is None or dz < best['dz']
                       or (dz == best['dz'] and abs(dx - 73) < abs(best['dx'] - 73))):
                best = r
    print()
    if best:
        r = best
        C = r['C']
        print(f'-- chosen DX={r["dx"]:.0f} DZ={r["dz"]:.0f}  (L2 center '
              f'x{r["l2x"]:.1f}, D456 back-face ({r["xm"]:.1f},0,{r["zm"]:.1f}))'
              f' --')
        print(f'  D456 body: x {C[:,0].min():.1f}..{C[:,0].max():.1f}  '
              f'z {C[:,2].min():.1f}..{C[:,2].max():.1f}  y +-{CAM_L/2:.1f}')
        print(f'  camera bottom z{r["cam_zmin"]:.1f} vs horn-plate top 84.75 '
              f'(margin {r["cam_zmin"]-84.75:+.1f})  / deck top {DECK_TOP_Z}')
        print(f'  L2 body x {r["l2x"]-37.5:.1f}..{r["l2x"]+37.5:.1f}  '
              f'z {r["seat"]:.0f}..{r["seat"]+65:.0f}  '
              f'optical ctr z~{r["seat"]+L2_OPT_DZ:.0f}')
        print(f'  camera top z{r["cam_top"]:.1f} vs L2 bottom {r["seat"]:.0f} '
              f'(gap {r["l2_gap"]:+.1f})')
        # CoM fore-aft shift vs retired positions
        M_ROBOT = 4200.0
        d_l2 = 230.0 * (r['l2x'] - OLD_L2_X)
        th = np.radians(TILT)
        cam_ctr_x = r['xm'] + (CAM_D / 2) * np.cos(th)
        old_cam_ctr = OLD_XM + (CAM_D / 2) * np.cos(th)
        d_d456 = 110.0 * (cam_ctr_x - old_cam_ctr)
        # head PA6-CF structure ~35 g (MEASURED 29.3 cm3 x 1.2); bracket ~17 g
        # rides the shoulder deck (barely moves the fore-aft CoM) so it is not
        # counted here.
        d_struct = 35.0 * ((r['l2x'] + r['xm']) / 2 - (OLD_L2_X + OLD_XM) / 2)
        net = (d_l2 + d_d456 + d_struct) / M_ROBOT
        print(f'\n  CoM fore-aft shift vs the riser head:')
        print(f'    L2 (230g):   x{OLD_L2_X}->{r["l2x"]:.0f}  {d_l2:+.0f} g.mm')
        print(f'    D456 (110g): ctr x{old_cam_ctr:.0f}->{cam_ctr_x:.0f}  '
              f'{d_d456:+.0f} g.mm')
        print(f'    structure (~120g): {d_struct:+.0f} g.mm')
        print(f'    net +{net:.1f} mm forward (of the 4.2 kg robot) -> nudge '
              f'the belly battery ~{net*M_ROBOT/300:.0f} mm rearward to null '
              f'(300 g pack), or accept front-load.')
    else:
        print('  NO clean shift in the tested range -- widen/retune.')


if __name__ == '__main__':
    main()
