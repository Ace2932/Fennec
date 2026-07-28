"""Reading the homing calibration, and deciding whether to publish it (#185).

The firmware's two protection tables are built from this data. Nothing had ever
read the artifact homing writes — `storage.load_latest()` had no consumers and
`nova_locomotion`'s calibration params had no producer — so a completed homing
run never reached the runtime.
"""

import pytest

from nova_ops.safety_envelope.calibration_io import (
    CalibrationFormatError,
    calibration_from_doc,
    read_calibration,
)
from nova_ops.safety_envelope.firmware_limits import build_firmware_tables


def _doc(n=12, sign=+1, home=2048):
    return {
        "schema": 1,
        "created": "2026-07-28T09:00:00",
        "note": "test",
        "joints": {
            j: {
                "name": f"j{j}",
                "home_raw": home,
                "stop_pos_raw": 1000,
                "peak_load": 200,
                "urdf_sign": sign,
            }
            for j in range(1, n + 1)
        },
    }


# ---- reading the artifact -------------------------------------------------


def test_full_doc_loads_every_joint():
    calib = calibration_from_doc(_doc())
    assert sorted(calib) == list(range(1, 13))
    assert calib[1].home_raw == 2048.0 and calib[1].urdf_sign == +1


def test_empty_or_missing_is_the_PRE_HOMING_state_not_an_error():
    """No artifact is normal before the first homing run. It must not stop a
    node from starting — and must not be read as 'calibrated with zeros'."""
    assert calibration_from_doc({}) == {}
    assert read_calibration("/nonexistent/path/servo_offsets_latest.yaml") == {}


def test_urdf_sign_zero_means_UNCALIBRATED_not_calibrated_positive():
    """A joint homed before homing produced signs has sign 0. Reading that as
    +1 would fabricate a direction the robot never observed."""
    calib = calibration_from_doc(_doc(sign=0))
    assert calib == {}


def test_unknown_schema_is_REFUSED():
    """Silently reading a v2 file with v1 assumptions moves the limit table and
    the command together — the #154 shape, where the guard agrees with the bug.
    """
    doc = _doc()
    doc["schema"] = 2
    with pytest.raises(CalibrationFormatError, match="schema"):
        calibration_from_doc(doc)


def test_malformed_entries_raise_rather_than_defaulting():
    bad = _doc()
    del bad["joints"][3]["home_raw"]
    with pytest.raises(CalibrationFormatError, match="home_raw"):
        calibration_from_doc(bad)

    bad = _doc()
    bad["joints"][99] = {"home_raw": 2048, "urdf_sign": 1}
    with pytest.raises(CalibrationFormatError, match="outside"):
        calibration_from_doc(bad)

    bad = _doc()
    bad["joints"] = ["not", "a", "mapping"]
    with pytest.raises(CalibrationFormatError):
        calibration_from_doc(bad)


def test_a_sign_with_no_home_raw_still_fails_loud():
    """build_calib's doctrine must survive the trip through this loader: a
    joint given a sign but no home would take home_raw=0.0, a 2048-count
    (180 deg) error that the firmware window — built from the SAME calibration
    — moves with and cannot catch."""
    doc = _doc(n=2)
    doc["joints"][2]["home_raw"] = 9999  # outside the STS3215 range
    with pytest.raises(ValueError, match="outside the STS3215 range"):
        calibration_from_doc(doc)


# ---- the cross-package seam ----------------------------------------------


def test_round_trips_through_nova_calibration_REAL_writer(tmp_path, monkeypatch):
    """Read what homing actually writes, not what we think it writes.

    The schema is written in nova_calibration and parsed in nova_ops, and
    nova_ops cannot import nova_calibration (that package already imports this
    one — the reverse is a cycle). So the two sides can drift, and asserting
    against a hand-built dict would not notice: a stale reader and a stale test
    agree with each other. This drives the REAL save_offsets().
    """
    storage = pytest.importorskip(
        "nova_calibration.servo_homing.storage",
        reason="nova_calibration not on the path",
    )
    monkeypatch.setattr(storage, "CALIB_DIR", str(tmp_path))

    class R:
        def __init__(self, jid):
            self.joint_id = jid
            self.name = f"j{jid}"
            self.home_raw = 2000 + jid
            self.stop_pos_raw = 3000
            self.peak_load = 210
            self.urdf_sign = +1 if jid % 2 else -1

    storage.save_offsets([R(j) for j in range(1, 13)])
    calib = read_calibration(str(tmp_path / storage.LATEST))

    assert sorted(calib) == list(range(1, 13))
    for j in range(1, 13):
        assert calib[j].home_raw == float(2000 + j)
        assert calib[j].urdf_sign == (+1 if j % 2 else -1)


