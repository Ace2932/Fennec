"""jog CLI (#286) — target computation + clamping, no rclpy required.

Replaces the docs/setup-jetson.md smoke-test hazard (raw `ros2 topic pub`
writing radian-shaped floats straight into main.cpp's raw-count command
path). These tests lock the pure logic jog.py's ROS glue calls into:
compute_target (delta/absolute + limit clamp + safety-cap refusal),
clamp_hfe_posture (chassis envelope), check_calibration (all-or-nothing
refusal), resolve_joint (name/id lookup).
"""

import math

import pytest

from nova_ops.jog import (
    JogRefused,
    check_calibration,
    clamp_hfe_posture,
    compute_target,
    deg_to_raw,
    resolve_joint,
)


# ---- deg_to_raw (--raw mode unit conversion) ------------------------------


def test_deg_to_raw_five_degrees_is_about_57_counts():
    """5 deg should be ~4096*5/360 ~= 56.9 raw counts. Locks the bug where
    RAW_PER_RAD (counts per RADIAN) was applied straight to a degrees value
    with no radians() step, an ~57x overshoot (5 deg -> 3259 counts)."""
    assert deg_to_raw(5.0) == pytest.approx(4096 * 5 / 360, rel=1e-3)


def test_raw_mode_cap_refuses_large_delta_without_force():
    """Negative control for the cap-never-binds half of the same bug: with
    the fix, deg_to_raw(20) > deg_to_raw(15) so a 20 deg raw-mode delta must
    REFUSE without --force. Before the fix both were computed in COUNTS
    already past 0..4095 for any joint, so raw mode's cap could never bind."""
    with pytest.raises(JogRefused, match="exceeds the"):
        compute_target(
            present=2048.0,
            delta=deg_to_raw(20.0),
            to=None,
            lower=0.0,
            upper=4095.0,
            cap=deg_to_raw(15.0),
            force=False,
        )


# ---- compute_target ------------------------------------------------------


def test_delta_within_cap_and_limits_passes_through():
    target, clamped = compute_target(
        present=0.0, delta=0.1, to=None, lower=-1.0, upper=1.0, cap=0.3, force=False
    )
    assert target == pytest.approx(0.1)
    assert clamped is False


def test_to_absolute_within_limits_passes_through():
    target, clamped = compute_target(
        present=0.0, delta=None, to=0.2, lower=-1.0, upper=1.0, cap=0.3, force=False
    )
    assert target == pytest.approx(0.2)
    assert clamped is False


def test_target_beyond_limit_table_is_clamped():
    """Negative control: a delta that lands outside [lower, upper] must come
    back clamped to the boundary, not the raw requested value."""
    target, clamped = compute_target(
        present=0.9, delta=0.5, to=None, lower=-1.0, upper=1.0, cap=1.0, force=False
    )
    assert target == pytest.approx(1.0)  # clamped to upper, not 1.4
    assert clamped is True


def test_delta_over_cap_refuses_without_force():
    """Negative control: a move bigger than the safety cap must REFUSE, not
    silently clamp to the cap — the whole point is stopping the request, not
    reshaping it into something that looks smaller than what was typed."""
    with pytest.raises(JogRefused, match="exceeds the"):
        compute_target(
            present=0.0, delta=1.0, to=None, lower=-2.0, upper=2.0, cap=0.5, force=False
        )


def test_delta_over_cap_with_force_proceeds():
    target, clamped = compute_target(
        present=0.0, delta=1.0, to=None, lower=-2.0, upper=2.0, cap=0.5, force=True
    )
    assert target == pytest.approx(1.0)
    assert clamped is False


# ---- clamp_hfe_posture ----------------------------------------------------


def test_hfe_posture_clamps_deep_inboard_fold():
    """At full inboard haa the chassis fold cap collapses well under the
    mechanical +86 deg limit (see rom_envelope.py) -- a +70 deg hfe request
    at haa -15 deg must come back clamped tighter than requested."""
    haa = math.radians(-15.0)
    kfe = math.radians(-90.0)
    requested_hfe = math.radians(70.0)
    clamped_hfe, was_clamped = clamp_hfe_posture("FL", requested_hfe, haa, kfe)
    assert was_clamped is True
    assert clamped_hfe < requested_hfe


def test_hfe_posture_leaves_roomy_posture_alone():
    haa = 0.0
    kfe = math.radians(-90.0)
    requested_hfe = math.radians(10.0)  # well inside any measured cap at haa 0
    clamped_hfe, was_clamped = clamp_hfe_posture("FL", requested_hfe, haa, kfe)
    assert was_clamped is False
    assert clamped_hfe == pytest.approx(requested_hfe)


# ---- check_calibration ----------------------------------------------------


def test_check_calibration_refuses_when_absent():
    """Negative control: no homing artifact, no params -> refuse, not
    silently pass radians through to a firmware reading raw counts."""
    with pytest.raises(JogRefused, match="uncalibrated"):
        check_calibration({})


def test_check_calibration_refuses_when_partial():
    from nova_ops.safety_envelope.firmware_limits import JointHomeCalib

    calib = {1: JointHomeCalib(home_raw=2048, urdf_sign=+1)}  # only 1 of 12
    with pytest.raises(JogRefused, match="partial"):
        check_calibration(calib)


def test_check_calibration_passes_when_active():
    from nova_ops.safety_envelope.firmware_limits import JointHomeCalib

    calib = {i: JointHomeCalib(home_raw=2048, urdf_sign=+1) for i in range(1, 13)}
    check_calibration(calib)  # must not raise


# ---- resolve_joint ---------------------------------------------------------


def test_resolve_joint_by_name():
    id_map = {"FL_haa": 1, "FL_hfe": 2, "FL_kfe": 3}
    bus_id, name = resolve_joint("FL_hfe", id_map)
    assert (bus_id, name) == (2, "FL_hfe")


def test_resolve_joint_by_bus_id():
    id_map = {"FL_haa": 1, "FL_hfe": 2, "FL_kfe": 3}
    bus_id, name = resolve_joint("2", id_map)
    assert (bus_id, name) == (2, "FL_hfe")


def test_resolve_joint_rejects_unknown_name():
    with pytest.raises(JogRefused, match="unknown joint"):
        resolve_joint("bogus_joint", {"FL_haa": 1})


def test_resolve_joint_rejects_unknown_id():
    with pytest.raises(JogRefused, match="not in joint_id_map"):
        resolve_joint("99", {"FL_haa": 1})
