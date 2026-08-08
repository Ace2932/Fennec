"""Smoke tests for the preflight check registry.

Import-only — these don't spin up ROS 2, because the checks need real topic
traffic from the Teensy bridge to succeed. They assert the *registry* is
coherent, which is the part that rots silently when a check is added.

HISTORY, because it explains the shape of these tests. Until 2026-07-30 this
file ran NOWHERE: CI passed `--ignore=test/test_preflight.py` (no rclpy in the
runner) and CLAUDE.md told you to skip it locally for the same reason. So when
#187 added FirmwareTablesCheck, `test_v1_checks_have_expected_count` started
failing against a hardcoded 3 and nothing said so. The import barrier is gone
now — the checks defer their ROS imports into run() — so these run everywhere.
"""

from nova_ops.preflight.checks import V1_CHECKS, CheckStatus
from nova_ops.preflight.checks.base import CheckResult

#: The registry contract, in order. Adding a check SHOULD fail this test — that
#: is the point. Update it deliberately, and say in the commit why the new check
#: is (or is not) critical.
EXPECTED = ["bus_ping", "estop", "battery_latch", "firmware_tables", "posture_gate"]


def test_registry_matches_the_expected_check_set():
    assert [c.name() for c in V1_CHECKS] == EXPECTED


def test_check_names_are_unique():
    names = [c.name() for c in V1_CHECKS]
    assert len(set(names)) == len(names)


def test_every_check_is_critical():
    # Non-critical means bringup proceeds despite the failure. Every check in
    # the set is a reason NOT to power a 12-servo robot, so a downgrade here is
    # a safety change and has to be visible in a diff.
    for c in V1_CHECKS:
        assert c.critical is True, (
            f"{c.name()} is non-critical — bringup would continue after it "
            f"fails. If that is intended, change it here too and justify it."
        )


def test_firmware_tables_check_is_present_and_critical():
    # #187 specifically: the Teensy boots with BOTH protection tables wide open
    # and only the host can narrow them. Without this check passing-and-critical,
    # preflight green-lights a robot with no firmware-side protection at all.
    # This is the assertion that was not running when it was added.
    fw = [c for c in V1_CHECKS if c.name() == "firmware_tables"]
    assert len(fw) == 1, "firmware_tables check missing from V1_CHECKS (#187)"
    assert fw[0].critical is True


def test_check_result_defaults_to_critical():
    r = CheckResult(name="x", status=CheckStatus.OK, message="ok")
    assert r.critical is True
    assert r.status == CheckStatus.OK


def test_status_enum_values_match_diagnostic_levels():
    # Aligned with diagnostic_msgs/DiagnosticStatus:
    #   OK=0, WARN=1, ERROR=2, STALE=3
    assert CheckStatus.OK == 0
    assert CheckStatus.WARN == 1
    assert CheckStatus.FAIL == 2
    assert CheckStatus.STALE == 3


def test_registry_imports_without_a_ros_runtime():
    # The regression guard for the fix that made this file runnable. If someone
    # moves `import rclpy` back to module scope in any check, importing the
    # registry starts requiring a ROS install and this file silently drops out
    # of CI again — exactly how the #187 gap survived.
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['rclpy'] = None; "
            "import nova_ops.preflight.checks as c; print(len(c.V1_CHECKS))",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (
        f"importing the check registry now needs a ROS runtime again:\n{r.stderr}"
    )
