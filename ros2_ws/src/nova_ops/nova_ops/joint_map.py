"""Canonical joint-ID map loader (system-audit "joint-ID map", 2026-07-06).

`nova_description/config/joint_id_map.yaml` is the single source of
truth tying Feetech bus IDs (1-12) to URDF joint names, but until now
NOTHING loaded it — limits.py, servo_homing/config.py, the URDF, and
the firmware docs all restate the convention by hand and could drift
silently. This module loads the YAML and test_joint_map.py locks every
consumer to it.

Resolution order for the YAML:
  1. explicit ``path=`` argument
  2. ament package share (installed workspace on the Jetson)
  3. repo-relative walk-up from this file (dev checkouts / CI / mac)
"""

import os
from typing import Dict, Optional

import yaml

LEGS = ("FL", "FR", "RL", "RR")
JOINTS = ("haa", "hfe", "kfe")  # mechanical chain order within a leg


def _repo_relative_path() -> Optional[str]:
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        cand = os.path.join(
            d, "ros2_ws", "src", "nova_description", "config", "joint_id_map.yaml"
        )
        if os.path.exists(cand):
            return cand
        # also handle being inside ros2_ws already
        cand2 = os.path.join(
            d, "src", "nova_description", "config", "joint_id_map.yaml"
        )
        if os.path.exists(cand2):
            return cand2
        cand3 = os.path.join(d, "nova_description", "config", "joint_id_map.yaml")
        if os.path.exists(cand3):
            return cand3
        d = os.path.dirname(d)
    return None


def _ament_path() -> Optional[str]:
    try:
        from ament_index_python.packages import get_package_share_directory

        share = get_package_share_directory("nova_description")
        cand = os.path.join(share, "config", "joint_id_map.yaml")
        return cand if os.path.exists(cand) else None
    except Exception:
        return None


def load_joint_id_map(path: Optional[str] = None) -> Dict[str, int]:
    """Return {joint_name: bus_id} from the canonical YAML. Raises
    FileNotFoundError when the file cannot be located, ValueError when
    the content is malformed (missing key, non-int IDs, duplicates)."""
    p = path or _ament_path() or _repo_relative_path()
    if p is None or not os.path.exists(p):
        raise FileNotFoundError(
            "joint_id_map.yaml not found (tried ament share + repo walk)"
        )
    with open(p) as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or "joint_id_map" not in doc:
        raise ValueError(f"{p}: missing top-level 'joint_id_map' key")
    m = doc["joint_id_map"]
    if not isinstance(m, dict) or not m:
        raise ValueError(f"{p}: 'joint_id_map' must be a non-empty mapping")
    out: Dict[str, int] = {}
    seen_ids = set()
    for name, jid in m.items():
        if not isinstance(jid, int):
            raise ValueError(f"{p}: id for {name!r} not an int: {jid!r}")
        if jid in seen_ids:
            raise ValueError(f"{p}: duplicate bus id {jid}")
        seen_ids.add(jid)
        out[str(name)] = jid
    return out


def id_to_name(mapping: Dict[str, int]) -> Dict[int, str]:
    return {v: k for k, v in mapping.items()}


def expected_name(bus_id: int) -> str:
    """The PER-LEG-SEQUENTIAL convention, computed: leg = (id-1)//3 in
    FL,FR,RL,RR order; joint = (id-1)%3 in haa,hfe,kfe order."""
    if not 1 <= bus_id <= 12:
        raise ValueError(f"leg bus ids are 1..12, got {bus_id}")
    return f"{LEGS[(bus_id - 1) // 3]}_{JOINTS[(bus_id - 1) % 3]}"
