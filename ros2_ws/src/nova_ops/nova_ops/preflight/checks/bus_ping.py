"""Servo bus ping-sweep check.

Reads `/servo_present_mask` (std_msgs/Int32 bitmask) once, verifies all
12 expected servo IDs (1..12 for v1; 13..18 are reserved Phase 4 arm
and are NOT checked) report present.

Firmware contract (per firmware/teensy/firmware/README.md):
  bit i set = joint i+1 has answered at least one ping since boot
"""
from .base import Check


# v1 active servos: bus IDs 1..12. Bit 0 = ID 1, Bit 11 = ID 12.
V1_EXPECTED_BITS = sum(1 << i for i in range(12))   # = 0x0FFF
V1_EXPECTED_IDS = list(range(1, 13))


class BusPingCheck(Check):

    def name(self) -> str:
        return 'bus_ping'

    def run(self, node) -> 'CheckResult':
        # ROS imports are deferred to run() ON PURPOSE: importing the check
        # REGISTRY must not require a ROS runtime. checks/__init__ imports every
        # check eagerly, so a module-scope `import rclpy` made
        # `from nova_ops.preflight.checks import V1_CHECKS` fail anywhere rclpy is
        # absent — which is why test_preflight.py was excluded from CI and from the
        # documented local command, and therefore never ran at all (#187 follow-up).
        import rclpy
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from std_msgs.msg import Int32

        # Wait for one message on /servo_present_mask.
        # rclpy doesn't have wait_for_message in Humble (added later), so
        # spin until callback fires or timeout.
        latest = {'mask': None}

        def cb(msg):
            latest['mask'] = msg.data

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        sub = node.create_subscription(Int32, '/servo_present_mask', cb, qos)

        # Spin up to 5 seconds waiting for the bitmask
        end = node.get_clock().now().nanoseconds + 5_000_000_000
        while latest['mask'] is None and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)

        if latest['mask'] is None:
            return self._stale(
                'no /servo_present_mask in 5 s — Teensy bridge down or '
                'firmware not flashed')

        mask = latest['mask']
        missing = [i + 1 for i in range(12) if not (mask & (1 << i))]
        if missing:
            return self._fail(
                f'servos missing from bus: {missing} (expected IDs 1..12, '
                f'got mask 0x{mask & 0xFFF:03x})')

        return self._ok(f'all 12 servos present (mask 0x{mask & 0xFFF:03x})')
