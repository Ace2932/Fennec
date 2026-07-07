"""Backlash comp: steady bias, single flip on reversal, deadband jitter."""

import pytest

from nova_locomotion.gait.backlash import (
    DEFAULT_BACKLASH_RAD,
    BacklashComp,
)

B = 0.010  # test backlash (rad), half-bias 0.005
DB = 0.002


def _comp():
    return BacklashComp({"j": B}, deadband=DB)


def test_default_table_covers_all_twelve_joints():
    assert len(DEFAULT_BACKLASH_RAD) == 12
    assert DEFAULT_BACKLASH_RAD["FL_haa"] == pytest.approx(0.0087)
    assert DEFAULT_BACKLASH_RAD["RR_kfe"] == pytest.approx(0.0087)


def test_steady_motion_constant_half_bias():
    c = _comp()
    targets = [0.00, 0.01, 0.02, 0.03, 0.04]
    out = [c.apply("j", t, +1.0) for t in targets]
    assert out == pytest.approx([t + 0.5 * B for t in targets])


def test_reversal_flips_bias_exactly_once():
    c = _comp()
    c.apply("j", 0.00, +1.0)
    c.apply("j", 0.05, +1.0)  # extreme = 0.05
    # real reversal (well beyond deadband): bias flips negative...
    assert c.apply("j", 0.04, -1.0) == pytest.approx(0.04 - 0.5 * B)
    # ...and STAYS flipped on continued motion (no double-flip)
    assert c.apply("j", 0.03, -1.0) == pytest.approx(0.03 - 0.5 * B)
    assert c.apply("j", 0.02, -1.0) == pytest.approx(0.02 - 0.5 * B)


def test_jitter_within_deadband_keeps_bias():
    c = _comp()
    c.apply("j", 0.00, +1.0)
    c.apply("j", 0.05, +1.0)
    # retreat by less than the deadband with a reversed direction hint:
    # NOT a real reversal, bias stays positive
    assert c.apply("j", 0.0495, -1.0) == pytest.approx(0.0495 + 0.5 * B)
    assert c.apply("j", 0.0505, +1.0) == pytest.approx(0.0505 + 0.5 * B)
    assert c.apply("j", 0.0495, -1.0) == pytest.approx(0.0495 + 0.5 * B)


def test_deadband_then_real_reversal_still_flips():
    c = _comp()
    c.apply("j", 0.05, +1.0)
    c.apply("j", 0.0495, -1.0)  # jitter, ignored
    assert c.apply("j", 0.04, -1.0) == pytest.approx(0.04 - 0.5 * B)


def test_zero_direction_keeps_current_bias():
    c = _comp()
    c.apply("j", 0.01, +1.0)
    assert c.apply("j", 0.01, 0.0) == pytest.approx(0.01 + 0.5 * B)


def test_unseeded_and_unknown_joint_pass_through():
    c = _comp()
    assert c.apply("j", 0.02, 0.0) == pytest.approx(0.02)  # no direction yet
    assert c.apply("other", 0.02, +1.0) == pytest.approx(0.02)  # no table entry


def test_reset_forgets_direction():
    c = _comp()
    c.apply("j", 0.05, +1.0)
    c.reset()
    # post-reset the first motion seeds fresh — no deadband to overcome
    assert c.apply("j", 0.049, -1.0) == pytest.approx(0.049 - 0.5 * B)
