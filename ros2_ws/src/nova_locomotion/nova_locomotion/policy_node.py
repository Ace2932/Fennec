"""policy_node — the sim-trained RL policy's ROS 2 bridge (#289).

Was `sim/nova_mjx/deploy/policy_node.py`: published `Int32MultiArray` on
`/joint_goal_ticks`, a topic with ZERO subscribers anywhere in the stack, from
a directory with no `package.xml`/`setup.py` — not even buildable. That file
is now a deprecation stub pointing here. This node instead publishes
`/joint_commands` (radians) through the SAME `SafeJointCommandPublisher` +
`_CountsAdapter` path `node.py`'s `gait_node` uses, so it inherits the limits
table, the posture clamp, and the per-joint homing-calibration conversion for
free — one publish path, not two.

ONE-COPY DECISION (#289): `policy_runner.py` (pure numpy, the obs-assembly +
inference math) moved here verbatim from `sim/nova_mjx/deploy/policy_runner.py`
— see that module's own docstring for the 105-d obs contract. It had zero ROS
imports, same as this package's other pure modules (`kinematics/leg_ik.py`,
etc.), so it belongs beside them rather than forked. `sim/nova_mjx/deploy`'s
tests were repointed at the new location (still pass from there); nothing in
`sim/nova_mjx` was deleted.

Topology:
  /joint_states -> raw counts -> radians (via the SAME homing calibration
                   gait_node reads, resolve_calibration) -> obs history    \\
  /imu           -> gyro + proj_grav (gravity rotated into body frame)     +-> policy_runner.NovaPolicy -> 12 rad targets
  /cmd_vel       -> command                                               /        |
  /nova/policy_enable (std_msgs/Bool, default False, never auto-arms) ----+        v
                                                                     ramp-on-enable blend
                                                                                    |
                                                                                    v
                                             SafeJointCommandPublisher -> _CountsAdapter -> /joint_commands

GATING, all of which must hold before a single inference runs (PolicyGate,
pure/tested without rclpy — see test_policy_node.py, same rclpy-stub pattern
as test_counts_adapter_log.py):
  * preflight    — reuses controller.PreflightGate, the #285 mechanism
                    gait_node already gates motion modes with. Same
                    /preflight/status subscription, same verdict function
                    (controller.preflight_all_critical_ok).
  * calibration  — resolve_calibration() must find ALL 12 joints homed
                    (firmware_limits.calibration_state == "active"). Stricter
                    than gait_node, which degrades to a radians-passthrough
                    when uncalibrated: gait's choreo moves are small and
                    bounded, but a live RL policy's raw output fed through an
                    unconverted identity path is an unbounded step. Refuse
                    outright instead.
  * imu          — gyro/proj_grav are dims 0-5 of every 30-d history frame
                    (policy_runner.py). No /imu message within
                    IMU_TIMEOUT_SEC refuses inference and names #14 (no
                    ICM-42688-P driver yet) — expected today, not a bug.
  * enable       — /nova/policy_enable (std_msgs/Bool) must be True. Default
                    False: this node never arms itself.

RAMP ON ENABLE: the scaffold's own TODO ("RAMP from the measured current pose
to default on start, never snap") — the first `ramp_ticks` ticks after
inference starts interpolate from the last measured /joint_states pose to the
policy's own output (`ramp_alpha`/`ramp_blend`, pure functions). Firmware-side
slew already exists; this is the host-side start-of-motion nicety.
"""

from __future__ import annotations

import os
from typing import List, Optional, Sequence

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Bool

from nova_locomotion.controller import JOINTS, LEGS, PreflightGate, preflight_all_critical_ok
from nova_locomotion.node import _CountsAdapter
from nova_locomotion.policy_runner import NovaPolicy
from nova_ops.joint_map import load_joint_id_map
from nova_ops.safety_envelope.calibration_io import (
    DEFAULT_CALIBRATION_PATH,
    apply_haa_confirmations,
    resolve_calibration,
)
from nova_ops.safety_envelope.firmware_limits import (
    RAW_PER_RAD,
    calibration_state,
    convert_positions,
)
from nova_ops.safety_envelope.limits import load_default_limits
from nova_ops.safety_envelope.wrapper import SafeJointCommandPublisher

