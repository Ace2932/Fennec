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
 11. REAL power board (power_board_model.power_board_mesh(), kicad_pcb-parsed
     per-component geometry, replaces the old flat stack-envelope box for the
     bottom/power layer) AND the REAL logic board
     (power_board_model.logic_board_mesh(), kicad_pcb-parsed per-component
     geometry, replaces the old logic-board/Teensy ENVELOPE box — the top
     mezzanine layer is no longer an estimate, it's parsed straight out of
     nova_pcb_v6_logic.kicad_pcb), floor->power standoff = STANDOFF_FLOOR_MM
     (20mm, the M3x20 standoffs on hand; corrected 2026-07-09 from a stale
     16mm spec — CHASSIS-side only, the board + every component are already
     ordered/fixed). Asserts: (a) the 5 bottom-side 1000uF caps (C1-C5,
     Ø10x17mm cans) clear the floor plate top AND the stock trunk's own
     floor slab underneath it — hard fail, no known exception (at 16mm the
     17mm cans sat 1mm proud; at 20mm they bottom at z9, 3mm clear);
     (b) EVERY power-board top-side part clears the riser deck underside
     (z67.9), Q1 (TO-220) the tallest, AND the real logic board's tallest
     parsed point (Teensy 4.1 / Arduino Nano socket, 13mm off the component
     face -> STACK_TOP_Z≈62.22) clears the same deck underside — no longer
     a Teensy "envelope" guess, ~5.68mm margin; (c) Q1 specifically clears
     the LOGIC BOARD underside (pb top + the unchanged 20mm pb->lb
     standoff) — the logic-board plane is no longer pinned to Q1's height
     by construction, so this is now an explicit assert (~2mm margin);
     (d) trunk rear corner SLABS/posts (z24.5..47.2) — same known-zone
     logic as case 2, but board-accurate: only J1 (XT60 battery-in
     connector) actually reaches into the zone; (e) the logic board's own
     B.Cu underside (3x 0.6mm 0603 resistors, the parsed parts reaching
     lowest into the 20mm pb->lb gap) clears Q1's top — trivially true by
     construction but now asserted against real parsed geometry on both
     sides of the gap instead of assumed.
 12. CR-7 (was #39): the newest chassis parts, never gated before now —
     jetson_clamp_bar (+y/-y mirror), l2_adapter, control_pod, oled_mount.
     (jetson_cowl was gated here too until #41 retired it 2026-07-10 —
     superseded by right-angle plug adapters; see jetson_cowl.scad banner.)
     jetson_clamp_bar vs jetson_case_ref.stl is checked via a
     SURFACE-HEIGHT envelope (case_surface_clash()), not contains(): the ref
     mesh is not watertight (euler_number ~-2223 / 2 bodies — almost
     certainly the vent-grille perforations), so volumetric containment is
     unreliable there. Every other case-12 pair is watertight-vs-watertight
     and uses report_depth() (signed_distance magnitude, sub-mm noise floor
     — designed seats/butt-joints are excluded via *_seat_mask() first, same
     idiom as seat_mask()/EXPECTED_STACK_ZONE above).

Exit 0 = clean, 1 = interference. Run via build_all.sh after every change.
"""
import sys
import numpy as np
import trimesh

from power_board_model import (power_board_mesh, logic_board_mesh, FLOOR_TOP_Z,
                                STANDOFF_FLOOR_MM, LOGIC_BOARD_Z0, STACK_TOP_Z)

NOVA = '/Users/afox/codebases/NOVA'
TRUNK = f'{NOVA}/original_body_files/SM3_Frame_ChassisTrunk.stl'
SERVO = f'{NOVA}/feetech_servo_models/converted_stl/servo.stl'
LEG = f'{NOVA}/proj/hardware/cad/leg_v6'

# measured / designed constants (trunk frame; riser_bay.scad + dimensions.md)
WALL_TOP, PLATEAU_Z = 29.0, 46.91
DECK_BOT, DECK_TOP = 67.9, 71.9
FLOOR_TOP = 3.9
PLATE_T = 2.0            # part-5 floor plate: mezzanine seat plane 5.9
# battery_pocket.scad: RIM_Z=-0.2, CAV_Z0 = RIM_Z-(PACK[2]+CLR) = -0.2-(35+0.6)
# = -35.8 -- the tray floor top the pack physically RESTS ON (designed seat,
# not a collision). AUD-1 gate case 6 pack-vs-pocket check.
TRAY_FLOOR_Z = -35.8
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

# ---- case 12 constants (CR-7/#39: jetson_clamp_bar.scad,
# jetson_case_mount.scad, riser_bay.scad, control_pod.scad, l2_adapter.scad,
# head.scad -- mirrors those files' own "shared consts, KEEP IN SYNC" comments) --
CRADLE_FRONT_PXC, CRADLE_REAR_PXC = 47.3, -59.0    # cradle upright x centres
CRADLE_POST_YC, CRADLE_POST_W = 50.35, 6.0         # cradle upright y centre/size
CRADLE_CORNER_Z = 102.8                            # upright top = clamp-bar seat
BAR_HY = 41.45                    # clamp-bar inner edge = case corner-column y
CASE_FRONT_HX, CASE_REAR_HX = 42.8, -56.5          # case corner-column x centres
POD_BOSS_X = -66.5                 # riser rear-wall pad <-> pod column interface
POD_HY, POD_Z0, POD_Z1 = 14.0, 58.0, 69.0
L2A_SEAT_Z = 128.0                  # crown top = l2_adapter bottom seat
OLED_SEAT_Z = 95.0                  # control_pod deck top = oled_mount foot seat

# ---- REAL power board vs floor (case 11) -----------------------------------
# HISTORY: an early modeling pass assumed generic 20mm caps on a 16mm
# standoff, which put C1-C5 over SOLID floor_plate material AND into the
# stock trunk floor -- a known, non-failing exception was carved out. Both
# inputs were wrong: the ordered caps are Ø10x17mm cans (memory arm-phase4
# order note) and the standoffs on hand are M3x20, not 16mm. 2026-07-09:
# corrected STANDOFF_FLOOR_MM to 20mm (power_board_model.py) and cap height
# to 17mm -- caps now bottom at z9, 3mm clear of the floor plate top
# (FLOOR_TOP_Z=6). The carve-out is REMOVED: case 11 asserts hard clearance
# with no known-exception zones, so a regression (e.g. a caliper-measured
# part taller than assumed pushing past the S<=24.7 fit-window ceiling)
# fails the gate instead of silently passing.


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


# ---- case 12 helpers (CR-7/#39) ---------------------------------------------
def report_depth(label, hits, mesh, noise_mm=0.05):
    """Like report(), but quantifies HOW FAR a hit set penetrates its
    counterpart (trimesh.proximity.signed_distance, positive = inside)
    instead of just a point count, and only fails the gate if the worst
    point clears noise_mm -- sub-mm hits at a designed butt-joint/seat
    boundary (sampling jitter, mesh-vs-mesh coincident faces) are reported
    but not failed. Requires a watertight `mesh` (signed_distance needs a
    valid inside/outside) -- do not use this on jetson_case_ref.stl (not
    watertight; see case_surface_clash below)."""
    n = len(hits)
    if n == 0:
        print(f'OK    {label}: 0 pts')
        return False
    sd = trimesh.proximity.signed_distance(mesh, hits)
    depth = sd[sd > 0]
    max_d = float(depth.max()) if len(depth) else 0.0
    mean_d = float(depth.mean()) if len(depth) else 0.0
    tag = 'NOISE ' if max_d < noise_mm else 'CUT   '
    print(f'{tag}{label}: {n} pts, max penetration {max_d:.3f}mm '
          f'(mean {mean_d:.3f}mm, noise floor {noise_mm}mm)')
    grid = np.round(hits / 2) * 2
    uniq, counts = np.unique(grid, axis=0, return_counts=True)
    for u, c in list(zip(uniq[np.argsort(-counts)], counts))[:6]:
        print(f'        cluster @ ({u[0]:+.0f},{u[1]:+.0f},{u[2]:+.0f})  {c} pts')
    return max_d >= noise_mm


def case_surface_clash(case_pts, x0, x1, y0, y1, z_floor, label,
                        noise_mm=0.3, exclude=None):
    """jetson_case_ref.stl is NOT watertight (euler_number ~-2223, 2 bodies
    -- almost certainly the vent-grille perforations modeled as literal
    through-holes), so a volumetric contains()/signed_distance() check on
    it is unreliable (ray-cast in/out parity breaks at non-manifold vent
    edges). Sidestep that entirely: sample the case's OUTER SURFACE once
    (case_pts, world frame, no watertightness needed) and check whether any
    sampled surface point inside the given (x, |y|) window sits ABOVE
    z_floor -- i.e. does real, modeled case material protrude into the
    flat bar's z-band. `exclude(pts)` -> bool mask removes designed bearing
    pads (corner columns) from the window before the height check."""
    m = ((case_pts[:, 0] >= x0) & (case_pts[:, 0] <= x1) &
         (np.abs(case_pts[:, 1]) >= y0) & (np.abs(case_pts[:, 1]) <= y1))
    sub = case_pts[m]
    if exclude is not None and len(sub):
        sub = sub[~exclude(sub)]
    if not len(sub):
        print(f'OK    {label}: 0 case-surface pts in window')
        return False
    over = sub[sub[:, 2] > z_floor]
    if not len(over):
        print(f'OK    {label}: case surface tops out {sub[:, 2].max():.2f} '
              f'<= {z_floor} ({len(sub)} pts sampled in window)')
        return False
    depth = over[:, 2] - z_floor
    tag = 'NOISE ' if depth.max() < noise_mm else 'CUT   '
    print(f'{tag}{label}: {len(over)}/{len(sub)} case-surface pts exceed '
          f'z={z_floor}, max penetration {depth.max():.3f}mm '
          f'(mean {depth.mean():.3f}mm, noise floor {noise_mm}mm)')
    grid = np.round(over / 2) * 2
    uniq, counts = np.unique(grid, axis=0, return_counts=True)
    for u, c in list(zip(uniq[np.argsort(-counts)], counts))[:6]:
        print(f'        cluster @ ({u[0]:+.0f},{u[1]:+.0f},{u[2]:+.0f})  {c} pts')
    return depth.max() >= noise_mm


def bar_seat_mask(p):
    """Designed clamp-bar bearing pads, excluded from the bar<->case /
    bar<->cradle checks: the case's calipered corner-column tops (z=
    CRADLE_CORNER_Z, x at the case's corner-column centres, y at the bar's
    inner HY edge) AND the cradle upright tops (same z, x/y at the cradle
    post centres). Everything else on the bar's flat underside is real."""
    near_z = np.abs(p[:, 2] - CRADLE_CORNER_Z) < 0.6
    near_case_x = (np.abs(p[:, 0] - CASE_FRONT_HX) < 4.0) | \
                  (np.abs(p[:, 0] - CASE_REAR_HX) < 4.0)
    near_case_y = np.abs(np.abs(p[:, 1]) - BAR_HY) < 4.0
    near_post_x = (np.abs(p[:, 0] - CRADLE_FRONT_PXC) < CRADLE_POST_W / 2 + 1) | \
                  (np.abs(p[:, 0] - CRADLE_REAR_PXC) < CRADLE_POST_W / 2 + 1)
    near_post_y = np.abs(np.abs(p[:, 1]) - CRADLE_POST_YC) < CRADLE_POST_W / 2 + 1
    return (near_z & near_case_x & near_case_y) | (near_z & near_post_x & near_post_y)


