#!/usr/bin/env python3
"""leg_v6 fit gate — REAL-geometry collision check.

Places the actual STS3215 mesh (feetech_servo_models/converted_stl/servo.stl,
spline axis moved to the origin to match leg_v6_common's servo frame) at each
part's pocket pose and samples the servo (surface + volume points) against the
printed part's solid. ANY servo point inside the part = the part cuts the
servo. Run after every geometry change:  ../../../.venv/bin/python check_fit.py

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


def sweep_checks(servo, pts0):
    """Pose sweeps: knee fold (tibia+servo vs femur+knee_arm) and hip pitch
    (femur+arm+servo vs coax). Software limits kfe ±126°, hfe ±86° — any
    contact INSIDE those = design bug (mech stops computed at ~141/~91)."""
    bad = False
    femur = trimesh.load('femur_R.stl')
    arm = trimesh.load('knee_arm.stl')
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.2]))
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
    for ang in [-109, -90, -60, 60, 90, 109, 118]:  # sw limit 1.9rad=109; 118 = measured mech stop (expect HIT, documents it)
        T = T_knee @ trimesh.transformations.rotation_matrix(
            np.radians(ang), [0, 0, 1])
        p = trimesh.transform_points(tib_pts, T)
        p = p[np.linalg.norm(p[:, :2] - [106.9, 0], axis=1) > 13]
        n = int(femur.contains(p).sum()) + int(arm.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n and abs(ang) <= 109: bad = True   # hits beyond sw limit are the mech stop
        print(f'   {status} kfe {ang:+4d}deg: {n} pts')
    coax = trimesh.load('coax_R.stl')
    fem_asm = np.vstack([trimesh.sample.sample_surface(femur, 5000, seed=0)[0],
                         trimesh.sample.sample_surface(arm, 1500, seed=0)[0],
                         trimesh.transform_points(pts0, rot_z180())])
    M = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    print('-- hip pitch sweep (femur assembly vs coax)')
    for ang in [-86, -60, -30, 30, 60, 86]:
        S = rot_about(ang, [1, 0, 0], [33.8, 11.6, -9.5])
        # place femur (M), then rotate about the hfe axis (S)
        p = trimesh.transform_points(
            trimesh.transform_points(fem_asm, M), S)
        # exclude the designed disc/boss interface about the hfe X-axis
        p = p[np.linalg.norm(p[:, 1:] - [11.6, -9.5], axis=1) > 13]
        n = int(coax.contains(p).sum())
        status = 'OK ' if n == 0 else 'HIT'
        if n: bad = True
        print(f'   {status} hfe {ang:+4d}deg: {n} pts')
    return bad


def shoulder_checks(servo, pts0):
    """Shoulder vs the swinging leg about the haa axis (Y-line at x=39.05,
    z=0). Right hip; the left is the mirror. Leg assembly = coax (+its
    servo) + femur + tibia + knee_arm, mounted horn-forward (mirror-Y of
    the coax frame — see the chirality note in the design memory)."""
    bad = False
    sh = trimesh.load('shoulder.stl')
    pl = trimesh.load('shoulder_plate.stl')
    coax = trimesh.load('coax_R.stl')
    femur = trimesh.load('femur_R.stl')
    tibia = trimesh.load('tibia_R.stl')
    arm = trimesh.load('knee_arm.stl')
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.2]))
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
    if '--shoulder' in sys.argv or do_sweep:
        bad = shoulder_checks(servo, pts0) or bad
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
