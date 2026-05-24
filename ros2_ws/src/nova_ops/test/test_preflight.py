"""Minimal smoke tests for the preflight check classes.

These tests are import-only — they don't spin up ROS 2 because the checks
need real topic traffic from the Teensy bridge to succeed. The check
classes themselves are easy to mock around when needed.
"""
from nova_ops.preflight.checks import V1_CHECKS, Check, CheckStatus
from nova_ops.preflight.checks.base import CheckResult


def test_v1_checks_have_expected_count():
    # v1 = bus_ping + estop + battery_latch (mandatory critical 3)
    assert len(V1_CHECKS) == 3


def test_check_names_are_unique_and_match():
    names = [c.name() for c in V1_CHECKS]
    assert names == ['bus_ping', 'estop', 'battery_latch']
    assert len(set(names)) == len(names)


def test_all_v1_checks_are_critical_by_default():
    for c in V1_CHECKS:
        assert c.critical is True, (
            f'{c.name()} is non-critical; v1 spec says all 3 are critical')


def test_check_result_dataclass():
    r = CheckResult(name='x', status=CheckStatus.OK, message='ok')
    assert r.critical is True
    assert r.status == CheckStatus.OK


def test_status_enum_values_match_diagnostic_levels():
    # Aligned with diagnostic_msgs/DiagnosticStatus:
    #   OK=0, WARN=1, ERROR=2, STALE=3
    assert CheckStatus.OK == 0
    assert CheckStatus.WARN == 1
    assert CheckStatus.FAIL == 2
    assert CheckStatus.STALE == 3
