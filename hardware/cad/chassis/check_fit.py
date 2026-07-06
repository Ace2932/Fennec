#!/usr/bin/env python3
"""chassis fit gate — riser bay vs REAL counterpart geometry.

leg_v6/check_fit.py pattern: sample real/measured counterpart solids, ANY
point inside the designed part = the part cuts its counterpart. Cases:

  1. riser <-> stock trunk mesh (both directions; designed seat bands excluded)
  2. mezzanine stack envelope (112 x 90 x 58 measured + boss budget) vs riser
     AND vs trunk — the four stack corners vs the trunk's leaning corner
     slabs is a KNOWN, DOCUMENTED conflict (see EXPECTED_STACK_ZONE): the
     fix is a hand-trim of the slab lower corners when the boards arrive,
     NOT a riser change. Gate fails only on hits OUTSIDE that zone.
  3. v6 shoulders (rev w/ notch + riser holes) at both ends vs riser
  4. CROUCH-pose leg sweep vs riser: haa x hfe x kfe grid, all four hips
     (rear end + left side are mirror placements — chirality is irrelevant
     for a swept-envelope check against the y-symmetric riser solid)
  5. static fixture asserts (service access, stack headroom, L2/Jetson gaps)
  6. belly battery pocket + pack envelope vs trunk / shoulders / crouch legs
  7. L2 mast vs riser (designed flange seat excluded), Jetson + plug
     envelopes, the shoulder deck-extension fin, and the seated L2 body
  8. D456 head bracket + camera envelope (UNDER-CHIN, z -16.5..12.5 —
     the v1 riser-wall position died on the shoulder shear webs) vs
     trunk/riser/pocket/pack/shoulders + the crouch sweep

Exit 0 = clean, 1 = interference. Run via build_all.sh after every change.
"""
import sys
import numpy as np
import trimesh

NOVA = '/Users/afox/codebases/NOVA'
TRUNK = f'{NOVA}/original_body_files/SM3_Frame_ChassisTrunk.stl'
SERVO = f'{NOVA}/feetech_servo_models/converted_stl/servo.stl'
LEG = f'{NOVA}/proj/hardware/cad/leg_v6'

# measured / designed constants (trunk frame; riser_bay.scad + dimensions.md)
WALL_TOP, PLATEAU_Z = 29.0, 46.91
DECK_BOT, DECK_TOP = 67.9, 71.9
FLOOR_TOP = 3.9
STACK = dict(x=56.0, y=45.0, z0=FLOOR_TOP, z1=FLOOR_TOP + 58.0)  # measured stack
BOSS_BUDGET = 2.0        # mezzanine floor-boss cap (part 5: countersunk plate)
HIP_FA, HIP_LAT, HIP_Z = 141.2, 39.05, 38.05

# stack corners vs the trunk's leaning corner slabs — known + documented.
# The slabs lean inward with height, so the overlap with the 112-long stack
# runs their FULL height at |x| 53.3..56. Disposition: trim the four slab
# inner ends back to |x| >= 56.5 (full height) when the fabbed boards
# arrive — the slabs only ever supported the stock covers.
EXPECTED_STACK_ZONE = dict(x=(53.0, 56.6), y=(28.5, 48.5), z=(24.5, 47.2))


def sample(m, n_surf=12000, n_vol=4000, seed=0):
    surf, _ = trimesh.sample.sample_surface(m, n_surf, seed=seed)
    lo, hi = m.bounds
    vol = np.random.default_rng(seed).uniform(lo, hi, (n_vol * 4, 3))
    vol = vol[m.contains(vol)][:n_vol]
    return np.vstack([surf, vol])


def report(label, hits, bad=True):
    n = len(hits)
    if n == 0:
        print(f'OK    {label}: 0 pts')
        return False
    print(f'{"CUT " if bad else "HIT "}  {label}: {n} pts')
    grid = np.round(hits / 2) * 2
    uniq, counts = np.unique(grid, axis=0, return_counts=True)
    for u, c in list(zip(uniq[np.argsort(-counts)], counts))[:6]:
        print(f'        cluster @ ({u[0]:+.0f},{u[1]:+.0f},{u[2]:+.0f})  {c} pts')
    return bad