#: no /imu within this long (continuously, not just at the moment of enable)
#: -> refuse. 0.5s is a few control periods at 50 Hz -- long enough to absorb
#: one dropped message, short enough that a truly dead IMU is caught fast.
IMU_TIMEOUT_SEC = 0.5

#: ticks (at control_hz) to blend from the measured pose to the policy's own
#: output after enable, instead of snapping. 100 @ 50 Hz = 2s.
DEFAULT_RAMP_TICKS = 100


def ramp_alpha(tick: int, ramp_ticks: int) -> float:
    """Blend fraction toward the policy output at `tick` ticks since enable:
    0 (fully the measured pose) rising to 1 (fully the policy) over
    `ramp_ticks`, then held at 1. `ramp_ticks<=0` means no ramp (full
    authority immediately)."""
    if ramp_ticks <= 0:
        return 1.0
    return min(1.0, (tick + 1) / ramp_ticks)


def ramp_blend(current: Sequence[float], target: Sequence[float], alpha: float) -> List[float]:
    """Per-joint linear interpolation current -> target (both radians, same
    order); alpha 0..1 from ramp_alpha. The anti-snap the old scaffold's TODO
    named."""
    return [c + (t - c) * alpha for c, t in zip(current, target)]


class PolicyGate:
    """Arming interlock for the policy bridge (#289): four independent
    preconditions, all required, that say WHY when one is missing. See the
    module docstring for what each guards against."""

    def __init__(self, preflight: PreflightGate, imu_timeout: float = IMU_TIMEOUT_SEC):
        self.preflight = preflight
        self.imu_timeout = imu_timeout
        self.calibrated = False
        self.enabled = False
        self._last_imu_t: Optional[float] = None

    def observe_calibration(self, calibrated: bool) -> None:
        self.calibrated = bool(calibrated)

    def observe_imu(self, now: float) -> None:
        self._last_imu_t = now

    def observe_enable(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def refusal(self, now: float) -> Optional[str]:
        """None if inference may run this tick; else the reason it can't.
        Checked in a fixed order (enable, preflight, calibration, imu) so the
        log always reports the FIRST unmet precondition, not whichever one
        the caller happens to notice."""
        if not self.enabled:
            return "policy disabled (publish True on /nova/policy_enable to arm)"
        if not self.preflight.allows("policy"):  # any non-"idle" mode string
            return "preflight gate: no observed PASS on /preflight/status"
        if not self.calibrated:
            return (
                "calibration incomplete: all 12 joints must be homed "
                "(nova_calibration) before the policy is allowed to run"
            )
        if self._last_imu_t is None or (now - self._last_imu_t) > self.imu_timeout:
            return (
                "no live /imu stream (needs the ICM-42688-P driver, #14) "
                "-- refusing to enable"
            )
        return None


def _raw_vel_to_rad(vel_raw: Sequence[float], calib) -> List[float]:
    """Raw STS3215 velocity register -> rad/s, per joint (bus-ID order).

    Same per-joint linear scale firmware_limits.rad_to_raw uses for position,
    with no home-offset term (velocity has none). Uncalibrated joints read 0 --
    harmless because PolicyGate already refuses inference unless every joint
    is calibrated, so this path only ever runs fully calibrated.

    ponytail: assumes the raw velocity register is counts/s like position raw
    counts are -- unverified against a real STS3215 bus (nothing has read this
    field before #289). Confirm at first bench test; upgrade to a measured
    scale if it disagrees.
    """
    out = []
    for i, v in enumerate(vel_raw):
        c = calib.get(i + 1)
        if c is None or c.urdf_sign not in (1, -1):
            out.append(0.0)
        else:
            out.append(float(v) / (c.urdf_sign * RAW_PER_RAD))
    return out


class PolicyNode(Node):
    def __init__(self):
        super().__init__("nova_policy")
        self.declare_parameter("policy_npz", "")
        self.declare_parameter("control_hz", 50.0)
        self.declare_parameter("require_preflight", True)
        self.declare_parameter("home_raw", [0.0] * 12)
        self.declare_parameter("urdf_sign", [0] * 12)
        self.declare_parameter("calibration_path", DEFAULT_CALIBRATION_PATH)
        self.declare_parameter("ramp_ticks", DEFAULT_RAMP_TICKS)
        self.declare_parameter("imu_timeout_sec", IMU_TIMEOUT_SEC)

        npz = self.get_parameter("policy_npz").value
        if not npz or not os.path.exists(npz):
            # #288: no checkpoint has been pulled onto the robot yet. Refuse
            # at construction -- do not start a node that can never infer.
            raise RuntimeError(
                f"policy_npz {npz!r} not found. No trained checkpoint has "
                "been pulled onto this machine yet (#288). Export one with "
                "sim/nova_mjx/export_policy.py and point the policy_npz "
                "parameter at the resulting .npz before launching this node."
            )
        self.pol = NovaPolicy(npz)  # raises loud on an obs-contract mismatch
        m = self.pol.meta
        self.get_logger().info(
            f"loaded {npz}: label='{m.get('label', '?')}' sha={m.get('sha', '?')} "
            f"created={m.get('created', '?')} obs={self.pol.mean.shape[0]} "
            f"hist={self.pol.hist} prop={self.pol.prop}"
        )

        # policy output / obs joint order == bus-ID order (per-leg-sequential:
        # FL haa,hfe,kfe, FR ..., per joint_id_map.yaml) -- but ALWAYS route
        # through the id map by name, never assume the identity holds
        # (the #163/#175-class bug: an assumption about the map's SHAPE
        # instead of a read of the map).
        self.id_map = load_joint_id_map()
        self.jorder = [f"{leg}_{j}" for leg in LEGS for j in JOINTS]
        self._bus_idx = [self.id_map[name] - 1 for name in self.jorder]

        require_preflight = bool(self.get_parameter("require_preflight").value)
        if not require_preflight:
            self.get_logger().warn(
                "!!! require_preflight:=false -- nova_policy will accept "
                "/nova/policy_enable WITHOUT ever observing a preflight PASS. "
                "Bench debugging only. Do not run this against real servos. !!!"
            )
        self.preflight_gate = PreflightGate(require=require_preflight)
        self.gate = PolicyGate(
            preflight=self.preflight_gate,
            imu_timeout=float(self.get_parameter("imu_timeout_sec").value),
        )

        self.calib = self._load_calib()
        self._load_haa_confirmations()
        state, missing = calibration_state(self.calib)
        self.gate.observe_calibration(state == "active")
        if state != "active":
            self.get_logger().warn(
                f"nova_policy: calibration {state} (missing {missing}) -- "
                "will refuse /nova/policy_enable until all 12 joints are homed"
            )

        raw_pub = self.create_publisher(JointState, "/joint_commands", 10)
        adapter = _CountsAdapter(raw_pub, self.calib, logger=self.get_logger())
        self.safe_pub = SafeJointCommandPublisher(
            node=self, limits=load_default_limits(), raw_publisher=adapter
        )

        self._jpos = list(self.pol.default_pose)
        self._jvel = [0.0] * 12
        self._gyro = [0.0, 0.0, 0.0]
        self._grav = [0.0, 0.0, -1.0]
        self._cmd = [0.0, 0.0, 0.0]
        self._ramp_tick: Optional[int] = None
        self._last_refusal: Optional[str] = None

        self.create_subscription(JointState, "/joint_states", self._on_states, 10)
        self.create_subscription(Imu, "/imu", self._on_imu, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd, 10)
        self.create_subscription(Bool, "/nova/policy_enable", self._on_enable, 10)
        self.create_subscription(
            DiagnosticArray, "/preflight/status", self._on_preflight_status, 10
        )

        self.ramp_ticks = int(self.get_parameter("ramp_ticks").value)
        hz = float(self.get_parameter("control_hz").value)
        self.create_timer(1.0 / hz, self._tick)
        self.get_logger().info(
            "nova_policy up, DISABLED -- publish True on /nova/policy_enable to "
            "arm (also needs preflight PASS + full calibration + a live /imu)"
        )

    # ---- setup helpers ---------------------------------------------------

    def _load_calib(self):
        calib, source = resolve_calibration(
            list(self.get_parameter("home_raw").value or []),
            list(self.get_parameter("urdf_sign").value or []),
            self.get_parameter("calibration_path").value,
        )
        self.get_logger().info(f"nova_policy: calibration from {source}")
        return calib

    def _load_haa_confirmations(self) -> None:
        """Load persisted haa sign confirmations (#194) — mirrors
        gait_node._load_haa_confirmations; see that docstring for why this
        must run before load_default_limits()."""
        path = self.get_parameter("calibration_path").value
        try:
            applied = apply_haa_confirmations(path)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(
                f"haa confirmations at {path} are unreadable: {exc}. haa "
                f"stays on the conservative symmetric clamp until fixed."
            )
            return
        if applied:
            self.get_logger().info(
                f"loaded {applied} confirmed haa sign(s) from {path}"
            )

    # ---- subscriptions -----------------------------------------------------

    def _on_states(self, msg: JointState) -> None:
        self.safe_pub.on_joint_states(msg)  # envelope load window, same as gait_node
        if len(msg.position) < 12:
            return
        pos = list(msg.position[:12])  # bus-ID order, raw counts
        if self.calib:
            converted = convert_positions(pos, self.calib, to_raw=False)
            if converted is not None:
                pos = converted
        vel_raw = list(msg.velocity[:12]) if len(msg.velocity) >= 12 else [0.0] * 12
        vel = _raw_vel_to_rad(vel_raw, self.calib) if self.calib else vel_raw
        self._jpos = [pos[i] for i in self._bus_idx]
        self._jvel = [vel[i] for i in self._bus_idx]

    def _on_imu(self, msg: Imu) -> None:
        g = msg.angular_velocity
        self._gyro = [g.x, g.y, g.z]
        q = msg.orientation
        w, x, y, z = q.w, q.x, q.y, q.z
        # gravity (world -z) rotated into body frame via the IMU quaternion
        # (R^T @ [0,0,-1]), same formula the old scaffold verified.
        self._grav = [
            -2 * (x * z - w * y),
            -2 * (y * z + w * x),
            -(1 - 2 * (x * x + y * y)),
        ]
        self.gate.observe_imu(self.get_clock().now().nanoseconds / 1e9)

    def _on_cmd(self, msg: Twist) -> None:
        self._cmd = [msg.linear.x, msg.linear.y, msg.angular.z]

    def _on_enable(self, msg: Bool) -> None:
        enabling = bool(msg.data)
        self.gate.observe_enable(enabling)
        if enabling:
            self._ramp_tick = 0  # (re)start the anti-snap ramp from the current pose
        else:
            self._ramp_tick = None
            self.pol.reset()  # hold last_action/history clean while disabled

    def _on_preflight_status(self, msg: DiagnosticArray) -> None:
        self.preflight_gate.observe(preflight_all_critical_ok(msg.status))

    # ---- control loop -------------------------------------------------

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        reason = self.gate.refusal(now)
        if reason is not None:
            if reason != self._last_refusal:
                self.get_logger().warn(f"nova_policy: inference refused: {reason}")
                self._last_refusal = reason
            self.pol.reset()
            self._ramp_tick = None
            return
        self._last_refusal = None

        target = self.pol.joint_targets(
            self._gyro, self._grav, self._cmd, self._jpos, self._jvel
        ).tolist()
        if self._ramp_tick is None:
            self._ramp_tick = 0
        alpha = ramp_alpha(self._ramp_tick, self.ramp_ticks)
        blended = ramp_blend(self._jpos, target, alpha)
        self._ramp_tick += 1

        positions = [0.0] * 12
        for i, idx in enumerate(self._bus_idx):
            positions[idx] = blended[i]

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.position = positions
        self.safe_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
