"""Liveness watchdog ROS 2 node — thin wrapper over LivenessMonitor.

    ros2 run nova_ops liveness_node

Watches the Teensy `/heartbeat` (plus `/command_stale` and `/safety_state`)
and publishes `/system_ok` (Bool, latched). The gait controller / bringup
should refuse to drive while `/system_ok` is False. Closes the audit gap
"nothing consumes /heartbeat — a FW reset or agent death mid-motion goes
unnoticed."

This node should be respawned by bringup (a dead watchdog is itself a
liveness hole) but is otherwise allowed-to-crash.

Parameters:
  heartbeat_timeout_s  (double, 3.0)  — stale-heartbeat threshold (3 missed beats)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from std_msgs.msg import Bool, Int32

from . import LivenessMonitor


class LivenessNode(Node):
    def __init__(self):
        super().__init__("liveness_watchdog")

        self.declare_parameter("heartbeat_timeout_s", 3.0)
        self.monitor = LivenessMonitor(
            heartbeat_timeout_s=self.get_parameter("heartbeat_timeout_s").value
        )

        self.create_subscription(Int32, "/heartbeat", self._on_heartbeat, 10)
        self.create_subscription(Bool, "/command_stale", self._on_command_stale, 10)
        self.create_subscription(Int32, "/safety_state", self._on_safety_state, 10)

        # Latched so a late-joining gait controller / Foxglove sees current state.
        latched_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.ok_pub = self.create_publisher(Bool, "/system_ok", latched_qos)
        self._last_ok = None

        # 2 Hz — must be faster than heartbeat_timeout so a stop is timely.
        self.create_timer(0.5, self._evaluate)
        self.get_logger().info(
            f"liveness_watchdog up. heartbeat_timeout="
            f"{self.monitor.heartbeat_timeout_s}s"
        )

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_heartbeat(self, msg: Int32):
        self.monitor.on_heartbeat(msg.data, self._now_s())

    def _on_command_stale(self, msg: Bool):
        self.monitor.on_command_stale(msg.data)

    def _on_safety_state(self, msg: Int32):
        self.monitor.on_safety_state(msg.data)

    def _evaluate(self):
        ok, reason = self.monitor.evaluate(self._now_s())
        if ok != self._last_ok:
            self._last_ok = ok
            self.ok_pub.publish(Bool(data=ok))
            if ok:
                self.get_logger().info("/system_ok -> True (live, fault-free)")
            else:
                self.get_logger().error(f"/system_ok -> False: {reason}")


def main(args=None):
    rclpy.init(args=args)
    node = LivenessNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
