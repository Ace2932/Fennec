"""Incident-bundle writer: copy current bag set + metadata when a
trigger fires (E-stop, safety FSM non-zero, /diagnostics ERROR,
manual freeze).

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


def _free_disk_mb(p: Path) -> int:
    try:
        st = shutil.disk_usage(p)
        return st.free // (1024 * 1024)
    except OSError:
        return -1


def _jetson_uptime_s() -> int:
    """Parse /proc/uptime first field as integer seconds. Returns -1 if unavailable."""
    try:
        with open('/proc/uptime') as f:
            return int(float(f.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return -1


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
        return '(dmesg unavailable; needs CAP_SYSLOG or sysctl kernel.dmesg_restrict=0)'


def _git_sha() -> str:
    """Read deployed-firmware SHA written by `make deploy` to
    ~/.nova/running-git-sha, fall back to git in $NOVA_REPO env, fall
    back to 'unknown'.
    """
    sha_file = Path.home() / '.nova' / 'running-git-sha'
    if sha_file.exists():
        try:
            return sha_file.read_text().strip()
        except OSError:
            pass
    repo = os.environ.get('NOVA_REPO')
    if repo:
        try:
            return subprocess.check_output(
                ['git', '-C', repo, 'rev-parse', 'HEAD'],
                stderr=subprocess.DEVNULL,
                timeout=2.0,
                text=True,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return 'unknown'


def _write_yaml(path: Path, data: dict) -> None:
    """Write data as YAML. Uses pyyaml if available; otherwise emits a
    safe-quoted fallback (good enough for the simple key/value/list
    payload we generate)."""
    try:
        import yaml  # type: ignore
        path.write_text(yaml.safe_dump(data, default_flow_style=False))
    except ImportError:
        # Fallback writer — handle our specific value types only.
        lines = []
        for k, v in data.items():
            if isinstance(v, bool):
                lines.append(f'{k}: {"true" if v else "false"}')
            elif isinstance(v, (int, float)):
                lines.append(f'{k}: {v}')
            elif isinstance(v, list):
                if not v:
                    lines.append(f'{k}: []')
                else:
                    lines.append(f'{k}:')
                    for item in v:
                        lines.append(f'  - {str(item)!r}')
            else:
                lines.append(f'{k}: {str(v)!r}')
        path.write_text('\n'.join(lines) + '\n')


def write_bundle(
    bag_root: Path,
    incident_root: Path = DEFAULT_INCIDENT_ROOT,
    trigger: str = 'manual',
    extra_metadata: Optional[dict] = None,
) -> Path:
    """Copy current bag set under bag_root to a new incident dir.

    Returns the incident directory path. The recorder should be stopped
    or paused before calling this (so the active bag is fully flushed);
    the dashcam node handles that orchestration.
    """
    # Capture free disk BEFORE we start copying (the metadata is meant to
    # reflect state at trigger time, not after the copy has eaten space).
    free_mb_at_trigger = _free_disk_mb(incident_root.parent if incident_root.parent.exists() else Path('/'))
    uptime_s = _jetson_uptime_s()
    git_sha = _git_sha()

    incident_root.mkdir(parents=True, exist_ok=True)
    out = incident_root / _now_iso()
    out.mkdir(parents=True, exist_ok=False)

    # Copy every bag directory currently under bag_root.
    bags_copied = []
    copy_error: Optional[str] = None
    if bag_root.exists():
        for entry in bag_root.iterdir():
            if entry.is_dir():
                try:
                    shutil.copytree(entry, out / 'bags' / entry.name)
                    bags_copied.append(entry.name)
                except OSError as e:
                    copy_error = f'{type(e).__name__}: {e}'
                    break

    meta = {
        'trigger': trigger,
        'timestamp': _now_iso(),
        'free_disk_mb_at_trigger': free_mb_at_trigger,
        'jetson_uptime_s': uptime_s,
        'git_sha': git_sha,
        'bags_copied': bags_copied,
    }
    if copy_error:
        meta['copy_error'] = copy_error
    if extra_metadata:
        meta.update(extra_metadata)

    _write_yaml(out / 'metadata.yaml', meta)

    # Recent kernel log tail
    try:
        (out / 'dmesg.tail').write_text(_dmesg_tail(50))
    except OSError:
        pass

    return out
