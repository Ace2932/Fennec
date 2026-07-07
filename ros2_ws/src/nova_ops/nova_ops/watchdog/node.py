"""Jetson watchdog ROS 2 node — systemd WATCHDOG=1 feeder.

    ros2 run nova_ops watchdog_node

Runs inside the nova-bringup.service process tree (NotifyAccess=all lets
any child feed). A ROS timer at 4x the feed rate emits WATCHDOG=1 while
the executor spins; if the stack deadlocks or this process wedges,
systemd's WatchdogSec expires and the whole bringup tree is killed and
restarted. Also sends READY=1 once at startup (harmless under
Type=exec, required if the unit is ever switched to Type=notify).

Publishes /watchdog_fed (Int32, feed counter, 0.2 Hz) as a diagnostic
breadcrumb — flat counter in a bag = the stack was wedged (or the unit
had no WatchdogSec and feeding was disabled).

Outside systemd ($NOTIFY_SOCKET unset) the node idles harmlessly.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

from . import WatchdogFeeder, sd_notify, watchdog_usec_from_env


class WatchdogNode(Node):
    def __init__(self):
        super().__init__("jetson_watchdog")
        usec = watchdog_usec_from_env()
        now = self.get_clock().now().nanoseconds / 1e9
        self.feeder = WatchdogFeeder(usec, now)

        sd_notify("READY=1")
        if self.feeder.enabled:
            period = self.feeder.interval_s / 2.0  # 4x WatchdogSec margin
            self.get_logger().info(
                f"systemd watchdog armed: feeding every {period:.1f}s "
                f"(WATCHDOG_USEC={usec})"
            )
        else:
            period = 5.0
            self.get_logger().info(
                "no WATCHDOG_USEC in env — feeder disabled (dev run or "
                "unit missing WatchdogSec=); idling"
            )

        self._pub = self.create_publisher(Int32, "/watchdog_fed", 1)
        self.create_timer(period, self._tick)
        self.create_timer(5.0, self._publish_count)

    def _tick(self):
        now = self.get_clock().now().nanoseconds / 1e9
        if self.feeder.due(now):
            if sd_notify("WATCHDOG=1"):
                self.feeder.fed(now)

    def _publish_count(self):
        m = Int32()
        m.data = int(self.feeder.feed_count)
        self._pub.publish(m)


def main(args=None):
    rclpy.init(args=args)
    node = WatchdogNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
