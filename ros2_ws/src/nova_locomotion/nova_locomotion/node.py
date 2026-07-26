"""gait_node — thin rclpy glue around controller.GaitController.

Roadmap stage 1 item 1 (docs/roadmap-trot-balance.md). ALL logic lives
in controller.py (pure, tested without rclpy); this file only wires
topics, the 100 Hz timer, and nova_ops' safety envelope. No test
imports this module.

Topology (the project-policy publish path, wrapper.py docstring):
  /nova/mode (std_msgs/String: idle|stand_up|sit|crawl|trot)  --\\
  /cmd_vel   (geometry_msgs/Twist, stored for the Raibert lane) -+-> timer
  /joint_states -> envelope load window + current-pose seed     --/   |
                                                                      v
  GaitController -> radians ordered by bus ID (joint_id_map) ->
  SafeJointCommandPublisher (clamp/refuse) -> _CountsAdapter ->
  /joint_commands

UNITS — WIRE-AT-CALIBRATION: positions here are RADIANS end to end;
firmware main.cpp reads /joint_commands as RAW STS3215 COUNTS. The
conversion happens AFTER the envelope (limits are radians), in both
directions, and is PER JOINT (#154):

    raw = home_raw + urdf_sign * theta * RAW_PER_RAD

from the `home_raw` / `urdf_sign` params, filled by servo homing. This
was two GLOBAL scalars, which could not express the per-joint SIGN the
limits path was already using — an inverted joint would have received a
correctly-signed limit window and a wrong-signed command. Both paths now
share firmware_limits.rad_to_raw/raw_to_rad, so they cannot diverge.

Uncalibrated (any joint with urdf_sign 0) = radians pass straight
through, unchanged, which is the pre-hardware state. All-or-nothing on
purpose: the firmware reads the whole array in ONE unit.
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from nova_locomotion.controller import (
    ControllerParams,
    GaitController,
    positions_to_pose,
)
from nova_locomotion.gait.backlash import BacklashComp
from nova_ops.joint_map import load_joint_id_map
from nova_ops.safety_envelope.firmware_limits import (
    JointHomeCalib,
    build_calib,
    convert_positions,
)
from nova_ops.safety_envelope.limits import load_default_limits
from nova_ops.safety_envelope.wrapper import SafeJointCommandPublisher

RATE_HZ = 100.0  # firmware command rate


class _CountsAdapter:
    """Publisher shim: radians -> firmware units AFTER the envelope.

    PER-JOINT since issue #154. This used to apply two GLOBAL scalars
    (counts_per_rad, home_offset) to all twelve joints, while the limits path
    already converted per joint via JointHomeCalib.urdf_sign. A joint whose
    servo is mounted inverted therefore received a correctly-signed limit
    window and a WRONG-SIGNED command — it would drive away from target into
    its stop at full authority, with the firmware backstop computed for the
    opposite sense so it could not help.

    The kinematic left/right mirror is a different thing and is already handled
    (solve_side flips haa only; hfe/kfe need no flip because their axis is
    PARALLEL to the mirror normal, so the axis flip and the angle negation
    cancel). THIS is the servo MOUNTING direction: per joint, physical, and
    only knowable once homing has watched a real servo move.

    Identity until every joint is calibrated — see convert_positions() for why
    the all-or-nothing rule is deliberate.
    """

    def __init__(self, raw_pub, calib=None):
        self.raw_pub = raw_pub
        self.calib = calib or {}
        self._warned = False

    def publish(self, msg):
        if self.calib:
            converted = convert_positions(list(msg.position), self.calib, to_raw=True)
            if converted is not None:
                msg.position = converted
        self.raw_pub.publish(msg)


class GaitNode(Node):
    def __init__(self):
        super().__init__("gait_node")
        # Per-joint homing calibration (#154). home_raw + urdf_sign per bus ID,
        # filled by servo homing. Empty = uncalibrated = radians pass straight
        # through, which is the pre-hardware state.
        self.declare_parameter("home_raw", [0.0] * 12)  # WIRE-AT-CALIBRATION
        self.declare_parameter("urdf_sign", [0] * 12)  # 0 = unknown

        self.id_map = load_joint_id_map()
        self.controller = GaitController(ControllerParams(), BacklashComp())
        self.cmd_vel = (0.0, 0.0)  # stored for the stage-4 Raibert lane
        self._current_positions = None  # last /joint_states positions

        raw_pub = self.create_publisher(JointState, "/joint_commands", 10)
        self.calib = self._load_calib()
        adapter = _CountsAdapter(raw_pub, self.calib)
        self.safe_pub = SafeJointCommandPublisher(
            node=self, limits=load_default_limits(), raw_publisher=adapter
        )

        self.create_subscription(JointState, "/joint_states", self._on_states, 10)
        self.create_subscription(String, "/nova/mode", self._on_mode, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_timer(1.0 / RATE_HZ, self._tick)
        self.get_logger().info("gait_node up: modes idle|stand_up|sit|crawl|trot")

    # ---- subscriptions -------------------------------------------------

    def _load_calib(self):
        """Bus ID -> JointHomeCalib from the ROS params. See build_calib()."""
        return build_calib(
            list(self.get_parameter("home_raw").value or []),
            list(self.get_parameter("urdf_sign").value or []),
        )

    def _on_states(self, msg: JointState) -> None:
        self.safe_pub.on_joint_states(msg)  # envelope load window
        if len(msg.position) >= 12:
            # RAW COUNTS -> RADIANS before seeding (#154). positions_to_pose()
            # expects radians; feeding it raw counts made stand_up(start_pose=)
            # begin from a garbage pose — and that is the E-stop RECOVERY path.
            pos = list(msg.position[:12])
            if self.calib:
                converted = convert_positions(pos, self.calib, to_raw=False)
                if converted is not None:
                    pos = converted
            self._current_positions = pos

    def _on_mode(self, msg: String) -> None:
        mode = msg.data.strip()
        now = self.get_clock().now().nanoseconds / 1e9
        current = (
            positions_to_pose(self._current_positions, self.id_map)
            if self._current_positions is not None
            else None
        )
        try:
            self.controller.set_mode(mode, now, current_pose=current)
        except ValueError as e:
            self.get_logger().warn(str(e))
            return
        self.get_logger().info(f"mode -> {mode}")

    def _on_cmd_vel(self, msg: Twist) -> None:
        self.cmd_vel = (msg.linear.x, msg.linear.y)

    # ---- 100 Hz command path -------------------------------------------

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        positions = self.controller.command_positions(now, self.id_map)
        if positions is None:
            return  # idle before any pose — publish nothing, servos hold
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        # name[] intentionally empty: firmware convention, position[i] = bus i+1
        msg.position = positions
        self.safe_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GaitNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
