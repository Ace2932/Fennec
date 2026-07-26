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


def rad_to_raw(theta_rad: float, calib: JointHomeCalib) -> float:
    """URDF radians -> raw servo counts for ONE joint.

    THE single conversion. Issue #154: this formula lived only inside
    _raw_pair(), so the LIMITS path applied per-joint ``urdf_sign`` while the
    COMMAND path (node.py's unit shim) used one global scalar for all twelve.
    A joint whose servo is mounted inverted therefore got a correctly-signed
    limit window and a WRONG-SIGNED command — driving away from target into its
    stop, with the firmware backstop computed for the opposite sense.

    Both paths call this now. Callers must check ``is_calibrated`` first;
    an unknown sign has no defined conversion.
    """
    return calib.home_raw + calib.urdf_sign * theta_rad * RAW_PER_RAD


def raw_to_rad(raw: float, calib: JointHomeCalib) -> float:
    """Raw servo counts -> URDF radians. Inverse of rad_to_raw.

    Needed on the way BACK: node.py seeds ``current_pose`` from /joint_states
    and feeds it to positions_to_pose(), which expects radians. Without this
    the E-stop recovery path (stand_up(start_pose=...)) starts from a garbage
    pose.
    """
    return (raw - calib.home_raw) / (calib.urdf_sign * RAW_PER_RAD)


def is_calibrated(calib: Optional[JointHomeCalib]) -> bool:
    return calib is not None and calib.urdf_sign in (1, -1)


def convert_positions(
    positions: List[float],
    calib: Dict[int, JointHomeCalib],
    to_raw: bool,
) -> Optional[List[float]]:
    """Convert a bus-ordered 12-vec, or None if the conversion is not defined.

    ALL OR NOTHING, deliberately. The firmware reads the whole array in ONE
    unit, so converting the joints that happen to be calibrated and passing the
    rest through would emit a message that is part counts and part radians —
    far worse than not converting. None means "leave it alone" (the
    WIRE-AT-CALIBRATION identity behaviour).
    """
    fn = rad_to_raw if to_raw else raw_to_rad
    out: List[float] = []
    for idx, value in enumerate(positions[:N_JOINTS]):
        c = calib.get(idx + 1)
        if not is_calibrated(c):
            return None
        out.append(fn(value, c))
    return out if len(out) == N_JOINTS else None


def build_calib(home, sign):
    """Bus ID -> JointHomeCalib. Unknown sign (0) = omitted = uncalibrated.

    Pure, so it is testable without rclpy (same reason hard_stop.py is
    ROS-free). FAILS LOUD on an inconsistent calibration rather than filling a
    default: a joint given a sign but no ``home_raw`` used to silently take
    home_raw=0.0 instead of ~2048 — a 2048-count, 180-degree error. The
    firmware backstop is built from this SAME calibration, so the window moves
    with the error and cannot catch it. That is exactly the #154 shape: a
    wrong command with a limit that agrees with it. 0.0 is also inside the
    legal raw range, so nothing downstream would have rejected it.

    Raising stops the node: a broken calibration must not become motion. Note
    what this does NOT do — silently dropping the joint would leave the calib
    partial, so convert_positions() would return None and pass RADIANS to a
    firmware reading raw counts, which is worse again.
    """
    out = {}
    for i in range(N_JOINTS):
        jid = i + 1
        s = int(sign[i]) if i < len(sign) else 0
        if s == 0:
            continue  # unknown sign -> uncalibrated, the pre-hardware state
        if s not in (1, -1):
            raise ValueError(
                f"joint {jid}: urdf_sign must be +1, -1 or 0 (unknown), got {s}"
            )
        if i >= len(home):
            raise ValueError(
                f"joint {jid}: urdf_sign={s:+d} given but home_raw has only "
                f"{len(home)} entries. Refusing to default home_raw — it would be "
                f"a ~2048-count (180 deg) error that the firmware window, built "
                f"from this same calibration, could not catch."
            )
        hr = float(home[i])
        if not 0.0 <= hr <= 4095.0:
            raise ValueError(
                f"joint {jid}: home_raw={hr} outside the STS3215 range 0..4095"
            )
        out[jid] = JointHomeCalib(home_raw=hr, urdf_sign=s)
    return out


def _raw_pair(lower_rad: float, upper_rad: float, calib: JointHomeCalib) -> tuple:
    if not is_calibrated(calib):
        return (RAW_MIN, RAW_MAX)
    a = rad_to_raw(lower_rad, calib)
    b = rad_to_raw(upper_rad, calib)
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
