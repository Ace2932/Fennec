#!/usr/bin/env python3
"""head_ear LiDAR-occlusion analysis (2026-07-13).

The fennec ears sit in the Unitree L2's rear 360-deg mapping sector. A flat
blade facing the L2 broad-side blocks a wide azimuth arc; yawed edge-on it
blocks a narrow one. This script:
  1. sweeps EAR_YAW to find the arc blocked per ear (silhouette azimuth width
     as seen from the L2 optical center), and
  2. measures the SHIPPED mesh (head_ear.stl) before/after in the mapping band.

Occlusion is reported in the z>155 band (near-horizontal + up) -- the part of
the scan volume that actually maps the environment. The foot flange (z131..135)
sits ~-36 deg below the L2 at the crown/mount plane, out of the useful band, so
it is excluded from the headline number.

Run:  ../../../.venv/bin/python occlusion_ear.py
Deps: trimesh, numpy (proj/.venv). Renders yaw sweep from the .scad via OpenSCAD.
"""
import subprocess
import numpy as np
import trimesh

OPENSCAD = "/opt/homebrew/bin/openscad"
O = np.array([126.5, 0.0, 160.0])   # L2 optical center (head.scad crown ctr, optical ~z160)
MAP_ZMIN = 155                      # mapping band: near-horizontal + up


def az_block(mesh, zmin=MAP_ZMIN, n=40000):
    """Azimuthal arc (deg) the mesh blocks from O, counting only pts above zmin."""
    p = trimesh.sample.sample_surface(mesh, n)[0]
    p = p[p[:, 2] > zmin]
    az = np.degrees(np.arctan2(p[:, 1] - O[1], p[:, 0] - O[0]))
    return az.max() - az.min()


def render(yaw, path):
    subprocess.run([OPENSCAD, "-D", f"EAR_YAW={yaw}", "-o", path, "head_ear.scad"],
                   check=True, capture_output=True)
    return trimesh.load(path)


def min_l2_clearance(mesh):
    """Closest approach of the ear to the L2 body (axis x126.5,y0, Ø51 -> r25.5)."""
    p = trimesh.sample.sample_surface(mesh, 8000)[0]
    return float(np.min(np.hypot(p[:, 0] - 126.5, p[:, 1]))) - 25.5


if __name__ == "__main__":
    print("EAR_YAW sweep (arc blocked per ear, mapping band z>155):")
    best = None
    for yaw in range(0, 61, 5):
        m = render(yaw, "/tmp/_ear_sweep.stl")
        w = az_block(m)
        clr = min_l2_clearance(m)
        print(f"  yaw {yaw:+3d}: {w:5.1f} deg blocked   L2 clearance {clr:+5.1f} mm")
        if best is None or w < best[1]:
            best = (yaw, w)
    print(f"min-occlusion yaw ~ {best[0]:+d} deg ({best[1]:.1f} deg). SHIPPED = +45 "
          f"(near-optimal without the ears leaning too far back).")

    # shipped part, exact before/after
    a0 = az_block(render(0, "/tmp/_ear0.stl"))
    a45 = az_block(trimesh.load("head_ear.stl"))
    print(f"\nSHIPPED head_ear.stl: yaw 0 -> {a0:.1f} deg/ear, yaw 45 -> {a45:.1f} deg/ear "
          f"-> {a0 - a45:.1f} recovered/ear, {2 * (a0 - a45):.1f} across both.")
