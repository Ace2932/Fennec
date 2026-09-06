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
     sides of the gap instead of assumed; (f) the 4 floor->power-board
     mezzanine standoffs (M3x20, Ø5 posts, AUD-4) are now modeled as real
     cylinder geometry and checked against Q1 + C1-C6 (the tightest
     top-side and bottom-side parts) — Q1 is XY-closest to the
     (-40.5,-33) post (~1.55mm across-flats / ~1.16mm across-corners,
     both clear) plus a volumetric backstop vs the full board mesh.
 13. DERIVED TRUNK (trunk.scad / trunk_build.py) hole alignment: samples
     each mating fastener's own axis (battery mount x6 — battery_pocket.scad
     BOSS_X/BOSS_Y; shoulder-foot CSK x4 — leg_v6/shoulder.scad
     FOOT_BOLT_X/Y; shoulder-flange end-wall x8 — ALREADY-STOCK holes,
     regression guard only) and asserts trunk.stl (the printed, holed part)
     is OPEN, not solid, all along it — the actual proof the modeled bores
     land where the bolts go, not just that a hole exists somewhere.
 12. CR-7 (was #39): the newest chassis parts, never gated before now —
     jetson_clamp_bar (+y/-y mirror), l2_adapter, control_pod.
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
 14. HEAD-BOSS <-> NECK-BRACKET bolt-axis alignment (AUD-12, 2026-07-10):
     the head.scad USB-C column channel used to run straight through the
     boss, voiding the +y pair of the 4 rear-boss->bracket-wall M3 heat-set
     inserts (0mm floor/wall at HM_Y=10, z89/100) — cases 7+8 only checked
     head/bracket ENVELOPES against the rest of the chassis, never each
     other's own fastener bores, so this went ungated. Same axis-probe
     pattern as case 13, both directions: head boss must be SOLID at the
     insert floor, neck-bracket wall must be OPEN at the matching axis.
 15. LA-22a (2026-07-11, fault audit): head_ear/head_ear_L bolt-axis (same
     axis-probe pattern as 13/14) + L2/D456 clearance; skid_rail key vs
     battery_pocket recess alignment (both files independently cite the
     same trunk x -43/+58 key centers -- this is the first thing that
     actually checks it); a mirrored-LEFT haa roll sweep (leg assembly vs
     shoulder + shoulder_plate_L.stl) -- leg_v6/check_fit.py's own
     shoulder_checks() only ever swept the RIGHT horn plate.
 16. Neck-bracket cable slot <-> shoulder deck window continuity (2026-07-16
     review): the head/L2/D456 cable drops from neck_bracket.scad's
     base-plate slot straight down through the (front) shoulder's own deck
     lightening window -- two independently-authored voids, in different
     parts and different local frames, that no case before this one ever
     checked against each other. A hand-transform (shoulder-local sx =
     world_y, sy = world_x - HIP_FA, sz = world_z - HIP_Z -- the same
     inverse shoulder.scad's own NECK_HS_XY derivation comment documents)
     found only ~0.8mm margin at one edge. This case makes that transform
     an automated, regression-caught assert: FAIL if the slot footprint
     misses the window outright, WARN (not a hard fail) at the known
     ~0.8mm-margin boundary.

Exit 0 = clean, 1 = interference. Run via build_all.sh after every change.
"""
import pathlib
import re
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cad_assets import LEG_V6, asset  # noqa: E402  (path insert must be first)
import cad_contains  # noqa: E402  (#195 propagation -- installed in main())

from power_board_model import (power_board_mesh, logic_board_mesh, FLOOR_TOP_Z,
                                STANDOFF_FLOOR_MM, LOGIC_BOARD_Z0, STACK_TOP_Z,
                                BOARD_BOTTOM_Z)
import power_board_model as pbm
from trunk_build import BATT_BOSS_X, BATT_BOSS_Y, FOOT_XY

# Vendored / in-repo since #166. These were absolute /Users paths, two of them
# into the ROOT repo (a different git repo), so this gate ran on exactly one
# machine and never in CI — on the project whose dominant bug class is geometry
# that is individually right and wrong at the seam.
TRUNK = str(asset('SM3_Frame_ChassisTrunk.stl'))
SERVO = str(asset('servo.stl'))
LEG = str(LEG_V6)

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
#: minimum leg-to-oled_tray clearance (#35). 5mm, not a hair over whatever the
#: sweep happens to measure: the sweep is a GRID, so the true worst pose falls
#: between samples, and the servo horn backlash the trot work characterises is
#: itself worth a couple of mm at the foot.
TRAY_LEG_MIN_MM = 5.0

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

# ---- case 11f: mezzanine floor->power-board standoff hardware (AUD-4,
# 2026-07-10) -- case 11 checked the boards vs the trunk but never modeled
# the physical standoff hardware, so the audit's Q1-vs-standoff near-miss
# went ungated. 4x M3x20, Ø5 posts (radius 2.5mm "across flats" -- the
# hex-flat clocking is a real assembly choice, not fixed by this model, so
# the gate also reports the worst-case "across corners" radius, a hex
# whose flat-to-flat = Ø5: across-corners = across-flats * 2/sqrt(3)),
# 20mm tall (FLOOR_TOP_Z -> BOARD_BOTTOM_Z, power_board_model.py). XY
# cross-checked against floor_plate.scad's STK_X=[-40.5,33.5] / STK_Y=33
# mezzanine-pilot pattern (74 x 66, power_v2 fab pattern) -- both files
# must stay in sync.
STANDOFF_XY = [(-40.5, -33), (-40.5, 33), (33.5, -33), (33.5, 33)]
STANDOFF_R_FLATS = 2.5                                  # Ø5, as modeled
STANDOFF_R_CORNERS = STANDOFF_R_FLATS * 2 / np.sqrt(3)  # hex worst case, ~2.887mm


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
    """Designed l2_adapter <-> crown-top seat (z=L2A_SEAT_Z): the main
    plate's flat bottom face only, x104..146 y-24..24 (l2_adapter.scad's
    main plate `translate([104, -24, Z0]) cube([42, 48, T])`) -- the ONLY
    part of l2_adapter that actually rests on the crown top. The front
    tongue (x146..158, thin 2mm slab) does NOT touch the crown -- it
    slides UNDER a crown lip through a matching slot head.scad hollows
    out, so head.contains() is already False there by construction and
    needs no mask. AUD-6 (2026-07-10): tightened from a z-band-only mask
    (no x/y bound at all -- the loosest mask in this file) to the real
    seat footprint, so anything proud elsewhere on the z=L2A_SEAT_Z plane
    is no longer silently excluded."""
    near_z = np.abs(p[:, 2] - L2A_SEAT_Z) < 0.6
    near_xy = (p[:, 0] > 103.4) & (p[:, 0] < 146.6) & (np.abs(p[:, 1]) < 24.6)
    return near_z & near_xy



# ---- leg assembly point cloud (leg_v6 gate composition, coax frame) --------
def rot(deg, axis, point=None):
    return trimesh.transformations.rotation_matrix(
        np.radians(deg), axis, point)


def tf(pts, M):
    return trimesh.transform_points(pts, M)


def near_bbox(pts, target, margin=0.5):
    """Pre-filter `pts` to the ones that could possibly be inside `target`.

    #47 REDUX (2026-07-31). The crouch sweep used to hand-type a literal bbox
    per target as a speed pre-filter before target.contains(). A pre-filter is
    lossless only if it is a SUPERSET of the target's own bounding box -- a
    point outside that box cannot be inside the mesh, but a point the window
    drops while the box still contains it is evidence thrown away.

    Six of the seven hand-typed windows were supersets. The seventh, `head`,
    was not: window x100..146 / |y|<40 / z82..130 against a head spanning
    x71..160 / |y|<=60 / z84..132.5 -- clipping the target by 43mm in x and
    40mm in y. Measured across all 1120 sweep poses it admitted ZERO points,
    so the head-vs-leg check had never once executed. #47 diagnosed exactly
    this in 2026-07 and the fix was to write head_cap_sweep.py BESIDE it; the
    dead window itself was left in place and kept reporting green.

    Deriving the window from the target instead of typing it removes the whole
    failure mode: it cannot clip, it cannot go stale when geometry moves, and
    it is FASTER here (every superset window admitted more points than the
    real bbox does). `margin` only guards float edge effects on the boundary.
    """
    lo, hi = target.bounds
    m = np.asarray(pts)
    keep = np.all((m >= lo - margin) & (m <= hi + margin), axis=1)
    return m[keep]


# ---- LA-22a: mirrored-LEFT shoulder sweep -----------------------------------
def left_shoulder_sweep_check():
    """leg_v6/check_fit.py's shoulder_checks() only ever swept the RIGHT leg
    assembly (coax_R/femur_R/tibia_R + shoulder_plate.stl, the R horn plate)
    against shoulder.stl -- shoulder_plate_L.stl (the genuinely distinct
    mirrored horn-plate part that bolts the LEFT hip to the SAME shoulder
    crossmember; shoulder.scad is "one crossmember per trunk end", hips at
    x=+-39.05, heat-set bores "4x per side") had ZERO gate coverage.

    Reuses the RIGHT leg point cloud (same coax/femur/knee_arm/tibia meshes,
    same placement transforms as leg_v6/check_fit.py's shoulder_checks()) and
    X-mirrors the WHOLE assembled cloud before placing it at the LEFT hip --
    the same "chirality is irrelevant for an envelope check" precedent this
    file already uses for the crouch sweep's MIRX (see coax_to_trunk_bases()
    docstring / case 4). shoulder_plate_L.stl is the one real, non-mirrored
    input under test here."""
    bad = False
    sh = trimesh.load(f'{LEG}/shoulder.stl')
    pl_L = trimesh.load(f'{LEG}/shoulder_plate_L.stl')
    coax = trimesh.load(f'{LEG}/coax_R.stl')
    femur = trimesh.load(f'{LEG}/femur_R.stl')
    tibia = trimesh.load(f'{LEG}/tibia_R.stl')
    arm = trimesh.load(f'{LEG}/knee_arm.stl')
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.75]))
    servo = trimesh.load(SERVO)
    servo.apply_translation([-12.5, 0, 0])
    pts0 = trimesh.sample.sample_surface(servo, 6000, seed=0)[0]

    ry = rot(-90, [0, 1, 0]); rx = rot(90, [1, 0, 0])
    coax_pose = ry @ rx
    HFE_Y, HFE_Z, FEMUR_MID = 11.6, -9.5, 33.8
    M_f = (trimesh.transformations.translation_matrix([FEMUR_MID, HFE_Y, HFE_Z])
           @ rot(180, [0, 0, 1]) @ rot(90, [0, 1, 0]))
    T_t = trimesh.transformations.translation_matrix([106.9, 0, 0])
    leg = np.vstack([
        trimesh.sample.sample_surface(coax, 6000, seed=0)[0],
        tf(pts0, coax_pose),
        tf(trimesh.sample.sample_surface(femur, 4000, seed=0)[0], M_f),
        tf(trimesh.sample.sample_surface(arm, 1000, seed=0)[0], M_f),
        tf(trimesh.sample.sample_surface(tibia, 3000, seed=0)[0], M_f @ T_t),
    ])
    # X-mirror the whole RIGHT leg cloud -> a valid LEFT leg envelope
    MIRX = np.eye(4); MIRX[0, 0] = -1
    leg_L = tf(leg, MIRX)

    # coax frame -> shoulder frame: mirror Y (same as the R sweep in
    # leg_v6/check_fit.py's shoulder_checks()), then place at the LEFT hip
    MIRY = np.eye(4); MIRY[1, 1] = -1
    base = trimesh.transformations.translation_matrix([-HIP_LAT, 0, 0]) @ MIRY
    print('-- LA-22a: LEFT haa roll sweep (mirrored leg assembly vs shoulder + shoulder_plate_L) --')
    for ang in (-45, -40, -25, 0, 25, 40, 45):
        S = rot(ang, [0, 1, 0], [-HIP_LAT, 0, 0])
        p = tf(tf(leg_L, base), S)
        # exclude the designed disc/boss interface about the haa axis
        keep = np.sqrt((p[:, 0] + HIP_LAT) ** 2 + p[:, 2] ** 2) > 13
        p = p[keep]
        n = int(sh.contains(p).sum()) + int(pl_L.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 40: bad = True   # beyond 40 = documenting stops
        print(f'   {status} haa {ang:+4d}deg: {n} pts')
    return bad


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
    LEFT side is a mirror (real: coax_L/femur_L/tibia_L are mirrored parts).

    REAR = THE FRONT PLACEMENT YAWED 180 deg ABOUT Z — CORRECTED 2026-07-26.
    Two earlier revisions were both wrong, in opposite directions, and the
    physical option (a plain 180 deg YAW: det +1, a real rotation any part can
    take) was never on the table:
      * pre-2026-07-25 carried `end` inside the rotation AND the lateral row,
        which came out an improper placement of the R leg at the rear-R corner;
      * 2026-07-25 replaced it with a PURE TRANSLATION on the grounds that "a
        reflection is not a placement any physical part can take" — true, but
        the fix for an improper placement is the missing ROTATION, not dropping
        the fore-aft flip.

    WHY A YAW IS FORCED (all repo numbers): shoulder.scad is ONE part at both
    ends ("SAME part both ends; print 2") and its flange (shoulder-local
    y -77.7) bolts to the trunk's END FACE (x +-63.5, trunk.stl bounds) — that
    is what puts the hip station at +-HIP_FA in the first place (63.5 + 77.7 =
    141.2). Under a pure translation the REAR flange lands at x = -218.9, i.e.
    155 mm behind the trunk it is bolted to, and the rear coax's horn face ends
    up at x = -123.4 while the rear shoulder's own horn plane is at -158.9.
    THIS FILE ALREADY PLACES THE SHOULDER CORRECTLY (cases 3 + 6 keep `end` in
    the rotation, so the rear flange lands on the end face) — the translated
    rear LEG was therefore bolted to a shoulder the same gate had placed the
    other way round. (Those two shoulder placements also swap the lateral row
    without the `end` sign; harmless, because shoulder.stl is mirror-symmetric
    in its own sx — every feature is cut for sx = +-1 — so the placed solid is
    identical either way. The LEG is NOT sx-symmetric, which is why it matters
    here and not there.)

    MEASURED consequences (both verified against the real meshes, 2026-07-26):
      * the hfe axis sits 11.6 mm TOWARD THE TRUNK at BOTH ends (x +-129.6);
        the translated rear put it 11.6 mm the other way (-152.8), i.e. 23.2 mm
        of rear leg station error. NB +-129.6 is also what the URDF/MJX hip
        grid should carry for the pitch axes (they still use +-141.2 with a
        zero haa->hfe fore-aft term — see dimensions.md "Hip grid").
      * leg CHIRALITY PAIRS DIAGONALLY: the +y corner takes coax_R at the FRONT
        and coax_L at the REAR (and vice versa). Still two parts, two of each,
        but NOT the same part at both ends of one side. MIRX below is therefore
        keyed on the sign of the shoulder-local station (sx < 0), which under
        the yaw is the diagonal, not the side.
      * front and rear DO share an hfe window (they are mirror images), so the
        "the two ends do not share a window" note this docstring used to carry
        was an artefact of the translated placement. Re-measured with
        hfe_envelope.py's own targets + 5 mm proximity rule at haa 0: the rear
        interval comes out equal to the front's ([-94, +66] at kfe -109,
        [-94, +72] at kfe 0, leg-local sign) instead of the flat [-76, +94]
        the shipped table carries at every kfe.
      * => rom_envelope_table.py's REAR rows are STALE and ~5-10 deg LOOSE on
        the constrained side, and they lost their kfe dependence entirely.
        Regenerate (needs the real servo.stl) before trusting them; the runtime
        posture gate is now the SOLE chassis protection (limits.py loosened the
        hfe scalar to mechanical +-86 on 2026-07-25).
    """
    T = trimesh.transformations.translation_matrix
    MIR = np.eye(4); MIR[1, 1] = -1                    # coax -> shoulder
    bases = []
    for corner_y in (1, -1):                           # world +y / -y hip
        for end in (1, -1):                            # front / rear
            # shoulder -> trunk. end=+1 is the front placement, unchanged;
            # end=-1 is that same placement yawed 180 deg about Z (both rows
            # carry `end`), which lands the flange on the trunk end face.
            S2T = np.array([[0, end, 0, end * HIP_FA],
                            [end, 0, 0, 0],
                            [0, 0, 1, HIP_Z],
                            [0, 0, 0, 1.0]])
            # world_y = end * sx, so hold the CORNER fixed and let the
            # shoulder-local station follow the yaw.
            sx = end * corner_y * HIP_LAT
            MIRX = np.eye(4)
            if sx < 0:
                MIRX[0, 0] = -1                        # mirror the leg itself
            bases.append((f'{"F" if end > 0 else "R"}{"R" if corner_y > 0 else "L"}',
                          S2T @ T([sx, 0, 0]) @ MIRX @ MIR))
    return bases


def _scad_num(path, name):
    """Read a top-level numeric constant out of a .scad file.

    Same idiom, and same reason, as nova_locomotion/test/test_urdf_sync.py: a
    constant retyped into a second file is a SEAM, and seams are this repo's
    dominant bug class. The SW1 envelope below is derived from shoulder.scad so
    that moving the cutout moves the thing that checks the cutout.
    """
    m = re.search(rf'\b{re.escape(name)}\s*=\s*(-?[0-9.]+)\s*;',
                  pathlib.Path(path).read_text())
    if not m:
        raise AssertionError(f'{name} not found in {path} -- '
                             'the SW1 envelope cannot be derived')
    return float(m.group(1))


def _sw1_body_box(clr=2.0):
    """Trunk-frame envelope of the SW1 switch body on the FRONT shoulder (#377).

    Derived from shoulder.scad, never retyped. The switch seats on the wall's
    forward face (shoulder-local y = REAR_W1) and hangs SW1_DEPTH rearward;
    `clr` pads the cutout footprint for the wings and body flare.
    """
    sc = f'{LEG}/shoulder.scad'
    g = lambda n: _scad_num(sc, n)   # noqa: E731
    y1, depth, proud = g('REAR_W1'), g('SW1_DEPTH'), g('SW1_PROUD')
    x, w = g('SW1_X'), g('SW1_W')
    z, h = g('SW1_Z'), g('SW1_H')
    # FULL envelope: body BEHIND the panel *and* the bezel PROUD of it. The
    # first version of this box stopped at the panel face, which is exactly
    # where the interesting volume starts -- the bezel protrudes into the side
    # of the wall the coax sweeps past (0.5mm at the hip stations). Measured
    # 2026-08-15: no leg point enters the centreline footprint in any
    # chassis-safe pose, and no static part does either. This keeps it that way.
    return make_box(y1 - depth + HIP_FA, y1 + proud + HIP_FA,
                    x - w / 2 - clr, x + w / 2 + clr,
                    z - h / 2 - clr + HIP_Z, z + h / 2 + clr + HIP_Z)


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


# ---- floor-thickness gate (#67/#70 blind-spot, 2026-07-12) ------------------
# A blind heat-set bore must leave a floor >= the material minimum between its
# bottom and the next exterior/cavity, or the insert blows through on the
# heat-press. Min by bore dia: M3 (Ø4) -> 1.5mm, M2 (Ø3) -> 1.0mm (fastener-
# schedule.md). Registry = the audit-known bores; extend as bores are added.
# (part, mouth xyz, axis-INTO-part, bore depth, bore dia, label)
FLOOR_MIN = {4.0: 1.5, 3.0: 1.0}
# known-constrained thin floors: WARN (documented), don't fail the gate. A NEW
# thin floor (not listed) DOES fail -> regressions are caught.
ACCEPTED_THIN = {('l2_adapter.stl', 'crown-mount')}  # #70b: 5mm plate + L2 on
    # top + bolt from below -> can't thicken either way; already short insert.
    # Design decision pending (M3x3 insert vs plate redesign).
FLOOR_BORES = [
    ('head.stl',          (77,  10, 131),   (0, 0, -1), 4.2, 4.0, 'ear-pad'),
    ('head.stl',          (77, -10, 131),   (0, 0, -1), 4.2, 4.0, 'ear-pad'),
    ('head.stl',          (83,  10, 131),   (0, 0, -1), 4.2, 4.0, 'ear-pad'),
    ('head.stl',          (83, -10, 131),   (0, 0, -1), 4.2, 4.0, 'ear-pad'),
    ('l2_adapter.stl',    (114,  9, 128),   (0, 0,  1), 4.2, 4.0, 'crown-mount'),
    ('l2_adapter.stl',    (114, -9, 128),   (0, 0,  1), 4.2, 4.0, 'crown-mount'),
    ('battery_pocket.stl',(-35, 27.5, -0.2),(0, 0, -1), 4.2, 4.0, 'pad'),
    ('battery_pocket.stl',(40,  27.5, -0.2),(0, 0, -1), 4.2, 4.0, 'pad'),
    # --- leg parts (first-article, printing) ---
    (f'{LEG}/coax_R.stl',  (15.9, 24.0, 10.4),(0, -1, 0), 6.2, 4.0, 'coax HFE mount'),
    (f'{LEG}/femur_R.stl', (65,  8, 17.75),  (0, 0, -1), 6.2, 4.0, 'knee-arm mount'),
    (f'{LEG}/femur_R.stl', (65, -8, 17.75),  (0, 0, -1), 6.2, 4.0, 'knee-arm mount'),
    (f'{LEG}/femur_R.stl', (75,  8, 17.75),  (0, 0, -1), 6.2, 4.0, 'knee-arm mount'),
    (f'{LEG}/femur_R.stl', (75, -8, 17.75),  (0, 0, -1), 6.2, 4.0, 'knee-arm mount'),
    (f'{LEG}/shoulder.stl',( 51.75, -77.7, -33.05),(0, 1, 0), 6.2, 4.0, 'trunk-flange'),
    (f'{LEG}/shoulder.stl',(-51.75, -77.7, -33.05),(0, 1, 0), 6.2, 4.0, 'trunk-flange'),
    (f'{LEG}/shoulder.stl',( 51.75, -77.7, -14.05),(0, 1, 0), 6.2, 4.0, 'trunk-flange'),
    (f'{LEG}/shoulder.stl',(-51.75, -77.7, -14.05),(0, 1, 0), 6.2, 4.0, 'trunk-flange'),
    (f'{LEG}/shoulder.stl',( 18, -73.7, -22.05),(0, -1, 0), 6.2, 4.0, 'rear-pad'),
    (f'{LEG}/shoulder.stl',(-18, -73.7, -22.05),(0, -1, 0), 6.2, 4.0, 'rear-pad'),
    (f'{LEG}/shoulder.stl',( 18, -73.7, -10.05),(0, -1, 0), 6.2, 4.0, 'rear-pad'),
    (f'{LEG}/shoulder.stl',(-18, -73.7, -10.05),(0, -1, 0), 6.2, 4.0, 'rear-pad'),
    # --- chassis (head boss / riser pod) ---
    ('head.stl', (121,  10, 89),  (1, 0, 0), 6.2, 4.0, 'boss'),
    ('head.stl', (121, -10, 89),  (1, 0, 0), 6.2, 4.0, 'boss'),
    ('head.stl', (121,  10, 100), (1, 0, 0), 6.2, 4.0, 'boss'),
    ('head.stl', (121, -10, 100), (1, 0, 0), 6.2, 4.0, 'boss'),
    # NOTE: riser FLG + shoulder-deck (PLATE_BX/BY) heat-sets are THROUGH-
    # mounts (Ø4 insert bore + a Ø3.4 clearance continuing to the far face for
    # the bolt), NOT blind bores -- no floor to gate; excluded on purpose.
    ('riser_bay.stl', (-66.5, -10, 61), (1, 0, 0), 4.0, 3.0, 'pod M2'),
    ('riser_bay.stl', (-66.5,  10, 61), (1, 0, 0), 4.0, 3.0, 'pod M2'),
    ('riser_bay.stl', (-66.5, -10, 66), (1, 0, 0), 4.0, 3.0, 'pod M2'),
    ('riser_bay.stl', (-66.5,  10, 66), (1, 0, 0), 4.0, 3.0, 'pod M2'),
]


def floor_thickness_check():
    print('-- floor gate (#67/#70): blind heat-set bore floor >= M3 1.5 / M2 1.0 --')
    bad = False
    cache = {}
    for part, mouth, ax, depth, dia, label in FLOOR_BORES:
        if part not in cache:
            cache[part] = trimesh.load(part)
        a = np.asarray(ax, float); a /= np.linalg.norm(a)
        bot = np.asarray(mouth, float) + depth * a
        # scan outward from the bore bottom; floor = the first contiguous solid
        # run. Skip a small leading void (<= GAP_TOL) so a scan point landing
        # exactly on the bore-bottom boundary (void by an EPS) doesn't false-
        # read 0 -- the bug the coax 9.71mm floor exposed.
        ts = np.arange(0.02, 8.0, 0.02)
        ins = cache[part].contains(bot + np.outer(ts, a))
        GAP_TOL = 0.3
        first = next((k for k, i in enumerate(ins) if i), None)
        if first is None or ts[first] > GAP_TOL:
            floor = 0.0
        else:
            last = first
            while last + 1 < len(ins) and ins[last + 1]:
                last += 1
            floor = ts[last] - ts[first] + 0.02
        # 0.05mm tolerance absorbs the scan step + print slop so an AT-spec
        # floor (e.g. the M2 1.0mm minimum) isn't false-flagged.
        thr = FLOOR_MIN[dia]
        ok = floor >= thr - 0.05
        accepted = (part, label) in ACCEPTED_THIN
        tag = 'OK   ' if ok else ('WARN ' if accepted else 'THIN ')
        if not ok and not accepted:
            bad = True
        print(f"{tag} {part} {label} @ {tuple(mouth)}: "
              f"floor {floor:.2f}mm (need >= {thr})"
              + ('  [#70b known-constrained]' if not ok and accepted else ''))
    return bad


# ---- cross-family fastener-overlap gate (#68, blind-spot #3) ----------------
# Two DIFFERENT fastener families on one part must not collide: no fastener of
# family A within (rA + rB) of one from family B. #68: the battery csk (Ø6.8
# head) overlapped the mezzanine standoff foot (Ø5) on floor_plate -- each
# family was internally fine, nothing checked A-vs-B. Pure position+radius,
# no mesh. STANDOFF_XY / STANDOFF_R_CORNERS reused from case 11f above.
BAT_XY = [(bx, sy * 27.5) for bx in (-35, 0, 40) for sy in (1, -1)]  # floor_plate
                          # BAT_X/BAT_Y (#68: -x col now -35); Ø6.8 csk head r3.4
FASTENER_FAMILIES = [
    ('floor_plate', [('battery-csk',   BAT_XY,      3.4),
                     ('mezz-standoff', STANDOFF_XY, STANDOFF_R_CORNERS)]),
]


def cross_family_check():
    print('-- cross-family fastener gate (#68): family-A vs family-B >= rA+rB --')
    bad = False
    for part, fams in FASTENER_FAMILIES:
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                na, pa, ra = fams[i]
                nb, pb, rb = fams[j]
                need = ra + rb
                worst = min(float(np.hypot(ax - bx, ay - by))
                            for ax, ay in pa for bx, by in pb)
                ok = worst >= need - 1e-6
                bad |= not ok
                print(f"{'OK   ' if ok else 'CLASH'} {part}: {na} <-> {nb} "
                      f"min {worst:.2f}mm (need >= {need:.2f})")
    return bad


# ---- case 15: mating-part fastener sides (2026-07-12) ------------------------
# case 13/14 gate the trunk-side bores + the head<->neck-bracket joint. This
# closes the MATING sides of the remaining bolted chassis joints, each verified
# in its OWN part's native frame (shoulder = shoulder-local; neck_bracket/head/
# l2_adapter = world/trunk). Every clearance scan carries a solid-material guard
# (a ring at r+1.2 must read solid) so an empty-space false-CLEAR -- the exact
# trap the leg coax_L mirror bug hit -- can't slip through; every heat-set scan
# proves a real blind bore with solid backing.
#   A shoulder foot-pad M3 clearance (nyloc seats on top)  -> trunk foot CSK (case 13)
#   B shoulder flange end-wall M3 heat-sets (fore-aft +y)  -> trunk stock bores (case 13)
#   C neck_bracket base M3 clearance + shoulder DECK heat-sets (deck hold-down joint)
#   D l2_adapter rear M3 heat-sets + head CROWN clearance + 4x L2-base CSK
SH_STL = f'{LEG}/shoulder.stl'
# shoulder-local (shoulder.scad): foot bolt, neck-deck heat-sets, end-wall heat-sets
SH_FOOT_XY   = [(42, -81.7), (-42, -81.7)]           # FOOT_BOLT_X/Y (both sx)
SH_FOOT_Z    = (-33.8, -30.3)                         # pad clearance span (FOOT_Z0..+THK)
SH_NECK_HS   = [(20, -24.2), (-20, -24.2), (19.5, 4.8), (-19.5, 4.8)]  # NECK_HS_XY
SH_NECK_TOP  = 41.5                                   # DECK_Z1 (bore opens here, -z)
SH_NECK_DEP  = 4.2                                    # NECK_HS_DEPTH
SH_EW_X      = 51.75                                  # TRUNK_HOLE_X
SH_EW_Z      = [-33.05, -14.05]                       # TRUNK_HOLE_Z
SH_FLANGE_Y0 = -77.7                                  # FLANGE_Y0 (bore opens here, +y)
# world/trunk: neck_bracket base bolts, crown clearance, l2_adapter heat-sets/CSK
NB_BOLT_XY   = [(117, 20), (117, -20), (146, 19.5), (146, -19.5)]  # BOLT_XY
NB_BASE_Z    = (79.55, 83.55)                         # DECK_TOP..+BASE_T
CROWN_CLR_XY = [(114, 9), (114, -9)]                  # head.scad L2 rear clearance
CROWN_Z      = (124, 128)                             # CROWN_Z0..+CROWN_T
L2A_HS_XY    = [(114, 9), (114, -9)]                  # l2_adapter rear heat-sets
L2A_Z0       = 128                                    # adapter bottom (bore opens, +z)
L2A_HS_DEP   = 4.2
L2A_CSK_XY   = [(144.5, 18), (144.5, -18), (108.5, 18), (108.5, -18)]  # CTR±18
L2A_CSK_Z    = (128, 133)
HS_D, HS_L   = 4.0, 6.2                               # HEATSET_D / HEATSET_L


def mating_fastener_checks():
    print('-- case 15: mating-part fastener sides (shoulder feet/end-wall, neck-deck, L2-crown) --')
    bad = False
    sh = trimesh.load(SH_STL)
    nb = trimesh.load('neck_bracket.stl')
    hd = trimesh.load('head.stl')
    l2a = trimesh.load('l2_adapter.stl')

    def clear_z(m, cx, cy, zlo, zhi, r, label):
        """Vertical clearance bore: centerline VOID + a ring at r+1.2 SOLID
        (proves a real drilled hole in material, not empty air)."""
        t = np.linspace(zlo + 0.2, zhi - 0.2, 20)
        center = int(m.contains(
            np.column_stack([np.full(20, cx), np.full(20, cy), t])).sum())
        ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        ring = np.column_stack([cx + (r + 1.2) * np.cos(ang),
                                cy + (r + 1.2) * np.sin(ang),
                                np.full(8, (zlo + zhi) / 2)])
        rs = int(m.contains(ring).sum())
        ok = center == 0 and rs >= 4
        print(f'{"OK  " if ok else "FAIL"}  {label}: center_solid={center} ring_solid={rs}/8')
        return not ok

    def pocket(m, cx, cy, top, dirn, depth, label, axis='z', warn_floor=False):
        """Blind heat-set pilot: bore OPEN `depth` from `top` along dirn, with
        SOLID backing just past it. axis='y' scans along +/-Y (cy is the z
        coord). warn_floor: bore must be open but thin/absent backing only
        WARNs (the #70b-style accepted seat-surface floor)."""
        tb = top + dirn * np.linspace(0.3, depth - 0.3, 16)
        if axis == 'z':
            b = np.column_stack([np.full(16, cx), np.full(16, cy), tb])
        else:
            b = np.column_stack([np.full(16, cx), tb, np.full(16, cy)])
        bore = int(m.contains(b).sum())
        tk = top + dirn * np.linspace(depth + 0.4, depth + 2.0, 6)
        if axis == 'z':
            k = np.column_stack([np.full(6, cx), np.full(6, cy), tk])
        else:
            k = np.column_stack([np.full(6, cx), tk, np.full(6, cy)])
        back = int(m.contains(k).sum())
        if warn_floor:
            ok = bore == 0
            note = '' if back >= 3 else ' -- thin floor (#70b accepted seat surface, WARN)'
            print(f'{"OK  " if ok else "FAIL"}  {label}: bore_open={16 - bore}/16 backing={back}/6{note}')
        else:
            ok = bore == 0 and back >= 3
            print(f'{"OK  " if ok else "FAIL"}  {label}: bore_open={16 - bore}/16 backing={back}/6')
        return not ok

    r3 = 3.4 / 2
    # A. shoulder foot-pad clearance (nyloc on top) -- shoulder-local
    for cx, cy in SH_FOOT_XY:
        bad |= clear_z(sh, cx, cy, SH_FOOT_Z[0], SH_FOOT_Z[1], r3,
                       f'A shoulder foot clearance ({cx:+.0f},{cy:.1f})')
    # B. shoulder flange end-wall heat-sets (screws fore-aft from inside trunk)
    for sx in (1, -1):
        for hz in SH_EW_Z:
            bad |= pocket(sh, sx * SH_EW_X, hz, SH_FLANGE_Y0, 1, HS_L,
                          f'B shoulder end-wall heat-set x={sx * SH_EW_X:+.2f} z={hz}',
                          axis='y')
    # C1. neck_bracket base bolts clearance -- world
    for bx, by in NB_BOLT_XY:
        bad |= clear_z(nb, bx, by, NB_BASE_Z[0], NB_BASE_Z[1], r3,
                       f'C neck-bracket base bolt ({bx},{by:+.1f})')
    # C2. shoulder deck heat-sets receiving them (blind, backed) -- shoulder-local
    for x, y in SH_NECK_HS:
        bad |= pocket(sh, x, y, SH_NECK_TOP, -1, SH_NECK_DEP,
                      f'C shoulder deck heat-set ({x},{y})')
    # D1. head crown clearance for the 2 rear L2-adapter bolts -- world
    for cx, cy in CROWN_CLR_XY:
        bad |= clear_z(hd, cx, cy, CROWN_Z[0], CROWN_Z[1], r3,
                       f'D crown clearance ({cx},{cy:+d})')
    # D2. l2_adapter rear heat-sets (thin seat-floor above = #70b, WARN)
    for cx, cy in L2A_HS_XY:
        bad |= pocket(l2a, cx, cy, L2A_Z0, 1, L2A_HS_DEP,
                      f'D l2-adapter heat-set ({cx},{cy:+d})', warn_floor=True)
    # D3. l2_adapter 4x L2-base CSK (bolts the sensor on the bench)
    for cx, cy in L2A_CSK_XY:
        bad |= clear_z(l2a, cx, cy, L2A_CSK_Z[0], L2A_CSK_Z[1], r3,
                       f'D l2-adapter L2 CSK ({cx},{cy:+d})')
    return bad


# ---- case 16: neck-bracket cable slot <-> shoulder deck window (2026-07-16
# review) -----------------------------------------------------------------
# neck_bracket.scad: translate([128, -7, DECK_TOP-EPS]) cube([18, 14,
# BASE_T+2*EPS]) -- the L2/head cable-drop slot cut through the base plate,
# world footprint x 128..146, y -7..7 (at the deck-top interface plane,
# z=DECK_TOP=79.55; neck_bracket.scad's own header comment already proves
# DECK_TOP(79.55) - HIP_Z(38.05) = 41.5 = shoulder.scad's DECK_Z1 exactly,
# so the two parts' z-bands coincide and only the XY footprint needs a
# fresh check here).
NECK_SLOT_WORLD_X = (128, 146)
NECK_SLOT_WORLD_Y = (-7, 7)
# shoulder.scad: translate([-16, -14, DECK_Z0-1]) cube([32, 26,
# DECK_Z1-DECK_Z0+2]) -- the deck lightening/vent window between the hips,
# shoulder-local x -16..16, y -14..12 (z 34..~42.5, the deck slab band).
SH_WINDOW_X = (-16, 16)
SH_WINDOW_Y = (-14, 12)


def neck_slot_shoulder_window_check():
    """FIX 3 (2026-07-16 review): the head/L2/D456 cable falls from the
    neck_bracket base-plate slot straight into the FRONT shoulder's own deck
    lightening window -- two independently-authored voids that were never
    checked against each other. Transform the neck-bracket slot's world
    footprint into shoulder-local using the SAME inverse shoulder.scad's own
    NECK_HS_XY comment documents for the FRONT placement (end=+1: sx =
    world_y, sy = world_x - HIP_FA, sz = world_z - HIP_Z), then assert the
    transformed footprint lands fully inside the window, reporting the
    margin on every side. FAIL if any margin < 0 (the aperture misses the
    window -- the cable pinches on solid deck material); WARN (does not fail
    the gate) if the worst margin < 1.0mm -- the known-tight boundary this
    review found (~0.8mm at the -y edge) is real but not yet a hard failure,
    flagged so a future window/slot shrink regresses loudly instead of
    silently."""
    print('-- case 16: neck-bracket cable slot vs shoulder deck window continuity --')
    bad = False
    sx_lo, sx_hi = NECK_SLOT_WORLD_Y                       # sx = world_y
    sy_lo = NECK_SLOT_WORLD_X[0] - HIP_FA                  # sy = world_x - HIP_FA
    sy_hi = NECK_SLOT_WORLD_X[1] - HIP_FA
    margins = {
        f'-x (window {SH_WINDOW_X[0]})': sx_lo - SH_WINDOW_X[0],
        f'+x (window {SH_WINDOW_X[1]})': SH_WINDOW_X[1] - sx_hi,
        f'-y (window {SH_WINDOW_Y[0]})': sy_lo - SH_WINDOW_Y[0],
        f'+y (window {SH_WINDOW_Y[1]})': SH_WINDOW_Y[1] - sy_hi,
    }
    for label, m in margins.items():
        print(f'      margin {label}: {m:+.2f}mm')
    worst_label = min(margins, key=margins.get)
    worst = margins[worst_label]
    if worst < 0:
        tag = 'FAIL'
        bad = True
    elif worst < 1.0:
        tag = 'WARN'
    else:
        tag = 'OK  '
    print(f'{tag}  neck slot (shoulder-local x[{sx_lo:.1f},{sx_hi:.1f}] '
          f'y[{sy_lo:.1f},{sy_hi:.1f}]) vs window (x{SH_WINDOW_X} y{SH_WINDOW_Y}): '
          f'worst margin {worst:+.2f}mm at {worst_label}'
          + ('  -- KNOWN TIGHT BOUNDARY (2026-07-16 review, not a hard fail)'
             if tag == 'WARN' else ''))
    return bad


def main():
    bad = False
    # #195 PROPAGATION (2026-07-31). trimesh's contains() resolves ambiguous
    # parity with a draw from the GLOBAL RNG, so it can answer differently on
    # identical input and can shift when an unrelated earlier check consumes
    # RNG. leg_v6's gate pinned this in #195; this file never did, and it casts
    # into shoulder.stl, which is one of the two meshes measured to actually
    # flicker (1/3000 points over 12 calls). See cad_contains for the numbers.
    cad_contains.install()
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
    # #377: the ends are DIFFERENT PARTS now — front carries the SW1 Contura
    # panel hole, rear is plain. Sample each end from its own mesh.
    shp_by_end = {
        e: trimesh.sample.sample_surface(
            trimesh.load(f'{LEG}/shoulder_sw1.stl' if e > 0 else
                         f'{LEG}/shoulder.stl'), 8000, seed=0)[0]
        for e in (1, -1)}
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0],
                        [0, 0, 1, HIP_Z],
                        [0, 0, 0, 1.0]])
        p = tf(shp_by_end[end], S2T)
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

    # ---- 3c. SW1 switch BODY clearance (#377, 2026-08-15) ----------------------
    # The cutout does more than remove material: it puts 37 mm of SWITCH into
    # the front shoulder's C-box gap, a solid that exists in no other model.
    # panel_probe.py FOUND that volume; this is what KEEPS it — without a target
    # here, a later riser or neck_bracket revision could grow into the space the
    # switch needs and every gate would still be green.
    #
    # Envelope: from the panel's own seating face (shoulder-local y REAR_W1
    # -28.1, = trunk x 113.1) running 37 mm rearward, cutout footprint + 2 mm
    # per side for the wings and body flare. Trunk frame, FRONT end only.
    SW1_BODY = _sw1_body_box()
    sw1_pts = trimesh.sample.sample_surface(SW1_BODY, 4000, seed=0)[0]
    for nm, target in (('riser', riser), ('trunk', trunk), ('bracket', bracket)):
        near = near_bbox(sw1_pts, target)
        hits = near[target.contains(near)] if len(near) else near
        bad |= report(f'SW1 switch body vs {nm}', hits)

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
    # per-target survivor tally: a target that admits ZERO points at every pose
    # contributed nothing to this verdict, and must say so rather than pass
    # quietly. That silence is what let #47's dead head window sit green.
    seen = {k: 0 for k in ('riser', 'pocket', 'pack', 'rails',
                           'head', 'bracket', 'camera', 'sw1')}
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
                    # windows are DERIVED from each target's own bounds, never
                    # hand-typed -- see near_bbox() and #47 REDUX
                    for tname, target in (('riser', riser), ('pocket', pocket),
                                          ('pack', pack), ('rails', rails),
                                          ('head', head), ('bracket', bracket),
                                          ('camera', cam),
                                          # #377: the leg must never reach the
                                          # SW1 body. The wall separates them,
                                          # but "separated by a wall" is what
                                          # this sweep exists to PROVE.
                                          ('sw1', SW1_BODY)):
                        near = near_bbox(p, target)
                        seen[tname] += len(near)
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
    # NB `worst` is the max over ALL targets, not riser -- the old message said
    # "near-riser" and printed the pocket window's number.
    print(f'   sweep done (max {worst} in-window pts for any target in any pose)')
    print('   per-target points admitted across the sweep: '
          + ', '.join(f'{k}={v}' for k, v in seen.items()))
    dead = [k for k, v in seen.items() if v == 0]
    if dead:
        print(f'   NOTE {len(dead)} of {len(seen)} targets admitted NO points at any '
              f'pose ({", ".join(dead)}) -- the leg never enters their bounds in '
              f'this ROM, so their "no contact" result asserts nothing. Stated '
              f'explicitly because a dead check is indistinguishable from a '
              f'passing one otherwise (#47).')

    # ---- 5b. oled_tray vs the legs (#35) ------------------------------------
    # oled_tray sits on the REAR shoulder's deck top, which is the highest point
    # on the shoulder (79.55) -- so the only thing that can reach it is a moving
    # leg. That is exactly the claim the part is justified by, and nothing else
    # in this file gates it.
    #
    # NOT done as an eighth crouch-sweep target on purpose. near_bbox() admits
    # points NEAR a target's bounds; if the legs never get close the tray admits
    # zero and lands in the `dead` list above -- a check that asserts nothing,
    # which is the #47 failure this file already carries a NOTE about. A
    # CLEARANCE number cannot go vacuous: it is either a distance or a failure.
    #
    # Measured as distance to the tray's AXIS-ALIGNED BOX. That is exact for the
    # box and therefore a valid LOWER BOUND on distance to the solid inside it,
    # so a pass here is a real pass.
    #
    # Do NOT "simplify" this to a Z-only gap (tray_z0 minus the cloud's max z).
    # The first version of this check did exactly that and reported a 96mm
    # INTERSECTION, because at high protraction the leg swings up past z=170 --
    # but it does so at |y| ~ 39, outboard of this tray's |y| <= 26, and never
    # comes near it. A Z-only test is a sound lower bound only while the cloud
    # stays below the tray; above it, it is not a distance at all.
    tray = trimesh.load('oled_tray.stl')
    t_lo, t_hi = tray.bounds

    def _d_box(p):
        d = np.maximum(np.maximum(t_lo - p, p - t_hi), 0.0)
        return np.linalg.norm(d, axis=1)

    print(f'-- oled_tray (#35) vs ALL-FOUR-LEG sweep: tray z {t_lo[2]:.2f}..{t_hi[2]:.2f} --')
    # COVERAGE, fixed after review. The first version swept hfe -86..+50, kfe in
    # steps of 10 (which never sampled the +109 endpoint), and REAR hips only,
    # while its comment claimed "swept to their mech stops". All three were
    # wrong: the mechanical hfe window is symmetric +/-86 (limits.py
    # _thigh_flexion -- the +50 fold cap moved OUT of the scalar into the
    # posture-aware rom_envelope on 2026-07-25), so 36 deg of the fold side went
    # unswept, and the front legs were never checked at all on a hand-waved
    # "they can't reach" that is exactly the reasoning that already failed once
    # here. Measured with full coverage the front legs come within 31.78mm --
    # clear, but a third of the margin I assumed.
    HFE_SWEEP = range(-86, 87, 4)
    KFE_SWEEP = [round(v) for v in np.linspace(-109, 109, 23)]   # endpoints included
    worst_gap, worst_pose = 1e9, None
    stop_gap = 1e9
    for hfe in HFE_SWEEP:
        for kfe in KFE_SWEEP:
            cloud = leg_cloud(hfe, kfe)
            for haa in (-40, -25, -15, -7, 0, 7, 15, 25, 40):
                for label, base in coax_to_trunk_bases():
                    inboard = -haa if label[1] == 'R' else haa
                    inside_rom = inboard <= 15   # hfe/kfe swept to their mech stops
                    Sx = rot(haa, [1, 0, 0],
                             [HIP_FA if label[0] == 'F' else -HIP_FA,
                              HIP_LAT if label[1] == 'R' else -HIP_LAT, HIP_Z])
                    p = tf(tf(cloud, base), Sx)
                    gap = float(_d_box(p).min())
                    if inside_rom:
                        if gap < worst_gap:
                            worst_gap, worst_pose = gap, (label, haa, hfe, kfe)
                    else:
                        stop_gap = min(stop_gap, gap)
    lab, ha, hf, kf = worst_pose
    if worst_gap < TRAY_LEG_MIN_MM:
        bad = True
        print(f'   FAIL rear leg reaches within {worst_gap:.2f}mm of the tray '
              f'({lab} haa{ha:+d} hfe{hf:+d} kfe{kf:+d}) -- need '
              f'{TRAY_LEG_MIN_MM}mm')
    else:
        print(f'   OK   worst clearance {worst_gap:.2f}mm over the FULL hfe/kfe '
              f'mechanical range (at {lab} haa{ha:+d} hfe{hf:+d} kfe{kf:+d}), '
              f'{stop_gap:.2f}mm even at outboard-haa stops')

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
    # #377: per-end parts (front carries the SW1 cutout)
    sh_pts_by_end = {
        e: trimesh.sample.sample_surface(
            trimesh.load(f'{LEG}/shoulder_sw1.stl' if e > 0 else
                         f'{LEG}/shoulder.stl'), 8000, seed=0)[0]
        for e in (1, -1)}
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        p = tf(sh_pts_by_end[end], S2T)
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
        p = tf(sh_pts_by_end[end], S2T)
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

    # ---- 15. LA-22a: head_ear/head_ear_L bolt-axis + L2/D456 clearance,
    # skid_rail vs battery_pocket recess alignment, mirrored-LEFT shoulder
    # sweep -- zero prior gate coverage for any of these (fault audit
    # 2026-07-11); build_all.sh has rendered head_ear/head_ear_L/skid_rail
    # since 2026-07-08/07-06 but nothing ever checked them. -----------------
    print('-- case 15 (LA-22a): head_ear / skid_rail / mirrored-LEFT shoulder --')
    # head.scad: heat-set bore = translate([ex, sy*10, CROWN_Z0+7-6.2])
    # cylinder(d=4.0, h=6.2+EPS) -- CROWN_Z0=124, so the bore spans z
    # 124.8..131.05 (from the pad TOP z131 down to a BLIND floor at 124.8,
    # only 0.8mm above CROWN_Z0=124). head_ear.scad's clearance bore
    # (translate([ex,10,PAD_Z-EPS]) cylinder(d=M3_CLEAR,h=4+2*EPS), PAD_Z=131)
    # spans z 130.95..135.05 through the foot flange. The two bores meet
    # at the pad top (z~131) and share the same (ex, sy*10) axis.
    EAR_BOLT_Z0, EAR_BOLT_Z1 = 130.95, 135.05
    EAR_FLOOR_Z0, EAR_FLOOR_Z1 = 124.05, 124.7   # the 0.8mm blind floor below the heat-set
    EAR_WALL_R = 2.3                              # just past the Ø4 bore's own 2mm radius
    EAR_WALL_Z = 128.0                             # mid-bore
    for side, ear_file, sy in (('R', 'head_ear.stl', 1), ('L', 'head_ear_L.stl', -1)):
        ear = trimesh.load(ear_file)
        for ex in (77, 83):
            # ear's own M3 clearance bore must be OPEN through its foot flange
            pts = np.array([[ex, sy * 10, z]
                            for z in np.linspace(EAR_BOLT_Z0 + 0.3, EAR_BOLT_Z1 - 0.3, 6)])
            n = int(ear.contains(pts).sum())
            tag = 'OK  ' if n == 0 else 'FAIL'
            print(f'{tag}  head_ear_{side} bolt clearance x={ex} y={sy * 10:+d}: '
                  f'{n}/{len(pts)} axis pts land in solid')
            bad |= n > 0
            # matching head heat-set: the blind floor below the bore, AND
            # the wall material just past the bore's own radius, must both
            # be SOLID -- otherwise the insert has nothing to bite into
            # (same concern AUD-12/case 14 caught for the head-boss inserts).
            pts = np.array([[ex, sy * 10, z]
                            for z in np.linspace(EAR_FLOOR_Z0, EAR_FLOOR_Z1, 5)])
            n = int(head.contains(pts).sum())
            tag = 'OK  ' if n == len(pts) else 'FAIL'
            print(f'{tag}  head heat-set floor under ear_{side} x={ex} y={sy * 10:+d}: '
                  f'{n}/{len(pts)} axis pts land in solid')
            bad |= n < len(pts)
            ring = np.array([[ex + EAR_WALL_R * np.cos(a), sy * 10 + EAR_WALL_R * np.sin(a),
                             EAR_WALL_Z] for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)])
            n = int(head.contains(ring).sum())
            tag = 'OK  ' if n == len(ring) else 'FAIL'
            print(f'{tag}  head heat-set wall under ear_{side} x={ex} y={sy * 10:+d}: '
                  f'{n}/{len(ring)} ring pts land in solid')
            bad |= n < len(ring)
        # L2 / D456 clearance: the ear panel leans up/out from the rear pad --
        # must clear the seated L2 body and the D456 camera envelope
        ep = sample(ear, 5000, 1200, seed=14)
        hits = ep[l2.contains(ep)]
        bad |= report(f'head_ear_{side} vs seated L2 body', hits)
        hits = ep[cam.contains(ep)]
        bad |= report(f'head_ear_{side} vs D456 camera envelope', hits)

    # -- skid_rail key vs battery_pocket recess alignment (backlog #15,
    # battery_pocket.scad "skid-rail key recesses") -- skid_rail.stl renders
    # in its own RAIL-LOCAL frame (x 0..130, y 0..12, z -RAIL_T..~0); trunk
    # placement (matches the case-4 sweep's `rails` envelope box AND the two
    # files' own KEY_X/kx comments, both independently citing trunk x -43/+58):
    # local x0 -> trunk x=-55, local y0 -> trunk y=+9 (the +y rail; the -y
    # rail is this same STL Y-mirrored), local z0 -> trunk z=BOT_Z=-39.2
    # (battery_pocket.scad BOT_Z). The recess is a void cut INTO the pocket
    # solid, so a genuinely aligned key's own volume must sample OUTSIDE the
    # pocket solid -- any point of the key landing inside pocket.contains()
    # means the recess is missing or misaligned there.
    BOT_Z = -39.2   # battery_pocket.scad BOT_Z = CAV_Z0 - WALL
    rail = trimesh.load('skid_rail.stl')
    rp = sample(rail, 4000, 1200, seed=15)
    rp_keys = rp[rp[:, 2] > 0.02]   # the raised KEY bumps only (local z>0; rail body is z<=0)
    T_R = trimesh.transformations.translation_matrix([-55, 9, BOT_Z])
    MIRY2 = np.eye(4); MIRY2[1, 1] = -1
    T_L = MIRY2 @ T_R
    for label, M in (('+y', T_R), ('-y', T_L)):
        kp = tf(rp_keys, M)
        hits = kp[pocket.contains(kp)] if len(kp) else kp
        bad |= report(f'skid_rail key ({label}) vs battery_pocket solid '
                      f'(recess must clear the key)', hits)

    bad |= left_shoulder_sweep_check()

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
        p = tf(sh_pts_by_end[end], S2T)
        near = p[np.abs(p[:, 0]) < 66]
        hits = near[cradle.contains(near)] if len(near) else near
        bad |= report(f'{"front" if end > 0 else "rear"} shoulder vs cradle', hits)

    # ---- 11. REAL power board + REAL logic board (power_board_model),
    # STANDOFF_FLOOR_MM=20 ------------------------------------------------------
    pb_mesh, pb_components, pb_fps = power_board_mesh()
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

    # (c) EVERY power-board top-side part (max z1 over pb_tops) clears the
    # logic board underside (LOGIC_BOARD_Z0, power_board_model.py). The
    # logic board sits on the pb->lb standoff directly above the power
    # board's TOP FACE -- NOT pinned to any one part's height
    # (preview_assembly.py) -- so this must be checked explicitly rather
    # than assumed by construction, and checked against the whole set, not
    # a single named ref (#391 -- Q1-only missed the taller INA226/C8/C9).
    tallest = max(pb_tops, key=lambda c: c['z1'])
    ok = tallest['z1'] <= LOGIC_BOARD_Z0
    print(('OK    ' if ok else 'FAIL  ') + f"tallest power-board top part ({tallest['ref']} "
          f"z={tallest['z1']:.2f}) clears logic board underside ({LOGIC_BOARD_Z0:.2f}), "
          f"margin={LOGIC_BOARD_Z0 - tallest['z1']:.2f}mm")
    bad |= not ok
    for c in pb_tops:
        if c['ref'] in pbm.UNMEASURED:
            print(f"WARN  {c['ref']} height ({pbm.INA226_STACK_MM}mm) is UNMEASURED "
                  f"(STATUS.md) -- caliper before trusting this margin")

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
    # 20mm pb->lb gap) clears the tallest power-board top-side part, which
    # sits in the same gap (#391 -- this used to assume Q1 was that part;
    # checked against `tallest` from case (c) so it stays true if a taller
    # part is added/re-measured later).
    lb_bot_z = min(c['z0'] for c in lb_bots)
    lb_bot_ref = min(lb_bots, key=lambda c: c['z0'])['ref']
    ok = lb_bot_z >= tallest['z1']
    print(('OK    ' if ok else 'FAIL  ') + f'logic board B.Cu underside ({lb_bot_ref} '
          f"z={lb_bot_z:.2f}) clears {tallest['ref']} top ({tallest['z1']:.2f}) in the "
          f"pb->lb gap, margin={lb_bot_z - tallest['z1']:.2f}mm")
    bad |= not ok

    # (f) mezzanine standoff hardware (AUD-4): model the 4 floor->power
    # standoffs as real geometry and check the power-board components
    # against them -- reusing power_board_model's own footprint-extent /
    # component-mesh helpers (pbm._component_mesh, pbm._footprint_xy_extent)
    # so the clearance is measured against the SAME box/cylinder shapes the
    # gate already builds pb_mesh out of, not a re-derived approximation.
    # Q1 (TO-220) is the tallest top-side part and, per the audit, the
    # tightest XY neighbor of the standoff at (-40.5,-33); C1-C6 are the
    # bottom-side caps whose z-band (9..26) actually overlaps the standoff
    # barrel's z-band (6..26), so they're the ones with a genuine 3D
    # coincidence risk, not just an XY graze like Q1 (Q1 sits on TOP of the
    # board, z>=27.62, a full board-thickness above the standoff top at
    # z=26 -- no z-overlap is possible, so this is a plan-view XY clearance
    # check: does anything reaching toward that corner, on either face,
    # crowd the post).
    standoffs = trimesh.util.concatenate([
        trimesh.creation.cylinder(
            radius=STANDOFF_R_FLATS, height=BOARD_BOTTOM_Z - FLOOR_TOP_Z,
            transform=trimesh.transformations.translation_matrix(
                [sx, sy, (FLOOR_TOP_Z + BOARD_BOTTOM_Z) / 2]))
        for sx, sy in STANDOFF_XY])
    print('-- case 11f: mezzanine standoff hardware (AUD-4) --')
    for ref in ('Q1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'):
        info = next(c for c in pb_components if c['ref'] == ref)
        fp = pb_fps[ref]
        sx, sy = min(STANDOFF_XY,
                     key=lambda s: (s[0] - info['x']) ** 2 + (s[1] - info['y']) ** 2)
        if fp['diameter'] is not None:
            center_d = float(np.hypot(info['x'] - sx, info['y'] - sy))
            gap = lambda r, d=center_d, cr=fp['diameter'] / 2: d - cr - r
        else:
            xw, yw = pbm._footprint_xy_extent(fp)
            rx0, rx1 = info['x'] - xw / 2, info['x'] + xw / 2
            ry0, ry1 = info['y'] - yw / 2, info['y'] + yw / 2
            nx = min(max(sx, rx0), rx1)
            ny = min(max(sy, ry0), ry1)
            edge_d = float(np.hypot(sx - nx, sy - ny))
            gap = lambda r, d=edge_d: d - r
        gap_flats, gap_corners = gap(STANDOFF_R_FLATS), gap(STANDOFF_R_CORNERS)
        tag = 'OK  ' if gap_flats >= 0 else 'FAIL'
        clock_note = ('  (clocking-sensitive: worst-case hex corner interferes)'
                      if gap_corners < 0 else '')
        print(f'{tag}  {ref} vs standoff ({sx:+.1f},{sy:+.1f}): '
              f'{gap_flats:+.2f}mm across-flats, {gap_corners:+.2f}mm '
              f'across-corners{clock_note}')
        bad |= gap_flats < 0
    # volumetric backstop: sample the standoff posts themselves and check
    # against the REAL power-board mesh (not just the two named part
    # families above) -- catches anything else crowding a post that the
    # per-ref loop didn't name. The slab's own underside is a designed
    # seat (board bottom z=BOARD_BOTTOM_Z rests directly on the standoff
    # top), so exclude points within jitter of that mating plane the same
    # way the floor-plate/deck seats are excluded elsewhere in this file.
    sop = sample(standoffs, 6000, 1500, seed=11)
    sop_f = sop[sop[:, 2] < BOARD_BOTTOM_Z - 0.3]
    hits = sop_f[pb_mesh.contains(sop_f)] if len(sop_f) else sop_f
    bad |= report_depth('standoff posts vs power board (mating seat excluded)',
                        hits, pb_mesh, noise_mm=0.05)

    # ---- 12. NEW chassis parts (CR-7, was #39): jetson_clamp_bar (+y/-y),
    # l2_adapter, control_pod. These have had real
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
    rear_sh = tf(sh_pts_by_end[-1], S2T_rear)   # REAR end = the plain part (#377)
    hits = rear_sh[pod.contains(rear_sh)] if len(rear_sh) else rear_sh
    bad |= report('control pod vs rear shoulders', hits)
    hits = podp[box.contains(podp)]
    bad |= report('control pod vs mezzanine stack envelope', hits)

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
    # The CASE_SLOT r=4 blowout is FIXED (riser_bay.scad 2026-07-10, slot
    # widened to 9mm). This liner is an EDGE CLIP (spine + one bottom leg over
    # a 4mm deck edge), NOT a closed-bore grommet -- most of its volume is the
    # exposed cable channel in the slot VOID by design, so "% inside solid"
    # caps well under 100%. The old ">85%" target was carried over from the
    # closed-bore grommet_insert intuition and is not meaningful here. Primary
    # retention = the zip-tie tab (per the .scad header); spine interference +
    # bottom leg are secondary. Report FYI; only flag if implausibly low.
    # grip% is an INVERTED proxy for this open edge liner: more overlap = the
    # leg jammed deeper into the rigid skirt = LESS installable, not more
    # secure. Retention is the zip-tie tab by design, so this NEVER gates --
    # pure FYI (LEG_REACH is sized for installability, which reads ~12%).
    print(f'NOTE  case_slot_grommet edge-clip: {grip_frac * 100:.0f}% of its '
          f'volume overlaps solid riser (leg backstops on the skirt inner face; '
          f'the rest is the exposed cable channel + bay air, by design). '
          f'grip% is an inverted proxy — retention = the zip-tie tab. FYI only.')

    # ---- 13. DERIVED TRUNK (trunk.scad/trunk_build.py) hole alignment -----------
    # trunk.stl replaces the stock mesh with 10 modeled clearance/CSK bores
    # (battery mount x6, shoulder-foot CSK x4) so nothing is drilled at
    # assembly; the shoulder-flange end-wall bores (x8) are ALREADY stock
    # (measured — see trunk.scad header + measure_trunk.py + README.md "What
    # the trunk ACTUALLY is") and are checked here too, purely as a
    # regression guard (a stock-mesh swap or a shoulder.scad rev could move
    # TRUNK_HOLE_X/Z without anyone noticing). This is the REAL value of this
    # case: proof the modeled bores sit exactly on each mating part's own
    # bolt axis, not just that "a hole" exists somewhere nearby.
    print('-- case 13: derived trunk (trunk.stl) hole alignment --')
    trunk_holes = trimesh.load('trunk.stl')

    def axis_open(mesh, pts, label):
        inside = mesh.contains(pts)
        n = int(inside.sum())
        tag = 'OK  ' if n == 0 else 'FAIL'
        print(f'{tag}  {label}: {n}/{len(pts)} axis pts land in solid')
        return n > 0

    # SET 1 — battery mount, 6x M3 (battery_pocket.scad BOSS_X/BOSS_Y),
    # vertical bore through the 3.9mm floor.
    for bx in BATT_BOSS_X:
        for sy in (1, -1):
            pts = np.array([[bx, sy * BATT_BOSS_Y, z]
                            for z in np.linspace(0.3, 3.6, 6)])
            bad |= axis_open(trunk_holes, pts,
                              f'battery bolt axis bx={bx:+d} sy={sy:+d}')

    # SET 2 — shoulder-foot CSK, 4x M3x14 (leg_v6/shoulder.scad
    # FOOT_BOLT_X/Y, transformed via the front/rear S2T placements),
    # vertical bore through the same floor slab.
    for (wx, wy) in FOOT_XY:
        pts = np.array([[wx, wy, z] for z in np.linspace(0.3, 3.6, 6)])
        bad |= axis_open(trunk_holes, pts,
                          f'shoulder-foot bolt axis x={wx:+.1f} y={wy:+.1f}')

    # SET 3 — shoulder-flange end-wall clearance, 8x M3 (leg_v6/shoulder.scad
    # TRUNK_HOLE_X/Z) — ALREADY STOCK, regression guard only. Bore axis runs
    # fore-aft (world x) through the end wall/boss near the trunk edge.
    for x_span in (np.linspace(57.5, 63.0, 6), np.linspace(-63.0, -57.5, 6)):
        end = 'F' if x_span[0] > 0 else 'R'
        for sx in (1, -1):
            for hz in (5.0, 24.0):
                pts = np.array([[x, sx * 51.75, hz] for x in x_span])
                bad |= axis_open(trunk_holes, pts,
                                  f'shoulder-flange bolt axis end={end} '
                                  f'y={sx * 51.75:+.2f} z={hz:.1f}')

    # ---- 14. HEAD-BOSS <-> NECK-BRACKET bolt-axis alignment (AUD-12,
    # 2026-07-10, gate hardening) --------------------------------------------
    # The confirmed defect this closes: head.scad's old USB-C column channel
    # (a straight cube, x127..138 y6..15, run all the way down to the boss
    # bottom z84) hollowed out the ENTIRE +y insert column of the rear-boss->
    # bracket-wall M3 heat-sets (HM_Y=10, z89 & z100) -- 0mm insert
    # floor/wall at both, measured. Nothing gated this axis (case 7+8 checks
    # head/bracket ENVELOPES vs the rest of the chassis, never each other's
    # own fastener bores), so it went in silent. Model after case 13's
    # axis-alignment pattern: probe each of the 4 bolt axes on BOTH sides of
    # the joint -- the head boss must have SOLID insert material just past
    # the heat-set bore's own end (the "floor/wall" a nylon M3 actually
    # bites into), and the neck-bracket wall must be OPEN (M3 clearance +
    # rear counterbore, driven from behind) at the matching axis, so a bolt
    # driven through the wall actually lands in a backed insert, not a void.
    print('-- case 14: head-boss <-> neck-bracket bolt-axis alignment (AUD-12) --')

    def axis_solid(mesh, pts, label):
        inside = mesh.contains(pts)
        n = int(inside.sum())
        tag = 'OK  ' if n == len(pts) else 'FAIL'
        print(f'{tag}  {label}: {n}/{len(pts)} axis pts land in solid')
        return n < len(pts)

    for sy in (1, -1):
        for hz in (89, 100):
            # head boss: insert floor/wall just past the heat-set bore's own
            # end (bore runs x121..127.15; probe x128/129/130, the same
            # points the AUD-12 write-up measured as 0.0 before the fix) --
            # must be SOLID at every one.
            pts = np.array([[x, sy * 10, hz] for x in (128, 129, 130)])
            bad |= axis_solid(head, pts,
                              f'head-boss insert floor y={sy * 10:+d} z={hz}')
            # neck bracket: the wall's M3 clearance bore (drive access from
            # behind the wall, x103..121, WALL_X0=113 -> the boss face x121)
            # must be OPEN along the same y/z axis.
            pts = np.array([[x, sy * 10, hz] for x in np.linspace(105, 120, 6)])
            bad |= axis_open(bracket, pts,
                             f'neck-bracket wall clear y={sy * 10:+d} z={hz}')

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
        ('neck-bracket deck-through bolts span (29 fore-aft) >= 25',
         146 - 117 >= 25),   # NO-DRILL fix 2026-07-10: front pair moved
                             # x110->x117 (off the shoulder's 22.5mm rear-wall
                             # rib, onto the flat deck) shrank the span
                             # 36->29 and threshold 30->25. Acceptable: the
                             # rear VERTICAL-FACE head heat-sets at x121 carry
                             # the primary head-cantilever moment; these 4
                             # base bolts are secondary hold-down (see
                             # neck_bracket.scad:64-72).
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

    bad |= mating_fastener_checks()
    bad |= floor_thickness_check()
    bad |= cross_family_check()
    bad |= neck_slot_shoulder_window_check()
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