def seat_mask(p):
    """Designed riser<->trunk contact bands (excluded from the gate)."""
    skirt = (np.abs(p[:, 2] - WALL_TOP) < 0.4) & \
            (np.abs(p[:, 1]) > 51.4) & (np.abs(p[:, 1]) < 55.3)
    plateau = (np.abs(p[:, 2] - PLATEAU_Z) < 0.4) & \
              (np.abs(p[:, 0]) > 53.0) & \
              (np.abs(p[:, 1]) > 29.4) & (np.abs(p[:, 1]) < 36.6)
    return skirt | plateau


def in_zone(p, z):
    return ((np.abs(p[:, 0]) > z['x'][0]) & (np.abs(p[:, 0]) < z['x'][1]) &
            (np.abs(p[:, 1]) > z['y'][0]) & (np.abs(p[:, 1]) < z['y'][1]) &
            (p[:, 2] > z['z'][0]) & (p[:, 2] < z['z'][1]))


# ---- leg assembly point cloud (leg_v6 gate composition, coax frame) --------
def rot(deg, axis, point=None):
    return trimesh.transformations.rotation_matrix(
        np.radians(deg), axis, point)


def tf(pts, M):
    return trimesh.transform_points(pts, M)


def leg_cloud(hfe, kfe):
    """coax + haa servo + femur/knee_arm/tibia posed at (hfe, kfe), coax frame."""
    T = trimesh.transformations.translation_matrix
    ry = rot(-90, [0, 1, 0]); rx = rot(90, [1, 0, 0])
    coax_pose = ry @ rx
    M_f = T([33.8, 11.6, -9.5]) @ rot(180, [0, 0, 1]) @ rot(90, [0, 1, 0])
    S_hfe = rot(hfe, [1, 0, 0], [33.8, 11.6, -9.5])
    T_knee = T([106.9, 0, 0])
    pts = np.vstack([
        LEGPTS['coax'],
        tf(LEGPTS['servo'], coax_pose),
        tf(LEGPTS['femur'], S_hfe @ M_f),
        tf(LEGPTS['arm'], S_hfe @ M_f),
        tf(LEGPTS['tibia'], S_hfe @ M_f @ T_knee @ rot(kfe, [0, 0, 1])),
    ])
    return pts


def load_leg_parts():
    T = trimesh.transformations.translation_matrix
    servo = trimesh.load(SERVO)
    servo.apply_translation([-12.5, 0, 0])
    arm = trimesh.load(f'{LEG}/knee_arm.stl')
    arm.apply_transform(T([59, 0, 17.2]))
    tib = trimesh.load(f'{LEG}/tibia_R.stl')
    tib_pts = trimesh.sample.sample_surface(tib, 4000, seed=0)[0]
    return dict(
        coax=trimesh.sample.sample_surface(
            trimesh.load(f'{LEG}/coax_R.stl'), 5000, seed=0)[0],
        servo=trimesh.sample.sample_surface(servo, 5000, seed=0)[0],
        femur=trimesh.sample.sample_surface(
            trimesh.load(f'{LEG}/femur_R.stl'), 4000, seed=0)[0],
        arm=trimesh.sample.sample_surface(arm, 1000, seed=0)[0],
        tibia=tib_pts,
    )


