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

SERVO = '/Users/afox/codebases/NOVA/feetech_servo_models/converted_stl/servo.stl'


def servo_mesh():
    m = trimesh.load(SERVO)
    m.apply_translation([-12.5, 0, 0])   # spline axis -> origin (common frame)
    return m


def sample_points(m, n_surface=15000, n_volume=6000):
    surf = m.sample(n_surface)
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


CASES = [
    ('femur_R.stl', rot_z180(), 'HFE servo in femur pocket'),
    ('tibia_R.stl', rot_z180(), 'KFE servo in tibia pocket'),
    ('coax_R.stl',  coax_pose(), 'HAA servo in coax pocket'),
]


def main():
    servo = servo_mesh()
    pts0 = sample_points(servo)
    bad = False
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
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