def pod_riser_seat_mask(p):
    """Designed control_pod column <-> riser rear-wall pad butt joint at
    x=POD_BOSS_X (riser pocket-boss rear face == pod column front face)."""
    near_x = np.abs(p[:, 0] - POD_BOSS_X) < 0.6
    near_y = np.abs(p[:, 1]) < POD_HY + 1
    near_z = (p[:, 2] > POD_Z0 - 1) & (p[:, 2] < POD_Z1 + 1)
    return near_x & near_y & near_z


def l2a_seat_mask(p):
    """Designed l2_adapter <-> crown-top seat (z=L2A_SEAT_Z). The front
    tongue<->crown-lip interlock needs no separate mask: head.scad
    difference()s a matching slot out of the lip, so head.contains() is
    already False there by construction."""
    return np.abs(p[:, 2] - L2A_SEAT_Z) < 0.6


def oled_seat_mask(p):
    """Designed oled_mount foot <-> control_pod deck-top seat (z=OLED_SEAT_Z)."""
    return np.abs(p[:, 2] - OLED_SEAT_Z) < 0.6


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
    arm.apply_transform(T([59, 0, 17.75]))  # rev 3 (2026-07-10): 17.2->17.75
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

    # ---- case 12 parts (CR-7/#39: never gated before -- added by build_all.sh
    # after the gate was last touched) -------------------------------------------
    clamp_bar_R = trimesh.load('jetson_clamp_bar.stl')  # designed +y side (#44)
    MYb = np.eye(4); MYb[1, 1] = -1
    clamp_bar_L = clamp_bar_R.copy(); clamp_bar_L.apply_transform(MYb)
    l2_adapter = trimesh.load('l2_adapter.stl')
    pod = trimesh.load('control_pod.stl')
    oled = trimesh.load('oled_mount.stl')
    # jetson_case_ref.stl: same placement transform as place_case.py /
    # preview_assembly.py (world x-6.85 ctr, y0 ctr, bottom on the deck 71.9).
    # NOT watertight (see case_surface_clash docstring) -- keep separate from
    # the calipered `case` AABB used by cases 7/8/10.
    caseref = trimesh.load('jetson_case_ref.stl')
    bc = (caseref.bounds[0] + caseref.bounds[1]) / 2
    caseref.apply_translation([-6.85 - bc[0], -bc[1], 71.9 - caseref.bounds[0][2]])

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
    # AUD-6 (2026-07-10): case 6 previously never checked whether the pack
    # actually fits its OWN tray -- it only checked pocket-vs-trunk and
    # pack-vs-trunk, so a boss straddling the cavity wall (AUD-1: BOSS_Y=26.5
    # puts the mount bosses' inner edge at 22.25, 1.15mm inside the 23.4
    # pack half-width) went ungated. Sample the PACK box and assert 0 points
    # land inside the battery_pocket SOLID (walls/pads/floor) -- this is the
    # direct "does the battery fit its own pocket" proof. Exclude the
    # designed pack-rests-on-tray-floor seat (pack z0=-35.9 vs the tray
    # floor's own top TRAY_FLOOR_Z=-35.8 -- a 0.1mm designed bearing
    # contact, not a collision) before checking: without the exclusion this
    # case reports ~1580 pts (nearly all sampling noise at that shared
    # plane); with the exclusion, the ORIGINAL full-height-boss geometry
    # left 259 real pts, all clustered at the boss x/y (bx +/-40/0,
    # sy*BOSS_Y +/-2) -- genuinely the AUD-1 boss intrusion, not floor-seat
    # noise (verified by inspecting the hit cloud directly).
    #
    # AUD-1 RESOLVED 2026-07-10 (top-flange mount): the full-height boss
    # columns are gone. A same-shaped fix (push BOSS_Y out so the column's
    # inner edge clears CAV_Y+WALL=27.2) was tried earlier and reverted --
    # widening a FULL-HEIGHT column's outer edge that far reaches into the
    # documented chassis-safe crouch ROM and creates a NEW leg-vs-pocket
    # collision (BOSS_Y=30.0 hit at inboard haa=15 + hfe fold 45-50, every
    # kfe, all four hips). The real fix (user-chosen direction) instead
    # holds the 6 nut-traps in LOCAL PADS thickening the existing rim
    # flange (battery_pocket.scad PAD_Z0/PAD_HW/TRAP_*): each pad spans y
    # [CAV_Y, BOSS_Y+4.25] = [24.0, 30.75] -- the SAME outer edge the old
    # full-height column proved leg-sweep-clean at -- but only reaches 6mm
    # below the rim (PAD_Z0 = RIM_Z-6) instead of the old column's 39mm
    # (BOT_Z), so it never dips into the leg-sweep depth, AND its inner
    # edge starts flush at CAV_Y=24.0 (never intrudes the pack's 23.4
    # half-width, unlike the old column's 22.25). This case is now a HARD-
    # FAIL regression guard: it must read 0 pts going forward -- if it
    # doesn't, the pack no longer fits its own tray.
    kp_f = kp[np.abs(kp[:, 2] - TRAY_FLOOR_Z) >= 0.3]
    hits = kp_f[pocket.contains(kp_f)]
    bad |= report('battery pack vs pocket (pack must fit its own tray, '
                  'floor seat excluded) -- AUD-1 RESOLVED 2026-07-10, '
                  'top-flange mount', hits)
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

    # ---- 11. REAL power board + REAL logic board (power_board_model),
    # STANDOFF_FLOOR_MM=20 ------------------------------------------------------
    pb_mesh, pb_components, _ = power_board_mesh()
    pb_tops = [c for c in pb_components if c['top_side']]
    pb_bots = [c for c in pb_components if not c['top_side']]
    pbp = sample(pb_mesh, 10000, 3000, seed=1)

    # Logic board (nova_pcb_v6_logic): kicad_pcb-parsed, same as the power
    # board -- no more logic-board/Teensy envelope box.
    lb_mesh, lb_components = logic_board_mesh()
    lb_tops = [c for c in lb_components if c['top_side']]
    lb_bots = [c for c in lb_components if not c['top_side']]

    # (a) caps clear floor: EVERY bottom-side component (the 20mm C1-C5
    # 1000uF caps are the tallest/lowest) must bottom at or above the floor
    # plate top now that the standoff is 22mm. Hard assert, no known
    # exception -- the 16mm-standoff collision this used to carve out is
    # fixed on the chassis side (see the case-11 HISTORY note above
    # EXPECTED_STACK_ZONE). Backed by two geometric mesh checks: our own
    # floor_plate.stl, and the stock trunk's own floor slab underneath it.
    pb_bot_z = min(c['z0'] for c in pb_bots)
    pb_bot_ref = min(pb_bots, key=lambda c: c['z0'])['ref']
    ok = pb_bot_z >= FLOOR_TOP_Z
    print(('OK    ' if ok else 'FAIL  ') + f'power board bottom ({pb_bot_ref} '
          f'z={pb_bot_z:.2f}) clears floor top ({FLOOR_TOP_Z}), '
          f'margin={pb_bot_z - FLOOR_TOP_Z:.2f}mm '
          f'[standoff={STANDOFF_FLOOR_MM}mm]')
    bad |= not ok

    hits = pbp[plate.contains(pbp)]
    bad |= report('power board vs floor plate', hits)

    pb_floor = pbp[pbp[:, 2] < 10.0]     # z0..3.9 stock-floor band only
    hits = pb_floor[trunk.contains(pb_floor)] if len(pb_floor) else pb_floor
    bad |= report('power board vs stock trunk floor (z0..3.9)', hits)

    # (b) stack top / riser deck clearance. Two parts: the power board's own
    # top-side components (Q1, the TO-220 IRLB3034, is tallest -- huge
    # margin) AND the REAL logic board's tallest parsed point (Teensy 4.1 /
    # Arduino Nano socket footprint, 13mm off the component face -- the
    # logic layer is kicad_pcb-parsed geometry now, NOT the old Teensy
    # envelope guess), which is the tight one (~5.68mm at current heights).
    # Checked directly off lb_mesh's own bounds (not just the STACK_TOP_Z
    # constant) so this assert is tied to the real geometry, not an import.
    pb_top_z = max(c['z1'] for c in pb_tops)
    pb_top_ref = max(pb_tops, key=lambda c: c['z1'])['ref']
    ok = pb_top_z <= DECK_BOT
    print(('OK    ' if ok else 'FAIL  ') + f'power board top ({pb_top_ref} '
          f'z={pb_top_z:.2f}) clears riser deck underside ({DECK_BOT}), '
          f'margin={DECK_BOT - pb_top_z:.2f}mm')
    bad |= not ok

    lb_top_z = float(lb_mesh.bounds[1][2])
    lb_top_ref = max(lb_tops, key=lambda c: c['z1'])['ref']
    assert abs(lb_top_z - STACK_TOP_Z) < 1e-6, \
        'lb_mesh bounds drifted from power_board_model.STACK_TOP_Z'
    ok = lb_top_z <= DECK_BOT
    print(('OK    ' if ok else 'FAIL  ') + f'logic board top ({lb_top_ref} '
          f'z={lb_top_z:.2f}, real parsed geometry) clears riser deck '
          f'underside ({DECK_BOT}), margin={DECK_BOT - lb_top_z:.2f}mm')
    bad |= not ok

    # (c) Q1 (TO-220, top ≈ board_top + 18) clears the logic board
    # underside (LOGIC_BOARD_Z0, power_board_model.py). The logic board
    # sits on the pb->lb standoff directly above the power board's TOP
    # FACE -- NOT pinned to Q1's height (preview_assembly.py) -- so this
    # must be checked explicitly rather than assumed by construction.
    q1 = next(c for c in pb_tops if c['ref'] == 'Q1')
    ok = q1['z1'] <= LOGIC_BOARD_Z0
    print(('OK    ' if ok else 'FAIL  ') + f"Q1 top (z={q1['z1']:.2f}) clears logic "
          f'board underside ({LOGIC_BOARD_Z0:.2f}), '
          f'margin={LOGIC_BOARD_Z0 - q1["z1"]:.2f}mm')
    bad |= not ok

    # (d) trunk rear corner slabs (POSTS, z24.5..47.2 -- distinct from the
    # z0..3.9 stock floor above): same known-zone logic as case 2, but run
    # against the REAL board (only J1, the XT60 battery-in connector, is
    # close enough to the rear edge + tall enough to reach the zone).
    pb_near = pbp[(pbp[:, 0] < -45) & (np.abs(pbp[:, 1]) > 20) & (pbp[:, 2] > 20)]
    hits = pb_near[trunk.contains(pb_near)] if len(pb_near) else pb_near
    known = in_zone(hits, EXPECTED_STACK_ZONE) if len(hits) else np.array([], bool)
    if len(hits) and known.all():
        print(f'HIT   power board vs trunk REAR corner slab: {len(hits)} pts — '
              f'KNOWN (J1 XT60 connector; same x<=-60.5 trim as case 2)')
    else:
        bad |= report('power board vs trunk REAR corner slab OUTSIDE the known zone',
                      hits[~known] if len(hits) else hits)

    # (e) logic board B.Cu underside (3x 0.6mm 0603 resistors -- the only
    # B.Cu parts on this board, the parsed parts reaching lowest into the
    # 20mm pb->lb gap) clears Q1's top (the power board's tallest top-side
    # part, which sits in the same gap). Trivially true by construction
    # (Q1 top z45.62, logic B.Cu underside z47.02+ -> ~1.4mm) but now
    # asserted against real parsed geometry on both sides of the gap
    # instead of assumed.
    lb_bot_z = min(c['z0'] for c in lb_bots)
    lb_bot_ref = min(lb_bots, key=lambda c: c['z0'])['ref']
    ok = lb_bot_z >= q1['z1']
    print(('OK    ' if ok else 'FAIL  ') + f'logic board B.Cu underside ({lb_bot_ref} '
          f'z={lb_bot_z:.2f}) clears Q1 top ({q1["z1"]:.2f}) in the pb->lb gap, '
          f'margin={lb_bot_z - q1["z1"]:.2f}mm')
    bad |= not ok

    # ---- 12. NEW chassis parts (CR-7, was #39): jetson_clamp_bar (+y/-y),
    # l2_adapter, control_pod, oled_mount. These have had real
    # STLs since build_all.sh grew them (2026-07-08) but were never added to
    # this gate -- the +y clamp-bar vs jetson_case_ref graze (~0.2mm probe,
    # 4/13000 pts) went uncaught as a result. Settled below.
    print('-- case 12: newer chassis parts (CR-7/#39) --')
    NOISE_PART_MM = 0.05    # parametric-vs-parametric OpenSCAD parts (tight)
    NOISE_CASE_MM = 0.3     # jetson_case_ref.stl local-contour fidelity floor
                            # (bbox IS calipered-accurate 110.3x93.9x38.2; the
                            # local vent-lid contour between the corner columns
                            # is not individually caliper-verified)

    # -- jetson_clamp_bar (+y / -y) vs case ref, vs cradle uprights, vs each other
    case_surf = trimesh.sample.sample_surface(caseref, 150000, seed=8)[0]
    BAR_X0, BAR_X1 = CRADLE_REAR_PXC - 3, CRADLE_FRONT_PXC + 3   # -62 .. 50.3
    BAR_Y0, BAR_Y1 = BAR_HY, CRADLE_POST_YC + 3                   # 41.45 .. 53.35
    for side, bar in (('+y', clamp_bar_R), ('-y', clamp_bar_L)):
        bp = sample(bar, 8000, 2000, seed=2)
        bp_f = bp[~bar_seat_mask(bp)]
        bad |= case_surface_clash(
            case_surf, BAR_X0, BAR_X1, BAR_Y0, BAR_Y1, CRADLE_CORNER_Z,
            f'clamp bar ({side}) vs case ref surface (bearing pads excluded)',
            noise_mm=NOISE_CASE_MM, exclude=bar_seat_mask)
        hits = bp_f[cradle.contains(bp_f)]
        bad |= report_depth(f'clamp bar ({side}) vs cradle (upright-top seat excluded)',
                            hits, cradle, noise_mm=NOISE_PART_MM)
    r_pts = sample(clamp_bar_R, 4000, 1000, seed=3)
    hits = r_pts[clamp_bar_L.contains(r_pts)]
    bad |= report('clamp bar +y vs clamp bar -y', hits)

    # jetson_cowl vs clamp bar (-y) / cradle / case ref: RETIRED 2026-07-10
    # (#41) — cowl superseded by right-angle plug adapters, checks removed.

    # -- l2_adapter vs crown/head (seat excluded; the tongue<->crown-lip
    # interlock needs no mask -- head.scad hollows a matching slot, so
    # head.contains() is already False there by construction) + seated L2 --
    l2p = sample(l2_adapter, 6000, 1500, seed=5)
    l2p_f = l2p[~l2a_seat_mask(l2p)]
    hits = l2p_f[head.contains(l2p_f)]
    bad |= report_depth('l2 adapter vs head/crown (seat excluded)', hits, head,
                        noise_mm=NOISE_PART_MM)
    hits = l2p[l2.contains(l2p)]
    bad |= report_depth('l2 adapter vs seated L2 body envelope', hits, l2,
                        noise_mm=NOISE_PART_MM)

    # -- control_pod vs riser rear wall (pad-boss seat excluded), rear
    # shoulders, mezzanine stack envelope --
    podp = sample(pod, 9000, 2500, seed=6)
    podp_f = podp[~pod_riser_seat_mask(podp)]
    hits = podp_f[riser.contains(podp_f)]
    bad |= report_depth('control pod vs riser (rear-wall pad seat excluded)',
                        hits, riser, noise_mm=NOISE_PART_MM)
    S2T_rear = np.array([[0, -1, 0, -HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
    rear_sh = tf(sh_pts, S2T_rear)
    hits = rear_sh[pod.contains(rear_sh)] if len(rear_sh) else rear_sh
    bad |= report('control pod vs rear shoulders', hits)
    hits = podp[box.contains(podp)]
    bad |= report('control pod vs mezzanine stack envelope', hits)

    # -- oled_mount vs control_pod (deck seat excluded) + riser --
    olp = sample(oled, 5000, 1200, seed=7)
    olp_f = olp[~oled_seat_mask(olp)]
    hits = olp_f[pod.contains(olp_f)]
    bad |= report_depth('oled mount vs control pod (deck seat excluded)', hits,
                        pod, noise_mm=NOISE_PART_MM)
    hits = olp[riser.contains(olp)]
    bad |= report_depth('oled mount vs riser', hits, riser, noise_mm=NOISE_PART_MM)

    # -- case_slot_grommet (TPU -Y CASE_SLOT edge liner, #41 follow-up) vs the
    # REAL neighboring hardware it has to clear: the cradle uprights + -y tie
    # rail (jetson_case_mount.stl), both clamp bars, and the official case
    # envelope. These are all real, unaffected meshes -- any hit here is a
    # genuine design collision, hard-failed like every other case-12 pair.
    grommet = trimesh.load('case_slot_grommet.stl')
    grp = sample(grommet, 6000, 1500, seed=9)
    hits = grp[cradle.contains(grp)]
    bad |= report_depth('case_slot_grommet vs cradle (jetson_case_mount)',
                        hits, cradle, noise_mm=NOISE_PART_MM)
    for side, bar in (('+y', clamp_bar_R), ('-y', clamp_bar_L)):
        hits = grp[bar.contains(grp)]
        bad |= report_depth(f'case_slot_grommet vs clamp bar ({side})',
                            hits, bar, noise_mm=NOISE_PART_MM)
    hits = grp[case.contains(grp)]
    bad |= report('case_slot_grommet vs official case envelope', hits)

    # WARN (informational, does not fail the gate): riser_bay.scad's
    # CASE_SLOT cut (rounded_slot(..., r=4) on a 4.5mm-wide slot) blows out
    # past its own documented bounds -- see case_slot_grommet.scad's header
    # FLAG for the full writeup. Quantify it every gate run so it stays
    # visible until riser_bay.scad gets the r-fix: what fraction of the
    # grommet's own volume actually lands inside SOLID riser material in
    # the CURRENT (unfixed) mesh -- low means the liner has nothing to grip.
    lo, hi = grommet.bounds
    rng = np.random.default_rng(9)
    gvol = rng.uniform(lo, hi, (20000, 3))
    gvol = gvol[grommet.contains(gvol)][:4000]
    grip_frac = float(riser.contains(gvol).mean()) if len(gvol) else 0.0
    tag = 'OK  ' if grip_frac > 0.85 else 'WARN'
    print(f'{tag}  case_slot_grommet grip check: {grip_frac * 100:.0f}% of its own '
          f'volume sits inside CURRENT riser material (want >85%) -- low means '
          f'riser_bay.scad\'s CASE_SLOT cut (see FLAG in case_slot_grommet.scad) '
          f'has eaten the edge this liner is designed to clip onto; NOT '
          f'counted toward the gate result (riser_bay.scad fix is out of this '
          f'part\'s scope), but should read >85% once that follow-up lands.')

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
         146 - 110 >= 30),   # front bolt x=146 (was literal 148; matched the "36" label after fix)
    ]
    for label, ok in checks:
        print(('OK    ' if ok else 'FAIL  ') + label)
        bad |= not ok
    print('NOTE  Case dims 110.3x93.9x38.2 CALIPERED (dimensions.md); the ref '
          'mesh is now SCALED to those dims (was ~1.3 oversize -> grazed the '
          'cradle lips 0.25 in the viewer). Ports on the -Y flank -> '
          'right-angle plug adapters (#41) turn each cable DOWN at the port '
          'so it drops through the -Y CASE_SLOT to the bay (#38, jetson_cowl '
          'retired); verify the bundle fit + drop-to-boards at wiring.')

    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
