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


#: floats per envelope bucket: haa_raw_lo, haa_raw_hi, hfe_raw_lo, hfe_raw_hi
HFE_ENV_STRIDE = 4

#: bus IDs per leg, in the order the payload is emitted (FL, FR, RL, RR)
_ENV_LEGS = (("FL", 1, 2), ("FR", 4, 5), ("RL", 7, 8), ("RR", 10, 11))


def build_hfe_envelope_data(calib: Dict[int, JointHomeCalib]) -> List[float]:
    """Posture-aware hfe backstop for the firmware, in RAW COUNTS (#142).

    WHY THIS EXISTS. Loosening hfe to the mechanical +-86 moved the chassis
    constraint entirely into the host (`wrapper._clamp_posture`), because the
    constraint is posture-dependent and a per-joint scalar cannot express it.
    That left the riser skirt and the belly pack protected by exactly one code
    path. The Teensy's own table could not help: it is per joint, and the fold a
    leg may safely take depends on where that leg's HIP is.

    WHY NOT JUST A TIGHTER SCALAR. Because a scalar is permissive precisely
    where the hazard is. Measured from the chassis gate, front leg:

        haa +40 -> fold cap 47.2 deg      haa   0 -> 67.9
        haa -15 -> fold cap 13.8 deg      haa -20 ->  9.7      haa -30 -> 0.5

    Inboard haa tucks the leg under the belly where the LiPo sits, and the fold
    cap collapses. The +50 scalar this replaces would happily pass a +50 fold at
    haa -15, where the real cap is +13.8. A scalar that DID cover the legal haa
    range would have to be +13.8, which deletes the gait (the trot peaks at
    +59.4). So the backstop has to see posture, and this is the smallest thing
    that does.

    THE FIRMWARE STAYS DUMB. Everything is converted to raw counts HERE, by the
    same `rad_to_raw` the limits table already uses. The Teensy does integer
    comparisons on values it already has (`latched_cmd_position` holds all 12
    targets in one pass), and needs no calibration, no trig, and no chassis
    model. It also means this cannot disagree with the host about what a raw
    count means -- there is one conversion, in one place.

    CONSERVATIVE OVER kfe, EXACT OVER haa. The real envelope is 2-D in
    (haa, kfe); this collapses the kfe axis by taking the tightest window over
    every kfe in the table. So the firmware window is never LOOSER than the host
    gate at any posture (the safety property, and there is a test for it over
    both mounting signs), at the cost of being up to ~1.6 deg tighter at haa 0.
    The trot fits with room; a 2-D table would cost message size and firmware
    complexity to buy back degrees nothing uses.

    Returns ``[]`` unless every haa and hfe joint is calibrated -- a partial
    table would clamp some legs against a window built from a guessed home,
    which is the #154 shape: a wrong command with a limit that agrees with it.
    """
    from ..rom_envelope import hfe_bounds
    from ..rom_envelope_table import HAAS, KFES

    needed = [jid for _, haa_id, hfe_id in _ENV_LEGS for jid in (haa_id, hfe_id)]
    if not all(is_calibrated(calib.get(jid)) for jid in needed):
        return []

    n_buckets = len(HAAS) - 1
    out: List[float] = [float(n_buckets)]
    for leg, haa_id, hfe_id in _ENV_LEGS:
        haa_c, hfe_c = calib[haa_id], calib[hfe_id]
        rows = []
        for i in range(n_buckets):
            span = (HAAS[i], HAAS[i + 1])
            # tightest window over BOTH ends of the haa span and every kfe --
            # the firmware interpolates nothing, so the bucket must be valid
            # everywhere inside it.
            lo, hi = -1e9, 1e9
            for haa_deg in span:
                for kfe_deg in KFES:
                    g_lo, g_hi = hfe_bounds(
                        leg, math.radians(haa_deg), math.radians(kfe_deg)
                    )
                    lo, hi = max(lo, g_lo), min(hi, g_hi)
            if lo > hi:  # fully blocked posture band -- pin the joint
                lo = hi = 0.5 * (lo + hi)
            a, b = rad_to_raw(lo, hfe_c), rad_to_raw(hi, hfe_c)
            hfe_lo, hfe_hi = (a, b) if a <= b else (b, a)
            ra, rb = (rad_to_raw(math.radians(d), haa_c) for d in span)
            haa_lo, haa_hi = (ra, rb) if ra <= rb else (rb, ra)
            rows.append([haa_lo, haa_hi, _clip(hfe_lo), _clip(hfe_hi)])

        rows.sort(key=lambda r: r[0])
        # extend the outer buckets to the full raw range: outside the swept haa
        # grid the host clamps to the edge cell, so the firmware must too, and a
        # gap would be a haa the firmware cannot classify at all.
        rows[0][0] = RAW_MIN
        rows[-1][1] = RAW_MAX
        for prev, nxt in zip(rows, rows[1:]):  # close float seams exactly
            nxt[0] = prev[1]
        for r in rows:
            out.extend(r)
    return out


