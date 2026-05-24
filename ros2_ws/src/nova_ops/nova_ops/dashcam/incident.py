"""Incident-bundle writer: copy current bag set + metadata when a
trigger fires (E-stop, safety FSM non-zero, manual freeze).

Per docs/notes-qol-features.md §2:

    On E-stop engage, safety_state going non-zero, or any diagnostic
    going to ERROR: stop rotation (so the buffer at fault time is
    preserved) and copy the current bag set into
    /var/log/nova/incidents/<iso-timestamp>/.

Includes a metadata.yaml with: free disk at trigger, Jetson uptime,
recent kernel log tail, git SHA of running code.
"""
import datetime
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


# Where incident bundles land. /var/log requires root for first mkdir;
# the dashcam node mkdirs at startup with the user's permissions if it
# can't reach /var/log. Override via env NOVA_INCIDENT_DIR for testing.
DEFAULT_INCIDENT_ROOT = Path(os.environ.get(
    'NOVA_INCIDENT_DIR', '/var/log/nova/incidents'))


def _now_iso() -> str:
    return datetime.datetime.now().strftime('%Y%m%dT%H%M%S')


def _free_disk_bytes(p: Path) -> int:
    st = shutil.disk_usage(p)
    return st.free


def _jetson_uptime() -> str:
    try:
        with open('/proc/uptime') as f:
            return f.read().split()[0]
    except OSError:
        return 'unknown'


def _dmesg_tail(n: int = 50) -> str:
    try:
        out = subprocess.check_output(
            ['dmesg', '--ctime'],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            text=True,
        )
        lines = out.strip().split('\n')[-n:]
        return '\n'.join(lines)
    except (OSError, subprocess.SubprocessError):
        return '(dmesg unavailable; needs CAP_SYSLOG)'


def _git_sha(repo: Path = Path.home() / 'code' / 'LE_NOVA') -> str:
    try:
        return subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            text=True,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return 'unknown'


def write_bundle(
    bag_root: Path,
    incident_root: Path = DEFAULT_INCIDENT_ROOT,
    trigger: str = 'manual',
    extra_metadata: Optional[dict] = None,
) -> Path:
    """Copy current bag set under bag_root to a new incident dir.

    Returns the incident directory path. The recorder should be stopped
    before calling this (so the active bag is fully flushed); the
    dashcam node handles that orchestration.
    """
    incident_root.mkdir(parents=True, exist_ok=True)
    out = incident_root / _now_iso()
    out.mkdir(parents=True, exist_ok=False)

    # Copy every bag directory currently under bag_root.
    bags_copied = []
    if bag_root.exists():
        for entry in bag_root.iterdir():
            if entry.is_dir():
                dest = out / 'bags' / entry.name
                shutil.copytree(entry, dest)
                bags_copied.append(entry.name)

    # Write metadata
    meta = {
        'trigger': trigger,
        'timestamp': _now_iso(),
        'free_disk_mb': _free_disk_bytes(out) // (1024 * 1024),
        'jetson_uptime_s': _jetson_uptime(),
        'git_sha': _git_sha(),
        'bags_copied': bags_copied,
    }
    if extra_metadata:
        meta.update(extra_metadata)

    meta_path = out / 'metadata.yaml'
    with open(meta_path, 'w') as f:
        for k, v in meta.items():
            f.write(f'{k}: {v!r}\n')

    # Recent kernel log tail
    dmesg_path = out / 'dmesg.tail'
    dmesg_path.write_text(_dmesg_tail(50))

    return out
