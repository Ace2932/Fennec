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


def main():
    bad = False
    riser = trimesh.load('riser_bay.stl')
    trunk = trimesh.load(TRUNK)

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

    # ---- 4. CROUCH-pose leg sweep vs riser --------------------------------------
    # CHASSIS-SAFE ROM (this gate is the authority, like the leg_v6 sweep
    # limits): hfe toward-trunk fold **+50 sw** — the folded tibia/knee
    # flank (tibia jogs 30.5 back inboard) starts grazing the riser side
    # skirt at ~+55 with kfe folded + haa -40. Crouch itself needs only
    # ~+40 (kfe 109 chord math). Away-trunk -86 stays fully clean. Feeds
    # the URDF joint ranges + firmware clamps ("joint ranges = sweep gate
    # values", design-outline). Poses beyond +50 are printed as HIT to
    # document the stop, and do NOT fail the gate.
    global LEGPTS
    LEGPTS = load_leg_parts()
    print('-- crouch sweep (haa x hfe x kfe at all four hips vs riser)')
    print('   chassis-safe hfe: -86..+50 sw (contact from ~+55: documented)')
    worst = 0
    for hfe in (-86, -45, 0, 45, 50, 55, 70, 86):
        inside_rom = hfe <= 50
        for kfe in (-109, 0, 109):
            cloud = leg_cloud(hfe, kfe)
            for haa in (-40, -25, 0, 25, 40):
                for label, base in coax_to_trunk_bases():
                    # haa axis runs fore-aft (trunk x) through the hip
                    Sx = rot(haa, [1, 0, 0],
                             [HIP_FA if label[0] == 'F' else -HIP_FA,
                              HIP_LAT if label[1] == 'R' else -HIP_LAT, HIP_Z])
                    p = tf(tf(cloud, base), Sx)
                    near = p[(np.abs(p[:, 0]) < 70) & (np.abs(p[:, 1]) < 58)
                             & (p[:, 2] > 25) & (p[:, 2] < 75)]
                    if not len(near):
                        continue
                    worst = max(worst, len(near))
                    n = int(riser.contains(near).sum())
                    if n and inside_rom:
                        bad = True
                        print(f'   CUT {label} haa{haa:+d} hfe{hfe:+d} '
                              f'kfe{kfe:+d}: {n} pts  (INSIDE safe ROM!)')
                    elif n:
                        print(f'   HIT {label} haa{haa:+d} hfe{hfe:+d} '
                              f'kfe{kfe:+d}: {n} pts  (beyond sw limit — '
                              f'documents the stop)')
    print(f'   sweep done (max {worst} near-riser pts in any pose)')

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
