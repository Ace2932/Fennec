"""firmware_limits: URDF-rad -> raw table for the Teensy `joint_limits`
topic, plus the haa asymmetric/conservative default behavior in limits."""

import math

from nova_ops.safety_envelope import (
    JointHomeCalib,
    JointLimit,
    JointLimits,
    build_joint_limits_data,
    load_default_limits,
)
from nova_ops.safety_envelope.firmware_limits import RAW_PER_RAD
from nova_ops.safety_envelope import limits as limits_mod


# ---- haa defaults (gate ROM, firmware-limits lane) ---------------------


def test_haa_default_is_conservative_symmetric_15deg():
    """Unknown inboard sign -> both directions capped at the chassis
    gate's 15-deg inboard limit (NOT the old +/-45)."""
    lim = load_default_limits()
    for hid in (1, 4, 7, 10):
        jl = lim.get(hid)
        assert math.isclose(jl.upper, math.radians(15.0)), hid
        assert math.isclose(jl.lower, -math.radians(15.0)), hid


def test_haa_asymmetric_when_sign_known():
    """Filling HAA_INBOARD_SIGN unlocks 15-inboard / 40-outboard."""
    old = dict(limits_mod.HAA_INBOARD_SIGN)
    try:
        limits_mod.HAA_INBOARD_SIGN[1] = +1  # +cmd = inboard
        limits_mod.HAA_INBOARD_SIGN[4] = -1  # -cmd = inboard
        lim = load_default_limits()
        j1 = lim.get(1)
        assert math.isclose(j1.upper, math.radians(15.0))
        assert math.isclose(j1.lower, -math.radians(40.0))
        j4 = lim.get(4)
        assert math.isclose(j4.upper, math.radians(40.0))
        assert math.isclose(j4.lower, -math.radians(15.0))
    finally:
        limits_mod.HAA_INBOARD_SIGN.clear()
        limits_mod.HAA_INBOARD_SIGN.update(old)


# ---- raw table computation ---------------------------------------------


def _one_joint_limits(lower, upper):
    return JointLimits(
        {1: JointLimit(lower=lower, upper=upper, velocity=6.0, effort=0.7)}
    )


def test_calibrated_joint_maps_to_raw_window():
    lims = _one_joint_limits(-math.radians(30), math.radians(60))
    calib = {1: JointHomeCalib(home_raw=2048, urdf_sign=+1)}
    data = build_joint_limits_data(lims, calib)
    assert len(data) == 24
    lo, hi = data[0], data[1]
    assert math.isclose(lo, 2048 - math.radians(30) * RAW_PER_RAD, abs_tol=0.01)
    assert math.isclose(hi, 2048 + math.radians(60) * RAW_PER_RAD, abs_tol=0.01)
    # every other joint (no calib) stays wide open
    assert data[2:] == [0.0, 4095.0] * 11


def test_negative_sign_flips_window():
    lims = _one_joint_limits(-math.radians(30), math.radians(60))
    calib = {1: JointHomeCalib(home_raw=2048, urdf_sign=-1)}
    data = build_joint_limits_data(lims, calib)
    lo, hi = data[0], data[1]
    assert math.isclose(lo, 2048 - math.radians(60) * RAW_PER_RAD, abs_tol=0.01)
    assert math.isclose(hi, 2048 + math.radians(30) * RAW_PER_RAD, abs_tol=0.01)


def test_unknown_sign_stays_wide_open():
    lims = _one_joint_limits(-1.0, 1.0)
    calib = {1: JointHomeCalib(home_raw=2048, urdf_sign=None)}
    data = build_joint_limits_data(lims, calib)
    assert data[0] == 0.0 and data[1] == 4095.0


def test_window_clamped_to_servo_range_and_never_degenerate():
    # home near the 0 end, huge range -> clamped, still min < max
    lims = _one_joint_limits(-math.pi, math.pi)
    calib = {1: JointHomeCalib(home_raw=100, urdf_sign=+1)}
    data = build_joint_limits_data(lims, calib)
    lo, hi = data[0], data[1]
    assert 0.0 <= lo < hi <= 4095.0
    # home fully off-scale -> degenerate window -> wide open fallback
    calib = {1: JointHomeCalib(home_raw=-9000, urdf_sign=+1)}
    data = build_joint_limits_data(lims, calib)
    assert (data[0], data[1]) == (0.0, 4095.0)


def test_firmware_message_contract():
    """Every pair must satisfy the firmware's whole-message validation:
    0 <= min < max <= 4095 — else the Teensy rejects the entire table."""
    lims = load_default_limits()
    calib = {
        i: JointHomeCalib(home_raw=2048, urdf_sign=(+1 if i % 2 else -1))
        for i in range(1, 13)
    }
    data = build_joint_limits_data(lims, calib)
    assert len(data) == 24
    for i in range(12):
        lo, hi = data[2 * i], data[2 * i + 1]
        assert 0.0 <= lo < hi <= 4095.0
