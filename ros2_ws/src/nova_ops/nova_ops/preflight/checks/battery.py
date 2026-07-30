"""Battery latch check.

Reads `/battery_low` (std_msgs/Bool, edge-driven). Must be False for
bringup. True = the 13.0 V comparator has latched (pack at or below
the graceful-shutdown threshold; the 12.4 V hard-cutoff will fire in
~30-60 s).

Continuous pack voltage isn't on a topic today (only the binary
comparator output). See docs/notes-qol-features.md §9 for the Option B
plan to add a 4th INA226 on the battery feed.
"""
from .base import Check


class BatteryLatchCheck(Check):

    def name(self) -> str:
        return 'battery_latch'

    def run(self, node) -> 'CheckResult':
        # ROS imports are deferred to run() ON PURPOSE: importing the check
        # REGISTRY must not require a ROS runtime. checks/__init__ imports every
        # check eagerly, so a module-scope `import rclpy` made
        # `from nova_ops.preflight.checks import V1_CHECKS` fail anywhere rclpy is
        # absent — which is why test_preflight.py was excluded from CI and from the
        # documented local command, and therefore never ran at all (#187 follow-up).
        import rclpy
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from std_msgs.msg import Bool

        latest = {'val': None}

        def cb(msg):
            latest['val'] = msg.data

        # VOLATILE to match micro-ROS publisher defaults (see estop.py).
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        sub = node.create_subscription(Bool, '/battery_low', cb, qos)

        end = node.get_clock().now().nanoseconds + 5_000_000_000
        while latest['val'] is None and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)

        if latest['val'] is None:
            return self._stale(
                'no /battery_low message in 5 s — Teensy bridge down')

        if latest['val']:
            return self._fail(
                'battery comparator tripped (pack ≤ 13.0 V) — recharge '
                'before bringup; 12.4 V hard cutoff is ~30-60 s away')

        return self._ok('battery above 13.0 V threshold')
