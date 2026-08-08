"""build_limp_pose_data — the firmware's soft-fault controlled-limp target
(#145). Mirrors test_firmware_tables.py's "publish-or-not" doctrine: this
table is all-or-nothing, and it fails safe (None) rather than guess.
"""

import math

from nova_ops.safety_envelope import limits as limits_mod
from nova_ops.safety_envelope.firmware_limits import build_calib
from nova_ops.safety_envelope.limits import record_haa_confirmation
from nova_ops.safety_envelope.limp_pose import (
    LIMP_JOINTS_CANONICAL,
    build_limp_pose_data,
    limp_pose_canonical,
)

HOME = 2048.0


def _full_calib():
    return build_calib([HOME] * 12, [1] * 12)


def _confirm_all(monkeypatch):
    # Isolate the module-global confirmation state per test — record_haa_
    # confirmation() mutates HAA_INBOARD_SIGN/HAA_SIGN_CONFIRMATION in place,
    # and those are shared module globals other test files also touch.
    monkeypatch.setattr(
        limits_mod, "HAA_INBOARD_SIGN", dict(limits_mod.HAA_INBOARD_SIGN)
    )
    monkeypatch.setattr(
        limits_mod, "HAA_SIGN_CONFIRMATION", dict(limits_mod.HAA_SIGN_CONFIRMATION)
    )
    for jid in (1, 4, 7, 10):
        record_haa_confirmation(
            jid,
            sign=1,
            observed_utc="2026-08-08T00:00:00",
            method="test",
            assembly="test",
        )


# ---- canonical pose --------------------------------------------------------


def test_canonical_pose_is_backlog_15_angles():
    haa, hfe, kfe = LIMP_JOINTS_CANONICAL
    assert math.isclose(math.degrees(haa), 40.0)
    assert math.isclose(math.degrees(hfe), 40.0)
    assert math.isclose(math.degrees(kfe), -90.0)


def test_canonical_pose_mirrors_haa_by_side():
    pose = limp_pose_canonical()
    # left legs keep +haa, right legs get -haa; hfe/kfe identical every leg
    assert pose["FL"][0] == pose["RL"][0] == LIMP_JOINTS_CANONICAL[0]
    assert pose["FR"][0] == pose["RR"][0] == -LIMP_JOINTS_CANONICAL[0]
    for leg in ("FL", "FR", "RL", "RR"):
        assert pose[leg][1:] == LIMP_JOINTS_CANONICAL[1:]


# ---- publish-or-not, the actual #145 gate ----------------------------------


def test_WITHOUT_haa_confirmation_returns_None():
    """NEGATIVE CONTROL: full urdf_sign calibration alone must NOT be enough
    — that would command a 40 deg outboard splay nobody has confirmed is
    actually outboard on this hardware. Guard must still be up."""
    assert build_limp_pose_data(_full_calib()) is None


def test_partially_confirmed_haa_still_returns_None(monkeypatch):
    """NEGATIVE CONTROL: 3 of 4 hips confirmed is not enough either — the
    table is per-fault-episode all-or-nothing (main.cpp commands all 12
    joints from the same table)."""
    monkeypatch.setattr(
        limits_mod, "HAA_INBOARD_SIGN", dict(limits_mod.HAA_INBOARD_SIGN)
    )
    monkeypatch.setattr(
        limits_mod, "HAA_SIGN_CONFIRMATION", dict(limits_mod.HAA_SIGN_CONFIRMATION)
    )
    for jid in (1, 4, 7):  # RR (10) left unconfirmed
        record_haa_confirmation(
            jid, sign=1, observed_utc="t", method="m", assembly="a"
        )
    assert build_limp_pose_data(_full_calib()) is None


def test_confirmed_but_uncalibrated_hfe_kfe_still_returns_None(monkeypatch):
    """Haa confirmation alone isn't enough either — every one of the 12
    joints needs a real home_raw/urdf_sign, or rad_to_raw has no defined
    conversion for it."""
    _confirm_all(monkeypatch)
    calib = build_calib([HOME] * 12, [1, 1, 0] + [1] * 9)  # FL kfe unhomed
    assert build_limp_pose_data(calib) is None


def test_full_calibration_PLUS_confirmation_yields_12_raw_counts(monkeypatch):
    _confirm_all(monkeypatch)
    data = build_limp_pose_data(_full_calib())
    assert data is not None
    assert len(data) == 12
    assert all(0.0 <= v <= 4095.0 for v in data)

    # FL (ids 1,2,3): haa/hfe +40 deg outboard from home, kfe -90 deg
    raw_per_rad = 4096.0 / (2.0 * math.pi)
    assert math.isclose(data[0], HOME + math.radians(40.0) * raw_per_rad)
    assert math.isclose(data[1], HOME + math.radians(40.0) * raw_per_rad)
    assert math.isclose(data[2], HOME + math.radians(-90.0) * raw_per_rad)
    # FR (ids 4,5,6): haa MIRRORED (-40 deg), hfe/kfe identical to FL
    assert math.isclose(data[3], HOME - math.radians(40.0) * raw_per_rad)
    assert math.isclose(data[4], data[1])
    assert math.isclose(data[5], data[2])
