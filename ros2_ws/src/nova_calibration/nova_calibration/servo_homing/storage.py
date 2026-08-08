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
      1: {name: FL_coxa, home_raw: 1421, stop_pos_raw: 1933, peak_load: 240,
          urdf_sign: -1}
      ...
    haa_confirmations:
      1: {sign: 1, observed_utc: "2026-08-06T18:00:00", method: "...",
          assembly: "leg_v6 rev2 / FL / servo 1"}
      ...

``haa_confirmations`` (#194) is a SEPARATE thing from ``joints``: it records
the observed HAA_INBOARD_SIGN direction (nova_ops.safety_envelope.limits),
not a home_raw/urdf_sign pair — haa stays out of the hard-stop routine itself
(config.py's PLACEHOLDER_REASON) until this confirmation exists. It lives in
the SAME artifact rather than a second file so there is one calibration
record per robot, not two that can silently drift apart.
"""
import os
from datetime import datetime

import yaml

CALIB_DIR = os.path.expanduser('~/.nova/calibration')
LATEST = 'servo_offsets_latest.yaml'


def ensure_dir() -> str:
    os.makedirs(CALIB_DIR, mode=0o770, exist_ok=True)
    return CALIB_DIR


def _write_and_link(doc: dict) -> str:
    """Write `doc` as a datestamped YAML file and refresh the LATEST symlink.

    Shared by save_offsets() and save_haa_confirmations() — one write path,
    so the "datestamp + atomic-ish symlink swap" behaviour cannot drift
    between the two things that persist into this artifact.
    """
    ensure_dir()
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


def save_offsets(results, note='hard-stop home auto-detect') -> str:
    """results: iterable of hard_stop.HardStopResult with outcome OK.

    Returns the path written. Also refreshes the servo_offsets_latest.yaml
    link. Preserves any haa_confirmations already on record — a new homing
    sweep (which never touches haa, see config.PLACEHOLDER_REASON) must not
    wipe out a previously-recorded haa confirmation.
    """
    joints = {
        r.joint_id: {
            'name': getattr(r, 'name', ''),
            'home_raw': r.home_raw,
            'stop_pos_raw': r.stop_pos_raw,
            'peak_load': r.peak_load,
            # The COMMAND path consumes this (nova_locomotion node.py's
            # urdf_sign param). Persisting home_raw alone left that param with
            # no producer at all, so the per-joint sign could never activate.
            'urdf_sign': getattr(r, 'urdf_sign', 0),
        }
        for r in results
    }
    doc = load_latest() or {}
    doc['schema'] = 1
    doc['created'] = datetime.now().isoformat(timespec='seconds')
    doc['note'] = note
    doc['joints'] = joints
    return _write_and_link(doc)


def save_haa_confirmation(joint_id: int, confirmation, note='haa sign confirmation') -> str:
    """Merge one HaaSignConfirmation (nova_ops.safety_envelope.limits) into
    the calibration artifact's haa_confirmations block.

    Loads whatever is already on disk (preserving `joints` and any OTHER
    joint's haa_confirmations entry) and rewrites — same merge discipline
    save_offsets() uses in the other direction.
    """
    doc = load_latest() or {}
    doc['schema'] = 1
    doc['created'] = datetime.now().isoformat(timespec='seconds')
    doc['note'] = note
    doc.setdefault('joints', {})
    haa = doc.get('haa_confirmations') or {}
    haa[joint_id] = {
        'sign': confirmation.sign,
        'observed_utc': confirmation.observed_utc,
        'method': confirmation.method,
        'assembly': confirmation.assembly,
    }
    doc['haa_confirmations'] = haa
    return _write_and_link(doc)


def load_latest() -> dict:
    """Return the latest offsets doc, or {} if none calibrated yet."""
    link = os.path.join(CALIB_DIR, LATEST)
    if not os.path.exists(link):
        return {}
    with open(link) as f:
        return yaml.safe_load(f) or {}
