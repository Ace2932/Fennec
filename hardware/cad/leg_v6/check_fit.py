#!/usr/bin/env python3
"""leg_v6 fit gate — REAL-geometry collision check.

Places the actual STS3215 mesh (feetech_servo_models/converted_stl/servo.stl,
spline axis moved to the origin to match leg_v6_common's servo frame) at each
part's pocket pose and samples the servo (surface + volume points) against the
printed part's solid. ANY servo point inside the part = the part cuts the
servo. Run after every geometry change:  ../../../.venv/bin/python check_fit.py

Flags: --sweep (kfe/hfe pose sweeps + insertion + shoulder + through-hole +
cable + fastener, all of the below), --insertion (#53 femur-insertion sweep
alone), --shoulder (haa roll sweep alone), --through (LA-21 through-hole
probe alone), --cable (LA-20 cable-loop span sweep alone), --fastener (#67
coax_hfe cap mount-hardware gate alone).

Exit 0 = clean, 1 = interference (clusters printed).
"""
import pathlib
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cad_assets import asset  # noqa: E402  (path insert must come first)

# servo.stl = STS3215_03a v1 (same snapshot as the canonical
# "STS3215_03a v1.3mf") INCLUDING the output horn + bottom wheel bodies the
# 3mf omits. Cross-checked 2026-07-03: the 3mf's bare case matches this
# mesh's case body feature-for-feature (pins/screw bores/spline boss/cap)
# within 0.1mm after a +1.0mm z-origin shift.
# Vendored into this repo (#166) — was an absolute /Users path into the ROOT
# repo, so this gate could only run on one machine.
SERVO = str(asset('servo.stl'))


def servo_mesh():
    m = trimesh.load(SERVO)
    m.apply_translation([-12.5, 0, 0])   # spline axis -> origin (common frame)
    return m


#: Rough bytes per (ray, triangle) candidate pair inside trimesh's pure-numpy
#: ray engine: `barycentric` is (pairs, 3) float64 plus several (pairs,)
#: arrays. Measured against the real thing rather than derived — a chunk of
#: 2000 on servo.stl (42k faces) still peaked at 11.4 GB, which back-solves to
#: about this.
_BYTES_PER_PAIR = 56
#: Memory budget for ONE contains() batch. Everything else in this gate is
#: small, so this effectively sets the whole gate's peak.
#:
#: This exists for trimesh's PURE-NUMPY ray engine, which has no spatial
#: acceleration and tests every ray against every triangle. With embreex
#: installed trimesh uses Embree's BVH instead and never builds that array, so
#: the batching is unnecessary there — but measured, removing it under embree
#: saved 1% (103.4 s vs 104.5 s), because the remaining time is proximity
#: queries and mesh loading, not contains(). Not worth an engine-aware branch,
#: so this stays unconditional and simply costs nothing when embree is present.
CONTAINS_BUDGET_BYTES = 500_000_000


#: Seed for the ray retry below. Any fixed value works; what matters is that
#: it is fixed.
CONTAINS_SEED = 0


def _contains_seeded(mesh, pts):
    """mesh.contains(), made REPRODUCIBLE (#195).

    trimesh casts a ray forward and backward and takes the parity. When the two
    directions disagree and neither is free space, it recurses:

        # try to run again with a new random vector
        new_direction = util.unitize(np.random.random(3) - 0.5)

    That draw is from numpy's GLOBAL RNG, so contains() returns DIFFERENT
    ANSWERS ON IDENTICAL INPUT — measured 3-6 points of 3000 flipping, with no
    two runs agreeing. Every verdict in this gate is a threshold on a count, so
    a flipped surface-adjacent point can turn OK into HIT.

    It is not the engine: embreex (embree) shows the same instability, because
    the retry is in trimesh's parity logic, not the traversal. Seeding fixes it,
    and as a bonus makes contains_chunked() bit-exact against the unbatched
    call, which it was not before.

    The global RNG state is saved and restored, so seeding here cannot reach
    into anything else that draws from np.random.
    """
    state = np.random.get_state()
    try:
        np.random.seed(CONTAINS_SEED)
        return mesh.contains(pts)
    finally:
        np.random.set_state(state)


def contains_chunked(mesh, points, budget=CONTAINS_BUDGET_BYTES):
    """mesh.contains() in bounded-memory batches (#178).

    trimesh has no embree here, so the pure-numpy ray engine broadcasts
    RAYS x TRIANGLES in one array. Against servo.stl that is:

        24,000 query points x 42,166 faces = 1.01e9 elements
        = 8.1 GB per float64 intermediate, ~17.6 GB live

    Measured: that single call was 100% of this gate's 18 GB peak — every
    other phase added 0.00 GB on top of it. Batching caps the intermediate at
    chunk x faces instead of n x faces; at 2000 that is ~0.7 GB.

    NOT bit-identical to one big call, and neither is the unbatched version to
    ITSELF: trimesh's contains() returns different answers on identical input
    run to run, ~0.15% of points (measured: 3-6 of 3000, no two runs agreeing).
    The flipping points are surface-adjacent, where the docstring says the
    behaviour is undefined. So batching costs no more reproducibility than
    re-running already does — but that instability is a real property of this
    gate and is tracked separately, because a verdict of "0 points inside"
    resting on a check that flickers is worth knowing about.
    """
    pts = np.asarray(points)
    # contains_points casts rays BOTH ways, so a batch of C points is 2C rays.
    # Scaling the batch to the FACE COUNT is the point: servo.stl (42k faces)
    # gets ~105 points per call, coax_hfe_plate (2.6k) gets ~1700, and any
    # future mesh sizes itself. A fixed chunk tuned to one mesh is how this was
    # 11 GB after the "fix".
    chunk = max(32, int(budget / (2 * max(1, len(mesh.faces)) * _BYTES_PER_PAIR)))
    if len(pts) <= chunk:
        return _contains_seeded(mesh, pts)
    return np.concatenate(
        [_contains_seeded(mesh, pts[i:i + chunk])
         for i in range(0, len(pts), chunk)])


def min_clearance_chunked(mesh, points, chunk=2000):
    """min(-signed_distance) in bounded-memory batches (#178).

    trimesh.proximity.signed_distance materialises per-candidate arrays for the
    WHOLE query at once. Measured: the ~20 calls sweep_checks makes, each on a
    ~26k-point swept cloud, were 10.8 GB of the gate's peak — the single
    largest consumer left after sample_points was batched.

    Unlike contains(), this one IS exact under batching: min over batches is
    min over the whole set, by definition. The only thing that varies is the
    ~0.15% surface-adjacent instability contains() already has, which
    signed_distance inherits for its SIGN — and these points are pre-filtered
    to the outside, where the sign is stable.
    """
    pts = np.asarray(points)
    if not len(pts):
        return float('inf')
    best = float('inf')
    for i in range(0, len(pts), chunk):
        d = -trimesh.proximity.signed_distance(mesh, pts[i:i + chunk])
        if len(d):
            best = min(best, float(d.min()))
    return best


def sample_points(m, n_surface=15000, n_volume=6000):
    surf, _ = trimesh.sample.sample_surface(m, n_surface, seed=0)
    lo, hi = m.bounds
    vol = np.random.default_rng(0).uniform(lo, hi, (n_volume * 4, 3))
    vol = vol[contains_chunked(m, vol)][:n_volume]
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


# ---- haa envelope, module-level so the drift guard can import it (#157) ----
# MEASURED, not read off a frame comment: the coax->shoulder MIR transform used
# by the cable/shoulder checks is the same one that nearly inverted the hip
# signs in #156 when hand-mapped. Probing points down the leg (foot at coax
# z=-200) through that transform, haa=-40 puts the foot at x=+167.6 while
# haa=+40 puts it at x=-89.5, across the centreline (hip station x=+39.05,
# centreline x=0). So NEGATIVE haa is OUTBOARD in this file's frame.
# Re-derive by running it, never by reading it.
HAA_OUTBOARD_SIGN = -1
# MJCF haa range [-0.262, +0.698] rad = 15deg inboard / 40deg outboard
# (sim/nova_mjx/nova.xml, mirrored per side). nova_ops test_derived_signs.py
# asserts these still match the model, so the gate cannot silently drift.
HAA_OUTBOARD_MAX_DEG = 40.0
HAA_INBOARD_MAX_DEG = 15.0


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
    min_d = min_clearance_chunked(target, p)
    if min_d < floor_mm:
        print(f'   WARN  {label}: clearance floor {min_d:.2f}mm (<{floor_mm:.1f}mm, '
              f'outside the designed-contact mask but a genuine near-miss — see LA-19)')


