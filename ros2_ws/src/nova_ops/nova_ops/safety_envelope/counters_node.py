"""Standalone publisher node for /safety_envelope_counters @ 1 Hz.

The gait controller will eventually own an EnvelopeCounters instance
via its SafeJointCommandPublisher and publish from there. This node
exists so you can run a placeholder right now (publishes all zeros
until the gait controller wires up).

Usage:
    ros2 run nova_ops safety_counters
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray

from .counters import EnvelopeCounters, MODES


class SafetyCountersNode(Node):

    def __init__(self):
        super().__init__('safety_envelope_counters')

        # v1: leg-only (IDs 1..12)
        self.counters = EnvelopeCounters(joint_ids=range(1, 13))

        self.pub = self.create_publisher(
            Int32MultiArray, '/safety_envelope_counters', 10)
        self.create_timer(1.0, self._on_tick)

        self.get_logger().info(
            f'safety_envelope_counters up. layout: '
            f'{", ".join(f"{m}_1..{m}_12" for m in MODES)}')

    def _on_tick(self):
        msg = Int32MultiArray()
        msg.data = self.counters.as_flat_list()
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SafetyCountersNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
