"""Compute + publish the firmware per-joint raw position-limit table.

Defense-in-depth (firmware-limits lane, 2026-07-06): the Teensy clamps
every goal to a per-joint raw table (`joint_limits` topic,
Float32MultiArray, 24 floats = min,max raw per bus ID 1..12). The table
boots wide open (0..4095); this module narrows it once homing
calibration provides, per joint:

  * ``home_raw``  — raw count at URDF zero (servo_homing storage)
  * ``urdf_sign`` — +1 if increasing raw counts = increasing URDF angle,
    -1 otherwise. NOT the homing ``search_dir`` (that encodes "safe stop
    direction"). Observed at calibration; unknown = None.

raw(theta) = home_raw + urdf_sign * theta * RAW_PER_RAD

Joints with no calibration entry or unknown sign stay WIDE OPEN in the
firmware table (the Jetson-side wrapper still clamps them) — publishing
a guessed narrow window in the wrong direction would pin the joint
against real ROM, which is worse than no firmware clamp.

Publish (host side, after homing, latched/transient-local QoS so a
rebooting Teensy re-receives):

    msg = Float32MultiArray()
    msg.data = build_joint_limits_data(limits, calib)
    pub.publish(msg)

Firmware rejects the whole message unless every pair is sane
(0 <= min < max <= 4095) — build_joint_limits_data guarantees that by
construction (wide-open fallback + clamping to [0, 4095]).
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from .limits import JointLimits

RAW_PER_RAD = 4096.0 / (2.0 * math.pi)
RAW_MIN = 0.0
RAW_MAX = 4095.0
N_JOINTS = 12


@dataclass
class JointHomeCalib:
    """One joint's calibration, as needed for the firmware table."""

    home_raw: float  # raw counts at URDF zero
    urdf_sign: Optional[int]  # +1 / -1 / None (unknown -> wide open)


def _raw_pair(lower_rad: float, upper_rad: float, calib: JointHomeCalib) -> tuple:
    if calib.urdf_sign not in (1, -1):
        return (RAW_MIN, RAW_MAX)
    a = calib.home_raw + calib.urdf_sign * lower_rad * RAW_PER_RAD
    b = calib.home_raw + calib.urdf_sign * upper_rad * RAW_PER_RAD
    lo, hi = (a, b) if a < b else (b, a)
    lo = max(RAW_MIN, min(lo, RAW_MAX))
    hi = max(RAW_MIN, min(hi, RAW_MAX))
    if not lo < hi:
        # degenerate after clamping (home near an end stop + range fully
        # outside 0..4095) — leave wide open rather than pin the joint
        return (RAW_MIN, RAW_MAX)
    return (lo, hi)


def build_joint_limits_data(
    limits: JointLimits,
    calib: Dict[int, JointHomeCalib],
) -> List[float]:
    """24 floats (min,max per bus ID 1..12) for the `joint_limits` topic.

    Uses the HARD limits (lower/upper), not the soft margins — the
    wrapper already enforces soft bounds; the firmware table is the
    backstop behind it.
    """
    data: List[float] = []
    for joint_id in range(1, N_JOINTS + 1):
        lim = limits.get(joint_id)
        c = calib.get(joint_id)
        if lim is None or c is None:
            data.extend((RAW_MIN, RAW_MAX))
            continue
        data.extend(_raw_pair(lim.lower, lim.upper, c))
    return data
