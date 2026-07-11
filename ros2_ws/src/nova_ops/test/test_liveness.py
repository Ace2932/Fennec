"""Unit tests for the liveness watchdog decision logic (no rclpy)."""

from nova_ops.liveness import LivenessMonitor


def test_no_heartbeat_is_not_ok():
    m = LivenessMonitor(heartbeat_timeout_s=3.0)
    ok, reason = m.evaluate(now_s=10.0)
    assert ok is False
    assert "no /heartbeat" in reason


def test_fresh_heartbeat_ok():
    m = LivenessMonitor(heartbeat_timeout_s=3.0)
    m.on_heartbeat(1, now_s=10.0)
    ok, _ = m.evaluate(now_s=11.0)  # 1 s later, < 3 s timeout
    assert ok is True


def test_stale_heartbeat_trips():
    m = LivenessMonitor(heartbeat_timeout_s=3.0)
    m.on_heartbeat(1, now_s=10.0)
    ok, reason = m.evaluate(now_s=14.0)  # 4 s > 3 s timeout
    assert ok is False
    assert "stale" in reason


def test_heartbeat_change_refreshes():
    m = LivenessMonitor(heartbeat_timeout_s=3.0)
    m.on_heartbeat(1, now_s=10.0)
    m.on_heartbeat(2, now_s=12.0)  # new beat at 12 s
    ok, _ = m.evaluate(now_s=14.0)  # 2 s since last change < 3 s
    assert ok is True


def test_unchanged_heartbeat_does_not_refresh():
    m = LivenessMonitor(heartbeat_timeout_s=3.0)
    m.on_heartbeat(7, now_s=10.0)
    m.on_heartbeat(7, now_s=12.0)  # same value = no new beat
    ok, _ = m.evaluate(now_s=13.5)  # 3.5 s since the real change > 3 s
    assert ok is False


def test_teensy_reset_detected():
    m = LivenessMonitor()
    m.on_heartbeat(50, now_s=10.0)
    m.on_heartbeat(0, now_s=11.0)  # counter went backwards = reboot
    assert m.teensy_reset_count == 1


def test_command_stale_trips():
    m = LivenessMonitor()
    m.on_heartbeat(1, now_s=10.0)
    m.on_command_stale(True)
    ok, reason = m.evaluate(now_s=10.5)
    assert ok is False
    assert "command_stale" in reason


def test_safety_fault_trips():
    m = LivenessMonitor()
    m.on_heartbeat(1, now_s=10.0)
    m.on_safety_state(3)  # SAFETY_FAULT_OTHER (stall)
    ok, reason = m.evaluate(now_s=10.5)
    assert ok is False
    assert "safety_state" in reason


def test_recovers_when_all_clear():
    m = LivenessMonitor()
    m.on_heartbeat(1, now_s=10.0)
    m.on_command_stale(True)
    assert m.evaluate(now_s=10.5)[0] is False
    m.on_command_stale(False)
    m.on_heartbeat(2, now_s=11.0)
    assert m.evaluate(now_s=11.5)[0] is True
