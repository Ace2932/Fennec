"""firmware_limits: URDF-rad -> raw table for the Teensy `joint_limits`
topic, plus the haa asymmetric/conservative default behavior in limits."""

import math
import pytest

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
    """A CONFIRMED sign unlocks 15-inboard / 40-outboard.

    Since #161 the unlock is keyed on the recorded observation, not on the
    number: this used to assign HAA_INBOARD_SIGN directly, which now leaves the
    hip conservative on purpose.
    """
    old = dict(limits_mod.HAA_INBOARD_SIGN)
    old_rec = dict(limits_mod.HAA_SIGN_CONFIRMATION)
    try:
        for jid, sign in ((1, +1), (4, -1)):  # +1: +cmd = inboard
            limits_mod.record_haa_confirmation(
                jid,
                sign=sign,
                observed_utc="2026-07-27T18:00:00Z",
                method="homing sweep",
                assembly="leg_v6 rev2",
            )
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
        limits_mod.HAA_SIGN_CONFIRMATION.clear()
        limits_mod.HAA_SIGN_CONFIRMATION.update(old_rec)


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


# ---- #154: command path and limit path must agree, per joint ----------------


def test_command_and_limit_paths_agree_on_an_INVERTED_joint():
    """The case that was silently broken: a servo mounted backwards.

    The limits path already converted per joint via urdf_sign; the command path
    used one global scalar for all twelve. So an inverted joint got a
    correctly-signed limit WINDOW and a wrong-signed COMMAND — it would drive
    away from target into its stop, with the firmware backstop computed for the
    opposite sense so it could not catch it.

    Both paths share rad_to_raw() now. This asserts they cannot diverge: a
    commanded angle inside the joint's radian limits must convert to a raw count
    inside the raw window the firmware was handed.
    """
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        build_joint_limits_data,
        rad_to_raw,
    )
    from nova_ops.safety_envelope.limits import load_default_limits

    limits = load_default_limits()
    for sign in (+1, -1):  # normal AND inverted mounting
        calib = {
            i: JointHomeCalib(home_raw=2048.0, urdf_sign=sign) for i in range(1, 13)
        }
        table = build_joint_limits_data(limits, calib)
        for jid in range(1, 13):
            lim = limits.get(jid)
            raw_lo, raw_hi = table[2 * (jid - 1)], table[2 * (jid - 1) + 1]
            # sample across the joint's legal radian span
            for f in (0.0, 0.25, 0.5, 0.75, 1.0):
                theta = lim.lower + f * (lim.upper - lim.lower)
                raw = rad_to_raw(theta, calib[jid])
                assert raw_lo - 1e-6 <= raw <= raw_hi + 1e-6, (
                    f"sign={sign:+d} joint {jid}: a LEGAL angle "
                    f"{math.degrees(theta):+.1f}° converts to raw {raw:.0f}, "
                    f"outside the firmware window [{raw_lo:.0f}, {raw_hi:.0f}] "
                    f"the same calibration produced"
                )


def test_round_trip_survives_an_inverted_joint():
    """raw_to_rad(rad_to_raw(x)) == x for both mounting directions.

    The /joint_states seeding path depends on this: node.py converts feedback
    back to radians before positions_to_pose(), which is what stand_up() uses
    as its start pose after an E-stop.
    """
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        raw_to_rad,
        rad_to_raw,
    )

    for sign in (+1, -1):
        c = JointHomeCalib(home_raw=1700.0, urdf_sign=sign)
        for deg in (-95.0, -40.0, 0.0, 37.5, 86.0):
            theta = math.radians(deg)
            assert raw_to_rad(rad_to_raw(theta, c), c) == pytest.approx(theta)


def test_partial_calibration_converts_NOTHING():
    """All-or-nothing. The firmware reads the whole array in ONE unit, so a
    part-counts / part-radians message is worse than no conversion."""
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        convert_positions,
    )

    partial = {
        i: JointHomeCalib(home_raw=2048.0, urdf_sign=+1) for i in range(1, 12)
    }  # 11 of 12
    assert convert_positions([0.1] * 12, partial, to_raw=True) is None
    full = dict(partial)
    full[12] = JointHomeCalib(home_raw=2048.0, urdf_sign=+1)
    assert convert_positions([0.1] * 12, full, to_raw=True) is not None


