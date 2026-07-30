"""E-stop release check.

Reads `/estop` (std_msgs/Bool, edge-driven publish from Teensy).
Must be False (released) for gait bringup to proceed.

Per firmware contract: True = pressed/engaged, False = released.
"""
from .base import Check


class EstopCheck(Check):

    def name(self) -> str:
        return 'estop'

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

        # /estop is published by micro-ROS Teensy. micro-ROS publishers
        # default to VOLATILE durability and have patchy TRANSIENT_LOCAL
        # support on Humble. Using TRANSIENT_LOCAL here would cause QoS
        # incompatibility and silent STALE results. Use VOLATILE so we
        # match the publisher; the trade-off is that we need an edge to
        # arrive within the 5 s window. Firmware publishes /estop on
        # boot self-test AND on every edge change, so 5 s of wait is OK
        # in practice; for the corner case where the user runs preflight
        # before the Teensy comes up, we report STALE which is the right
        # answer.
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        sub = node.create_subscription(Bool, '/estop', cb, qos)

        end = node.get_clock().now().nanoseconds + 5_000_000_000
        while latest['val'] is None and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)

        if latest['val'] is None:
            return self._stale(
                'no /estop message in 5 s — Teensy bridge down or '
                'firmware not publishing')

        if latest['val']:
            return self._fail(
                'E-stop ENGAGED — release the panel button before bringup')

        return self._ok('E-stop released')