# ---------------------------------------------------------------------------
# Designed-contact mask (#226, 2026-07-31) -- replaces the old bare "r > 13".
#
# WHY A MASK AT ALL: the bolted disc/boss interfaces at a joint axis overlap BY
# DESIGN, so an unmasked containment sweep reads blocked at every step and says
# nothing. Excluding them is correct. Two rules make the exclusion honest, and
# both were learned by shipping a part that could not be assembled:
#
#  1. RADIUS IS 10.3, NOT 13.  Measured 2026-07-31 across both rotation sweeps:
#     the designed overlap tops out at r = 10.00 EXACTLY (kfe 3.31..10.00, hfe
#     0.67..10.00, identical at every angle). r=13 was 3mm of gratuitous blind
#     spot -- and that annulus is where the #67 horn-bolt regression (BCD r=7)
#     hid, which cost a redesign.
#
#  2. ROTATION SWEEPS ONLY.  The justification is symmetry: a rotationally-
#     symmetric interface cannot be created OR resolved by rotating about its
#     own axis, so masking it discards no information. TRANSLATION has no such
#     symmetry -- a stub nested in a bore is untroubled by rotation and utterly
#     trapped by translation. #226 is exactly that failure: the mask was copied
#     onto the +Y insertion sweep ("same r13 convention as the hip-pitch
#     sweep"), where it swallowed the Ø19 outboard boss (r 0.7..9.5, x 51.6..
#     56.0) that stops the HFE joint assembling. The gate reported CLEAN for
#     its entire existence, on a part Aiden then printed and could not build.
#     insertion_checks() therefore masks NOTHING; see its docstring.
#
# Rule 2 is enforced, not just documented: mask_invariance_check() re-tests the
# masked points and fails if the masked overlap MOVES across the sweep, so a
# future edit cannot quietly park an interference inside the mask the way the
# boss did.
#
# It measures the ENVELOPE of the masked overlap, not its point COUNT. Counting
# was tried first and is far too blunt: designed contact contributes a ~380pt
# baseline carrying ~10% surface-sampling noise, so deliberately widening the
# mask until it swallowed a REAL collision (the hfe mech stop at +-95/100deg)
# moved the count only 10% -> 15% and the check stayed quiet. Measured on the
# same planted case, the envelope is not swamped, because designed contact sits
# in a FIXED (r, axial) box and interference has to push a corner of it:
#
#     mask r=10.3 (sound)   drift: r_max 0.00mm, ax_min 0.00mm, ax_max 0.02mm
#     mask r=20.0 (planted) drift: r_max 10.00mm, ax_min 0.00mm, ax_max 39.66mm
#
# ~500x separation instead of 1.5x. The threshold below sits 50x above the
# observed noise and 10x below the observed signal.
DESIGNED_CONTACT_R = 10.3
MASK_DRIFT_MM = 1.0
#: Points allowed to overlap at the SEATED pose (t=0) of the insertion sweep.
#: Measured 0 on the current geometry. Raising this is a deliberate act that
#: needs a reason in the commit, not a knob to turn when the gate goes red.
SEATED_OVERLAP_EXPECTED = 0


def mask_invariance_check(envelopes, label):
    """Assert the designed-contact mask is hiding designed contact.

    `envelopes` = per-sweep-step (n, r_max, axial_min, axial_max) of the points
    the mask excluded that were actually inside the target. Designed contact is
    rotation-invariant: the same interface overlaps the same way at every
    angle, so its envelope is fixed to within sampling noise. An envelope that
    MOVES means the masked region contains something the sweep is genuinely
    travelling through -- i.e. the mask is concealing interference, and every
    'OK' this sweep printed is worth nothing.
    """
    live = [e for e in envelopes if e[0] > 0]
    if not live:
        return False        # nothing masked -> nothing to justify
    if len(live) < 2:
        # Drift is a spread across steps; one step has no spread and would
        # report a flat 0.00mm -- an "OK" that checked nothing. Say so instead.
        print(f'   NOTE  {label}: only {len(live)} sweep step masked anything, '
              f'so invariance is INCONCLUSIVE here (a single sample cannot '
              f'drift). Not evidence the mask is sound.')
        return False
    arr = np.array([e[1:] for e in live], dtype=float)
    drift = arr.max(axis=0) - arr.min(axis=0)
    ns = [e[0] for e in live]
    if drift.max() > MASK_DRIFT_MM:
        print(f'   MASK  {label}: the masked-out overlap MOVES across the sweep '
              f'(drift r_max {drift[0]:.2f}mm, axial {drift[1]:.2f}/{drift[2]:.2f}mm '
              f'> {MASK_DRIFT_MM}mm). That is not designed contact, it is '
              f'interference hiding inside the r{DESIGNED_CONTACT_R} mask, so this '
              f'sweep\'s OK verdicts are void. See #226.')
        return True
    print(f'   OK    {label}: masked-out overlap fixed to '
          f'{drift.max():.2f}mm across the sweep ({min(ns)}..{max(ns)} pts) '
          f'-- consistent with designed contact')
    return False


