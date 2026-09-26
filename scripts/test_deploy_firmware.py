"""Tests for scripts/deploy-firmware.sh (#440): the flash guard must
actually see `gait_node`/`policy_node` running, and `verify` must catch a
SHA mismatch instead of just checking the topic answered.

Run: .venv/bin/python -m pytest scripts/test_deploy_firmware.py -q

Both checks are exercised by sourcing the script (guarded at the bottom so
sourcing doesn't also run cmd_deploy/cmd_verify) and calling the factored-out
functions directly, with `remote()` overridden to skip the ssh round trip.
"""
import os
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "deploy-firmware.sh")


def _run(bash_body):
    result = subprocess.run(
        ["bash", "-c", bash_body],
        cwd=_HERE,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# gait_guard_check() — must detect a running gait_node/policy_node.
#
# `remote` is overridden (after sourcing) to run the pgrep locally instead
# of over ssh. A real short-lived process named `gait_node` is put on PATH
# so this exercises real pgrep matching, not a hand-rolled stand-in.
# ---------------------------------------------------------------------------

_GUARD_HARNESS = '''
set -euo pipefail
TMPBIN=$(mktemp -d)
trap 'kill "$GAIT_PID" 2>/dev/null; rm -rf "$TMPBIN"' EXIT
printf '#!/bin/sh\\nsleep 30\\n' > "$TMPBIN/{procname}"
chmod +x "$TMPBIN/{procname}"
"$TMPBIN/{procname}" >/dev/null 2>&1 &
GAIT_PID=$!
sleep 0.3

source "{script}"
remote() {{ eval "$1"; }}

set +e
gait_guard_check
echo "RC=$?"
'''


def test_gait_guard_detects_running_gait_node():
    """The bug in #440: pgrep -x gait_controller never matches anything,
    because the real entry point is gait_node. This must fail (rc=5 path
    upstream) once gait_node is actually running."""
    rc, out, err = _run(_GUARD_HARNESS.format(script=_SCRIPT, procname="gait_node"))
    assert rc == 0, err
    assert "RC=0" in out, f"gait_guard_check did not detect gait_node running: {out}\n{err}"


def test_gait_guard_detects_running_policy_node():
    rc, out, err = _run(_GUARD_HARNESS.format(script=_SCRIPT, procname="policy_node"))
    assert rc == 0, err
    assert "RC=0" in out, f"gait_guard_check did not detect policy_node running: {out}\n{err}"


def test_gait_guard_old_pgrep_pattern_missed_gait_node():
    """Pins down the actual bug: the literal old pattern (`pgrep -x
    gait_controller`) does NOT see a running gait_node. Proves the guard
    was dead, independent of the fix above."""
    harness = '''
set -euo pipefail
TMPBIN=$(mktemp -d)
trap 'kill "$GAIT_PID" 2>/dev/null; rm -rf "$TMPBIN"' EXIT
printf '#!/bin/sh\\nsleep 30\\n' > "$TMPBIN/gait_node"
chmod +x "$TMPBIN/gait_node"
"$TMPBIN/gait_node" >/dev/null 2>&1 &
GAIT_PID=$!
sleep 0.3

remote() { eval "$1"; }
set +e
remote "pgrep -x gait_controller" >/dev/null 2>&1
echo "RC=$?"
'''
    rc, out, err = _run(harness)
    assert rc == 0, err
    assert "RC=1" in out, f"expected the old pattern to miss gait_node (rc=1); got: {out}\n{err}"


# ---------------------------------------------------------------------------
# check_firmware_sha() — must flag a mismatch between the running firmware's
# embedded SHA and this checkout's HEAD, and pass when they agree.
# ---------------------------------------------------------------------------

def test_check_firmware_sha_matches_head():
    harness = f'''
set -euo pipefail
cd "{_HERE}"
source "{_SCRIPT}"
LOCAL_SHA=$(git rev-parse --short HEAD)
set +e
check_firmware_sha "data: nova-teensy ${{LOCAL_SHA}} loop=200Hz"
echo "RC=$?"
'''
    rc, out, err = _run(harness)
    assert rc == 0, err
    assert "RC=0" in out, f"expected a matching SHA to pass: {out}\n{err}"


def test_check_firmware_sha_flags_mismatch():
    harness = f'''
set -euo pipefail
cd "{_HERE}"
source "{_SCRIPT}"
set +e
check_firmware_sha "data: nova-teensy deadbee loop=200Hz"
echo "RC=$?"
'''
    rc, out, err = _run(harness)
    assert rc == 0, err
    assert "RC=1" in out, f"expected a SHA mismatch to fail: {out}\n{err}"
    assert "mismatch" in err, err