def _clip(v: float) -> float:
    return max(RAW_MIN, min(v, RAW_MAX))


def build_firmware_tables(calib: Dict[int, JointHomeCalib]):
    """The firmware tables to publish. Returns ``(limits, envelope, limp_pose,
    state)``.

    Any of the first three may be ``None``, meaning "do not publish this
    one", and each follows a DIFFERENT rule because each table fails
    differently.

    ``limits`` — published whenever ANY joint is calibrated. The per-joint table
    is per-joint independent: ``build_joint_limits_data`` gives every calibrated
    joint its real narrow window and leaves only the uncalibrated ones wide open
    (0..4095), which is what the firmware already boots with. Withholding it
    during a partial calibration would therefore strip real protection off the
    joints that ARE homed in order to avoid an ambiguous status — a bad trade,
    and the reverse of the safe default.

    ``envelope`` — all-or-nothing, enforced by build_hfe_envelope_data itself.
    This one is posture-COUPLED: a leg's fold window is selected by that leg's
    haa, so a leg missing either joint cannot be bounded at all, and a table
    built around a guessed home would clamp against the wrong hip.

    ``limp_pose`` (#145) — all-or-nothing, enforced by build_limp_pose_data
    itself. Needs every leg's haa CONFIRMED (not just calibrated) as well,
    since the pose needs the same 40 deg outboard splay
    nova_locomotion.choreo.stand.pose_for('down') gates on. The firmware's
    fallback for "no valid table has ever arrived" is the pre-#145 instant
    torque release, which is the honest pre-homing/pre-confirmation state —
    the same "withhold rather than guess" doctrine as envelope.

    THE CATCH THIS LEAVES, and why the state is returned rather than implied:
    publishing a partial ``limits`` table increments the firmware's receive
    counter exactly like a complete one, so "the firmware accepted a table" does
    NOT mean "every joint is protected". The caller must surface `state` and
    `missing` alongside, or a partially-armed robot reads as armed. See #187.
    """
    state, missing = calibration_state(calib)
    if state == "uncalibrated":
        return None, None, None, state
    from .limits import load_default_limits

    limits = build_joint_limits_data(load_default_limits(), calib)
    envelope = build_hfe_envelope_data(calib) or None
    from .limp_pose import build_limp_pose_data

    limp_pose = build_limp_pose_data(calib)
    return limits, envelope, limp_pose, state


def calibration_state(calib: Dict[int, JointHomeCalib]):
    """Classify a calibration: ``(state, missing_ids)``. See #159.

    ``convert_positions`` is all-or-nothing, so it answers one question — does
    the conversion apply. It cannot distinguish the two ways of getting "no":

      * ``uncalibrated`` — NOTHING is homed. The pre-hardware state, expected,
        nothing is listening.
      * ``partial``      — SOME joints are homed. Identical behaviour, and it
        is the bring-up state: radians go to a firmware reading raw counts,
        so 0.6 rad becomes 0.6 counts and every servo drives toward a stop.
      * ``active``       — all twelve convert.

    Same behaviour, different consequence, and no caller could tell them apart.
    ``is_calibrated`` is the authority for "homed" (a present entry with an
    unknown sign has no defined conversion), so this stays in step with
    ``convert_positions`` by construction rather than by a parallel rule.
    """
    missing = [
        jid for jid in range(1, N_JOINTS + 1) if not is_calibrated(calib.get(jid))
    ]
    if not missing:
        return "active", missing
    if len(missing) == N_JOINTS:
        return "uncalibrated", missing
    return "partial", missing


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
