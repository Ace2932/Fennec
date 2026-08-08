"""ros2 run nova_ops jog — single-joint jog CLI (#286).

WHY THIS EXISTS. main.cpp's joint_cmd_callback (firmware/teensy/firmware/src/
main.cpp:568-574) writes msg.position[i] straight into
`latched_cmd_position[i]`, and broadcast_servo_commands() (main.cpp:342-414)
casts that DIRECTLY to RAW STS3215 COUNTS (0..4095) — no unit conversion, no
calibration. A bare `ros2 topic pub --once /joint_commands ... '{position:
[0.1, ...]}'` therefore commands raw count ~0 on every joint (one end of
travel), and bypasses SafeJointCommandPublisher + _CountsAdapter
(nova_locomotion/node.py) entirely — that wrapper only sits between the gait
controller and the topic, not on the topic itself.

This tool is the safe path for a manual nudge: read PRESENT position off
/joint_states, convert through the SAME calibration
(safety_envelope.calibration_io.resolve_calibration + firmware_limits.
convert_positions) gait_node uses, clamp against the per-joint limits table
and — for hfe — the posture-aware chassis envelope (rom_envelope.hfe_bounds),
then publish a full 12-vector with the other 11 joints held at PRESENT
(never zeros).

Usage:
    ros2 run nova_ops jog --joint FL_hfe --delta-deg 5
    ros2 run nova_ops jog --joint 5 --to-deg 12.0
    ros2 run nova_ops jog --joint FL_hfe --delta-deg 20 --force
    # pre-calibration wire test ONLY — no ROM/posture clamp, sign unverified:
    ros2 run nova_ops jog --joint FL_hfe --delta-deg 5 --raw
"""

import argparse
import math
import sys
import time
from typing import Dict, List, Optional, Tuple

from nova_ops.safety_envelope.firmware_limits import N_JOINTS, RAW_MAX, RAW_MIN, RAW_PER_RAD

DEFAULT_CAP_DEG = 15.0
JOINT_STATES_TIMEOUT_SEC = 3.0


class JogRefused(Exception):
    """A jog request was refused outright (not clamped — refused)."""


# ---- pure logic (no rclpy — testable directly) --------------------------


def deg_to_raw(deg: float) -> float:
    """Degrees -> raw servo counts, no calibration (--raw mode only).

    RAW_PER_RAD is counts per RADIAN (firmware_limits.py), so degrees must
    go through radians() first — skipping that step here was a 57x
    overshoot (5 deg computed as 3259 counts instead of ~56.9) and made the
    --raw safety cap unreachable (15 deg computed as 9779 counts, past the
    whole 0..4095 range).
    """
    return math.radians(deg) * RAW_PER_RAD


def resolve_joint(joint_arg: str, id_map: Dict[str, int]) -> Tuple[int, str]:
    """--joint accepts a name (e.g. FL_hfe) or a bus id (1-12)."""
    if joint_arg.lstrip("-").isdigit():
        bus_id = int(joint_arg)
        by_id = {v: k for k, v in id_map.items()}
        if bus_id not in by_id:
            raise JogRefused(f"bus id {bus_id} not in joint_id_map (1..{N_JOINTS})")
        return bus_id, by_id[bus_id]
    if joint_arg not in id_map:
        raise JogRefused(
            f"unknown joint {joint_arg!r} — known names: {sorted(id_map)}"
        )
    return id_map[joint_arg], joint_arg


def compute_target(
    present: float,
    delta: Optional[float],
    to: Optional[float],
    lower: float,
    upper: float,
    cap: float,
    force: bool,
) -> Tuple[float, bool]:
    """target = present + delta (or `to` absolute), clamped to [lower, upper].

    Unit-agnostic: pass radians+radians or raw-counts+raw-counts consistently.
    Raises JogRefused if the move exceeds `cap` and not `force` — a refusal,
    not a silent clamp, so an operator typo can't creep the leg past the safety
    cap by requesting a smaller-looking "clamped" move.
    """
    target = to if to is not None else present + delta
    if abs(target - present) > cap and not force:
        raise JogRefused(
            f"requested move {target - present:+.1f} exceeds the {cap:.1f} "
            f"safety cap — pass --force to override"
        )
    clamped = max(lower, min(upper, target))
    return clamped, clamped != target


