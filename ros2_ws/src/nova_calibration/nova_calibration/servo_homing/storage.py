"""Persist + load servo home offsets.

Results land in ~/.nova/calibration/ as datestamped YAML plus a stable
`servo_offsets_latest.yaml` symlink the gait layer reads on start. Per the
auto-cal notes the directory must exist with group-rw so a future system
service can share it; bringup is expected to create ~/.nova/ — here we just
mkdir -p as a fallback.

YAML schema (v1):

    schema: 1
    created: "2026-06-06T16:30:00"
    note: "hard-stop home auto-detect"
    joints:
      1: {name: FL_coxa, home_raw: 1421, stop_pos_raw: 1933, peak_load: 240}
      ...
"""
import os
from datetime import datetime

import yaml

CALIB_DIR = os.path.expanduser('~/.nova/calibration')
LATEST = 'servo_offsets_latest.yaml'


def ensure_dir() -> str:
    os.makedirs(CALIB_DIR, mode=0o770, exist_ok=True)
    return CALIB_DIR


def save_offsets(results, note='hard-stop home auto-detect') -> str:
    """results: iterable of hard_stop.HardStopResult with outcome OK.

    Returns the path written. Also refreshes the servo_offsets_latest.yaml link.
    """
    ensure_dir()
    joints = {
        r.joint_id: {
            'name': getattr(r, 'name', ''),
            'home_raw': r.home_raw,
            'stop_pos_raw': r.stop_pos_raw,
            'peak_load': r.peak_load,
        }
        for r in results
    }
    doc = {
        'schema': 1,
        'created': datetime.now().isoformat(timespec='seconds'),
        'note': note,
        'joints': joints,
    }

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = os.path.join(CALIB_DIR, f'servo_offsets_{stamp}.yaml')
    with open(path, 'w') as f:
        yaml.safe_dump(doc, f, sort_keys=True, default_flow_style=False)

    # Refresh the stable pointer (atomic-ish: write temp link then rename).
    link = os.path.join(CALIB_DIR, LATEST)
    tmp = link + '.tmp'
    if os.path.islink(tmp) or os.path.exists(tmp):
        os.remove(tmp)
    os.symlink(os.path.basename(path), tmp)
    os.replace(tmp, link)
    return path


def load_latest() -> dict:
    """Return the latest offsets doc, or {} if none calibrated yet."""
    link = os.path.join(CALIB_DIR, LATEST)
    if not os.path.exists(link):
        return {}
    with open(link) as f:
        return yaml.safe_load(f) or {}
