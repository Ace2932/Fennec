#!/usr/bin/env python3
"""leg_v6 fit gate — REAL-geometry collision check.

Places the actual STS3215 mesh (feetech_servo_models/converted_stl/servo.stl,
spline axis moved to the origin to match leg_v6_common's servo frame) at each
part's pocket pose and samples the servo (surface + volume points) against the
printed part's solid. ANY servo point inside the part = the part cuts the
servo. Run after every geometry change:  ../../../.venv/bin/python check_fit.py

Flags: --sweep (kfe/hfe pose sweeps + insertion + shoulder + through-hole +
cable, all of the below), --insertion (#53 femur-insertion sweep alone),
--shoulder (haa roll sweep alone), --through (LA-21 through-hole probe
alone), --cable (LA-20 cable-loop span sweep alone).

Exit 0 = clean, 1 = interference (clusters printed).
"""
import sys
import numpy as np
import trimesh

# servo.stl = STS3215_03a v1 (same snapshot as the canonical
# "STS3215_03a v1.3mf") INCLUDING the output horn + bottom wheel bodies the
# 3mf omits. Cross-checked 2026-07-03: the 3mf's bare case matches this
# mesh's case body feature-for-feature (pins/screw bores/spline boss/cap)
# within 0.1mm after a +1.0mm z-origin shift.
SERVO = '/Users/afox/codebases/NOVA/feetech_servo_models/converted_stl/servo.stl'


def servo_mesh():
    m = trimesh.load(SERVO)
    m.apply_translation([-12.5, 0, 0])   # spline axis -> origin (common frame)
    return m


def sample_points(m, n_surface=15000, n_volume=6000):
    surf, _ = trimesh.sample.sample_surface(m, n_surface, seed=0)
    lo, hi = m.bounds
    vol = np.random.default_rng(0).uniform(lo, hi, (n_volume * 4, 3))
    vol = vol[m.contains(vol)][:n_volume]
    return np.vstack([surf, vol])


def rot_z180():
    return trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])


def coax_pose():
    # rotate([0,-90,0]) rotate([90,0,0]) in OpenSCAD (right-multiplied):
    ry = trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0])
    rx = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    return ry @ rx


def mirror_z():
    m = np.eye(4); m[2, 2] = -1
    return m


def mirror_x():
    m = np.eye(4); m[0, 0] = -1
    return m


CASES = [
    ('femur_R.stl', rot_z180(), 'HFE servo in femur pocket'),
    ('tibia_R.stl', rot_z180(), 'KFE servo in tibia pocket'),
    ('coax_R.stl',  coax_pose(), 'HAA servo in coax pocket'),
    # left parts are Z-mirrors (coax: X-mirror) — servo pose mirrors with them
    ('femur_L.stl', mirror_z() @ rot_z180(), 'HFE servo in femur_L pocket'),
    ('tibia_L.stl', mirror_z() @ rot_z180(), 'KFE servo in tibia_L pocket'),
    ('coax_L.stl',  mirror_x() @ coax_pose(), 'HAA servo in coax_L pocket'),
]


def rot_about(angle_deg, axis, point):
    return trimesh.transformations.rotation_matrix(
        np.radians(angle_deg), axis, point)


def _clearance_warn(target, p, label, floor_mm=1.0):
    """LA-19b: a swept point cloud that passes the r13 mask and reads a
    boolean OK (0 pts inside `target`) can still be a hair's breadth away —
    the r13 0.4mm-floor class (LA-19) is exactly that: a genuine, constant,
    sub-mm clearance that a pure containment check reports as a clean 'OK'
    and hides. Compute the real distance-to-surface for the (already-outside)
    cloud and WARN (does not fail the gate) if the closest approach is
    <floor_mm. Cheap relative to the containment check already run."""
    if not len(p):
        return
    d = -trimesh.proximity.signed_distance(target, p)
    min_d = float(d.min())
    if min_d < floor_mm:
        print(f'   WARN  {label}: clearance floor {min_d:.2f}mm (<{floor_mm:.1f}mm, '
              f'outside the r13 mask but a genuine near-miss — see LA-19)')


