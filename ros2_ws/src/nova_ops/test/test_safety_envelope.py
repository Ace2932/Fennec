"""Unit tests for the safety envelope library.

Pure-Python tests — no rclpy required. Validates limit storage,
counter accounting, and the clamp + velocity + load logic in isolation.
"""

import math
import types


from nova_ops.safety_envelope import (
    EnvelopeCounters,
    JointLimit,
    JointLimits,
    SafeJointCommandPublisher,
    load_default_limits,
)


# ---- Limit table -----------------------------------------------------


def test_default_limits_cover_active_legs():
    lim = load_default_limits()
    for i in range(1, 13):
        assert i in lim, f"joint {i} missing"
    assert 13 not in lim, "arm IDs should NOT be in default (leg-only) table"


def test_arm_optional():
    lim = load_default_limits(include_arm=True)
    for i in range(13, 19):
        assert i in lim


def test_soft_margin_is_2_deg():
    lim = JointLimit(lower=-1.0, upper=1.0, velocity=10.0, effort=0.7)
    assert math.isclose(lim.soft_lower - lim.lower, math.radians(2.0))
    assert math.isclose(lim.upper - lim.soft_upper, math.radians(2.0))


# ---- Counters --------------------------------------------------------


def test_counter_flat_layout():
    c = EnvelopeCounters(joint_ids=[1, 2, 3])
    assert c.as_flat_list() == [0] * 9  # 3 modes * 3 joints
    c.increment("position", 1)
    c.increment("velocity", 2)
    c.increment("load", 3)
    flat = c.as_flat_list()
    # position_1=1, others zero; velocity_2=1; load_3=1
    assert flat[0] == 1
    assert flat[4] == 1  # position(3) + velocity(2-1) idx
    assert flat[8] == 1  # position(3) + velocity(3) + load(3-1) idx


def test_counter_ignores_untracked_joint():
    c = EnvelopeCounters(joint_ids=[1, 2])
    c.increment("position", 99)  # silently noop
    assert sum(c.as_flat_list()) == 0


def test_counter_reset():
    c = EnvelopeCounters(joint_ids=[1])
    c.increment("position", 1)
    c.increment("load", 1)
    c.reset()
    assert sum(c.as_flat_list()) == 0


# ---- Wrapper ---------------------------------------------------------


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self):
        self._ns = 0
        self.logs = []
        self._clock = types.SimpleNamespace(
            now=lambda: types.SimpleNamespace(nanoseconds=self._ns)
        )

    def get_clock(self):
        return self._clock

    def advance(self, sec):
        self._ns += int(sec * 1e9)

    def get_logger(self):
        node = self

        class _L:
            def warn(self, m):
                node.logs.append(m)

            def info(self, m):
                node.logs.append(m)

        return _L()


class _FakePub:
    def __init__(self):
        self.published = []

    def publish(self, msg):
        self.published.append(list(msg.position))


class _CmdMsg:
    def __init__(self, positions):
        self.position = list(positions)


def _hard_limit(
    lower=-math.pi / 4, upper=math.pi / 4, velocity=math.radians(180), effort=0.7
):
    return JointLimit(lower=lower, upper=upper, velocity=velocity, effort=effort)


def _wrapper(joint_count: int = 1):
    table = {i + 1: _hard_limit() for i in range(joint_count)}
    limits = JointLimits(table)
    node = _FakeNode()
    pub = _FakePub()
    sw = SafeJointCommandPublisher(node=node, limits=limits, raw_publisher=pub)
    return sw, node, pub


def test_publish_passes_in_bounds_command():
    sw, _, pub = _wrapper(1)
    sw.publish(_CmdMsg([0.0]))
    assert pub.published == [[0.0]]


def test_publish_clamps_out_of_bounds():
    sw, node, pub = _wrapper(1)
    sw.publish(_CmdMsg([math.pi]))  # WAY over upper
    assert pub.published
    out = pub.published[0][0]
    # Clamped to soft_upper = upper - 2° margin
    assert out < math.pi / 4
    assert out >= math.pi / 4 - math.radians(2.0) - 1e-6
    assert any("position" in m for m in node.logs)


def test_velocity_clamp_applies_after_first_sample():
    sw, node, pub = _wrapper(1)
    # First publish establishes baseline at 0
    sw.publish(_CmdMsg([0.0]))
    # 10ms later, jump full range — way past velocity limit
    node.advance(0.010)
    sw.publish(_CmdMsg([math.pi / 4 - math.radians(3)]))  # in-position OK
    assert pub.published[-1][0] < math.pi / 4 - math.radians(2)
    # Effective velocity over 10ms would be ~3500 deg/s; limit is 180 deg/s
    # so it must have been clamped (output should be ~0 + 180°/s * 0.01s = 1.8°)
    out_deg = math.degrees(pub.published[-1][0])
    assert out_deg < 5.0, f"velocity not clamped: out={out_deg}°"
    assert any("velocity" in m for m in node.logs)


def test_load_refusal_holds_position():
    sw, node, pub = _wrapper(1)
    # Establish baseline
    sw.publish(_CmdMsg([0.1]))
    # Pretend load samples come in over the threshold
    js = types.SimpleNamespace(effort=[0.85])  # 85% > 70% threshold
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    node.advance(0.020)
    # Now try to move further — should be refused, position held at 0.1
    sw.publish(_CmdMsg([0.3]))
    out = pub.published[-1][0]
    assert math.isclose(out, 0.1, abs_tol=1e-6), f"expected hold at 0.1, got {out}"
    assert any("load" in m for m in node.logs)


def test_load_refusal_allows_backoff():
    """The fix: under sustained +load, a load-REDUCING (back-off) move must
    pass — only load-increasing moves are refused. Pre-fix it held both."""
    sw, node, pub = _wrapper(1)
    sw.publish(_CmdMsg([0.3]))  # baseline at +0.3
    js = types.SimpleNamespace(effort=[0.85])  # +85% load → straining toward +
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    node.advance(0.1)
    sw.publish(_CmdMsg([0.28]))  # small back-off (−, opposite +load)
    out = pub.published[-1][0]
    # Allowed: goal moves toward 0.28, NOT held at 0.3.
    assert math.isclose(out, 0.28, abs_tol=1e-6), (
        f"load-reducing back-off should pass, got {out}"
    )