# ---- #159: the three calibration states must be DISTINGUISHABLE -----------


def test_calibration_state_names_the_three_states():
    """The dangerous state is PARTIAL, and it used to look like pre-hardware.

    Both emit radians into a firmware reading raw counts. Fully uncalibrated is
    the expected pre-hardware state (nothing is listening). Partial is bring-up
    with some joints homed — same behaviour, completely different consequence.
    """
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        calibration_state,
    )

    full = {i: JointHomeCalib(home_raw=2048.0, urdf_sign=+1) for i in range(1, 13)}
    assert calibration_state({}) == ("uncalibrated", list(range(1, 13)))
    assert calibration_state(full) == ("active", [])

    partial = {i: c for i, c in full.items() if i not in (4, 11)}
    assert calibration_state(partial) == ("partial", [4, 11])


def test_calibration_state_counts_an_unknown_SIGN_as_missing():
    """A present entry with urdf_sign None has no defined conversion — it is
    missing, not calibrated. is_calibrated() is the authority, not membership."""
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        calibration_state,
        convert_positions,
    )

    calib = {i: JointHomeCalib(home_raw=2048.0, urdf_sign=+1) for i in range(1, 13)}
    calib[7] = JointHomeCalib(home_raw=2048.0, urdf_sign=None)
    assert calibration_state(calib) == ("partial", [7])
    # and it agrees with the conversion it is describing
    assert convert_positions([0.1] * 12, calib, to_raw=True) is None


def test_calibration_state_agrees_with_convert_positions():
    """The classifier must never say 'active' where the conversion declines."""
    from nova_ops.safety_envelope.firmware_limits import (
        JointHomeCalib,
        calibration_state,
        convert_positions,
    )

    for drop in ([], [1], [6, 12], list(range(1, 13))):
        calib = {
            i: JointHomeCalib(home_raw=2048.0, urdf_sign=+1)
            for i in range(1, 13)
            if i not in drop
        }
        state, _ = calibration_state(calib)
        converted = convert_positions([0.1] * 12, calib, to_raw=True)
        assert (state == "active") == (converted is not None), (drop, state)


# ---- build_calib: a broken calibration must not become motion --------------


def test_build_calib_full_and_uncalibrated():
    from nova_ops.safety_envelope import build_calib

    assert len(build_calib([2048.0] * 12, [1] * 12)) == 12
    # sign 0 = unknown = uncalibrated, the pre-hardware state (NOT an error)
    assert build_calib([2048.0] * 12, [0] * 12) == {}
    # mixed: only the signed joints appear
    assert sorted(build_calib([2048.0] * 12, [1, 0, -1] + [0] * 9)) == [1, 3]


def test_short_home_raw_RAISES_instead_of_defaulting_to_zero():
    """The bug this guards: home_raw silently defaulting to 0.0.

    0.0 instead of ~2048 is a 2048-count, 180-degree command error, and the
    firmware backstop is built from the SAME calibration, so its window moves
    with the error and cannot catch it — the exact #154 shape. 0.0 is inside
    the legal raw range, so nothing downstream rejects it either.
    """
    from nova_ops.safety_envelope import build_calib

    with pytest.raises(ValueError, match="home_raw has only 3 entries"):
        build_calib([2048.0] * 3, [1] * 12)


def test_build_calib_rejects_bad_sign_and_out_of_range_home():
    from nova_ops.safety_envelope import build_calib

    with pytest.raises(ValueError, match="urdf_sign must be"):
        build_calib([2048.0] * 12, [2] * 12)
    for bad in (-1.0, 4096.0):
        with pytest.raises(ValueError, match="outside the STS3215 range"):
            build_calib([bad] * 12, [1] * 12)


