"""Unit tests for the battery-shutdown decision logic (pure, no ROS)."""
from nova_ops.battery_shutdown import (
    ShutdownDecider,
    SAFETY_NORMAL,
    SAFETY_ESTOP_LATCHED,
    SAFETY_BATTERY_LOW_LATCHED,
)


def test_no_signals_no_fire():
    d = ShutdownDecider()
    assert d.evaluate(t=100.0) is False
    assert d.fired is False


def test_latched_state_fires_immediately():
    d = ShutdownDecider()
    d.on_safety_state(SAFETY_BATTERY_LOW_LATCHED, t=10.0)
    assert d.evaluate(t=10.0) is True
    assert 'latched' in d.reason


def test_estop_latch_does_not_fire():
    d = ShutdownDecider()
    d.on_safety_state(SAFETY_ESTOP_LATCHED, t=10.0)
    assert d.evaluate(t=20.0) is False


def test_raw_sustained_fires_after_window():
    d = ShutdownDecider(raw_sustain_s=2.0)
    d.on_battery_low(True, t=10.0)
    assert d.evaluate(t=11.0) is False          # only 1.0 s sustained
    assert d.evaluate(t=12.0) is True           # 2.0 s — fires
    assert 'sustained' in d.reason


def test_raw_glitch_resets_window():
    d = ShutdownDecider(raw_sustain_s=2.0)
    d.on_battery_low(True, t=10.0)
    d.on_battery_low(False, t=11.0)             # cleared — reset
    d.on_battery_low(True, t=11.5)
    assert d.evaluate(t=13.0) is False          # 1.5 s since re-assert
    assert d.evaluate(t=13.6) is True           # 2.1 s — fires


def test_fire_is_permanent():
    d = ShutdownDecider(raw_sustain_s=2.0)
    d.on_battery_low(True, t=10.0)
    assert d.evaluate(t=12.5) is True
    d.on_battery_low(False, t=13.0)             # voltage "recovered" at idle
    assert d.evaluate(t=20.0) is True           # decision stands
    d.on_safety_state(SAFETY_NORMAL, t=21.0)    # even if FSM cleared
    assert d.evaluate(t=22.0) is True


def test_latched_beats_raw_window():
    d = ShutdownDecider(raw_sustain_s=2.0)
    d.on_battery_low(True, t=10.0)
    d.on_safety_state(SAFETY_BATTERY_LOW_LATCHED, t=10.1)
    assert d.evaluate(t=10.1) is True           # no need to wait out 2 s
