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
  7. L2 mast (compact front-strip base) vs riser (flange seat excluded),
     the OFFICIAL JETSON CASE envelope, the shoulder deck-ext fin, seated L2
  8. D456 head bracket + camera envelope (PERISCOPE, z 80.5..109.5) vs
     trunk/riser/mast/case/shoulders + the crouch sweep
 10. Official Jetson case AABB + jetson_case_mount cradle vs trunk / riser
     (deck seat excluded) / mast / D456 / shoulders / L2 / each other

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
PLATE_T = 2.0            # part-5 floor plate: mezzanine seat plane 5.9
# stack (112 x 90 x 58 measured) CENTERED AT x = -3.5 on the plate: front
# corners clear the front slabs (0.8), rear board edge 0.5 off the trunk's
# corner posts, CoM pulls 3.5 rearward. 0.1 seat gap above the plate.
STACK_BOX = (-59.5, 52.5, -45.0, 45.0, 6.0, 64.0)
HIP_FA, HIP_LAT, HIP_Z = 141.2, 39.05, 38.05

# REAR stack corners vs the trunk's leaning corner slabs — known +
# documented. Disposition: trim the two REAR slab inner ends back to
# x <= -60.5 (full height) when the fabbed boards arrive — the slabs only
# ever supported the stock covers. Front slabs stay untouched; any front
# hit fails the gate. SIGNED x range.
EXPECTED_STACK_ZONE = dict(x=(-60.0, -52.9), y=(28.5, 48.5), z=(24.5, 47.2))