def sweep_checks(servo, pts0):
    """Pose sweeps: knee fold (tibia+servo vs femur+knee_arm) and hip pitch
    (femur+arm+servo vs coax). Software limits kfe ±126°, hfe ±86° — any
    contact INSIDE those = design bug (mech stops computed at ~141/~91).

    LA-19 (2026-07-11): the hfe sweep used to stop at the sw limit itself
    (±86°), so it never probed for a mech stop the way the kfe sweep already
    does (109 sw / 118 measured stop) — extended to ±90/95/100 to pin it.
    Measured here: clean through ±92.5°, first contact at ±93° (symmetric).
    Also adds the LA-19b sub-mm clearance WARN (see _clearance_warn) to both
    sweeps, and includes kfe=0 (previously absent from the angle list) —
    that's where LA-19's named r13 near-miss lives (see below)."""
    bad = False
    femur = trimesh.load('femur_R.stl')
    arm = trimesh.load('knee_arm.stl')
    # rev 3 (2026-07-10): knee_arm seats at YOKE_TOP_IN, moved 17.2->17.75
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.75]))
    tibia = trimesh.load('tibia_R.stl')
    # knee_bumper (TPU, backlog #15 B) wraps the knee-end pocket block ±Y faces
    # + under the bottom; it RIDES the tibia through the kfe fold, so sweep it
    # WITH the tibia against the femur fork. (Replaces the retired tibia_pad.)
    kb = trimesh.load('knee_bumper.stl')
    tib_pts = np.vstack([trimesh.sample.sample_surface(tibia, 6000, seed=0)[0],
                         trimesh.sample.sample_surface(kb, 2000, seed=0)[0],
                         trimesh.transform_points(pts0, rot_z180())])
    T_knee = trimesh.transformations.translation_matrix([106.9, 0, 0])
    print('-- knee fold sweep (tibia+servo vs femur+knee_arm)')
    print('   (points within r13 of the joint axis excluded: the bolted')
    print('    disc/boss interfaces overlap BY DESIGN, rotation-symmetric)')
    # LA-19c: kfe=0 added -- this is where the named r13-14 near-miss sits.
    # NAMED (2026-07-11, cross-section probe): the closest approach is the
    # TIBIA pocket-block underside (SLAB_Z0/FLOOR_BOT, z=-22.2, a flat
    # z-normal face) grazing the FEMUR's yoke BOTTOM-ARM top face
    # (YOKE_BOT_IN, z=-22.6) at r~13.4 from the joint axis, x~98 (femur
    # frame) — 0.40mm apart. BY DESIGN: YOKE_BOT_IN = FLOOR_BOT - 0.4
    # (leg_v6_common.scad, "0.4: PA6-CF shrink robustness"), and both faces
    # are Z-const flat planes near the kfe rotation axis, so the gap stays
    # exactly 0.40mm across the whole sweep (kfe rotation doesn't change Z).
    # Deliberate, not a bug — but a genuinely sub-1mm margin worth the WARN.
    for ang in [-109, -90, -60, 0, 60, 90, 109, 118]:  # sw limit 1.9rad=109; 118 = measured mech stop (expect HIT, documents it)
        T = T_knee @ trimesh.transformations.rotation_matrix(
            np.radians(ang), [0, 0, 1])
        p = trimesh.transform_points(tib_pts, T)
        p = p[np.linalg.norm(p[:, :2] - [106.9, 0], axis=1) > 13]
        inside_fem = femur.contains(p)
        inside_arm = arm.contains(p)
        n = int(inside_fem.sum()) + int(inside_arm.sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 109: bad = True   # hits beyond sw limit are the mech stop
        print(f'   {status} kfe {ang:+4d}deg: {n} pts')
        if n == 0 and abs(ang) <= 109:
            _clearance_warn(femur, p, f'kfe {ang:+4d}deg vs femur')
            _clearance_warn(arm, p, f'kfe {ang:+4d}deg vs knee_arm')
    # #53 fix (2026-07-11): coax's inboard HFE arm is now a separate bolt-on
    # (coax_hfe_plate.scad) -- union it into the "coax" solid used for the
    # SEATED hip-pitch sweep (both parts are defined in the same coax world
    # frame at identity, no transform needed to combine them).
    coax = trimesh.util.concatenate([trimesh.load('coax_R.stl'),
                                      trimesh.load('coax_hfe_plate.stl')])
    fem_asm = np.vstack([trimesh.sample.sample_surface(femur, 5000, seed=0)[0],
                         trimesh.sample.sample_surface(arm, 1500, seed=0)[0],
                         trimesh.transform_points(pts0, rot_z180())])
    M = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    print('-- hip pitch sweep (femur assembly vs coax+coax_hfe_plate)')
    # LA-19a: extended past the sw limit (86) to ±90/95/100 to pin the mech
    # stop, same pattern as the kfe sweep's 109/118. Measured (2026-07-11,
    # 0.5deg-resolution bisection): clean through ±92.5deg, first contact at
    # +93deg (1 pt) / -93deg (3 pts) -- symmetric mech stop at ~93deg.
    for ang in [-100, -95, -90, -86, -60, -30, 30, 60, 86, 90, 95, 100]:
        S = rot_about(ang, [1, 0, 0], [33.8, 11.6, -9.5])
        # place femur (M), then rotate about the hfe axis (S)
        p = trimesh.transform_points(
            trimesh.transform_points(fem_asm, M), S)
        # exclude the designed disc/boss interface about the hfe X-axis
        p = p[np.linalg.norm(p[:, 1:] - [11.6, -9.5], axis=1) > 13]
        n = int(coax.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 86: bad = True   # hits beyond sw limit (86) document the mech stop (~93deg), same convention as kfe
        print(f'   {status} hfe {ang:+4d}deg: {n} pts')
        if n == 0 and abs(ang) <= 86:
            _clearance_warn(coax, p, f'hfe {ang:+4d}deg vs coax')
    return bad


def shoulder_checks(servo, pts0):
    """Shoulder vs the swinging leg about the haa axis (Y-line at x=39.05,
    z=0). Right hip; the left is the mirror. Leg assembly = coax (+its
    servo) + femur + tibia + knee_arm, mounted horn-forward (mirror-Y of
    the coax frame — see the chirality note in the design memory)."""
    bad = False
    sh = trimesh.load('shoulder.stl')
    pl = trimesh.load('shoulder_plate.stl')
    # #53 fix (2026-07-11): coax's inboard HFE arm is now coax_hfe_plate.scad
    coax = trimesh.util.concatenate([trimesh.load('coax_R.stl'),
                                      trimesh.load('coax_hfe_plate.stl')])
    femur = trimesh.load('femur_R.stl')
    tibia = trimesh.load('tibia_R.stl')
    arm = trimesh.load('knee_arm.stl')
    # rev 3 (2026-07-10): knee_arm seats at YOKE_TOP_IN, moved 17.2->17.75
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.75]))
    # leg points in COAX frame (coax + haa servo + femur/tibia/arm assembly)
    M_f = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
           @ rot_z180()
           @ trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    T_t = trimesh.transformations.translation_matrix([106.9, 0, 0])
    leg = np.vstack([
        trimesh.sample.sample_surface(coax, 6000, seed=0)[0],
        trimesh.transform_points(pts0, coax_pose()),                # haa servo
        trimesh.transform_points(
            trimesh.sample.sample_surface(femur, 4000, seed=0)[0], M_f),
        trimesh.transform_points(
            trimesh.sample.sample_surface(arm, 1000, seed=0)[0], M_f),
        trimesh.transform_points(
            trimesh.sample.sample_surface(tibia, 3000, seed=0)[0], M_f @ T_t),
    ])
    # coax frame -> shoulder frame: mirror Y (horn -Yc -> +Ys, yoke +X kept),
    # then translate the spline point to the right hip station
    MIR = np.eye(4); MIR[1, 1] = -1
    HIP = trimesh.transformations.translation_matrix([39.05, 0, 0])
    base = HIP @ MIR
    print('-- haa roll sweep (leg assembly vs shoulder + plate)')
    for ang in [-45, -40, -25, 0, 25, 40, 45]:
        S = rot_about(ang, [0, 1, 0], [39.05, 0, 0])
        p = trimesh.transform_points(trimesh.transform_points(leg, base), S)
        # exclude the designed disc/boss interface about the haa Y-axis
        keep = np.sqrt((p[:, 0] - 39.05)**2 + p[:, 2]**2) > 13
        p = p[keep]
        n = int(sh.contains(p).sum()) + int(pl.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 40: bad = True   # beyond 40 = documenting stops
        print(f'   {status} haa {ang:+4d}deg: {n} pts')
    return bad


def _axis_scan(mesh, base, direction, t_lo, t_hi, r=1.0, n=60):
    """Sample a ring of 4 points (+ the exact centerline) at radius `r`
    around `base + t*direction` for t in [t_lo, t_hi], and return the list
    of t-values where ANY of those points land inside `mesh`. The ring
    (rather than a single point exactly on the axis) dodges the fixed-
    direction containment-ray tangency issue trimesh hits on axis-aligned
    faces (same jitter reasoning as chassis/check_fit.py's sample())."""
    direction = np.asarray(direction, dtype=float)
    direction = direction / np.linalg.norm(direction)
    tmp = np.array([1.0, 0, 0]) if abs(direction[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(direction, tmp); u /= np.linalg.norm(u)
    v = np.cross(direction, u)
    ts = np.linspace(t_lo, t_hi, n)
    blocked = []
    for t in ts:
        c = np.asarray(base) + t * direction
        pts = np.vstack([c, c + r * u, c - r * u, c + r * v, c - r * v])
        if mesh.contains(pts).any():
            blocked.append(t)
    return blocked


# LA-21 (2026-07-11): neither check_fit.py nor check_shoe.py ever probed the
# parts' own fastener/zip-tie bores -- LA-4 (femur/tibia zip anchors modeled
# as h=12 BLIND pockets, 25.9mm of solid remaining above the "hole") sailed
# through both gates undetected because the sweep/servo-fit checks never
# looked at these bores at all. This is the missing class: for every zip-tie
# bore that's SUPPOSED to punch clean through the part (per the .scad's own
# comments — "genuine through-hole", "matches the x62/84 through-hole
# convention"), scan its axis well PAST both of its nominal ends (a fixed
# margin, not just the interior span the hole was modeled with) and assert
# nothing solid blocks it. A blind cap — modeled void that doesn't reach the
# true exterior surface — shows up as a blocked point past the nominal end;
# a genuine through-hole reads clean the whole way. R/L holes are derived
# from the SAME literal .scad coordinates via each part's own mirror
# convention (femur_L/tibia_L: mirror Z; coax_L: mirror X — see
# femur_L.scad/tibia_L.scad/coax_L.scad headers), so this is one source of
# truth, not two copy-pasted lists.
MARGIN_MM = 15.0   # scan this far past each hole's own nominal z0/z1

# (part, hole label, x0, y0, z0, z1) in the RIGHT part's own local frame —
# femur.scad / tibia.scad zip_pair_neg() calls run along local Z.
FEMUR_R_ZIP_HOLES = [
    ('x44', 44, -5, -23.2, 16.8), ('x44', 44, 5, -23.2, 16.8),
    ('x52', 52, -5, -23.2, 16.8), ('x52', 52, 5, -23.2, 16.8),
    ('x84 knee-crossing', 84, -5, -27.6, -21.6),
    ('x84 knee-crossing', 84, 5, -27.6, -21.6),
]
TIBIA_R_ZIP_HOLES = [
    ('x44', 44, -5, -23.2, 16.8), ('x44', 44, 5, -23.2, 16.8),
    ('x62', 62, 0, -23.2, 16.8),
    ('x84', 84, 0, -23.2, 16.8),
]
# coax.scad's side-wall zip exits run along local X (rotate([0,sx*90,0]) on a
# Z-cylinder); BLK_X-6 = 16.05-6 = 10.05 (leg_v6_common.scad CASE_HW+
# CLR_POCKET+WALL).
COAX_R_ZIP_HOLES_X = 7.0
COAX_R_ZIP_HOLES_H = 16.05 - 6


def through_hole_checks():
    print('-- LA-21: through-hole probe (zip-tie / cable bores must be open end-to-end) --')
    bad = False

    def check(part_file, label, base, direction, t_lo, t_hi):
        mesh = trimesh.load(part_file)
        blocked = _axis_scan(mesh, base, direction, t_lo - MARGIN_MM, t_hi + MARGIN_MM)
        if blocked:
            print(f'BLIND {part_file} {label}: solid blocks the bore axis at '
                  f't={blocked[0]:.1f}..{blocked[-1]:.1f} (nominal span '
                  f'{t_lo:.1f}..{t_hi:.1f}, scanned +/-{MARGIN_MM:.0f}mm past it)')
            return True
        print(f'OK    {part_file} {label}: open end-to-end '
              f'(scanned {t_lo - MARGIN_MM:.1f}..{t_hi + MARGIN_MM:.1f})')
        return False

    for label, x0, y0, z0, z1 in FEMUR_R_ZIP_HOLES:
        bad |= check('femur_R.stl', f'zip {label} y={y0:+d}', [x0, y0, 0], [0, 0, 1], z0, z1)
        # femur_L = Z-mirror of femur_R (femur_L.scad: mirror([0,0,1]))
        bad |= check('femur_L.stl', f'zip {label} y={y0:+d}', [x0, y0, 0], [0, 0, 1], -z1, -z0)
    for label, x0, y0, z0, z1 in TIBIA_R_ZIP_HOLES:
        bad |= check('tibia_R.stl', f'zip {label} y={y0:+d}', [x0, y0, 0], [0, 0, 1], z0, z1)
        bad |= check('tibia_L.stl', f'zip {label} y={y0:+d}', [x0, y0, 0], [0, 0, 1], -z1, -z0)
    for sx in (1, -1):
        x0 = sx * COAX_R_ZIP_HOLES_X
        t_lo, t_hi = sorted([x0, x0 + sx * COAX_R_ZIP_HOLES_H])
        bad |= check('coax_R.stl', f'zip sx={sx:+d}', [0, 17, -36], [1, 0, 0], t_lo, t_hi)
        # coax_L = X-mirror of coax_R (coax_L.scad: mirror([1,0,0]))
        bad |= check('coax_L.stl', f'zip sx={sx:+d}', [0, 17, -36], [1, 0, 0], -t_hi, -t_lo)
    return bad


def cable_checks():
    """LA-20: check_fit never swept cable geometry -- the exact blind-spot
    class that would have caught LA-14 (the 1e5 cyc/hr service loops forced
    tighter than the design's own >=40mm bend-radius spec, backlog #18).
    Places the documented zip-tie anchor points (cable_clip.scad's own
    pairing: "coax tunnel-exit pair + femur x44 pair = the HIP loop
    (haa+hfe)"; "femur x84 (yoke plate) + tibia x44 pair = the KNEE loop
    (kfe)") at the LITERAL translate() coordinates each anchor is cut at in
    the .scad (coax.scad:170, femur.scad:148/153, tibia.scad:150), and
    sweeps their 3D separation with the SAME kfe/hfe transforms
    sweep_checks() already uses. A loop needs >= 2x the min bend radius
    (backlog #18: >=40mm radius -> 80mm span) to avoid folding tighter than
    spec.

    WARN only, never fails the gate: LA-14 already found (and left OPEN,
    un-fixed) that both loops dip under 80mm across part of the ROM -- this
    check makes that visible on every gate run, it isn't claiming the
    geometry is now fixed. KNEE-loop numbers cross-check exactly against
    LA-14's own figures (67.0mm @ kfe0 -> 39.2mm @ the kfe118 mech stop);
    HIP-loop numbers here (anchor = each hole's own translate() origin) run
    ~60-79mm across hfe, a similar but not identical range to LA-14's cited
    76-93mm -- LA-14 likely referenced the coax's true bottom tunnel exit
    (z=-38.4) rather than this zip-hole's own coordinate; noted here as an
    approximation, not re-derived (see the priority-order note on LA-20 in
    the fault audit -- a full loop-length model was out of scope for this
    pass)."""
    print('-- LA-20: cable service-loop anchor separation vs ROM (backlog #18, >=40mm bend radius) --')
    MIN_SPAN = 80.0   # 2 x the >=40mm min bend radius (backlog #18)
    T = trimesh.transformations.translation_matrix

    # ---- KNEE loop: femur x84 (yoke-crossing zip pair) <-> tibia x44
    # (tunnel-exit zip pair), swept across kfe.
    fem_anchor = np.array([84, 0, -27.6])
    tib_anchor = np.array([44, 0, -23.2])
    T_knee = T([106.9, 0, 0])
    worst_knee = None
    for kfe in [-109, -90, -60, -30, 0, 30, 60, 90, 109, 118]:
        Tk = T_knee @ rot_about(kfe, [0, 0, 1], [0, 0, 0])
        p = trimesh.transform_points([tib_anchor], Tk)[0]
        d = float(np.linalg.norm(p - fem_anchor))
        worst_knee = d if worst_knee is None else min(worst_knee, d)
        tag = 'WARN' if d < MIN_SPAN else 'OK  '
        print(f'   {tag} KNEE loop kfe {kfe:+4d}deg: {d:.1f}mm span (>= {MIN_SPAN:.0f}mm wanted)')

    # ---- HIP loop: coax tunnel-exit zip pair <-> femur x44 zip pair,
    # swept across hfe (haa doesn't change this: it rotates the coax+leg
    # assembly rigidly, both anchors move together).
    coax_anchor = np.array([0, 17, -36])
    fem2_anchor = np.array([44, 0, -23.2])
    M_f = (T([33.8, 11.6, -9.5]) @ rot_z180()
           @ trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    worst_hip = None
    for hfe in [-93, -86, -60, -30, 0, 30, 60, 86, 93]:
        S = rot_about(hfe, [1, 0, 0], [33.8, 11.6, -9.5])
        p = trimesh.transform_points([fem2_anchor], S @ M_f)[0]
        d = float(np.linalg.norm(p - coax_anchor))
        worst_hip = d if worst_hip is None else min(worst_hip, d)
        tag = 'WARN' if d < MIN_SPAN else 'OK  '
        print(f'   {tag} HIP  loop hfe {hfe:+4d}deg: {d:.1f}mm span (>= {MIN_SPAN:.0f}mm wanted)')

    print(f'   worst-case span: KNEE {worst_knee:.1f}mm, HIP {worst_hip:.1f}mm -- '
          f'LA-14 (open, not fixed): both loops fold tighter than the '
          f'{MIN_SPAN:.0f}mm spec across part of the ROM. WARN only (informational; '
          f'does not fail the gate) -- see backlog #18 / LA-14.')
    return False   # WARN-only by design (see docstring) -- never fails the gate


def insertion_checks(servo, pts0):
    """#53 fix (2026-07-11): the coax's femur yoke used to be a rigid closed
    U (integral inboard arm + bridge + integral outboard arm) -- the femur+
    HFE-servo assembly had NO insertion path (this exact sweep, run against
    the pre-fix geometry, was blocked essentially across the whole travel).
    With the inboard arm now a separate bolt-on (coax_hfe_plate.scad),
    verify the assembly can be removed/inserted with the plate OFF: place
    it at its seated pose, sweep it AWAY along the real insertion axis, and
    assert clean (no mid-travel block) all the way out.

    Insertion axis (found by testing all 6 +-X/Y/Z directions on the fixed
    geometry, see coax.scad's own header): +Y (rearward), NOT axial +-X --
    both X directions stay solid-blocked even with the arm gone (the HAA
    housing's own pocket wall blocks -X; the integral outboard arm blocks
    +X). Real assembly: femur approaches from behind the coax (+Y), slides
    forward (-Y) to seat, wheel bolts to the integral outboard boss, THEN
    coax_hfe_plate bolts on to capture the horn."""
    bad = False
    coax = trimesh.load('coax_R.stl')   # plate OFF -- this is the state the
                                         # femur must be insertable/removable in
    femur = trimesh.load('femur_R.stl')
    arm = trimesh.load('knee_arm.stl')
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.75]))
    fem_asm = np.vstack([trimesh.sample.sample_surface(femur, 8000, seed=0)[0],
                         trimesh.sample.sample_surface(arm, 2000, seed=0)[0],
                         trimesh.transform_points(pts0, rot_z180())])
    M = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    seated = trimesh.transform_points(fem_asm, M)
    print('-- #53 insertion sweep (femur+HFE-servo assembly vs coax, plate OFF, +Y) --')
    for t in range(0, 72, 4):
        p = seated.copy()
        p[:, 1] += t
        # exclude the designed disc/boss interface about the hfe X-axis (same
        # r13 convention as the hip-pitch sweep -- legitimate seated contact)
        p = p[np.linalg.norm(p[:, 1:] - [11.6, -9.5], axis=1) > 13]
        n = int(coax.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and t > 0: bad = True   # t=0 (seated) legitimately touches at the disc interfaces
        print(f'   {status} t=+{t:3d}mm: {n} pts')
    return bad


def main():
    servo = servo_mesh()
    pts0 = sample_points(servo)
    bad = False
    do_sweep = '--sweep' in sys.argv
    for part_file, T, label in CASES:
        part = trimesh.load(part_file)
        pts = trimesh.transform_points(pts0, T)
        inside = part.contains(pts)
        n = int(inside.sum())
        if n == 0:
            print(f'OK    {label}: 0 / {len(pts)} servo points inside {part_file}')
            continue
        bad = True
        hits = pts[inside]
        print(f'CUT   {label}: {n} servo points inside {part_file}')
        # cluster report (rounded 2mm grid)
        grid = np.round(hits / 2) * 2
        uniq, counts = np.unique(grid, axis=0, return_counts=True)
        order = np.argsort(-counts)
        for u, c in list(zip(uniq[order], counts[order]))[:8]:
            print(f'        cluster @ ({u[0]:+.0f},{u[1]:+.0f},{u[2]:+.0f})  {c} pts')
    if do_sweep:
        bad = sweep_checks(servo, pts0) or bad
    if '--insertion' in sys.argv or do_sweep:
        bad = insertion_checks(servo, pts0) or bad
    if '--shoulder' in sys.argv or do_sweep:
        bad = shoulder_checks(servo, pts0) or bad
    if '--through' in sys.argv or do_sweep:
        bad = through_hole_checks() or bad
    if '--cable' in sys.argv or do_sweep:
        bad = cable_checks() or bad
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
