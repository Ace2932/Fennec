"""Unit tests for the haa sign confirmation probe (#194).

Pure-Python — no rclpy required. `confirm_and_record`/`compute_probe_target`
are the ROS-free logic `haa_confirm._run()` calls; see that module's
docstring for why an operator observation (not an automatic one) is what
this closes.
"""

import pytest

from nova_calibration.servo_homing.haa_confirm import (
    CLAMP_DEG,
    MAX_PROBE_DEG,
    HaaConfirmRefused,
    compute_probe_target,
    confirm_and_record,
    deg_to_raw,
    probe_fence_raw,
    resolve_haa_joint,
)
from nova_ops.safety_envelope import limits as limits_mod
from nova_ops.safety_envelope.derived_signs import (
    DERIVED_HAA_INBOARD_SIGN,
    HAA_IDS,
    HOME_TICK,
)

FL = HAA_IDS["FL"]
RL = HAA_IDS["RL"]

# well inside the safe probe bound (~85 raw for MAX_PROBE_DEG=7.5)
SMALL_DELTA = 50.0


@pytest.fixture(autouse=True)
def _isolate_haa_runtime_state(monkeypatch):
    """HAA_INBOARD_SIGN / HAA_SIGN_CONFIRMATION are module-global mutable
    dicts (limits.py) — replace them with copies so nothing here leaks
    between tests or into other test modules, matching the pattern already
    used in test_derived_signs.py / test_firmware_limits.py."""
    monkeypatch.setattr(
        limits_mod, "HAA_INBOARD_SIGN", dict(limits_mod.HAA_INBOARD_SIGN)
    )
    monkeypatch.setattr(
        limits_mod, "HAA_SIGN_CONFIRMATION", dict(limits_mod.HAA_SIGN_CONFIRMATION)
    )


def _agreeing_observed_inboard(joint_id: int, raw_delta: float) -> bool:
    """Whichever observed_inboard makes this raw_delta AGREE with the CAD
    derivation for this joint — see confirm_haa_sign's own math."""
    expected = DERIVED_HAA_INBOARD_SIGN[joint_id]
    positive_delta_wants_inboard = expected > 0
    return positive_delta_wants_inboard if raw_delta > 0 else not positive_delta_wants_inboard


# ---- resolve_haa_joint ----------------------------------------------------


def test_resolve_by_name_and_by_id_agree():
    assert resolve_haa_joint("FL") == (FL, "FL")
    assert resolve_haa_joint(str(FL)) == (FL, "FL")


def test_resolve_refuses_a_non_haa_joint():
    with pytest.raises(HaaConfirmRefused):
        resolve_haa_joint("FL_hfe")
    with pytest.raises(HaaConfirmRefused):
        resolve_haa_joint("2")  # bus id 2 is FL_hfe, not a haa id


# ---- compute_probe_target: the safety fence --------------------------------


def test_probe_target_stays_inside_the_runtime_clamp():
    lo, hi = probe_fence_raw()
    target = compute_probe_target(HOME_TICK, MAX_PROBE_DEG, +1)
    assert lo <= target <= hi
    # strictly inside home +- the runtime clamp, not just inside its own fence
    assert target < HOME_TICK + deg_to_raw(CLAMP_DEG)


def test_probe_deg_beyond_the_safe_bound_is_refused():
    """(iii) — the probe can never exceed the safety margin, let alone the
    runtime's own +-15 deg clamp."""
    with pytest.raises(HaaConfirmRefused, match="deg"):
        compute_probe_target(HOME_TICK, MAX_PROBE_DEG + 0.1, +1)


def test_probe_from_an_already_out_of_window_present_is_refused():
    """A present position outside the conservative clamp window is not a
    state this tool should nudge further from, regardless of probe size."""
    lo, hi = probe_fence_raw()
    with pytest.raises(HaaConfirmRefused, match="outside"):
        compute_probe_target(hi + 100, 1.0, -1)


