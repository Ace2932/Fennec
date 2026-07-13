"""lidar_selffilter: the static ear-sector mask drops the robot's own ear-mast
returns while keeping legit environment points — including the cases that make
a naive filter wrong (same azimuth but far/high, and a rotated L2 mount)."""

import math

import numpy as np

from nova_ops.lidar_selffilter import Sector, keep_mask


def sph(az_deg, el_deg, r):
    """(az, el, range) -> xyz in the LiDAR frame (+x fwd, +z up)."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return [
        r * math.cos(el) * math.cos(az),
        r * math.cos(el) * math.sin(az),
        r * math.sin(el),
    ]


# ---- ear returns get dropped ------------------------------------------------


def test_drops_points_in_each_ear_sector():
    # dead-center of each ear window (az ~±164, el 0, ~8 cm)
    pts = [sph(164, 0, 0.08), sph(-164, 0, 0.08)]
    assert not keep_mask(pts).any()


def test_drops_across_the_ear_range_span():
    for r in (0.05, 0.08, 0.11):
        assert not keep_mask([sph(164, 10, r)]).all()


# ---- legit environment points survive ---------------------------------------


def test_keeps_forward_obstacle():
    assert keep_mask([sph(0, 0, 3.0)]).all()


def test_keeps_same_azimuth_but_beyond_the_ear():
    # a wall directly behind the ear: same az, but 5 m out -> NOT the ear.
    # This is the case a pure angular mask would wrongly delete.
    assert keep_mask([sph(164, 0, 5.0)]).all()


def test_keeps_same_azimuth_but_above_the_ear():
    # straight up in the ear's azimuth but el +70 (above the mast top)
    assert keep_mask([sph(164, 70, 0.10)]).all()


def test_keeps_near_point_outside_the_ear_sectors():
    # a close obstacle to the SIDE (az 90) must survive — ear sectors are rear
    assert keep_mask([sph(90, 0, 0.08)]).all()


# ---- mixed cloud ------------------------------------------------------------


def test_mixed_cloud_partitions_correctly():
    pts = np.array(
        [
            sph(164, 0, 0.08),  # ear R   -> drop
            sph(-164, 5, 0.09),  # ear L   -> drop
            sph(0, 0, 4.0),  # forward -> keep
            sph(164, 0, 6.0),  # far rear wall -> keep
            sph(-90, -10, 1.2),  # left obstacle  -> keep
        ]
    )
    keep = keep_mask(pts)
    assert list(keep) == [False, False, True, True, True]


# ---- L2 mount-yaw correction (the 4-way orientation) ------------------------


def test_az_offset_follows_a_rotated_l2_mount():
    # L2 bolted 90° CCW: the ear that was at az 164 now reads az 164−90=74 in
    # the raw cloud. Without the offset it survives (wrong); with az_offset=90
    # the de-rotation puts it back in the sector and it drops.
    raw = [sph(74, 0, 0.08)]
    assert keep_mask(raw).all()  # not caught un-corrected
    assert not keep_mask(raw, az_offset_deg=90).any()  # caught once corrected


# ---- optional global near-field crop ----------------------------------------


def test_min_range_crops_all_directions():
    fwd_near = [sph(0, 0, 0.10)]
    assert keep_mask(fwd_near).all()  # kept without a crop
    assert not keep_mask(fwd_near, min_range=0.15).any()  # cropped with one


# ---- degenerate inputs ------------------------------------------------------


def test_empty_cloud():
    assert keep_mask(np.empty((0, 3))).shape == (0,)


def test_wraparound_sector():
    # a synthetic sector straddling ±180 (170..−170) must match both ends
    s = (Sector("wrap", 170.0, -170.0, -90.0, 90.0, 1.0),)
    assert not keep_mask([sph(175, 0, 0.5)], sectors=s).any()
    assert not keep_mask([sph(-175, 0, 0.5)], sectors=s).any()
    assert keep_mask([sph(0, 0, 0.5)], sectors=s).all()