def clamp_hfe_posture(
    leg: str, hfe: float, haa: float, kfe: float
) -> Tuple[float, bool]:
    """Posture-aware chassis clamp for hfe, mirroring wrapper._clamp_posture.

    HAA SIGN IS UNKNOWN in the servo command frame until homing, so — same as
    the gait-path wrapper — evaluate both interpretations of haa and take the
    tighter (conservative) window.
    """
    from nova_ops.rom_envelope import hfe_bounds

    lo_a, hi_a = hfe_bounds(leg, haa, kfe)
    lo_b, hi_b = hfe_bounds(leg, -haa, kfe)
    lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
    clamped = max(lo, min(hi, hfe))
    return clamped, clamped != hfe


def check_calibration(calib) -> None:
    """Raise JogRefused unless every joint is calibrated (state == active).

    Same all-or-nothing reading firmware_limits.convert_positions already
    enforces — a partial calibration converts NOTHING, so publishing through
    it would send radians to a firmware reading raw counts (#154/#188).
    """
    from nova_ops.safety_envelope.firmware_limits import calibration_state

    state, missing = calibration_state(calib)
    if state != "active":
        raise JogRefused(
            f"calibration is {state!r} (unhomed bus IDs: {missing}). Home the "
            "robot (nova_calibration) first, or pass --raw to bypass with NO "
            "conversion/clamp safety (raw counts, sign unverified)."
        )


# ---- ROS-touching glue (rclpy imported here, not at module scope, so this
# module stays importable — and unit-testable — without a ROS install) ------


def _wait_for_joint_states(node, timeout_sec: float) -> Optional[List[float]]:
    import rclpy

    box = {}

    def cb(msg):
        box["msg"] = msg

    from sensor_msgs.msg import JointState

    sub = node.create_subscription(JointState, "/joint_states", cb, 10)
    deadline = time.monotonic() + timeout_sec
    while "msg" not in box and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_subscription(sub)
    if "msg" not in box or len(box["msg"].position) < N_JOINTS:
        return None
    return list(box["msg"].position[:N_JOINTS])


def _publish_positions(node, positions: List[float]) -> None:
    from sensor_msgs.msg import JointState

    pub = node.create_publisher(JointState, "/joint_commands", 10)
    # ponytail: fixed settle so the discovery handshake lands before publish;
    # a subscriber-count wait would be more precise, upgrade if this ever
    # races on a slow bringup.
    time.sleep(0.2)
    msg = JointState()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.position = [float(p) for p in positions]
    pub.publish(msg)