def _mask_envelope(inside, radial, axial):
    """(n, r_max, axial_min, axial_max) of the masked points that are inside."""
    n = int(inside.sum())
    if n == 0:
        return (0, 0.0, 0.0, 0.0)
    return (n, float(radial[inside].max()),
            float(axial[inside].min()), float(axial[inside].max()))


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
    print(f'   (points within r{DESIGNED_CONTACT_R} of the joint axis excluded: the bolted')
    print('    disc/boss interfaces overlap BY DESIGN, rotation-symmetric.')
    print('    The exclusion is re-tested for invariance below -- see #226)')
    kfe_masked = []
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
        p_all = trimesh.transform_points(tib_pts, T)
        r_all = np.linalg.norm(p_all[:, :2] - [106.9, 0], axis=1)
        near = r_all <= DESIGNED_CONTACT_R
        p = p_all[~near]
        # envelope what the mask throws away, so mask_invariance_check() can
        # prove it is designed contact and not a hidden obstruction (#226).
        # kfe axis is Z -> axial coordinate is z.
        pm = p_all[near]
        kfe_masked.append(_mask_envelope(
            contains_chunked(femur, pm) | contains_chunked(arm, pm),
            r_all[near], pm[:, 2]))
        inside_fem = contains_chunked(femur, p)
        inside_arm = contains_chunked(arm, p)
        n = int(inside_fem.sum()) + int(inside_arm.sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 109: bad = True   # hits beyond sw limit are the mech stop
        print(f'   {status} kfe {ang:+4d}deg: {n} pts')
        if n == 0 and abs(ang) <= 109:
            _clearance_warn(femur, p, f'kfe {ang:+4d}deg vs femur')
            _clearance_warn(arm, p, f'kfe {ang:+4d}deg vs knee_arm')
    # #226 option C: the inboard arm is INTEGRAL now, and the removable member
    # is the OUTBOARD block -- union THAT into the "coax" solid for the SEATED
    # hip-pitch sweep, since the assembled leg carries it (both parts are
    # defined in the same coax world frame at identity, no transform needed).
    coax = trimesh.util.concatenate([trimesh.load('coax_R.stl'),
                                      trimesh.load('coax_hfe_block.stl')])
    fem_asm = np.vstack([trimesh.sample.sample_surface(femur, 5000, seed=0)[0],
                         trimesh.sample.sample_surface(arm, 1500, seed=0)[0],
                         trimesh.transform_points(pts0, rot_z180())])
    M = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    print('-- hip pitch sweep (femur assembly vs coax+coax_hfe_block)')
    hfe_masked = []
    # LA-19a: extended past the sw limit (86) to ±90/95/100 to pin the mech
    # stop, same pattern as the kfe sweep's 109/118. Measured (2026-07-11,
    # 0.5deg-resolution bisection): clean through ±92.5deg, first contact at
    # +93deg (1 pt) / -93deg (3 pts) -- symmetric mech stop at ~93deg.
    for ang in [-100, -95, -90, -86, -60, -30, 30, 60, 86, 90, 95, 100]:
        S = rot_about(ang, [1, 0, 0], [33.8, 11.6, -9.5])
        # place femur (M), then rotate about the hfe axis (S)
        p_all = trimesh.transform_points(
            trimesh.transform_points(fem_asm, M), S)
        # exclude the designed disc/boss interface about the hfe X-axis, and
        # keep the excluded points so the exclusion can be justified (#226)
        # hfe axis is X -> axial coordinate is x
        r_all = np.linalg.norm(p_all[:, 1:] - [11.6, -9.5], axis=1)
        near = r_all <= DESIGNED_CONTACT_R
        p, pm = p_all[~near], p_all[near]
        hfe_masked.append(_mask_envelope(
            contains_chunked(coax, pm), r_all[near], pm[:, 0]))
        n = int(contains_chunked(coax, p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 86: bad = True   # hits beyond sw limit (86) document the mech stop (~93deg), same convention as kfe
        print(f'   {status} hfe {ang:+4d}deg: {n} pts')
        if n == 0 and abs(ang) <= 86:
            _clearance_warn(coax, p, f'hfe {ang:+4d}deg vs coax')
    print('-- designed-contact mask invariance (#226: the mask must hide only '
          'designed contact) --')
    bad = mask_invariance_check(kfe_masked, 'kfe fold mask') or bad
    bad = mask_invariance_check(hfe_masked, 'hfe pitch mask') or bad
    return bad


def shoulder_checks(servo, pts0):
    """Shoulder vs the swinging leg about the haa axis (Y-line at x=39.05,
    z=0). Right hip; the left is the mirror. Leg assembly = coax (+its
    servo) + femur + tibia + knee_arm, mounted horn-forward (mirror-Y of
    the coax frame — see the chirality note in the design memory)."""
    bad = False
    sh = trimesh.load('shoulder.stl')
    pl = trimesh.load('shoulder_plate.stl')
    # #226 option C: removable member is the outboard block (see sweep_checks)
    coax = trimesh.util.concatenate([trimesh.load('coax_R.stl'),
                                      trimesh.load('coax_hfe_block.stl')])
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
        n = int(contains_chunked(sh, p).sum()) + int(contains_chunked(pl, p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 40: bad = True   # beyond 40 = documenting stops
        print(f'   {status} haa {ang:+4d}deg: {n} pts')
    # HAA horn SEATING (2026-07-11, user catch: "does the plate reach the coax
    # horn or float short?"): the sweep above only checks ABSENCE of
    # interpenetration, never that shoulder_plate positively SEATS on the servo
    # horn. Measure it at ang=0: the plate's horn-coupling region must CONTACT
    # the horn disc (small press), not sit with a gap. horn = servo pts at the
    # output-horn z-band (HORN_Z0..Z1 14.7..17.75) within the Ø20 disc, mapped
    # servo->coax->shoulder frame.
    horn0 = pts0[(pts0[:, 2] > 14.0) & (pts0[:, 2] < 18.0)
                 & (np.hypot(pts0[:, 0], pts0[:, 1]) <= 10.5)]
    horn_sh = trimesh.transform_points(
        trimesh.transform_points(horn0, coax_pose()), base)
    seat = float(trimesh.proximity.closest_point(pl, horn_sh)[1].min())
    ok = seat <= 0.5
    print(f"   {'OK ' if ok else 'GAP'} haa horn seat: plate<->horn min "
          f"{seat:.2f}mm (want <=0.5 = seated, not floating short)")
    if not ok: bad = True
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
        if contains_chunked(mesh, pts).any():
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
    # LA-30 (2026-07-16): second KNEE-loop anchor pair, farther from the kfe
    # axis than x44 (which stays the tunnel-exit strain relief) -- see
    # tibia.scad's own zip_pair_neg(58, ...) comment for the rationale.
    ('x58', 58, -5, -23.2, 16.8), ('x58', 58, 5, -23.2, 16.8),
    ('x62', 62, 0, -23.2, 16.8),
    ('x84', 84, 0, -23.2, 16.8),
]
# coax.scad's side-wall zip exits run along local X (rotate([0,sx*90,0]) on a
# Z-cylinder); BLK_X-6 = 16.05-6 = 10.05 (leg_v6_common.scad CASE_HW+
# CLR_POCKET+WALL).
COAX_R_ZIP_HOLES_X = 7.0
COAX_R_ZIP_HOLES_H = 16.05 - 6
# LA-29 (2026-07-16): HAA connector-bay zip anchor -- same X-axis/Ø3.2 style
# as the tunnel-exit pair above, sited near the rear (+Y) connector-bay face
# instead (see coax.scad's own comment on this pair for the (y,z) siting
# rationale). Same COAX_R_ZIP_HOLES_X/H reuse (identical wall geometry).
COAX_HAA_ZIP_Y = 19.0
COAX_HAA_ZIP_Z = -27.0

# LA-30 (2026-07-16, coordinator follow-up to the #7-fix session): two zip-
# tie bore classes existed with NO through-hole gate at all until now --
# both converted from self-tap pilots this same session and both bit a
# first-article probe before landing here (a blind-pocket regression class
# this table exists to catch, per LA-21's own header):
#   * tibia.scad's strap_pilot_neg() call (leg_v6_common.scad, CONVERTED
#     2026-07-16 from a self-tap pilot -- x0=31, wall_y=14.25, rim_z=
#     SLAB_Z1+3.2=17.9): real bore is Z-axis at (31, +/-(14.25+ZIP_Y_OUT)=
#     +/-15.60), z0=FLOOR_BOT-3=-25.2 .. z1=17.9. tibia_L is the SAME
#     Z-mirror convention as TIBIA_R_ZIP_HOLES above (tibia_L.scad:
#     mirror([0,0,1])) -- same (x0,y0), z-range negated.
#   * coax.scad's OWN separate front-strap-pilot cut (different axis/face,
#     doesn't call strap_pilot_neg() -- see that file's header), also
#     CONVERTED 2026-07-16: Y-axis bore at x=+/-(14.25+ZIP_Y_OUT)=+/-15.60,
#     z=-31, y spanning the pad face (-18.6) to well past the rear corner-
#     notch exit (21.0) -- the notch itself was MIRRORED this same pass
#     (coax.scad's corner-notch cut, was +X only) after a probe caught the
#     -X/coax_L +X bore landing in a genuine ~1.2mm blind plug there.
#     coax_L is coax.scad's own X-mirror convention (mirror([1,0,0])) --
#     same y-span, x negated.
TIBIA_STRAP_ZIP_HOLES = [
    ('strap', 31, 15.60, -25.2, 17.9),
    ('strap', 31, -15.60, -25.2, 17.9),
]
COAX_STRAP_ZIP_X = 14.25 + 1.35    # == leg_v6_common.scad's 14.25+ZIP_Y_OUT
COAX_STRAP_ZIP_Z = -31.0
COAX_STRAP_ZIP_Y0 = -18.6
COAX_STRAP_ZIP_Y1 = 21.0


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
    # LA-30 (2026-07-16): tibia's strap_pilot_neg() zip bores, same Z-mirror
    # convention as TIBIA_R_ZIP_HOLES above.
    for label, x0, y0, z0, z1 in TIBIA_STRAP_ZIP_HOLES:
        bad |= check('tibia_R.stl', f'{label} y={y0:+.2f}', [x0, y0, 0], [0, 0, 1], z0, z1)
        bad |= check('tibia_L.stl', f'{label} y={y0:+.2f}', [x0, y0, 0], [0, 0, 1], -z1, -z0)
    # LA-30 (2026-07-16): coax's own front-strap zip bores (Y-axis, NOT the
    # X-axis convention the tunnel-exit/HAA-bay pairs below use) -- coax_L is
    # coax.scad's own X-mirror (mirror([1,0,0])): same y-span, x negated.
    for sx in (1, -1):
        x0 = sx * COAX_STRAP_ZIP_X
        bad |= check('coax_R.stl', f'strap sx={sx:+d}', [x0, 0, COAX_STRAP_ZIP_Z],
                     [0, 1, 0], COAX_STRAP_ZIP_Y0, COAX_STRAP_ZIP_Y1)
        bad |= check('coax_L.stl', f'strap sx={sx:+d}', [-x0, 0, COAX_STRAP_ZIP_Z],
                     [0, 1, 0], COAX_STRAP_ZIP_Y0, COAX_STRAP_ZIP_Y1)
    for sx in (1, -1):
        x0 = sx * COAX_R_ZIP_HOLES_X
        t_lo, t_hi = sorted([x0, x0 + sx * COAX_R_ZIP_HOLES_H])
        bad |= check('coax_R.stl', f'zip sx={sx:+d}', [0, 17, -36], [1, 0, 0], t_lo, t_hi)
        # coax_L = X-mirror of coax_R (coax_L.scad: mirror([1,0,0]))
        bad |= check('coax_L.stl', f'zip sx={sx:+d}', [0, 17, -36], [1, 0, 0], -t_hi, -t_lo)
    # LA-29 (2026-07-16): HAA connector-bay zip anchor -- same geometry
    # convention as the tunnel-exit pair just above, different (y,z) siting.
    for sx in (1, -1):
        x0 = sx * COAX_R_ZIP_HOLES_X
        t_lo, t_hi = sorted([x0, x0 + sx * COAX_R_ZIP_HOLES_H])
        bad |= check('coax_R.stl', f'zip-haa sx={sx:+d}',
                     [0, COAX_HAA_ZIP_Y, COAX_HAA_ZIP_Z], [1, 0, 0], t_lo, t_hi)
        bad |= check('coax_L.stl', f'zip-haa sx={sx:+d}',
                     [0, COAX_HAA_ZIP_Y, COAX_HAA_ZIP_Z], [1, 0, 0], -t_hi, -t_lo)
    # HAA rear-arm wheel-bolt holes (2026-07-11, user catch: "the rear shoulder
    # holes don't look cut"): 4/station on the Ø14 BCD about each haa axis
    # (sx*HIP_X=39.05, z=0), drilled along +Y through the rear wall (-26.6..
    # -22.6) + wheel boss to the wheel face (-17.75). Confirmed present, but
    # never gated -> lock them in.
    for sx in (1, -1):
        for a in (45, 135, 225, 315):
            hx = sx*39.05 + 7.0*np.cos(np.radians(a))
            hz = 7.0*np.sin(np.radians(a))
            bad |= check('shoulder.stl', f'haa-wheel sx={sx:+d} a={a:3d}',
                         [hx, 0, hz], [0, 1, 0], -26.6, -17.75)
    return bad


def cable_checks():
    """LA-20: check_fit never swept cable geometry -- the exact blind-spot
    class that would have caught LA-14 (the 1e5 cyc/hr service loops forced
    tighter than the design's own >=40mm bend-radius spec, backlog #18).
    Places the documented zip-tie anchor points (cable_clip.scad's own
    pairing: "coax tunnel-exit pair + femur x44 pair = the HIP loop
    (haa+hfe)"; "femur x84 (yoke plate) + tibia x58 pair = the KNEE loop
    (kfe)") at the LITERAL translate() coordinates each anchor is cut at in
    the .scad (coax.scad:170, femur.scad:148/153, tibia.scad's zip_pair_neg
    calls), and sweeps their 3D separation with the SAME kfe/hfe transforms
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
    pass).

    LA-29 (cable-management review, 2026-07-16): added a 3rd case, the HAA
    loop -- coax.scad's new +Y connector-bay zip anchor (this review) vs
    the shoulder's own fixed Ø12 flange grommet (shoulder.scad, read-only
    this session; "2x Ø12 cable grommets at (+/-32,-26)", the trunk<->C-box
    interface -- the only fixed anchor available on that side). Same
    coax->shoulder transform shoulder_checks() already uses (mirror-Y, then
    translate to the hip station), same haa sweep angles (sw +/-40, mech
    stop ~+/-45). The grommet doesn't move (fixed to the shoulder); only
    the coax-side anchor sweeps with haa.

    LA-30 (same review): the KNEE loop's tibia-side anchor moved from x44
    to a NEW, dedicated x58 pair (x44 stays, now only the tunnel-exit
    strain relief -- see tibia.scad's own comment) to close some of the
    39.2mm-at-kfe118 gap found by LA-14. Anchor-radius law of cosines makes
    the tibia-side radius the dominant lever (the femur-side anchor barely
    moves the worst case) -- see tibia.scad for the full geometric
    rationale. Worst-case span improved 39.2mm -> ~51.6mm (still short of
    the 80mm target -- best achievable via anchor relocation alone without
    moving the loop noticeably farther from the actual knee crossing; the
    fold-before-zip discipline still covers the remaining shortfall)."""
    print('-- LA-20: cable service-loop anchor separation vs ROM (backlog #18, >=40mm bend radius) --')
    MIN_SPAN = 80.0   # 2 x the >=40mm min bend radius (backlog #18)
    T = trimesh.transformations.translation_matrix

    # ---- KNEE loop: femur x84 (yoke-crossing zip pair) <-> tibia x58
    # (LA-30, 2026-07-16: dedicated KNEE-loop pair, farther from the kfe
    # axis than the x44 tunnel-exit pair -- see tibia.scad), swept across kfe.
    fem_anchor = np.array([84, 0, -27.6])
    tib_anchor = np.array([58, 0, -23.2])
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

    # ---- HAA loop (LA-29, 2026-07-16): coax's new +Y connector-bay zip
    # anchor <-> the shoulder's fixed Ø12 flange grommet. Same coax->
    # shoulder transform as shoulder_checks() (mirror-Y, then translate to
    # the right hip station); the grommet is FIXED (on the shoulder), only
    # the coax-side anchor sweeps with haa.
    HIP_T = T([39.05, 0, 0])
    MIR = np.eye(4); MIR[1, 1] = -1
    base_cs = HIP_T @ MIR   # coax frame -> shoulder frame (right hip)
    haa_anchor = np.array([0, 19, -27])          # coax.scad's new pair midpoint (x=+/-7 avg 0)
    grommet = np.array([32, -75.7, -26])         # shoulder.scad Ø12 grommet bore midpoint
    # #157: this used to sweep a SYMMETRIC [-45..+45], which measured 40deg of
    # INBOARD travel the robot is not permitted to use while sampling the legal
    # outboard travel once. Sweep the real, asymmetric envelope instead.
    #
    # Sign and envelope live at module scope (see the block above rot_about) so
    # the nova_ops drift guard can import them.
    def _haa_samples():
        out = [HAA_OUTBOARD_SIGN * a for a in (40, 30, 20, 10, 0)]
        inb = [-HAA_OUTBOARD_SIGN * a for a in (5, 10, 15)]
        return out + inb

    print(f'   HAA envelope swept: {HAA_INBOARD_MAX_DEG:.0f}deg inboard .. '
          f'{HAA_OUTBOARD_MAX_DEG:.0f}deg outboard (asymmetric; '
          f'outboard = {"-" if HAA_OUTBOARD_SIGN < 0 else "+"}haa here)')
    worst_haa = None
    best_haa = None
    for haa in _haa_samples():
        S = rot_about(haa, [0, 1, 0], [39.05, 0, 0])
        p = trimesh.transform_points([haa_anchor], base_cs)[0]
        p = trimesh.transform_points([p], S)[0]
        d = float(np.linalg.norm(p - grommet))
        worst_haa = d if worst_haa is None else min(worst_haa, d)
        best_haa = d if best_haa is None else max(best_haa, d)
        tag = 'WARN' if d < MIN_SPAN else 'OK  '
        side = 'neutral ' if haa == 0 else (
            'OUTBOARD' if np.sign(haa) == HAA_OUTBOARD_SIGN else 'inboard ')
        print(f'   {tag} HAA  loop haa {haa:+4d}deg ({side}): {d:.1f}mm span '
              f'(>= {MIN_SPAN:.0f}mm wanted)')
    # The EXCURSION is the fatigue-relevant number at a ~1e5 cyc/hr joint: the
    # static minimum is what MIN_SPAN tests, but it is the swing between the
    # extremes that flexes the loop. Unlocking the 40deg splay (#156/#157)
    # leaves the minimum untouched -- it sits at the inboard limit, inside the
    # old +/-15 lock -- while roughly TRIPLING this, 1.71mm -> 5.26mm.
    print(f'   HAA  loop excursion across the envelope: '
          f'{best_haa - worst_haa:.2f}mm ({worst_haa:.1f}..{best_haa:.1f}mm)')

    print(f'   worst-case span: KNEE {worst_knee:.1f}mm, HIP {worst_hip:.1f}mm, '
          f'HAA {worst_haa:.1f}mm -- LA-14 (open, not fixed): all three loops fold '
          f'tighter than the {MIN_SPAN:.0f}mm spec across part of the ROM. WARN only '
          f'(informational; does not fail the gate) -- see backlog #18 / LA-14 / '
          f'LA-29 / LA-30.')
    return False   # WARN-only by design (see docstring) -- never fails the gate


def insertion_checks(servo, pts0):
    """#53 fix (2026-07-11): the coax's femur yoke used to be a rigid closed
    U (integral inboard arm + bridge + integral outboard arm) -- the femur+
    HFE-servo assembly had NO insertion path (this exact sweep, run against
    the pre-fix geometry, was blocked essentially across the whole travel).
    #226 option C (2026-07-31): the removable member is the OUTBOARD block
    now, so "with the removable part off" means coax_R.stl itself -- the
    outboard arm has left for coax_hfe_block.scad. Verify the assembly can be
    removed/inserted in that state: place it at its seated pose, sweep it AWAY
    along the real insertion axis, and assert clean all the way out.

    INSERTION AXIS IS NOW +X (2026-07-31). It used to be +Y, and this
    docstring used to record "+X blocked by the integral outboard arm" as the
    reason. Option C makes that arm removable, which is exactly what opens +X:
    measured 0 points over t=2..50mm. Real assembly: femur enters axially from
    outboard (-X to seat), THEN the block slides on (-X) and its 2x M3
    retention bolts are driven from +X open air -- the driver access the
    inboard cap never had.

    #226 (2026-07-31) -- THIS SWEEP MASKS NOTHING, AND MUST NOT.
    It used to drop every point within r13 of the hfe axis, inheriting the
    rotation sweeps' designed-contact mask verbatim ("same r13 convention as
    the hip-pitch sweep"). That convention does not transfer. The rotation
    mask is justified by SYMMETRY -- a rotationally-symmetric interface can
    be neither created nor resolved by rotating about its own axis, so
    discarding it discards nothing. A TRANSLATION has no such symmetry: a
    stub nested in a bore is perfectly happy under rotation and completely
    trapped under translation, which is precisely the geometry an insertion
    sweep exists to interrogate. The mask therefore deleted this gate's own
    subject.

    What it hid, measured: the Ø19 integral OUTBOARD boss, r 0.7..9.5 (well
    inside r13), x 51.6..56.0, ploughing the femur hub over 24mm of travel --
    327 points across t=4..24mm, reported as a clean 0. Aiden printed the
    part; it will not assemble.

    And the mask was never even load-bearing: at t=0 (seated) it suppresses
    ZERO points, so the "legitimate seated contact" it was justified by does
    not exist in this pose. It was pure loss. Designed seated contact, if a
    future revision has any, is handled by the t=0 exemption below -- which
    is asserted, not assumed, so it cannot become the next hiding place."""
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
    print('-- #226 insertion sweep (femur+HFE-servo vs coax, BLOCK OFF, +X) --')
    print('   (NO radial mask -- see #226 in the docstring; a translation sweep '
          'cannot mask its own axis)')
    blocked_t = []
    for t in range(0, 72, 2):
        p = seated.copy()
        p[:, 0] += t          # +X: axial, see the docstring
        inside = contains_chunked(coax, p)
        n = int(inside.sum())
        status = 'OK ' if n == 0 else 'HIT'
        # t=0 (seated) may legitimately touch at the disc interfaces, so it is
        # exempt from the travel test -- but the exemption is bounded by a
        # DECLARED expectation rather than being open-ended. Measured today the
        # seated pose overlaps by 0 points, so any overlap at all is new and
        # must be justified by whoever introduces it, not absorbed silently.
        # (An earlier revision of this block only printed a NOTE here while the
        # comment claimed it "asserted" the exemption -- a WARN wearing an
        # assertion's label, which is the exact thing this gate exists to stop.)
        if t == 0 and n > SEATED_OVERLAP_EXPECTED:
            bad = True
            print(f'SEAT  t=0 (seated): {n} pts overlap, expected '
                  f'<={SEATED_OVERLAP_EXPECTED}. Either the seat pose is wrong -- '
                  f'in which case every later step is measured from a bad origin '
                  f'-- or a real disc interface was introduced, in which case '
                  f'raise SEATED_OVERLAP_EXPECTED deliberately and say why.')
        if n and t > 0:
            bad = True
            blocked_t.append(t)
            # name the obstruction: where it is in (r, x) is what tells you
            # WHICH feature to change. #226 was found exactly this way.
            q = p[inside]
            r = np.linalg.norm(q[:, 1:] - [11.6, -9.5], axis=1)
            print(f'   {status} t=+{t:3d}mm: {n} pts  r {r.min():5.2f}..{r.max():5.2f}'
                  f'  x {q[:, 0].min():6.2f}..{q[:, 0].max():6.2f}')
        else:
            print(f'   {status} t=+{t:3d}mm: {n} pts')
    if blocked_t:
        print(f'BLOCK insertion sweep: the femur+HFE-servo assembly cannot be '
              f'withdrawn -- obstructed over t=+{min(blocked_t)}..+{max(blocked_t)}mm '
              f'({len(blocked_t)} of {len(range(2, 72, 2))} travel steps). The joint '
              f'does not assemble. See #226.')
    return bad


# ---------------------------------------------------------------------------
# REMOVABLE-MEMBER INSTALLABILITY (#226 follow-up, 2026-07-31)
#
# THE STEP NOTHING MODELLED. Four gates covered this joint -- the insertion
# sweep, the horn-bolt channels, the #67 fastener gate, the orientation gate --
# and all four were green on a part that cannot be built. The reason is that
# every one of them checked something OTHER than the step that actually fails:
#
#   insertion_checks   sweeps the FEMUR, with the cap OFF
#   horn_bolt_checks   scans bolt CHANNELS through the stub
#   #67 fastener gate  checks the cap's heat-set is reachable and backed
#   orientation gate   proves the servo seats one way round
#
# Nobody ever swept the CAP. Measured 2026-07-31, coax_hfe_plate is blocked in
# all six axes -- against the seated femur AND against a bare coax, in the
# current revision AND in the pre-#7-fix one. Its seated pose is legitimate
# (boolean intersection with the coax is 0.0 mm3), so it is a valid final
# position with no way to reach it: a ship in a bottle. That is exactly what
# Aiden reported from the bench ("doesn't really slide in") -- not a tolerance
# problem, no path at all.
#
# CRITERION. A keyed member is SUPPOSED to be constrained in most directions;
# that is what a key does. The failure is having NO free direction. So this
# passes if AT LEAST ONE axis is clear across the whole travel, and fails only
# when the member is enclosed on every one. Along its true install axis a
# slip-fit part slides out cleanly from t=0, so "clear" means zero blocked
# steps, not "few".
#
# LIMIT, stated because it bounds the verdict: rigid-body TRANSLATION along six
# axes. It does not model rotation, compound paths, or elastic snap-fit. A part
# this gate passes is installable; a part it fails might still go in with a
# twist -- but nothing in this joint is designed to, and the printed part did
# not.
REMOVABLE_MEMBERS = [
    # (member, side, obstacles that are already in place when it is installed)
    ('coax_hfe_plate.stl', 'R', 'coax_R.stl'),
    ('coax_hfe_plate_L.stl', 'L', 'coax_L.stl'),
]
INSTALL_DIRS = [('+X', (1, 0, 0)), ('-X', (-1, 0, 0)),
                ('+Y', (0, 1, 0)), ('-Y', (0, -1, 0)),
                ('+Z', (0, 0, 1)), ('-Z', (0, 0, -1))]


def _seated_obstacles(side, servo, pts0):
    """Everything already in place when the removable member goes on.

    The femur+HFE-servo is seated first (coax.scad's own documented order), so
    the member has to reach its seat past a loaded joint, not an empty one.
    """
    sx = 1.0 if side == 'R' else -1.0
    mirror = np.eye(4)
    mirror[0, 0] = sx
    M = (mirror
         @ trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    femur = trimesh.load(f'femur_{side}.stl')
    femur.apply_transform(M if side == 'R' else M @ mirror)
    srv = servo.copy()
    srv.apply_transform(M @ rot_z180())
    return [('femur', femur), ('servo', srv)], sx


def removable_member_checks(servo, pts0):
    print('-- removable-member installability (#226: the step no gate modelled) --')
    bad = False
    for member_file, side, coax_file in REMOVABLE_MEMBERS:
        member = trimesh.load(member_file)
        pts = trimesh.sample.sample_surface(member, 12000, seed=0)[0]
        obstacles, sx = _seated_obstacles(side, servo, pts0)
        obstacles = [('coax', trimesh.load(coax_file))] + obstacles

        free, report = [], []
        for label, d in INSTALL_DIRS:
            v = np.array(d, float) * np.array([sx, 1.0, 1.0])
            blocked = []
            for t in range(2, 42, 2):
                p = pts + v * t
                if any(int(contains_chunked(ob, p).sum()) for _, ob in obstacles):
                    blocked.append(t)
            if blocked:
                report.append(f'{label} blocked {blocked[0]}..{blocked[-1]}mm')
            else:
                free.append(label)
        if free:
            print(f'   OK    {member_file}: installable along {", ".join(free)}')
        else:
            bad = True
            print(f'TRAP  {member_file}: enclosed on ALL {len(INSTALL_DIRS)} axes with '
                  f'the femur+servo seated -- it has a valid seat and no way to '
                  f'reach it. Cannot be assembled at any tolerance. See #226.')
            print(f'        ({"; ".join(report)})')

    # SELF-TEST: a member parked clear of everything must read installable, or
    # this gate is stuck-on-fail and its TRAP verdicts mean nothing.
    ctrl = trimesh.load(REMOVABLE_MEMBERS[0][0])
    ctrl.apply_transform(trimesh.transformations.translation_matrix([0, 120, 0]))
    cpts = trimesh.sample.sample_surface(ctrl, 4000, seed=0)[0]
    coax = trimesh.load('coax_R.stl')
    free_ctrl = [lab for lab, d in INSTALL_DIRS
                 if not any(int(contains_chunked(coax, cpts + np.array(d, float) * t).sum())
                            for t in range(2, 42, 2))]
    if len(free_ctrl) != len(INSTALL_DIRS):
        bad = True
        print(f'   FAIL  self-test: a member parked 120mm clear read as blocked on '
              f'{len(INSTALL_DIRS) - len(free_ctrl)} axes -- this gate is broken, '
              f'ignore its verdicts above')
    else:
        print(f'   OK    self-test: a member parked clear reads installable on all '
              f'{len(INSTALL_DIRS)} axes (gate is not stuck-on-fail)')
    return bad


# #67 fix (2026-07-12): mount-hardware gate for the coax_hfe cap's fastener.
# A prior attempt against this same joint (rejected, never merged) added a
# FASTENER_GROUPS mechanism with genuinely axis-general MERGE/dot checks but
# a reachability check hardcoded to a Z-axis captured-nut model -- when that
# attempt's own redesign moved the fastener to a different axis, it shipped
# `holes=[]` to silence the check by omission instead of generalizing it,
# and (separately, the actual rejection reason) ended up threading directly
# into the coax's own PA6-CF with no insert at all -- a self-tap, which is
# never allowed here regardless of the gate.
#
# THIS design (coax.scad's coax_hfe_ear_channel()/coax_hfe_fastener_neg()):
# a real M3 heat-set (HEATSET_D/HEATSET_L) embedded axis +Y in the
# INTEGRAL stub/bridge (coax_R.stl / coax_L.stl), reached through a
# clearance hole + SHCS head counterbore in the removable CAP
# (coax_hfe_plate.stl / _L.stl). The two parts are different meshes, so the
# check below verifies BOTH sides explicitly and axis-generally (no
# hardcoded Z assumption): the stub's heat-set channel is open to a TRUE
# exterior point (well outside the part's own bounding box, not just an
# internal cavity) along `axis`, the heat-set bore itself has real solid
# material backing its blind end, and the cap's own clearance span is open
# along the same axis/position.
NUT_M3_AC     = 6.35    # kept for MERGE spacing on any future captured-nut
                         # group; unused by the heat-set group below (its own
                         # bore_d/head_d drive the merge/clearance checks)
MIN_DOT_DEPTH = 0.5      # a side-marker dimple must cut at least this deep

# leg_v6_common.scad constants (OpenSCAD-side; mirrored here byte-for-byte --
# `include` doesn't reach across into this Python gate)
M3_CLEAR  = 3.4    # general M3 clearance
HEATSET_D = 4.0    # Ruthex M3 insert bore
HEATSET_L = 6.2    # bore depth: 5.7 insert + 0.5 seat

# (cap_part, stub_part, hole (x,y,z) = where the cap's clearance ends and
# the stub's heat-set begins (coax.scad's EAR_Y0), axis = unit direction
# FROM the heat-set's blind end TOWARD the open exterior face, bore_d =
# bolt shank clearance, head_d = SHCS head counterbore dia, heatset_d/_l =
# real insert bore dia/length, dot_off = (f1,f2) reference-point offsets
# used to probe "nearby flat face" depth -- this cap's own mid-band wall is
# only 1.4mm wide (x) x 6.8mm tall (z), far smaller than the OLD full-disc
# plate's, so the offsets are sized to that wall (not the old 4mm default,
# which would sample points off the part entirely), dots = marker-dot
# probes (dx,dy,dz,nx,ny,nz))
# RIGHT cap gets 1 marker dot (LA-2 convention); LEFT gets 2 (the base dot,
# mirrored, plus its own 2nd disambiguation dot -- see coax_hfe_plate_L.
# scad's header).
# #226 option C (2026-07-31): retargeted from the retired inboard cap to the
# OUTBOARD block. Two M3 now instead of one, bored -X from the mortise blind
# end (x=MORT_X0=43.8) into the grown bridge, driven from +X open air -- so
# `axis` (blind end -> exterior) is +X on the R part and -X on the mirrored L.
# That access is the whole reason the removable member moved outboard: the cap
# had 0.8-4.5mm of driver run where 15-20mm was needed.
FASTENER_GROUPS = [
    dict(cap_part='coax_hfe_block.stl', stub_part='coax_R.stl',
         holes=[(43.8, 5.0, 12.5), (43.8, 18.0, 12.5)], axis=(1, 0, 0),
         bore_d=M3_CLEAR, head_d=6.0, heatset_d=HEATSET_D, heatset_l=HEATSET_L,
         dot_off=(0, 1.4),
         dots=[(60.15, 21.6, -21.5, 1, 0, 0)]),
    dict(cap_part='coax_hfe_block_L.stl', stub_part='coax_L.stl',
         dot_off=(0, 1.4),
         holes=[(-43.8, 5.0, 12.5), (-43.8, 18.0, 12.5)], axis=(-1, 0, 0),
         bore_d=M3_CLEAR, head_d=6.0, heatset_d=HEATSET_D, heatset_l=HEATSET_L,
         dots=[(-60.15, 21.6, -21.5, -1, 0, 0), (-60.15, 21.6, -18.5, -1, 0, 0)]),
]


def fastener_checks():
    print('-- #67 mount-hardware gate (heat-set reachability / merge / dot depth) --')
    bad = False
    for g in FASTENER_GROUPS:
        cap = trimesh.load(g['cap_part'])
        stub = trimesh.load(g['stub_part'])
        axis = np.asarray(g['axis'], float)
        H = g['holes']

        # MERGE: adjacent holes must clear the larger of the bore/head/
        # heatset diameter, else their bores/counterbores overlap into a slot.
        need = max(g['bore_d'], g['head_d'], g['heatset_d'])
        merged = [(H[i], H[j], np.linalg.norm(np.subtract(H[i], H[j])))
                  for i in range(len(H)) for j in range(i + 1, len(H))
                  if np.linalg.norm(np.subtract(H[i], H[j])) < need - 1e-6]
        if merged:
            bad = True
            for a, b, d in merged:
                print(f'MERGE {g["cap_part"]}: holes {a} & {b} {d:.1f}mm apart '
                      f'< {need:.1f}mm -> they merge into a slot')
        else:
            print(f'OK    {g["cap_part"]}: {len(H)} mount hole(s) all >= {need:.1f}mm apart')

        for hx, hy, hz in H:
            base = np.array([hx, hy, hz], float)
            # (a) stub-side EXTERIOR reachability: from the heat-set's own
            # mouth (the hole point), scan OUTWARD (+axis) through the whole
            # bridge/stub and PAST its own exterior face by a real margin --
            # against the STUB ALONE (cap may be off during installation).
            # A margin well past the part's own bbox extent along axis
            # proves TRUE exterior air, not just an internal void.
            far = float(np.abs(stub.bounds).max()) + 20.0
            blocked_out = _axis_scan(stub, base, axis, 0, far, r=g['bore_d'] / 2)
            if blocked_out:
                bad = True
                print(f'SEAL  {g["stub_part"]}: heat-set @ {tuple(base)} blocked '
                      f'along +axis at t={blocked_out[0]:.1f} -- no path to a true '
                      f'exterior face, insert/driver cannot reach it')
            else:
                print(f'OK    {g["stub_part"]}: heat-set @ {tuple(base)} open to a '
                      f'true exterior face along +axis (scanned 0..{far:.0f}mm)')

            # (b) stub-side BLIND-bore proof: the insert channel itself
            # (0..heatset_l, going -axis, into the stub) must be OPEN (a
            # real bore exists), and just past its far end must be BLOCKED
            # (real solid material backs it -- genuinely blind, not an
            # accidental through-hole into some other cavity).
            blocked_bore = _axis_scan(stub, base, -axis, 0, g['heatset_l'] - 0.1,
                                       r=g['heatset_d'] / 2 - 0.1)
            if blocked_bore:
                bad = True
                print(f'BLOCK {g["stub_part"]}: heat-set bore @ {tuple(base)} not '
                      f'open its own {g["heatset_l"]:.1f}mm length (blocked at '
                      f't={blocked_bore[0]:.1f})')
            blocked_backing = _axis_scan(stub, base, -axis,
                                          g['heatset_l'] + 0.3, g['heatset_l'] + 3.0, r=0.3)
            if not blocked_backing:
                bad = True
                print(f'HOLLOW {g["stub_part"]}: heat-set bore @ {tuple(base)} has NO '
                      f'solid backing past its own {g["heatset_l"]:.1f}mm depth -- not '
                      f'genuinely blind (punches into another void)')
            else:
                print(f'OK    {g["stub_part"]}: heat-set bore is a real blind pocket '
                      f'({g["heatset_l"]:.1f}mm deep, solid backing confirmed)')

            # (c) cap-side clearance: the SAME axis/position must be open
            # through the cap alone (its own bolt-shank clearance hole),
            # across the head-counterbore + shank span.
            blocked_cap = _axis_scan(cap, base, axis, -3.0, 5.0, r=g['bore_d'] / 2 - 0.1)
            if blocked_cap:
                bad = True
                print(f'BLIND {g["cap_part"]}: clearance hole @ {tuple(base)} blocked '
                      f'in the cap at t={blocked_cap[0]:.1f} -- bolt cannot pass')
            else:
                print(f'OK    {g["cap_part"]}: clearance hole open through the cap')

        # DOT: marker dimple must recess into solid vs the surrounding face.
        # Uses `.contains()` scans (like _axis_scan), not ray casting -- a
        # fixed-direction ray against this geometry's many axis-aligned
        # faces hits trimesh's known tangency issue (silent ray misses),
        # the same reasoning _axis_scan's own docstring already documents.
        o1, o2 = g.get('dot_off', (4.0, 4.0))
        for (dx, dy, dz, nx, ny, nz) in g['dots']:
            n = np.asarray([nx, ny, nz], float); n /= np.linalg.norm(n)
            ctr = np.array([dx, dy, dz], float)
            f1 = np.cross(n, [0, 0, 1.0])
            f1 = f1 / np.linalg.norm(f1) if np.linalg.norm(f1) > 1e-6 else np.array([0, 1.0, 0])
            f2 = np.cross(n, f1)
            at_dot = _surface_depth(cap, ctr, n)
            # o1/o2 == 0 means "this wall is too narrow along that axis for
            # any undisturbed reference point" (e.g. the #67 cap's mid-band
            # wall is only 1.4mm wide in X, narrower than the dot's own
            # 1.5mm radius) -- skip that axis rather than sample a point
            # that's still inside the dimple itself (which would silently
            # UNDERSTATE the measured depth, not a safe default).
            offs = ([o1 * f1, -o1 * f1] if o1 > 0 else []) + \
                   ([o2 * f2, -o2 * f2] if o2 > 0 else [])
            refs = [d for off in offs
                    for d in [_surface_depth(cap, ctr + off, n)] if d is not None]
            if at_dot is None or not refs:
                bad = True
                print(f'?     {g["cap_part"]}: marker dot @ ({dx},{dy},{dz}) surface not '
                      f'found -- cannot verify, treating as a failure')
                continue
            depth = at_dot - float(np.median(refs))
            if depth < MIN_DOT_DEPTH:
                bad = True
                print(f'DOT   {g["cap_part"]}: marker dot only {depth:.2f}mm deep '
                      f'(< {MIN_DOT_DEPTH}mm) -- invisible on the print')
            else:
                print(f'OK    {g["cap_part"]}: marker dot {depth:.2f}mm deep')
    return bad


# BUGFIX gate 2026-07-12 (full-leg assembly audit): the 4x M2.5 HFE horn bolts
# (BCD r7 about the hfe X-axis at y=HFE_Y, z=HFE_Z) are driven -X through the
# empty HAA pocket into the femur's servo horn to capture the coax<->femur
# joint. The #53 "nothing left to cut here" note was written when the whole
# inboard arm became a plate; #67 then kept the LOW-Y/BACK stub INTEGRAL, so
# the stub re-blocked every horn bolt 2.0-4.9mm and the joint could not be
# assembled. It slipped BOTH existing gates: the insertion/hip sweeps mask an
# r13 disc about the hfe axis (the BCD circle at r7 sits INSIDE that mask), and
# the #67 fastener gate only samples the cap heat-set, never the BCD circle.
# This gate closes that hole: it scans all 4 BCD channels through the coax stub
# (coax_R/coax_L) and asserts each is clear across the ARM_THK bolt span.
HORN_BCD_R = 7.0            # HORN_BCD/2 (leg_v6_common.scad)
HORN_M25   = 2.9           # M25_CLEAR bolt-shank clearance
HORN_ANGLES = (45, 135, 225, 315)
HFE_Y, HFE_Z = 11.6, -9.5  # hfe axis (coax.scad); FEMUR_MID = horn-face x
FEMUR_MID = 33.8
ARM_THK = 4.0              # horn couple channel length (leg_v6_common.scad)


def horn_bolt_checks():
    print('-- HFE horn-bolt gate (4x M2.5 BCD channels must clear through the coax stub) --')
    bad = False
    for part in ('coax_R.stl', 'coax_L.stl'):
        m = trimesh.load(part)
        # coax_L = mirror([1,0,0]) of coax_R: the whole horn joint (and its bolt
        # drive direction) flips in x. sx picks the correct side/direction so the
        # L part is probed at its OWN geometry, not empty +x space (which would
        # read a false CLEAR).
        sx = 1 if part == 'coax_R.stl' else -1
        for a in HORN_ANGLES:
            y = HFE_Y + HORN_BCD_R * np.sin(np.radians(a))
            z = HFE_Z + HORN_BCD_R * np.cos(np.radians(a))
            # channel runs toward the stub from FEMUR_MID over the horn couple's
            # own ARM_THK span; scan a MARGIN past both ends so a stub
            # re-thickening (the #67 regression) can't hide just outside it.
            base = np.array([sx * (FEMUR_MID + 0.5), y, z])
            blocked = _axis_scan(m, base, [-sx, 0, 0],
                                 -0.5, ARM_THK + MARGIN_MM, r=HORN_M25 / 2 - 0.1)
            if blocked:
                bad = True
                print(f'BLOCK {part}: horn bolt a={a:3d} (y={y:+.1f},z={z:+.1f}) '
                      f'blocked by stub at x={sx * (FEMUR_MID + 0.5 - blocked[0]):.2f}..'
                      f'{sx * (FEMUR_MID + 0.5 - blocked[-1]):.2f} -- joint cannot assemble')
            else:
                print(f'OK    {part}: horn bolt a={a:3d} (y={y:+.1f},z={z:+.1f}) '
                      f'clear across the {ARM_THK:.1f}mm span')
    return bad


# KFE joint gate 2026-07-12 (matches the HAA wheel-bolt gate; closes the last
# leg-side screw joint not under a dedicated gate). The femur is the DRIVEN
# yoke and the tibia hosts the KFE servo (verified: "KFE servo in tibia
# pocket"). Three bolt circles capture the joint, all about the kfe Z-axis at
# femur-frame x=FEMUR_LEN:
#   * TOP    knee_arm.stl 4x M2.5 horn BCD -> the tibia servo horn
#   * BOTTOM femur_R/L wheel BCD 4x M2.5   -> the tibia idler wheel
#   * MOUNT  knee_arm 4x M3 -> femur shelf heat-sets (holds the top plate on)
# Every scan carries a solid-material guard (a ring at r+1.2 must read solid):
# a bare centerline-void test reads a FALSE clear in empty space -- exactly the
# trap the coax_L mirror bug hit -- so the guard makes the gate self-validate
# against any future STL frame/transform change.
FEMUR_LEN   = 106.9              # kfe axis, femur frame
KFE_KNEE_X  = 47.9              # knee_arm-local kfe axis (FEMUR_LEN - X0=59)
KFE_WHEEL_Z = (-27.6, -17.75)  # femur_R wheel-BCD z span (z-mirrors for _L)
KNEE_MOUNT  = [(6, -8), (6, 8), (16, -8), (16, 8)]     # knee_arm-local M3 holes
FEMUR_MOUNT = [(65, -8), (65, 8), (75, -8), (75, 8)]   # femur-frame heat-sets
YOKE_TOP_IN = 17.75


def _bolt_clear(mesh, cx, cy, z_lo, z_hi, r):
    """True if the Z centerline at (cx,cy) is VOID across [z_lo,z_hi] AND a ring
    at r+1.2 is SOLID -- i.e. a real drilled hole through material, not empty
    air (the false-CLEAR trap). Returns (ok, center_solid, ring_solid)."""
    zc = np.linspace(z_lo + 0.2, z_hi - 0.2, 24)
    center = int(mesh.contains(
        np.column_stack([np.full(len(zc), cx), np.full(len(zc), cy), zc])).sum())
    ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    zmid = (z_lo + z_hi) / 2
    ring = np.column_stack([cx + (r + 1.2) * np.cos(ang),
                            cy + (r + 1.2) * np.sin(ang), np.full(8, zmid)])
    ring_solid = int(contains_chunked(mesh, ring).sum())
    return (center == 0 and ring_solid >= 4), center, ring_solid


def _blind_pocket(mesh, cx, cy, z_top, dirn, depth):
    """A heat-set pilot: bore open `depth` from z_top going `dirn`, with solid
    backing just past it. Returns (ok, bore_open, backing_solid)."""
    zb = z_top + dirn * np.linspace(0.3, depth - 0.3, 20)
    bore = int(mesh.contains(
        np.column_stack([np.full(len(zb), cx), np.full(len(zb), cy), zb])).sum())
    zk = z_top + dirn * np.linspace(depth + 0.4, depth + 2.5, 8)
    back = int(mesh.contains(
        np.column_stack([np.full(len(zk), cx), np.full(len(zk), cy), zk])).sum())
    return (bore == 0 and back >= 4), 20 - bore, back


def kfe_bolt_checks():
    print('-- KFE joint gate (knee-arm horn BCD + femur wheel BCD + knee-arm mount) --')
    bad = False
    r25 = HORN_M25 / 2
    # 1. knee_arm horn BCD (single part, no mirror) -> tibia servo horn
    ka = trimesh.load('knee_arm.stl')
    for a in HORN_ANGLES:
        cx = KFE_KNEE_X + HORN_BCD_R * np.cos(np.radians(a))
        cy = HORN_BCD_R * np.sin(np.radians(a))
        ok, c, rs = _bolt_clear(ka, cx, cy, -0.2, ARM_THK + 0.2, r25)
        if not ok:
            bad = True
            print(f'BLOCK knee_arm.stl: horn bolt a={a:3d} not clear-in-solid '
                  f'(center_solid={c}, ring_solid={rs}/8)')
        else:
            print(f'OK    knee_arm.stl: horn bolt a={a:3d} clear through the {ARM_THK:.1f}mm plate')
    # 1b. knee_arm mount M3 clearance (into femur heat-sets)
    for mx, my in KNEE_MOUNT:
        ok, c, rs = _bolt_clear(ka, mx, my, -0.2, ARM_THK + 0.2, M3_CLEAR / 2)
        if not ok:
            bad = True
            print(f'BLOCK knee_arm.stl: mount M3 ({mx},{my:+d}) not clear-in-solid '
                  f'(center_solid={c}, ring_solid={rs}/8)')
        else:
            print(f'OK    knee_arm.stl: mount M3 ({mx},{my:+d}) clear through the plate')
    # 2. femur wheel BCD -> tibia idler (femur_L = z-mirror)
    for part in ('femur_R.stl', 'femur_L.stl'):
        m = trimesh.load(part)
        zlo, zhi = KFE_WHEEL_Z if part == 'femur_R.stl' \
            else (-KFE_WHEEL_Z[1], -KFE_WHEEL_Z[0])
        for a in HORN_ANGLES:
            cx = FEMUR_LEN + HORN_BCD_R * np.cos(np.radians(a))
            cy = HORN_BCD_R * np.sin(np.radians(a))
            ok, c, rs = _bolt_clear(m, cx, cy, zlo, zhi, r25)
            if not ok:
                bad = True
                print(f'BLOCK {part}: wheel bolt a={a:3d} not clear-in-solid '
                      f'(center_solid={c}, ring_solid={rs}/8)')
            else:
                print(f'OK    {part}: wheel bolt a={a:3d} clear through the bottom boss')
    # 3. femur shelf heat-set pilots receiving the knee-arm mount M3 (blind,
    # aligned) -- proves the top plate actually screws to the femur.
    for part in ('femur_R.stl', 'femur_L.stl'):
        m = trimesh.load(part)
        zmir = part == 'femur_L.stl'
        z_top = -YOKE_TOP_IN if zmir else YOKE_TOP_IN
        dirn = 1 if zmir else -1
        for mx, my in FEMUR_MOUNT:
            ok, bore, back = _blind_pocket(m, mx, my, z_top, dirn, HEATSET_L)
            if not ok:
                bad = True
                print(f'BLOCK {part}: knee-arm heat-set ({mx},{my:+d}) not a blind '
                      f'pocket (bore_open={bore}/20, backing={back}/8)')
            else:
                print(f'OK    {part}: knee-arm heat-set ({mx},{my:+d}) blind pocket '
                      f'({HEATSET_L:.1f}mm, backed)')
    return bad


def _surface_depth(mesh, ctr, n, reach=8.0, n_steps=320):
    """`n` = the face's OUTWARD normal. Starting from a point clearly OUTSIDE
    the part (ctr + reach*n) and walking INWARD (-n) back past ctr, return
    the distance traveled before first entering solid -- i.e. how far
    inward the real surface sits from `ctr`. A deeper dimple at `ctr`
    (material removed) reads a LARGER distance than a flat reference point
    on the same nominal face. Returns None if no entrance is found."""
    ts = np.linspace(0, 2 * reach, n_steps)
    pts = (ctr + reach * n)[None, :] - ts[:, None] * n[None, :]
    inside = contains_chunked(mesh, pts)
    if not inside.any():
        return None
    return float(ts[np.argmax(inside)])   # first True index


def main():
    servo = servo_mesh()
    pts0 = sample_points(servo)
    bad = False
    do_sweep = '--sweep' in sys.argv
    for part_file, T, label in CASES:
        part = trimesh.load(part_file)
        pts = trimesh.transform_points(pts0, T)
        inside = contains_chunked(part, pts)
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
    if '--removable' in sys.argv or do_sweep:
        bad = removable_member_checks(servo, pts0) or bad
    if '--shoulder' in sys.argv or do_sweep:
        bad = shoulder_checks(servo, pts0) or bad
    if '--through' in sys.argv or do_sweep:
        bad = through_hole_checks() or bad
    if '--cable' in sys.argv or do_sweep:
        bad = cable_checks() or bad
    if '--fastener' in sys.argv or do_sweep:
        bad = fastener_checks() or bad
        bad = horn_bolt_checks() or bad
        bad = kfe_bolt_checks() or bad
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