def test_a_short_array_would_have_been_180_degrees_off():
    """Negative control on the FIX: prove the old default was catastrophic.

    Pins the magnitude so nobody re-introduces a lenient default thinking it
    is harmless.
    """
    from nova_ops.safety_envelope.firmware_limits import JointHomeCalib, rad_to_raw

    good = JointHomeCalib(home_raw=2048.0, urdf_sign=+1)
    bad = JointHomeCalib(home_raw=0.0, urdf_sign=+1)  # the old silent default
    err = rad_to_raw(0.6, good) - rad_to_raw(0.6, bad)
    assert err == pytest.approx(2048.0)
    assert math.degrees(2048.0 / RAW_PER_RAD) == pytest.approx(180.0, abs=0.5)


# ---- #142: the posture-aware firmware backstop ----------------------------


def _full_calib(sign=+1):
    from nova_ops.safety_envelope.firmware_limits import JointHomeCalib

    return {i: JointHomeCalib(home_raw=2048.0, urdf_sign=sign) for i in range(1, 13)}


def test_hfe_envelope_is_empty_until_the_haa_and_hfe_joints_are_calibrated():
    """No calibration -> no defined raw conversion -> publish nothing.

    A partial table would be worse than none: the firmware would clamp some
    legs against a window computed from a guessed home, which is the #154 shape
    (a wrong command with a limit that agrees with it).
    """
    from nova_ops.safety_envelope.firmware_limits import build_hfe_envelope_data

    assert build_hfe_envelope_data({}) == []
    partial = _full_calib()
    del partial[2]                                    # FL hfe uncalibrated
    assert build_hfe_envelope_data(partial) == []


def test_hfe_envelope_layout_and_raw_bounds():
    from nova_ops.safety_envelope.firmware_limits import (
        HFE_ENV_STRIDE, build_hfe_envelope_data,
    )

    data = build_hfe_envelope_data(_full_calib())
    n = int(data[0])
    assert n >= 8
    assert len(data) == 1 + 4 * n * HFE_ENV_STRIDE
    body = data[1:]
    for i in range(0, len(body), HFE_ENV_STRIDE):
        haa_lo, haa_hi, hfe_lo, hfe_hi = body[i:i + HFE_ENV_STRIDE]
        assert 0.0 <= haa_lo < haa_hi <= 4095.0, (i, haa_lo, haa_hi)
        assert 0.0 <= hfe_lo <= hfe_hi <= 4095.0, (i, hfe_lo, hfe_hi)


def test_hfe_envelope_buckets_span_the_whole_raw_range_with_no_gaps():
    """A gap is a hole in the backstop: a haa the firmware cannot classify."""
    from nova_ops.safety_envelope.firmware_limits import (
        HFE_ENV_STRIDE, build_hfe_envelope_data,
    )

    data = build_hfe_envelope_data(_full_calib())
    n = int(data[0])
    body = data[1:]
    for leg in range(4):
        buckets = [
            body[(leg * n + b) * HFE_ENV_STRIDE:(leg * n + b) * HFE_ENV_STRIDE + 4]
            for b in range(n)
        ]
        assert buckets[0][0] == 0.0, buckets[0]
        assert buckets[-1][1] == 4095.0, buckets[-1]
        for a, b in zip(buckets, buckets[1:]):
            assert a[1] == pytest.approx(b[0]), (a, b)


@pytest.mark.parametrize("sign", (+1, -1))
def test_firmware_window_is_NEVER_looser_than_the_host_gate(sign):
    """The safety property. A backstop that permits what the host refuses is
    not a backstop — and this must hold for BOTH servo mounting directions,
    since urdf_sign reverses which raw end is which."""
    import math

    from nova_ops.rom_envelope import hfe_bounds
    from nova_ops.rom_envelope_table import HAAS, KFES
    from nova_ops.safety_envelope.firmware_limits import (
        HFE_ENV_STRIDE, build_hfe_envelope_data, rad_to_raw,
    )

    calib = _full_calib(sign)
    data = build_hfe_envelope_data(calib)
    n = int(data[0])
    body = data[1:]
    legs = ("FL", "FR", "RL", "RR")
    haa_ids = (1, 4, 7, 10)
    hfe_ids = (2, 5, 8, 11)

    for li, (leg, haa_id, hfe_id) in enumerate(zip(legs, haa_ids, hfe_ids)):
        for haa_deg in HAAS:
            haa_raw = rad_to_raw(math.radians(haa_deg), calib[haa_id])
            # the bucket the firmware would select
            sel = None
            for b in range(n):
                o = (li * n + b) * HFE_ENV_STRIDE
                if body[o] <= haa_raw <= body[o + 1]:
                    sel = body[o:o + HFE_ENV_STRIDE]
                    break
            assert sel is not None, (leg, haa_deg, haa_raw)
            for kfe_deg in KFES:
                g_lo, g_hi = hfe_bounds(leg, math.radians(haa_deg),
                                        math.radians(kfe_deg))
                a = rad_to_raw(g_lo, calib[hfe_id])
                b_ = rad_to_raw(g_hi, calib[hfe_id])
                host_lo, host_hi = min(a, b_), max(a, b_)
                assert sel[2] >= host_lo - 1e-6, (leg, haa_deg, kfe_deg, sel)
                assert sel[3] <= host_hi + 1e-6, (leg, haa_deg, kfe_deg, sel)