def _run(node, args) -> int:
    from nova_ops.joint_map import load_joint_id_map
    from nova_ops.safety_envelope.calibration_io import resolve_calibration
    from nova_ops.safety_envelope.firmware_limits import convert_positions
    from nova_ops.safety_envelope.limits import load_default_limits

    id_map = load_joint_id_map()
    try:
        bus_id, name = resolve_joint(args.joint, id_map)
    except JogRefused as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 1
    leg, joint_type = name.split("_", 1)

    raw_positions = _wait_for_joint_states(node, JOINT_STATES_TIMEOUT_SEC)
    if raw_positions is None:
        print(
            f"refusing: no /joint_states (12+ positions) received within "
            f"{JOINT_STATES_TIMEOUT_SEC:.1f}s — is the Teensy bridge up?",
            file=sys.stderr,
        )
        return 1

    cap_deg = DEFAULT_CAP_DEG

    if args.raw:
        print(
            "!!! --raw: bypassing calibration. Publishing RAW SERVO COUNTS "
            "directly, no ROM clamp, no posture clamp, direction/sign "
            "UNVERIFIED. Pre-homing wire tests only. !!!",
            file=sys.stderr,
        )
        present = raw_positions[bus_id - 1]
        delta = deg_to_raw(args.delta_deg) if args.delta_deg is not None else None
        to = deg_to_raw(args.to_deg) if args.to_deg is not None else None
        try:
            target, clamped = compute_target(
                present, delta, to, RAW_MIN, RAW_MAX,
                deg_to_raw(cap_deg), args.force,
            )
        except JogRefused as e:
            print(f"refusing: {e}", file=sys.stderr)
            return 1
        out = list(raw_positions)
        out[bus_id - 1] = target
        _publish_positions(node, out)
        note = " (clamped to 0..4095 raw)" if clamped else ""
        print(f"{name} (id {bus_id}): {present:.0f} -> {target:.0f} raw counts{note}")
        return 0

    calib = resolve_calibration([], [0] * N_JOINTS, None)
    try:
        check_calibration(calib)
    except JogRefused as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 1

    present_rad = convert_positions(list(raw_positions), calib, to_raw=False)

    # Load any persisted haa sign confirmation (#194) before reading the ROM
    # table — load_default_limits() reads the module-global HAA_INBOARD_SIGN,
    # which starts all-None in a fresh process regardless of what a prior
    # confirm_haa_sign run recorded to disk.
    from nova_ops.safety_envelope.calibration_io import apply_haa_confirmations

    try:
        apply_haa_confirmations()
    except Exception as exc:  # noqa: BLE001
        print(
            f"warning: haa confirmations unreadable: {exc!r} — haa stays on "
            f"the conservative symmetric clamp",
            file=sys.stderr,
        )

    limits = load_default_limits()
    lim = limits.get(bus_id)
    if lim is None:
        print(f"refusing: no limits table entry for bus id {bus_id}", file=sys.stderr)
        return 1

    delta = math.radians(args.delta_deg) if args.delta_deg is not None else None
    to = math.radians(args.to_deg) if args.to_deg is not None else None
    try:
        target_rad, rom_clamped = compute_target(
            present_rad[bus_id - 1], delta, to, lim.lower, lim.upper,
            math.radians(cap_deg), args.force,
        )
    except JogRefused as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 1

    target_positions = list(present_rad)
    target_positions[bus_id - 1] = target_rad

    posture_clamped = False
    if joint_type == "hfe":
        haa_rad = target_positions[id_map[f"{leg}_haa"] - 1]
        kfe_rad = target_positions[id_map[f"{leg}_kfe"] - 1]
        target_rad, posture_clamped = clamp_hfe_posture(leg, target_rad, haa_rad, kfe_rad)
        target_positions[bus_id - 1] = target_rad

    raw_out = convert_positions(target_positions, calib, to_raw=True)
    _publish_positions(node, raw_out)

    note = ""
    if rom_clamped:
        note += " (clamped to ROM limits)"
    if posture_clamped:
        note += " (clamped by chassis posture envelope)"
    print(
        f"{name} (id {bus_id}): {math.degrees(present_rad[bus_id - 1]):.1f} -> "
        f"{math.degrees(target_rad):.1f} deg{note}"
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="jog", description="Safely jog a single Nova joint by name or bus id."
    )
    parser.add_argument("--joint", required=True, help="joint name (e.g. FL_hfe) or bus id 1-12")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--delta-deg", type=float, help="relative move, degrees")
    group.add_argument("--to-deg", type=float, help="absolute target, degrees")
    parser.add_argument(
        "--force", action="store_true",
        help=f"override the {DEFAULT_CAP_DEG:.0f} deg safety cap",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="bypass calibration requirement: raw counts, no ROM/posture clamp",
    )
    args = parser.parse_args(argv)

    import rclpy
    from rclpy.node import Node

    rclpy.init(args=None)
    node = Node("nova_ops_jog")
    try:
        rc = _run(node, args)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
