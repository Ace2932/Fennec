"""#159: the counts adapter must SAY which calibration state it is in.

`_CountsAdapter` is identity until every joint is homed. That identity means
radians reach a firmware reading raw counts — harmless before hardware (nothing
is listening), dangerous during bring-up (0.6 rad becomes 0.6 counts, every
servo driven toward a stop). The two states were indistinguishable in the log.

node.py needs rclpy, which is not installed off-Jetson, so the ROS surface it
touches is stubbed here. That is deliberate: the log lines ARE the fix, and a
test that only covered the pure classifier would not have caught the adapter
forgetting to call it.
"""

import sys
import types

import pytest


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return sys.modules[name]


@pytest.fixture(scope="module")
def adapter_cls():
    """Import nova_locomotion.node with the ROS packages stubbed."""
    if "rclpy" not in sys.modules:
        _stub(
            "rclpy",
            init=lambda *a, **k: None,
            spin=lambda *a, **k: None,
            shutdown=lambda *a, **k: None,
        )
        _stub(
            "rclpy.node",
            Node=type("Node", (), {"__init__": lambda self, *a, **k: None}),
        )
        _stub("geometry_msgs")
        _stub("geometry_msgs.msg", Twist=type("Twist", (), {}))
        _stub("sensor_msgs")
        _stub("sensor_msgs.msg", JointState=type("JointState", (), {}))
        _stub("std_msgs")
        _stub("std_msgs.msg", String=type("String", (), {}))

    from nova_locomotion.node import _CountsAdapter

    return _CountsAdapter


class _RecordingLogger:
    def __init__(self):
        self.infos = []
        self.warns = []

    def info(self, msg):
        self.infos.append(msg)

    def warn(self, msg):
        self.warns.append(msg)


def _calib(ids):
    from nova_ops.safety_envelope.firmware_limits import JointHomeCalib

    return {i: JointHomeCalib(home_raw=2048.0, urdf_sign=+1) for i in ids}


def test_uncalibrated_announces_INFO_not_a_warning(adapter_cls):
    """Pre-hardware is the expected state — warning on it trains people to
    ignore the warning that matters."""
    log = _RecordingLogger()
    adapter_cls(raw_pub=None, calib={}, logger=log)
    assert log.warns == []
    assert any("no joint calibration" in m for m in log.infos), log.infos


def test_PARTIAL_calibration_warns_and_names_the_missing_joints(adapter_cls):
    """The dangerous state. Naming the joints is the point: during bring-up the
    question is always *which* ones are still unhomed."""
    log = _RecordingLogger()
    adapter_cls(raw_pub=None, calib=_calib(set(range(1, 13)) - {4, 11}), logger=log)
    assert len(log.warns) == 1, log.warns
    msg = log.warns[0]
    assert "PARTIAL" in msg
    assert "[4, 11]" in msg, msg
    # and it must say what actually happens, not just that something is missing
    assert "raw counts" in msg


def test_active_calibration_says_counts_are_live(adapter_cls):
    log = _RecordingLogger()
    adapter_cls(raw_pub=None, calib=_calib(range(1, 13)), logger=log)
    assert log.warns == []
    assert any("ACTIVE" in m for m in log.infos), log.infos


def test_announcement_happens_ONCE_not_per_publish(adapter_cls):
    """At 100 Hz a per-publish warning is a denial-of-service on the log."""

    class _Pub:
        def __init__(self):
            self.n = 0

        def publish(self, msg):
            self.n += 1

    class _Msg:
        position = [0.0] * 12

    log = _RecordingLogger()
    pub = _Pub()
    a = adapter_cls(raw_pub=pub, calib=_calib(set(range(1, 13)) - {4}), logger=log)
    for _ in range(50):
        a.publish(_Msg())
    assert pub.n == 50
    assert len(log.warns) == 1, log.warns


def test_a_short_message_warns_once_even_when_calibration_is_full(adapter_cls):
    """A full calibration that still declines to convert means the MESSAGE was
    malformed — a different fault, and it was silent."""

    class _Pub:
        def publish(self, msg):
            pass

    class _ShortMsg:
        position = [0.0] * 9

    log = _RecordingLogger()
    a = adapter_cls(raw_pub=_Pub(), calib=_calib(range(1, 13)), logger=log)
    a.publish(_ShortMsg())
    a.publish(_ShortMsg())
    assert len(log.warns) == 1, log.warns
    assert "9-joint message" in log.warns[0]


def test_no_logger_is_not_a_crash(adapter_cls):
    """Constructed without a logger in tests and tools — must stay usable."""

    class _Pub:
        def publish(self, msg):
            pass

    class _Msg:
        position = [0.0] * 12

    a = adapter_cls(raw_pub=_Pub(), calib={}, logger=None)
    a.publish(_Msg())
