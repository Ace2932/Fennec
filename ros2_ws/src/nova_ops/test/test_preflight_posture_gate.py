"""#282: preflight must refuse a robot whose chassis posture gate is down.

wrapper.py's `_clamp_posture` silently disabled itself when the joint-ID map
failed to load — no log, no observable state, and the node still looked
healthy. Preflight checked the E-stop, the battery latch, the servo bus and
the firmware tables, and would happily pass a robot with the posture gate
gone and, in the pre-homing window, the firmware envelope empty too.

Only `classify()` is tested for the pure logic: `run()` is rclpy plumbing.
The check keeps its ROS imports INSIDE run() precisely so these tests import
and run off the Jetson (same convention as test_preflight_firmware_tables.py).
"""

import sys
import types


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)


if "rclpy" not in sys.modules:
    _stub("rclpy", spin_once=lambda *a, **k: None)
    _stub("rclpy.qos", QoSProfile=object, ReliabilityPolicy=object,
          DurabilityPolicy=object, QoSDurabilityPolicy=object,
          QoSReliabilityPolicy=object)
    _stub("std_msgs")
    _stub("std_msgs.msg", Bool=object, String=object, Int32=object,
          Float32MultiArray=object)

from nova_ops.preflight.checks.base import CheckStatus  # noqa: E402
from nova_ops.preflight.checks.posture_gate import PostureGateCheck  # noqa: E402


def test_active_passes():
    r = PostureGateCheck.classify("active")
    assert r.status == CheckStatus.OK


def test_inactive_FAILS_and_names_the_joint_map_as_the_cause():
    r = PostureGateCheck.classify("inactive")
    assert r.status == CheckStatus.FAIL
    assert "joint-ID map failed to load" in r.message


def test_an_unknown_state_string_FAILS_rather_than_passing():
    """Fail closed. A state this check does not understand must not read as
    healthy — that is how a renamed state silently disarms a safety gate."""
    r = PostureGateCheck.classify("armed")  # plausible, not emitted
    assert r.status == CheckStatus.FAIL


def test_it_is_registered_as_a_critical_v1_check():
    from nova_ops.preflight.checks import V1_CHECKS

    names = [c.name() for c in V1_CHECKS]
    assert "posture_gate" in names
    check = next(c for c in V1_CHECKS if c.name() == "posture_gate")
    assert check.critical is True, "a robot with no chassis gate must BLOCK bringup"


def test_run_executes_past_the_imports_and_returns_a_check_result(monkeypatch):
    """#283's lesson: a check whose run() body never actually executes (a
    NameError on its own imports, or an import missing entirely) still passes
    a classify()-only test suite. Drive run() itself through a fake node +
    the rclpy stub modules already registered above, patched just enough to
    be callable. The essential assertion is the last one: run() must not
    raise NameError."""
    qos_mod = sys.modules["rclpy.qos"]

    class _FakeQoSProfile:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _FakeReliabilityPolicy:
        RELIABLE = 1

    class _FakeDurabilityPolicy:
        TRANSIENT_LOCAL = 1

    monkeypatch.setattr(qos_mod, "QoSProfile", _FakeQoSProfile, raising=False)
    monkeypatch.setattr(qos_mod, "ReliabilityPolicy", _FakeReliabilityPolicy, raising=False)
    monkeypatch.setattr(qos_mod, "DurabilityPolicy", _FakeDurabilityPolicy, raising=False)

    spins = {"n": 0}
    monkeypatch.setattr(
        sys.modules["rclpy"], "spin_once",
        lambda node, timeout_sec=0.0: spins.__setitem__("n", spins["n"] + 1),
        raising=False,
    )

    class _FakeClock:
        """Advances 2s per call so the 5s wait window clears in ~3 calls
        instead of a real 5s sleep — no message ever arrives (cb is never
        invoked), driving run() down its STALE/timeout path."""

        def __init__(self):
            self._t = 0

        def now(self):
            self._t += 2_000_000_000
            return types.SimpleNamespace(nanoseconds=self._t)

    class _FakeNode:
        def __init__(self):
            self._clock = _FakeClock()

        def get_clock(self):
            return self._clock

        def create_subscription(self, msg_type, topic, cb, qos):
            return object()

        def destroy_subscription(self, sub):
            pass

    result = PostureGateCheck().run(_FakeNode())

    assert spins["n"] > 0, "run() never reached its spin_once loop"
    assert result.name == "posture_gate"
    assert result.status == CheckStatus.STALE
    assert "5 s" in result.message