# ---- publish-or-not ------------------------------------------------------


def test_full_calibration_yields_BOTH_tables():
    limits, env, state = build_firmware_tables(calibration_from_doc(_doc()))
    assert state == "active"
    assert len(limits) == 24
    assert len(env) > 1


def test_partial_calibration_STILL_PUBLISHES_the_per_joint_table():
    """Partial protection beats none, and this table degrades safely.

    I first wrote the opposite rule — withhold everything unless fully
    calibrated — on the belief that a partial table came out all-wide-open and
    would merely look armed. It does not: every homed joint gets its real narrow
    window and only the unhomed one stays open. Withholding would have stripped
    protection off 11 joints to tidy up a status flag.
    """
    doc = _doc()
    del doc["joints"][5]                      # FR hfe never homed
    limits, env, state = build_firmware_tables(calibration_from_doc(doc))
    assert state == "partial"
    assert limits is not None
    # joint 1 is homed -> real window; joint 5 is not -> wide open
    assert (limits[0], limits[1]) != (0.0, 4095.0)
    assert (limits[8], limits[9]) == (0.0, 4095.0)


def test_partial_calibration_withholds_the_ENVELOPE():
    """The posture table fails differently: a leg's fold window is selected by
    that leg's haa, so a leg missing either joint cannot be bounded at all and a
    guessed home would clamp it against the wrong hip."""
    doc = _doc()
    del doc["joints"][5]
    _, env, state = build_firmware_tables(calibration_from_doc(doc))
    assert state == "partial"
    assert env is None


def test_no_calibration_publishes_NOTHING():
    limits, env, state = build_firmware_tables({})
    assert limits is None and env is None
    assert state == "uncalibrated"


def test_a_partial_table_is_INDISTINGUISHABLE_to_the_firmware():
    """Why the caller must surface the state, not infer it from arming.

    A partial table is accepted by the firmware exactly like a complete one and
    bumps the same counter. So "the firmware accepted a table" cannot mean
    "every joint is protected" — pinned here because #187's preflight check
    would otherwise be free to assume it.
    """
    full, _, _ = build_firmware_tables(calibration_from_doc(_doc()))
    doc = _doc()
    del doc["joints"][5]
    part, _, _ = build_firmware_tables(calibration_from_doc(doc))
    assert len(part) == len(full) == 24        # same shape, same validity
    assert part != full                        # but not the same protection


# ---- #188: where a runtime node gets its calibration ----------------------


def test_params_win_when_they_carry_a_real_calibration(tmp_path):
    """Deliberate bench override beats the artifact."""
    from nova_ops.safety_envelope.calibration_io import resolve_calibration

    f = tmp_path / "cal.yaml"
    import yaml
    f.write_text(yaml.safe_dump(_doc(home=1000)))

    calib, source = resolve_calibration([2048.0] * 12, [1] * 12, str(f))
    assert source == "params"
    assert calib[1].home_raw == 2048.0        # params, not the file's 1000


def test_all_zero_sign_is_the_DEFAULT_not_a_calibration(tmp_path):
    """The bug this closes.

    nova_locomotion declares urdf_sign [0]*12 and nothing ever set it, so it
    read that as its calibration, got {} from build_calib, and published
    RADIANS to a firmware reading raw counts. An all-zero sign vector is the
    declared default; the artifact is the real source.
    """
    from nova_ops.safety_envelope.calibration_io import resolve_calibration

    f = tmp_path / "cal.yaml"
    import yaml
    f.write_text(yaml.safe_dump(_doc(home=1234)))

    calib, source = resolve_calibration([0.0] * 12, [0] * 12, str(f))
    assert source.startswith("file:")
    assert calib[1].home_raw == 1234.0


def test_no_params_and_no_artifact_is_reported_as_NONE(tmp_path):
    """Pre-homing. Must be distinguishable from an operator override — the two
    look identical from outside without the source string."""
    from nova_ops.safety_envelope.calibration_io import resolve_calibration

    calib, source = resolve_calibration(
        [0.0] * 12, [0] * 12, str(tmp_path / "missing.yaml"))
    assert calib == {}
    assert source == "none"


def test_a_partially_signed_param_vector_still_counts_as_params(tmp_path):
    """One observed sign is a real (if partial) calibration, and must not be
    silently replaced by the file — that would discard an operator's work."""
    from nova_ops.safety_envelope.calibration_io import resolve_calibration

    import yaml
    f = tmp_path / "cal.yaml"
    f.write_text(yaml.safe_dump(_doc()))

    signs = [0] * 12
    signs[0] = 1
    calib, source = resolve_calibration([2048.0] * 12, signs, str(f))
    assert source == "params"
    assert sorted(calib) == [1]