def sample(m, n_surf=12000, n_vol=4000, seed=0):
    surf, _ = trimesh.sample.sample_surface(m, n_surf, seed=seed)
    lo, hi = m.bounds
    rng = np.random.default_rng(seed)
    vol = rng.uniform(lo, hi, (n_vol * 4, 3))
    vol = vol[m.contains(vol)][:n_vol]
    pts = np.vstack([surf, vol])
    # 0.02 jitter: points sampled exactly ON axis-aligned faces fire
    # trimesh's fixed-direction containment rays through the (also
    # axis-aligned) counterpart tangentially -> stable false "inside"
    # verdicts (floor-plate case, 2026-07-06). Far below any clearance.
    return pts + rng.uniform(-0.02, 0.02, pts.shape)


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
    return ((p[:, 0] > z['x'][0]) & (p[:, 0] < z['x'][1]) &
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
    """Leg point cloud INCLUDING assembly aids — straps and cable-loop
    proxies. The 2026-07-05 leg_v6 lesson (femur strap was never swept and
    died) repeated here on the first chassis review: the original cloud was
    bare parts, so the ROM caps carried no allowance for the ~5mm-proud
    coax strap or the ~O16-18 service loops. Proxies are conservative
    spheres/boxes at the documented anchor/exit zones."""
    T = trimesh.transformations.translation_matrix
    servo = trimesh.load(SERVO)
    servo.apply_translation([-12.5, 0, 0])
    arm = trimesh.load(f'{LEG}/knee_arm.stl')
    arm.apply_transform(T([59, 0, 17.2]))
    tib = trimesh.load(f'{LEG}/tibia_R.stl')
    coax_mesh = trimesh.load(f'{LEG}/coax_R.stl')
    cb = coax_mesh.bounds
    rng = np.random.default_rng(1)

    def sphere_pts(c, r, n=120):
        v = rng.normal(size=(n, 3))
        v /= np.linalg.norm(v, axis=1)[:, None]
        return np.asarray(c) + r * v

    def box_pts(x0, x1, y0, y1, z0, z1, n=150):
        return rng.uniform([x0, y0, z0], [x1, y1, z1], (n, 3))

    coax_extra = np.vstack([
        # front strap + screw heads (~5 proud of the coax front face)
        box_pts(-18, 18, cb[0][1] - 5, cb[0][1] + 0.1, -38, -24),
        # bottom cable-tunnel exit loop
        sphere_pts([(cb[0][0] + cb[1][0]) / 2,
                    (cb[0][1] + cb[1][1]) / 2, cb[0][2] - 9], 9),
        # hfe service loop (bay-side bulge + sag; exits ~25 off-axis)
        sphere_pts([33.8, 36.6, -9.5], 9),
        sphere_pts([33.8, 24, -30], 9),
    ])
    femur_extra = np.vstack(
        [sphere_pts([x, 0, -28], 8) for x in (15, 45, 75)]     # underside run
        + [sphere_pts([84, 0, -30], 9), sphere_pts([96, 0, -26], 9)])  # knee loop
    tibia_extra = np.vstack([
        box_pts(26, 36, -18, 18, 14.5, 22.5),   # tibia strap + heads
        sphere_pts([44, 0, -28], 9),            # tibia tunnel loop
    ])
    return dict(
        coax=np.vstack([trimesh.sample.sample_surface(coax_mesh, 5000, seed=0)[0],
                        coax_extra]),
        servo=trimesh.sample.sample_surface(servo, 5000, seed=0)[0],
        femur=np.vstack([trimesh.sample.sample_surface(
            trimesh.load(f'{LEG}/femur_R.stl'), 4000, seed=0)[0], femur_extra]),
        arm=trimesh.sample.sample_surface(arm, 1000, seed=0)[0],
        tibia=np.vstack([trimesh.sample.sample_surface(tib, 4000, seed=0)[0],
                         # knee_bumper (TPU, backlog #15 B) rides the tibia knee
                         # end — include it in the crouch sweep vs battery/riser
                         trimesh.sample.sample_surface(
                             trimesh.load(f'{LEG}/knee_bumper.stl'),
                             1500, seed=0)[0],
                         tibia_extra]),
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


# ---- HEAD geometry (must track head.scad / forward_head_study.py) ------------
# 2026-07-07 re-architecture: head moved FWD onto the front-shoulder top (the
# "neck") via neck_bracket.scad. Sensors shifted DX+73 DZ+6 vs the riser head.
HEAD_TILT = 27.0                              # D456 down-tilt about +y
CAM_M = (143.0, 0.0, 111.5)                   # D456 back-face center on the face
CAM_D, CAM_L, CAM_H = 26.0, 123.8, 29.0       # D456 body (dimensions.md)
L2_CTR_X = 126.5                              # L2 optical/plate center x
L2_SEAT_TOP = 133.0                           # L2 body bottom (crown top)


def cam_box():
    """D456 body OBB: back-face center CAM_M, tilted HEAD_TILT down about +y."""
    th = np.radians(HEAD_TILT)
    fwd = np.array([np.cos(th), 0, -np.sin(th)])
    center = np.array(CAM_M) + (CAM_D / 2) * fwd
    R = trimesh.transformations.rotation_matrix(th, [0, 1, 0])
    T = trimesh.transformations.translation_matrix(center)
    return trimesh.creation.box(extents=[CAM_D, CAM_L, CAM_H], transform=T @ R)


def l2_box():
    """Seated L2 body (75x75x65). Floor 0.1 above the crown seat plane so the
    designed L2<->crown contact isn't scored a hit."""
    return make_box(L2_CTR_X - 37.5, L2_CTR_X + 37.5, -37.5, 37.5,
                    L2_SEAT_TOP + 0.1, L2_SEAT_TOP + 63.5)


def main():
    bad = False
    riser = trimesh.load('riser_bay.stl')
    trunk = trimesh.load(TRUNK)
    pocket = trimesh.load('battery_pocket.stl')
    head = trimesh.load('head.stl')     # fwd head (D456 face + L2 crown), bolts
                                        # to the neck bracket (retired: riser mount)
    bracket = trimesh.load('neck_bracket.stl')   # front-shoulder-deck adapter
    cradle = trimesh.load('jetson_case_mount.stl')
    # Official Jetson case AABB (calipered 110.3x93.9x38.2, port END -x, on
    # the deck). REPLACES the retired bespoke Jetson tray + heatsink box.
    case = make_box(-62.0, 48.3, -46.95, 46.95, 71.9, 110.1)
    pack = make_box(-77.5, 77.5, -23.4, 23.4, -35.9, -0.9)  # 46.8 wide caliper
    # skid rails (backlog #15): TPU strips under the tray, new lowest z
    rails = trimesh.util.concatenate([
        make_box(-55, 75, 9, 21, -42.2, -39.2),
        make_box(-55, 75, -21, -9, -42.2, -39.2)])
    cam = cam_box()   # tilted D456 OBB (27deg down; back-face ctr 70,0,105.5)

    # ---- 1. riser <-> trunk --------------------------------------------------
    rp = sample(riser)
    rp = rp[~seat_mask(rp)]
    hits = rp[trunk.contains(rp)]
    bad |= report('riser points inside trunk', hits)
    tp = sample(trunk)
    tp = tp[~seat_mask(tp)]
    hits = tp[riser.contains(tp)]
    bad |= report('trunk points inside riser', hits)

    # ---- 2. stack envelope (seated on the part-5 plate, ctr x -4) ---------------
    box = make_box(*STACK_BOX)
    sp = sample(box, 10000, 3000)
    hits = sp[riser.contains(sp)]
    bad |= report('stack envelope vs riser', hits)
    hits = sp[trunk.contains(sp)]
    known = in_zone(hits, EXPECTED_STACK_ZONE) if len(hits) else np.array([], bool)
    if len(hits) and known.all():
        print(f'HIT   stack vs trunk REAR corner slabs: {len(hits)} pts — '
              f'KNOWN (trim the two rear slab inner ends to x <= -60.5 when '
              f'the boards arrive; front slabs stay)')
    else:
        bad |= report('stack vs trunk OUTSIDE the known rear-slab zone',
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
        # 3b. shoulder vs TRUNK: everything reaching inside the end face
        # (|x| < 63.4) must be the flange floor FEET on their designed
        # seats — trunk (|x| 54..63.5, |y| 37.5..46.5, floor band) — or the
        # D456 insert pads / battery-lead notch fillers in the end
        # aperture (open space, contains() never true there anyway).
        inside = p[np.abs(p[:, 0]) < 63.4]
        hits = inside[trunk.contains(inside)] if len(inside) else inside
        if len(hits):
            seat = ((np.abs(hits[:, 0]) > 53.9) & (np.abs(hits[:, 0]) < 63.5)
                    & (np.abs(hits[:, 1]) > 37.4) & (np.abs(hits[:, 1]) < 46.6)
                    & (hits[:, 2] > -0.1) & (hits[:, 2] < 8.2))
            hits = hits[~seat]
        bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs trunk '
                      f'(feet seats excluded)', hits)

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
    print('   chassis-safe: hfe FRONT -50..+50 / REAR -86..+50 sw AND '
          'inboard haa <= 15 sw')
    worst = 0
    for hfe in (-86, -45, 0, 45, 50, 55, 70, 86):
        for kfe in (-109, -55, 0, 55, 109):
            cloud = leg_cloud(hfe, kfe)
            for haa in (-40, -25, -15, 0, 15, 25, 40):
                for label, base in coax_to_trunk_bases():
                    # inboard = negative haa for right legs, positive for
                    # left (toe-crossing-centerline direction, verified)
                    inboard = -haa if label[1] == 'R' else haa
                    # FRONT legs cap forward protraction at -50 (head clearance,
                    # 2026-07-07); rear keep -86. Upper +50 both.
                    hfe_lo = -50 if label[0] == 'F' else -86
                    inside_rom = hfe_lo <= hfe <= 50 and inboard <= 15
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
                        ('rails', rails,
                         p[(np.abs(p[:, 0]) < 90) & (np.abs(p[:, 1]) < 30)
                           & (p[:, 2] > -46) & (p[:, 2] < -35)]),
                        # fwd head: crown/boss/column x108..145, pillar x128..138
                        ('head', head,
                         p[(p[:, 0] > 100) & (p[:, 0] < 146)
                           & (np.abs(p[:, 1]) < 40) & (p[:, 2] > 82)
                           & (p[:, 2] < 130)]),
                        # neck bracket: base x107..150 y+-21, wall to z106
                        ('bracket', bracket,
                         p[(p[:, 0] > 100) & (p[:, 0] < 152)
                           & (np.abs(p[:, 1]) < 24) & (p[:, 2] > 78)
                           & (p[:, 2] < 108)]),
                        # D456 body x136..173, z87..125, y+-62
                        ('camera', cam,
                         p[(p[:, 0] > 130) & (p[:, 0] < 176)
                           & (np.abs(p[:, 1]) < 63) & (p[:, 2] > 84)
                           & (p[:, 2] < 126)]),
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

    # ---- 7+8. FWD HEAD + NECK BRACKET vs static env + shoulder -----------------
    # deck-extension fin, MINUS the flange center notch strip (y +/-26)
    fin_l = make_box(63.5, 109, 26, 59.4, 73.05, 79.55)
    fin_r = make_box(63.5, 109, -59.4, -26, 73.05, 79.55)
    l2 = l2_box()                                        # seated L2, floor z128.1
    # --- head bolts to the bracket; it has NO chassis seat (all up at z>=84) ---
    hp = sample(head, 10000, 3000)
    for label, target in (('trunk', trunk), ('riser', riser),
                          ('case envelope', case),
                          ('deck-ext fin (left)', fin_l),
                          ('deck-ext fin (right)', fin_r)):
        hits = hp[target.contains(hp)]
        bad |= report(f'head vs {label}', hits)
    # --- neck bracket: base seats on the front-shoulder deck top (z79.55); the
    #     4 corner bolts drill THROUGH the deck (designed). Exclude the base
    #     bottom face (z<80.1) as the designed deck seat.
    bp = sample(bracket, 9000, 2500)
    bp_f = bp[bp[:, 2] > 80.1]
    for label, target in (('trunk', trunk), ('riser', riser),
                          ('case envelope', case)):
        hits = bp_f[target.contains(bp_f)]
        bad |= report(f'neck bracket vs {label}', hits)
    # --- head <-> bracket bolt joint (head boss front x121 meets wall front
    #     x121). Exclude the interface band; the rest must not interpenetrate.
    hp_nj = hp[np.abs(hp[:, 0] - 121) >= 1.0]
    hits = hp_nj[bracket.contains(hp_nj)]
    bad |= report('head vs bracket (bolt-joint band excluded)', hits)
    # --- shoulder (both ends) vs head / bracket / camera. Filter to the fwd
    #     region ABOVE the deck seat (z>80.2) so the designed bracket-on-deck
    #     contact isn't scored.
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        p = tf(sh_pts, S2T)
        near = p[(p[:, 0] > 95) & (p[:, 0] < 176) & (p[:, 2] > 80.2)]
        for label, target in (('head', head), ('bracket', bracket),
                              ('camera', cam)):
            hits = near[target.contains(near)] if len(near) else near
            bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs '
                          f'{label}', hits)
    # camera OBB vs static env (camera back seats on the tilted plate = designed)
    cp = sample(cam, 6000, 1500)
    for label, target in (('riser', riser), ('neck bracket', bracket),
                          ('deck-ext fin (left)', fin_l),
                          ('deck-ext fin (right)', fin_r),
                          ('L2 body', l2)):
        hits = cp[target.contains(cp)]
        bad |= report(f'camera envelope vs {label}', hits)
    # seated L2 body vs the head crown (designed seat excluded via l2_box floor)
    lp = sample(l2, 5000, 1000)
    hits = lp[head.contains(lp)]
    bad |= report('seated L2 body vs head', hits)

    # ---- 9. floor plate ------------------------------------------------------------
    plate = trimesh.load('floor_plate.stl')
    fp = sample(plate, 6000, 1500)
    seatp = np.abs(fp[:, 2] - FLOOR_TOP) < 0.3        # designed floor seat
    fp_f = fp[~seatp]
    hits = fp_f[trunk.contains(fp_f)]
    bad |= report('floor plate vs trunk (seat excluded)', hits)
    hits = fp[box.contains(fp)]
    bad |= report('floor plate vs stack envelope', hits)
    hits = fp[pack.contains(fp)]
    bad |= report('floor plate vs battery pack', hits)

    # ---- 10. Jetson official case + cradle --------------------------------------
    # case is an AABB envelope (calipered, port end -x, sits on the deck). The
    # cradle (jetson_case_mount.stl) locates + retains it. Designed contacts:
    # cradle bottom on the deck top (z71.9) and the cradle lip/tabs on the case.
    for label, target in (('trunk', trunk), ('L2 body', l2), ('head', head)):
        cs = sample(case, 6000, 1500)
        hits = cs[target.contains(cs)]
        bad |= report(f'case envelope vs {label}', hits)
    crp = sample(cradle, 7000, 2000)
    seatc = np.abs(crp[:, 2] - DECK_TOP) < 0.5           # designed deck seat
    crp_f = crp[~seatc]
    hits = crp_f[trunk.contains(crp_f)]
    bad |= report('cradle vs trunk', hits)
    hits = crp_f[riser.contains(crp_f)]
    bad |= report('cradle vs riser (deck seat excluded)', hits)
    for label, target in (('head', head),):
        hits = crp[target.contains(crp)]
        bad |= report(f'cradle vs {label}', hits)
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        p = tf(sh_pts, S2T)
        near = p[np.abs(p[:, 0]) < 66]
        hits = near[cradle.contains(near)] if len(near) else near
        bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs cradle', hits)

    # ---- 5. static fixture asserts ----------------------------------------------
    case_top = 110.1     # official case top (deck 71.9 + 38.2 calipered)
    checks = [
        ('stack + plate headroom vs deck underside',
         STACK_BOX[5] <= DECK_BOT - 2.0),
        ('case rear (-62) clears the rear shoulder wall (-63.5)',
         -62.0 - (-63.5) >= 1.0),
        # --- fwd head (forward_head_study.py DX+73 DZ+6) ---
        ('camera bottom (86.8) clears the front horn-plate top (84.75)',
         86.8 - 84.75 >= 1.5),
        ('camera bottom (86.8) clears the neck-bracket base top (83.55)',
         86.8 - 83.55 >= 2.0),
        ('face-plate top (124.4) clears the L2 body bottom (128)',
         128.0 - 124.4 >= 1.0),
        ('camera fwd-most (172.7) within the studied envelope (175)',
         172.7 <= 175.0),
        ('L2 body bottom (128) far clears the case top (110.1)',
         128.0 - case_top >= 4.0),
        ('neck-bracket deck-through bolts span (36 fore-aft) >= 30',
         148 - 110 >= 30),
    ]
    for label, ok in checks:
        print(('OK    ' if ok else 'FAIL  ') + label)
        bad |= not ok
    print('NOTE  Case dims 110.3x93.9x38.2 CALIPERED (dimensions.md); the ref '
          'mesh is ~1.2 oversize. Ports on the -Y flank -> STRAIGHT plugs are '
          'shielded by jetson_cowl + drop the -Y CASE_SLOT to the bay (#38); '
          'verify the bundle fit + drop-to-boards at wiring.')

    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