def test_zero_or_negative_probe_deg_is_refused():
    with pytest.raises(HaaConfirmRefused):
        compute_probe_target(HOME_TICK, 0.0, +1)
    with pytest.raises(HaaConfirmRefused):
        compute_probe_target(HOME_TICK, -3.0, +1)


def test_max_probe_deg_is_strictly_inside_the_runtime_clamp():
    """Negative control on the module's OWN safety invariant, not a
    caller-facing assertion — this is what the module-level `assert` in
    haa_confirm.py enforces at import time (a future change to the runtime
    clamp cannot silently widen the probe past it)."""
    assert 0 < MAX_PROBE_DEG < CLAMP_DEG


# ---- confirm_and_record: (i) agree / (ii) disagree / no-op ----------------


def test_agreeing_observation_fills_the_sign():
    """(i) A confirmation that agrees with the CAD derivation records +
    returns the sign, and it reaches limits.HAA_INBOARD_SIGN."""
    expected = DERIVED_HAA_INBOARD_SIGN[FL]
    observed_inboard = _agreeing_observed_inboard(FL, SMALL_DELTA)
    confirmation = confirm_and_record(
        FL, SMALL_DELTA, observed_inboard, assembly="test rig / FL / servo 1"
    )
    assert confirmation is not None
    assert confirmation.sign == expected
    assert limits_mod.HAA_INBOARD_SIGN[FL] == expected
    assert limits_mod.confirmed_haa_sign(FL) == expected
    limits_mod.check_haa_sign_provenance()  # sign + record agree


def test_disagreeing_observation_leaves_the_sign_None_and_logs():
    """(ii) A mismatch must NOT record anything — the observation wins over
    the derivation only when they AGREE; disagreement is a loud stop."""
    expected = DERIVED_HAA_INBOARD_SIGN[FL]
    wrong_observed_inboard = not _agreeing_observed_inboard(FL, SMALL_DELTA)
    logged = []
    confirmation = confirm_and_record(
        FL,
        SMALL_DELTA,
        wrong_observed_inboard,
        assembly="test rig / FL / servo 1",
        log=logged.append,
    )
    assert confirmation is None
    assert limits_mod.HAA_INBOARD_SIGN[FL] is None
    assert limits_mod.HAA_SIGN_CONFIRMATION[FL] is None
    assert any("MISMATCH" in msg for msg in logged), logged


def test_already_confirmed_is_a_no_op():
    observed_inboard = _agreeing_observed_inboard(RL, SMALL_DELTA)
    first = confirm_and_record(
        RL, SMALL_DELTA, observed_inboard, assembly="test rig / RL"
    )
    assert first is not None
    logged = []
    second = confirm_and_record(
        RL, SMALL_DELTA, not observed_inboard,  # even a "wrong" report...
        assembly="test rig / RL", log=logged.append,
    )
    # ...changes nothing, because the no-op check runs before confirm_haa_sign
    assert second is not None
    assert second.sign == first.sign
    assert any("no-op" in msg for msg in logged), logged


def test_confirm_and_record_refuses_a_probe_it_did_not_command():
    """A raw_delta bigger than the safe probe bound must be refused outright
    — confirm_and_record is not just a wrapper around confirm_haa_sign, it is
    also a second gate against being handed an oversized/untrusted motion."""
    with pytest.raises(HaaConfirmRefused):
        confirm_and_record(
            FL, deg_to_raw(CLAMP_DEG), True, assembly="test rig / FL"
        )


def test_confirm_and_record_requires_a_non_haa_joint_id_to_raise():
    with pytest.raises(ValueError, match="not a haa joint"):
        confirm_and_record(2, SMALL_DELTA, True, assembly="x")


def test_confirm_and_record_requires_an_assembly():
    with pytest.raises(ValueError, match="assembly"):
        confirm_and_record(FL, SMALL_DELTA, True, assembly="   ")
