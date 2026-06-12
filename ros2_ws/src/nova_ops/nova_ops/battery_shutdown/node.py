"""Battery-low shutdown ROS 2 node — thin wrapper over ShutdownDecider.

    ros2 run nova_ops battery_shutdown_node

Unlike the rest of nova_ops, this node is NOT allowed-to-crash: it is the
software half of the two-stage LVC chain (13.0 V graceful / 12.4 V hardware
cutoff). The bringup composer launches it with respawn=True.

Shutdown sequence on trigger:
  1. log FATAL-level message with the trigger reason
  2. publish /shutdown_imminent (Bool, transient-local — late joiners like
     the dashcam see it even if they subscribe after the edge)
  3. wait grace_s (default 2.0 s) so the dashcam's safety-freeze finishes
     flushing its MCAP segment (dashcam freezes on /safety_state == 2 on
     its own; the grace period just gives that write time to land)
  4. exec poweroff_cmd (default: `sudo -n systemctl poweroff`)

Host prerequisite (documented in docs/setup-jetson.md): the node's user
needs passwordless poweroff —
    echo 'jetson ALL=(ALL) NOPASSWD: /usr/bin/systemctl poweroff' | \
        sudo tee /etc/sudoers.d/nova-battery-shutdown

Parameters:
  raw_sustain_s  (double, 2.0)  — sustain window for the raw signal path
  grace_s        (double, 2.0)  — delay between flag publish and poweroff
  dry_run        (bool, False)  — log + publish but skip the poweroff exec
"""
import shlex
import subprocess

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy)
from std_msgs.msg import Bool, Int32

from . import ShutdownDecider

POWEROFF_CMD = 'sudo -n systemctl poweroff'


class BatteryShutdownNode(Node):

    def __init__(self):
        super().__init__('battery_shutdown')

        self.declare_parameter('raw_sustain_s', 2.0)
        self.declare_parameter('grace_s', 2.0)
        self.declare_parameter('dry_run', False)

        self.decider = ShutdownDecider(
            raw_sustain_s=self.get_parameter('raw_sustain_s').value)
        self.grace_s = float(self.get_parameter('grace_s').value)
        self.dry_run = bool(self.get_parameter('dry_run').value)
        self._sequence_started = False

        # Teensy publishes are edge-only; reliable QoS so the edges we DO
        # get aren't dropped on a congested link.
        self.create_subscription(
            Bool, '/battery_low', self._on_battery_low, 10)
        self.create_subscription(
            Int32, '/safety_state', self._on_safety_state, 10)

        # Transient-local so a late-joining subscriber (dashcam restart,
        # operator Foxglove session) still sees the flag.
        latched_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.imminent_pub = self.create_publisher(
            Bool, '/shutdown_imminent', latched_qos)

        # 5 Hz evaluation — the raw-sustain path needs a clock, not edges.
        self.create_timer(0.2, self._evaluate)

        self.get_logger().info(
            f'battery_shutdown up. raw_sustain={self.decider.raw_sustain_s}s '
            f'grace={self.grace_s}s dry_run={self.dry_run}')

    # -- subscriptions -----------------------------------------------------

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_battery_low(self, msg: Bool):
        self.decider.on_battery_low(msg.data, self._now_s())
        if msg.data:
            self.get_logger().warn(
                '/battery_low HIGH — pack under 13.0 V at the comparator')

    def _on_safety_state(self, msg: Int32):
        self.decider.on_safety_state(msg.data, self._now_s())

    # -- shutdown sequence ---------------------------------------------------

    def _evaluate(self):
        if self._sequence_started:
            return
        if not self.decider.evaluate(self._now_s()):
            return
        self._sequence_started = True

        self.get_logger().fatal(
            f'BATTERY LOW SHUTDOWN: {self.decider.reason} — '
            f'poweroff in {self.grace_s}s '
            f'(hardware cutoff fires at 12.4 V regardless)')
        self.imminent_pub.publish(Bool(data=True))

        # One-shot timer for the grace period — keeps the executor spinning
        # so the /shutdown_imminent publish actually egresses.
        self._grace_timer = self.create_timer(self.grace_s, self._poweroff)

    def _poweroff(self):
        self._grace_timer.cancel()
        if self.dry_run:
            self.get_logger().fatal(
                f'DRY RUN — would exec: {POWEROFF_CMD}')
            return
        self.get_logger().fatal(f'executing: {POWEROFF_CMD}')
        try:
            subprocess.run(shlex.split(POWEROFF_CMD), check=True, timeout=10)
        except (subprocess.CalledProcessError,
                subprocess.TimeoutExpired, OSError) as e:
            # Last-ditch visibility — if poweroff is misconfigured the
            # hardware cutoff is now the only protection left.
            self.get_logger().fatal(
                f'poweroff FAILED ({e}) — check sudoers rule in '
                f'docs/setup-jetson.md. Hardware 12.4 V cutoff is now the '
                f'only remaining protection.')


def main(args=None):
    rclpy.init(args=args)
    node = BatteryShutdownNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