def coax_to_trunk_bases():
    """4 hip placements. Front: trunk = [s_y+141.2, s_x, s_z+38.05];
    rear + left side are mirrors (envelope check — see module docstring)."""
    T = trimesh.transformations.translation_matrix
    MIR = np.eye(4); MIR[1, 1] = -1                    # coax -> shoulder
    bases = []
    for hip_sign in (1, -1):                           # right / left hip
        HIP = T([hip_sign * HIP_LAT, 0, 0])
        MIRX = np.eye(4)
        if hip_sign < 0:
            MIRX[0, 0] = -1                            # mirror the leg itself
        for end in (1, -1):                            # front / rear
            S2T = np.array([[0, end, 0, end * HIP_FA],
                            [1, 0, 0, 0],
                            [0, 0, 1, HIP_Z],
                            [0, 0, 0, 1.0]])
            bases.append((f'{"F" if end > 0 else "R"}{"R" if hip_sign > 0 else "L"}',
                          S2T @ HIP @ MIRX @ MIR))
    return bases


def make_box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))


def main():
    bad = False
    riser = trimesh.load('riser_bay.stl')
    trunk = trimesh.load(TRUNK)
    pocket = trimesh.load('battery_pocket.stl')
    mast = trimesh.load('l2_mast.stl')
    head = trimesh.load('d456_head.stl')
    pack = make_box(-77.5, 77.5, -23, 23, -35.9, -0.9)   # 0.1 lift off tray
    cam = make_box(69.7, 95.7, -62, 62, 80.5, 109.5)     # D456, periscope

    # ---- 1. riser <-> trunk --------------------------------------------------
    rp = sample(riser)
    rp = rp[~seat_mask(rp)]
    hits = rp[trunk.contains(rp)]
    bad |= report('riser points inside trunk', hits)
    tp = sample(trunk)
    tp = tp[~seat_mask(tp)]
    hits = tp[riser.contains(tp)]
    bad |= report('trunk points inside riser', hits)

    # ---- 2. stack envelope (lifted whole by the floor-boss budget) -------------
    z0 = STACK['z0'] + BOSS_BUDGET
    z1 = STACK['z1'] + BOSS_BUDGET
    box = trimesh.creation.box(
        extents=[2 * STACK['x'], 2 * STACK['y'], z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [0, 0, (z0 + z1) / 2]))
    sp = sample(box, 10000, 3000)
    hits = sp[riser.contains(sp)]
    bad |= report('stack envelope vs riser', hits)
    hits = sp[trunk.contains(sp)]
    known = in_zone(hits, EXPECTED_STACK_ZONE) if len(hits) else np.array([], bool)
    if len(hits) and known.all():
        print(f'HIT   stack vs trunk corner slabs: {len(hits)} pts — KNOWN '
              f'(trim the 4 slab inner ends to |x| >= 56.5, full height, '
              f'when the boards arrive)')
    else:
        bad |= report('stack vs trunk OUTSIDE the known slab zone',
                      hits[~known] if len(hits) else hits)

    # ---- 3. shoulders vs riser -------------------------------------------------
    sh = trimesh.load(f'{LEG}/shoulder.stl')
    shp = trimesh.sample.sample_surface(sh, 8000, seed=0)[0]
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0],
                        [0, 0, 1, HIP_Z],
                        [0, 0, 0, 1.0]])
        p = tf(shp, S2T)
        near = p[(np.abs(p[:, 0]) < 72) & (p[:, 2] > 25)]
        hits = near[riser.contains(near)] if len(near) else near
        bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs riser', hits)

    # ---- 4. CROUCH-pose leg sweep vs riser + battery ------------------------------
    # CHASSIS-SAFE ROM (this gate is the authority, like the leg_v6 sweep
    # limits — feeds URDF joint ranges + firmware clamps):
    #   * hfe toward-trunk fold **+50 sw** — the folded tibia/knee flank
    #     (tibia jogs 30.5 back inboard) grazes the riser side skirt from
    #     ~+55 with kfe folded. Away-trunk -86 fully clean. Crouch needs
    #     only ~+40 (kfe-109 chord math).
    #   * **INBOARD haa +15 sw** (per leg; outboard splay keeps the full
    #     40) — the belly pack hangs 39 below the shell, and an inboard
    #     roll sweeps the folded leg under it: contact from ~18-20 deg at
    #     any hfe fold >= 30. Splay/stand-up choreography unaffected
    #     (outboard direction verified clean to 40). Inboard >15 has no
    #     use case anyway: the foot crosses the robot centerline.
    # Poses beyond either cap are printed as HIT (documented stops), and
    # do NOT fail the gate.
    global LEGPTS
    LEGPTS = load_leg_parts()
    print('-- crouch sweep (haa x hfe x kfe at all four hips vs riser/battery)')
    print('   chassis-safe: hfe -86..+50 sw AND inboard haa <= 15 sw')
    worst = 0
    for hfe in (-86, -45, 0, 45, 50, 55, 70, 86):
        for kfe in (-109, 0, 109):
            cloud = leg_cloud(hfe, kfe)
            for haa in (-40, -25, -15, 0, 15, 25, 40):
                for label, base in coax_to_trunk_bases():
                    # inboard = negative haa for right legs, positive for
                    # left (toe-crossing-centerline direction, verified)
                    inboard = -haa if label[1] == 'R' else haa
                    inside_rom = hfe <= 50 and inboard <= 15
                    # haa axis runs fore-aft (trunk x) through the hip
                    Sx = rot(haa, [1, 0, 0],
                             [HIP_FA if label[0] == 'F' else -HIP_FA,
                              HIP_LAT if label[1] == 'R' else -HIP_LAT, HIP_Z])
                    p = tf(tf(cloud, base), Sx)
                    for tname, target, near in (
                        ('riser', riser,
                         p[(np.abs(p[:, 0]) < 70) & (np.abs(p[:, 1]) < 58)
                           & (p[:, 2] > 25) & (p[:, 2] < 75)]),
                        ('pocket', pocket,
                         p[(np.abs(p[:, 0]) < 95) & (np.abs(p[:, 1]) < 35)
                           & (p[:, 2] > -45) & (p[:, 2] < 5)]),
                        ('pack', pack,
                         p[(np.abs(p[:, 0]) < 90) & (np.abs(p[:, 1]) < 30)
                           & (p[:, 2] > -40) & (p[:, 2] < 1)]),
                        ('head', head,
                         p[(p[:, 0] > 60) & (p[:, 0] < 73)
                           & (np.abs(p[:, 1]) < 61) & (p[:, 2] > 55)
                           & (p[:, 2] < 104)]),
                        ('camera', cam,
                         p[(p[:, 0] > 66) & (p[:, 0] < 99)
                           & (np.abs(p[:, 1]) < 65) & (p[:, 2] > 77)
                           & (p[:, 2] < 113)]),
                    ):
                        if not len(near):
                            continue
                        worst = max(worst, len(near))
                        n = int(target.contains(near).sum())
                        if n and inside_rom:
                            bad = True
                            print(f'   CUT {label} haa{haa:+d} hfe{hfe:+d} '
                                  f'kfe{kfe:+d} vs {tname}: {n} pts  '
                                  f'(INSIDE safe ROM!)')
                        elif n:
                            print(f'   HIT {label} haa{haa:+d} hfe{hfe:+d} '
                                  f'kfe{kfe:+d} vs {tname}: {n} pts  '
                                  f'(beyond sw limit — documents the stop)')
    print(f'   sweep done (max {worst} near-riser pts in any pose)')

    # ---- 6. battery pocket + pack ------------------------------------------------
    pp = sample(pocket, 8000, 2000)
    hits = pp[trunk.contains(pp)]
    bad |= report('battery pocket vs trunk', hits)
    kp = sample(pack, 6000, 1500)
    hits = kp[trunk.contains(kp)]
    bad |= report('battery pack vs trunk', hits)
    sh_pts = trimesh.sample.sample_surface(
        trimesh.load(f'{LEG}/shoulder.stl'), 8000, seed=0)[0]
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        p = tf(sh_pts, S2T)
        near = p[p[:, 2] < 5]
        for label, target in (('pocket', pocket), ('pack', pack)):
            hits = near[target.contains(near)] if len(near) else near
            bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs '
                          f'{label}', hits)

    # ---- 7. L2 mast ---------------------------------------------------------------
    mp = sample(mast, 8000, 2000)
    seat = (np.abs(mp[:, 2] - DECK_TOP) < 0.35)          # designed flange seat
    mp_f = mp[~seat]
    hits = mp_f[riser.contains(mp_f)]
    bad |= report('mast vs riser (seat excluded)', hits)
    jet = make_box(-60, 40, -49.4, 30, 78.2, 101.3)
    plugs = make_box(-55, 35, 30, 48, 78.2, 92)
    # deck-extension fin, MINUS the flange center notch strip (y +/-26)
    fin_l = make_box(63.5, 109, 26, 59.4, 73.05, 79.55)
    fin_r = make_box(63.5, 109, -59.4, -26, 73.05, 79.55)
    l2 = make_box(53.5 - 37.5, 53.5 + 37.5, -37.5, 37.5, 114.5, 179.4)
    for label, env in (('Jetson envelope', jet), ('Jetson plug zone', plugs),
                       ('deck-ext fin (left)', fin_l),
                       ('deck-ext fin (right)', fin_r)):
        hits = mp[env.contains(mp)]
        bad |= report(f'mast vs {label}', hits)
    lp = sample(l2, 5000, 1000)
    hits = lp[mast.contains(lp)]
    bad |= report('seated L2 body vs mast', hits)
    hits = lp[jet.contains(lp)]
    bad |= report('seated L2 body vs Jetson envelope', hits)

    # ---- 8. D456 head bracket + camera (periscope) --------------------------------
    hp = sample(head, 8000, 2000)
    for label, target in (('trunk', trunk), ('riser', riser),
                          ('mast', mast), ('deck-ext fin (left)', fin_l),
                          ('deck-ext fin (right)', fin_r),
                          ('Jetson envelope', jet)):
        hits = hp[target.contains(hp)]
        bad |= report(f'head bracket vs {label}', hits)
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        p = tf(sh_pts, S2T)
        near = p[np.abs(p[:, 0]) < 112]
        for label, target in (('head bracket', head), ('camera', cam)):
            hits = near[target.contains(near)] if len(near) else near
            bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs '
                          f'{label}', hits)
    cp = sample(cam, 5000, 1000)
    for label, target in (('riser', riser), ('mast', mast),
                          ('deck-ext fin (left)', fin_l),
                          ('deck-ext fin (right)', fin_r),
                          ('L2 body', l2), ('head bracket', head)):
        # camera rear seats on the plate face x 69.5: designed contact
        if label == 'head bracket':
            cp_f = cp[np.abs(cp[:, 0] - 69.6) > 0.3]
            hits = cp_f[target.contains(cp_f)]
        else:
            hits = cp[target.contains(cp)]
        bad |= report(f'camera envelope vs {label}', hits)

    # ---- 5. static fixture asserts ----------------------------------------------
    jet_top = DECK_TOP + 6.3 + 1.6 + 21.5     # spacer + pcb + heatsink (REVIEW)
    checks = [
        ('stack + boss headroom vs deck underside',
         STACK['z1'] + BOSS_BUDGET <= DECK_BOT - 2.0),
        ('mast bores clear of the Jetson footprint (driver access)',
         44 - 40.0 >= 3.0),
        ('L2 body bottom clears Jetson top + hood',
         146.9 - 65 / 2 >= jet_top + 4 + 2),
        ('deck slot under the Jetson plug row', 46 - 30 >= 12),
    ]
    for label, ok in checks:
        print(('OK    ' if ok else 'FAIL  ') + label)
        bad |= not ok
    print('NOTE  Jetson heatsink 21.5 is dimensions.md REVIEW — caliper '
          'before the hood part; D456 head shell top <= trunk z 72.8 '
          '(shoulder deck extension above).')

    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
