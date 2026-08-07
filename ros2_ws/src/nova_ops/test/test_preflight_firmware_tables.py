"""#187: preflight must refuse a robot whose firmware protection is unarmed.

The Teensy boots with both tables wide open — per-joint ROM at 0..4095 and the
posture backstop off — and only the host narrows them. Preflight checked the
E-stop, the battery latch and the servo bus, and passed a robot with no
firmware-side protection at all.

Only `classify()` is tested here: `run()` is rclpy plumbing. The check keeps its
ROS imports INSIDE run() precisely so these tests import and run off the Jetson
— a module-level `import rclpy` would skip the file and leave a safety check
with no coverage anywhere.
"""

import sys
import types


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)


# firmware_tables.py itself imports no ROS at module scope, but importing it
# initialises the checks PACKAGE, whose __init__ pulls estop/bus_ping/battery —
# and those do import rclpy. Stub the ROS surface so the pure decision logic is
# reachable off the Jetson. Same approach as test_counts_adapter_log.py.
if "rclpy" not in sys.modules:
    _stub("rclpy", spin_once=lambda *a, **k: None)
    _stub("rclpy.qos", QoSProfile=object, ReliabilityPolicy=object,
          DurabilityPolicy=object, QoSDurabilityPolicy=object,
          QoSReliabilityPolicy=object)
    _stub("std_msgs")
    # ONLY what checks/__init__ transitively needs. Deliberately narrow:
    # sys.modules is global to the pytest session, so an over-broad stub here
    # (sensor_msgs.JointState=object) silently broke test_counts_adapter_log,
    # which builds its own richer stubs. Stub the minimum, own nothing else.
    _stub("std_msgs.msg", Bool=object, String=object, Int32=object,
          Float32MultiArray=object)

from nova_ops.preflight.checks.base import CheckStatus  # noqa: E402
from nova_ops.preflight.checks.firmware_tables import (  # noqa: E402
    FirmwareTablesCheck,
)


def test_active_passes():
    r = FirmwareTablesCheck.classify("active;missing=[]")
    assert r.status == CheckStatus.OK


def test_uncalibrated_FAILS_and_says_the_teensy_is_wide_open():
    r = FirmwareTablesCheck.classify("uncalibrated;missing=[1, 2, 3]")
    assert r.status == CheckStatus.FAIL
    assert "wide-open" in r.message


def test_partial_FAILS_because_the_chassis_backstop_is_withheld():
    """Not a WARN. A partial calibration still publishes the per-joint table,
    so joints are protected — but build_hfe_envelope_data withholds the posture
    envelope entirely when any leg is missing a joint, so the CHASSIS has no
    protection below the host. Passing that would be the exact
    'partial looks armed' confusion the state string exists to prevent."""
    r = FirmwareTablesCheck.classify("partial;missing=[5]")
    assert r.status == CheckStatus.FAIL
    assert "backstop is NOT armed" in r.message
    assert "[5]" in r.message


def test_an_unknown_state_string_FAILS_rather_than_passing():
    """Fail closed. A state this check does not understand must not read as
    healthy — that is how a renamed state silently disarms a safety gate."""
    r = FirmwareTablesCheck.classify("armed")  # plausible, not emitted
    assert r.status == CheckStatus.FAIL


def test_it_does_not_claim_the_firmware_ACCEPTED_the_tables():
    """Honesty about what was established.

    This reads the HOST's view. Both firmware callbacks validate whole-message
    and reject silently, so a published-and-refused table looks identical from
    here. The OK message has to say so until #186 exposes the receive counters.
    """
    r = FirmwareTablesCheck.classify("active;missing=[]")
    assert "not verified" in r.message


def test_it_is_registered_as_a_critical_v1_check():
    from nova_ops.preflight.checks import V1_CHECKS

    names = [c.name() for c in V1_CHECKS]
    assert "firmware_tables" in names
    check = next(c for c in V1_CHECKS if c.name() == "firmware_tables")
    assert check.critical is True, "an unarmed robot must BLOCK bringup"


def test_run_executes_past_the_imports_and_returns_a_check_result(monkeypatch):
    """#283: run() used rclpy, QoSProfile, ReliabilityPolicy, DurabilityPolicy
    and String with NO import anywhere in the file — every call raised
    NameError, and node.py:62-68 turns that into a critical FAIL, so preflight
    could never pass a single robot. classify() being covered above did not
    catch this: run()'s body was never executed.

    This drives run() itself through a fake node + the rclpy stub modules
    already registered in sys.modules at the top of this file (module-level
    `import rclpy` inside run() resolves against sys.modules, not against
    anything importable from this test), patched just enough to be callable.
    The essential assertion is the last one: run() must not raise NameError.
    """
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

    result = FirmwareTablesCheck().run(_FakeNode())

    assert spins["n"] > 0, "run() never reached its spin_once loop"
    assert result.name == "firmware_tables"
    assert result.status == CheckStatus.STALE
    assert "5 s" in result.message
