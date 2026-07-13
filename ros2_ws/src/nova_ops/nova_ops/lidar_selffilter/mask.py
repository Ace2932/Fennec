"""Static LiDAR self-filter — drop returns that land on the robot's own rigid
ear masts before the cloud reaches SLAM.

WHY A STATIC MASK WORKS: the fennec ears are bolted to the same head as the
Unitree L2, so they never move relative to the sensor. That makes a fixed
angular+range mask in the LiDAR's own frame EXACT — no TF, no URDF, no
per-frame geometry. (Parts that DO move relative to the L2 — the legs — would
need robot_body_filter with the URDF instead; out of scope here.)

Sector numbers computed from the ear meshes (chassis/occlusion_ear.py /
head_ear.scad, 2026-07-13): each ear spans ~az ±152..176°, el −38..+35°, within
11 cm of the L2 optical center. The windows below add a ~2°/15 % inflation for
beam divergence + mount slop.

⚠ L2 MOUNT ORIENTATION — the Unitree L2's Ø51 4-hole base pattern is at 45°, so
the sensor can be bolted in FOUR orientations 90° apart. The azimuth windows
below assume the L2's zero-azimuth points ROBOT-FORWARD (+x). If it is installed
rotated 90/180/270°, the ear returns land in a different azimuth sector and this
mask points at empty air. Pass that installed yaw as `az_offset_deg` (see
node.py) — points are de-rotated by it before masking. VERIFY the orientation on
the bench (spin the L2, watch which raw-cloud azimuth the ears appear in) and set
az_offset_deg to match. Elevation + range are orientation-independent.

Pure logic, numpy-only — no ROS deps, so it unit-tests without a graph. node.py
does the PointCloud2 <-> ndarray glue.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Sector:
    """An angular+range exclusion window in the LiDAR frame (deg, deg, m)."""

    name: str
    az_min: float
    az_max: float
    el_min: float
    el_max: float
    range_max: float


# Default ear sectors, L2 optical frame (+x forward, +z up, az_offset_deg = 0).
# Inflated from the measured mesh windows (occlusion_ear.py).
EAR_SECTORS = (
    Sector("ear_R", 150.0, 178.0, -38.0, 35.0, 0.122),
    Sector("ear_L", -178.0, -150.0, -38.0, 35.0, 0.122),
)


def _norm_deg(a):
    """Wrap degrees into (−180, 180]."""
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


def keep_mask(points, sectors=EAR_SECTORS, min_range=0.0, az_offset_deg=0.0):
    """Return a boolean keep-mask for an (N,3) xyz cloud in the LiDAR frame.

    True = KEEP. A point is DROPPED if it falls inside any `sectors` window
    (azimuth AND elevation AND within range_max), or — when `min_range` > 0 —
    if it is closer than `min_range` (a global near-field crop, all directions).

    `az_offset_deg` corrects the L2 mount yaw: it is the sensor's zero-azimuth
    expressed in the robot-forward frame (equivalently, the CCW yaw the L2 is
    bolted at, one of 0/90/180/270 for the 4-hole base). Points are rotated by
    +az_offset_deg about +z — from the sensor frame back into the robot-forward
    frame the sectors are defined in — before the azimuth test. To set it: read
    the raw-cloud azimuth the ears appear at, and use az_offset ≈ sector_az −
    observed_az (e.g. ears defined at ~164°, seen raw at ~74° -> az_offset 90).
    """
    p = np.asarray(points, dtype=float)
    if p.size == 0:
        return np.ones((0,), dtype=bool)
    p = p.reshape(-1, 3)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]

    if az_offset_deg:
        t = np.radians(az_offset_deg)
        c, s = np.cos(t), np.sin(t)
        x, y = x * c - y * s, x * s + y * c  # rotate by +az_offset (sensor->robot)

    r = np.sqrt(x * x + y * y + z * z)
    az = np.degrees(np.arctan2(y, x))
    el = np.degrees(np.arctan2(z, np.hypot(x, y)))

    drop = np.zeros(len(p), dtype=bool)
    if min_range > 0:
        drop |= r < min_range

    for sec in sectors:
        in_el = (el >= sec.el_min) & (el <= sec.el_max)
        in_r = r <= sec.range_max
        lo, hi = _norm_deg(sec.az_min), _norm_deg(sec.az_max)
        if lo <= hi:
            in_az = (az >= lo) & (az <= hi)
        else:  # window wraps across ±180°
            in_az = (az >= lo) | (az <= hi)
        drop |= in_az & in_el & in_r

    return ~drop
