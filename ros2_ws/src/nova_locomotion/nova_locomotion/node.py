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
firmware main.cpp currently reads /joint_commands as RAW STS3215
COUNTS. Until the Jetson bridge owns the conversion, the
counts_per_rad + home_offset params (default identity = radians pass
straight through) convert AFTER the envelope (limits are radians).
TODO(calibration): fill from servo homing (counts_per_rad ~= 651.74 =
4096/2pi with per-joint sign, home_offset per joint) or delete once
the bridge converts. Same for /joint_states seeding: raw counts would
need the inverse before positions_to_pose().
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
from nova_ops.safety_envelope.limits import load_default_limits
from nova_ops.safety_envelope.wrapper import SafeJointCommandPublisher

RATE_HZ = 100.0  # firmware command rate


class _CountsAdapter:
    """Publisher shim: radians -> firmware units AFTER the envelope.
    Identity by default (WIRE-AT-CALIBRATION, module docstring)."""

    def __init__(self, raw_pub, counts_per_rad: float, home_offset: float):
        self.raw_pub = raw_pub
        self.counts_per_rad = counts_per_rad
        self.home_offset = home_offset

    def publish(self, msg):
        if self.counts_per_rad != 1.0 or self.home_offset != 0.0:
            msg.position = [
                p * self.counts_per_rad + self.home_offset for p in msg.position
            ]
        self.raw_pub.publish(msg)


class GaitNode(Node):
    def __init__(self):
        super().__init__("gait_node")
        self.declare_parameter("counts_per_rad", 1.0)  # WIRE-AT-CALIBRATION
        self.declare_parameter("home_offset", 0.0)  # WIRE-AT-CALIBRATION

        self.id_map = load_joint_id_map()
        self.controller = GaitController(ControllerParams(), BacklashComp())
        self.cmd_vel = (0.0, 0.0)  # stored for the stage-4 Raibert lane
        self._current_positions = None  # last /joint_states positions

        raw_pub = self.create_publisher(JointState, "/joint_commands", 10)
        adapter = _CountsAdapter(
            raw_pub,
            float(self.get_parameter("counts_per_rad").value),
            float(self.get_parameter("home_offset").value),
        )
        self.safe_pub = SafeJointCommandPublisher(
            node=self, limits=load_default_limits(), raw_publisher=adapter
        )

        self.create_subscription(JointState, "/joint_states", self._on_states, 10)
        self.create_subscription(String, "/nova/mode", self._on_mode, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_timer(1.0 / RATE_HZ, self._tick)
        self.get_logger().info("gait_node up: modes idle|stand_up|sit|crawl|trot")

    # ---- subscriptions -------------------------------------------------

    def _on_states(self, msg: JointState) -> None:
        self.safe_pub.on_joint_states(msg)  # envelope load window
        if len(msg.position) >= 12:
            # TODO(calibration): raw counts -> radians before seeding
            self._current_positions = list(msg.position[:12])

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
