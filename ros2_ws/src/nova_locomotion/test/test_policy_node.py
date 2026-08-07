"""policy_node's arming interlock (PolicyGate) and anti-snap ramp math (#289).

policy_node.py needs rclpy (it subclasses Node, imports sensor_msgs etc.),
which is not installed off-Jetson -- same situation node.py is in, so this
follows the SAME stub pattern test_counts_adapter_log.py uses: stub the ROS
message/rclpy modules before importing, so the pure PolicyGate/ramp_* pieces
inside policy_node.py can be exercised without a ROS install. Not guarded on
`"rclpy" not in sys.modules` for the same reason documented there -- another
test module stubbing rclpy first must not skip creating the OTHER modules
this file needs (Imu, Bool) that test_counts_adapter_log.py never had to add.
"""

import sys
import types

import pytest


def _stub(name, **attrs):
    """Get-or-create sys.modules[name], then ADD any attrs it doesn't already
    have. Plain setdefault (as test_counts_adapter_log.py's twin does) is not
    enough here: sys.modules is process-global, module-scoped fixtures are
    not, and if that file's fixture runs first (alphabetically "counts_" <
    "policy_") its sensor_msgs.msg stub is already registered WITHOUT Imu —
    setdefault on the whole module would then silently skip adding it."""
    mod = sys.modules.get(name) or types.ModuleType(name)
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


@pytest.fixture(scope="module")
def policy_node_mod():
    _stub("rclpy", init=lambda *a, **k: None, spin=lambda *a, **k: None,
          shutdown=lambda *a, **k: None, ok=lambda: True)
    _stub("rclpy.node",
          Node=type("Node", (), {"__init__": lambda self, *a, **k: None}))
    _stub("rclpy.qos", QoSProfile=object, ReliabilityPolicy=object,
          DurabilityPolicy=object, QoSDurabilityPolicy=object,
          QoSReliabilityPolicy=object)
    _stub("geometry_msgs")
    _stub("geometry_msgs.msg", Twist=type("Twist", (), {}))
    _stub("sensor_msgs")
    _stub("sensor_msgs.msg",
          JointState=type("JointState", (), {}), Imu=type("Imu", (), {}))
    _stub("std_msgs")
    _stub("std_msgs.msg", String=type("String", (), {}),
          Bool=type("Bool", (), {}), Int32=type("Int32", (), {}),
          Float32MultiArray=type("Float32MultiArray", (), {}))
    _stub("diagnostic_msgs")
    _stub("diagnostic_msgs.msg",
          DiagnosticArray=type("DiagnosticArray", (), {}),
          DiagnosticStatus=type(
              "DiagnosticStatus", (), {"OK": 0, "WARN": 1, "ERROR": 2, "STALE": 3}))

    import nova_locomotion.policy_node as pn

    return pn


# ---- ramp math (pure) ---------------------------------------------------


def test_ramp_alpha_rises_linearly_to_one(policy_node_mod):
    pn = policy_node_mod
    assert pn.ramp_alpha(0, 4) == pytest.approx(0.25)
    assert pn.ramp_alpha(3, 4) == pytest.approx(1.0)
    assert pn.ramp_alpha(99, 4) == pytest.approx(1.0)  # held at 1 past the ramp


def test_ramp_alpha_zero_or_negative_ticks_is_full_authority_immediately(policy_node_mod):
    pn = policy_node_mod
    assert pn.ramp_alpha(0, 0) == 1.0
    assert pn.ramp_alpha(0, -5) == 1.0


def test_ramp_blend_interpolates_current_to_target(policy_node_mod):
    pn = policy_node_mod
    current = [0.0, 1.0, -1.0]
    target = [1.0, 1.0, 1.0]
    assert pn.ramp_blend(current, target, 0.0) == pytest.approx(current)
    assert pn.ramp_blend(current, target, 1.0) == pytest.approx(target)
    assert pn.ramp_blend(current, target, 0.5) == pytest.approx([0.5, 1.0, 0.0])


# ---- PolicyGate -----------------------------------------------------------


def _armed_gate(pn, now=100.0):
    """A gate with every OTHER precondition satisfied, for isolating one."""
    gate = pn.PolicyGate(preflight=pn.PreflightGate(require=True))
    gate.preflight.observe(True)
    gate.observe_calibration(True)
    gate.observe_imu(now)
    gate.observe_enable(True)
    return gate


def test_refuses_when_not_enabled(policy_node_mod):
    pn = policy_node_mod
    gate = _armed_gate(pn)
    gate.observe_enable(False)
    reason = gate.refusal(100.0)
    assert reason is not None and "disabled" in reason


def test_refuses_without_preflight_pass(policy_node_mod):
    pn = policy_node_mod
    gate = _armed_gate(pn)
    gate.preflight.observe(False)
    reason = gate.refusal(100.0)
    assert reason is not None and "preflight" in reason


def test_refuses_without_full_calibration(policy_node_mod):
    pn = policy_node_mod
    gate = _armed_gate(pn)
    gate.observe_calibration(False)
    reason = gate.refusal(100.0)
    assert reason is not None and "calibration" in reason


def test_refuses_without_ever_seeing_imu(policy_node_mod):
    pn = policy_node_mod
    gate = pn.PolicyGate(preflight=pn.PreflightGate(require=True))
    gate.preflight.observe(True)
    gate.observe_calibration(True)
    gate.observe_enable(True)
    # observe_imu() never called
    reason = gate.refusal(100.0)
    assert reason is not None and "#14" in reason


def test_refuses_on_stale_imu(policy_node_mod):
    pn = policy_node_mod
    gate = _armed_gate(pn, now=0.0)
    reason = gate.refusal(0.0 + pn.IMU_TIMEOUT_SEC + 0.01)
    assert reason is not None and "#14" in reason


def test_allows_when_every_precondition_met(policy_node_mod):
    pn = policy_node_mod
    gate = _armed_gate(pn, now=100.0)
    assert gate.refusal(100.0) is None


def test_preflight_gate_reuse_is_honored_not_reimplemented(policy_node_mod):
    """PolicyGate must consult the SAME PreflightGate instance/behaviour
    #285 built for gait_node, not a parallel copy -- flipping the shared
    object's verdict must flip PolicyGate's, with nothing else touched."""
    pn = policy_node_mod
    shared = pn.PreflightGate(require=True)
    gate = pn.PolicyGate(preflight=shared)
    gate.observe_calibration(True)
    gate.observe_imu(100.0)
    gate.observe_enable(True)

    assert gate.refusal(100.0) is not None  # shared.passed still False
    shared.observe(True)
    assert gate.refusal(100.0) is None  # flips through the same object
    shared.observe(False)
    assert gate.refusal(100.0) is not None


def test_require_preflight_false_bypasses_only_that_leg(policy_node_mod):
    pn = policy_node_mod
    gate = pn.PolicyGate(preflight=pn.PreflightGate(require=False))
    gate.observe_calibration(True)
    gate.observe_imu(100.0)
    gate.observe_enable(True)
    assert gate.refusal(100.0) is None  # never observed a PASS, still allowed
    gate.observe_calibration(False)
    assert gate.refusal(100.0) is not None  # the OTHER legs still gate