def test_the_trot_has_a_SMALL_BUT_REAL_inboard_haa_tolerance():
    """How much inboard haa drift the trot survives. MEASURED, and it is tight.

    History: the coarse haa grid put the nearest inboard sample at -5, so
    conservative bracketing projected that cell's 56.7 cap across the whole
    span and the gate appeared to clip the trot at haa -0.001 -- a 0.001 deg
    knife-edge. #181 regenerated the table with samples at -1, -0.5 and the
    real crossing showed up between -0.75 and -0.5:

        haa -1.000 -> cap 57.0   clips the trot's +59.4
        haa -0.750 -> cap 57.0   clips
        haa -0.500 -> cap 66.4   fits, +7.0 margin
        haa  0.000 -> cap 66.3   fits, +6.9 margin

    So the tolerance is ~0.5 deg, not zero -- 500x what the old table implied,
    and still only about 6 servo counts (4096/2pi = 0.088 deg per count). Worth
    knowing before first stand: the trot does not require haa to be bit-exact
    zero, but it does require it not to drift half a degree inboard.

    Pinned so a future regeneration announces a change rather than silently
    moving the margin. If the crossing moves OUTBOARD (tolerance shrinks) that
    is a real regression; if it moves inboard, the trot got safer.
    """
    import math

    from nova_ops.rom_envelope import hfe_bounds

    TROT_PEAK = 59.4
    KFE = math.radians(-98.8)

    def cap(haa_deg):
        return math.degrees(hfe_bounds("FL", math.radians(haa_deg), KFE)[1])

    assert cap(0.0) > TROT_PEAK, cap(0.0)
    assert cap(-0.5) > TROT_PEAK, cap(-0.5)          # the tolerance is real
    assert cap(-0.75) < TROT_PEAK, cap(-0.75)        # and it is bounded
    assert cap(-1.0) < TROT_PEAK, cap(-1.0)
    # the margin where it holds is worth having, not a rounding artefact
    assert cap(-0.5) - TROT_PEAK > 5.0, cap(-0.5)


def test_deep_inboard_haa_plus_deep_fold_is_REFUSED():
    """The failure this exists to catch: a host bug commanding the leg inboard
    under the LiPo AND folded. The gate caps fold at +13.8 deg at haa -15."""
    import math

    from nova_ops.safety_envelope.firmware_limits import (
        HFE_ENV_STRIDE, build_hfe_envelope_data, rad_to_raw,
    )

    calib = _full_calib(+1)
    data = build_hfe_envelope_data(calib)
    n = int(data[0])
    body = data[1:]
    haa_raw = rad_to_raw(math.radians(-15.0), calib[1])
    bad_raw = rad_to_raw(math.radians(50.0), calib[2])   # what a +50 scalar allows
    for b in range(n):
        o = b * HFE_ENV_STRIDE
        if body[o] <= haa_raw <= body[o + 1]:
            assert not (body[o + 2] <= bad_raw <= body[o + 3]), (
                "a +50 deg fold at haa -15 must be refused: the gate caps it "
                "at +13.8 deg there, which is why a scalar cannot do this job"
            )
            return
    raise AssertionError("no bucket contains haa -15")
