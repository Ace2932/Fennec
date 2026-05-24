"""Preflight check ROS 2 node.

Exposes:
  Service ~/run (std_srvs/Trigger): runs all v1 checks, returns
    success=True iff every critical check is OK.
  Topic ~/status (diagnostic_msgs/DiagnosticArray): published once per
    service call with the per-check breakdown. Foxglove + RGB status
    LED node subscribe to this.

Usage:
    ros2 run nova_ops preflight_node

  Or via launch:
    ros2 launch nova_ops preflight.launch.py
"""
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from .checks import V1_CHECKS, CheckStatus


# Map our CheckStatus to diagnostic_msgs/DiagnosticStatus level byte
_STATUS_TO_LEVEL = {
    CheckStatus.OK:    DiagnosticStatus.OK,
    CheckStatus.WARN:  DiagnosticStatus.WARN,
    CheckStatus.FAIL:  DiagnosticStatus.ERROR,
    CheckStatus.STALE: DiagnosticStatus.STALE,
}


class PreflightNode(Node):

    def __init__(self):
        super().__init__('preflight')

        # Optional: which checks to run (default = V1_CHECKS).
        # Subclasses or future versions can override via parameter list.
        self.checks = list(V1_CHECKS)

        # Service callback MUST be in a reentrant group: each check's
        # run() spins the node to wait for one message, and that spin
        # re-enters the executor. With the default mutex-cb group the
        # service callback would deadlock its own executor.
        # The MultiThreadedExecutor + ReentrantCallbackGroup combo
        # is the supported pattern for "service does spin-blocking work".
        cb_group = ReentrantCallbackGroup()
        self.create_service(Trigger, '~/run', self._on_run, callback_group=cb_group)
        self.status_pub = self.create_publisher(
            DiagnosticArray, '~/status', 10)

        self.get_logger().info(
            f'preflight node up. {len(self.checks)} check(s) registered: '
            f'{[c.name() for c in self.checks]}')

    def _on_run(self, request, response):
        results = []
        for check in self.checks:
            try:
                r = check.run(self)
            except Exception as e:  # check should never crash but be safe
                from .checks.base import CheckResult
                r = CheckResult(check.name(), CheckStatus.FAIL,
                                f'check raised {type(e).__name__}: {e}',
                                getattr(check, 'critical', True))
            results.append(r)
            self.get_logger().info(
                f'  [{r.status.name:5s}] {r.name:14s} {r.message}')

        # Build the DiagnosticArray payload
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        for r in results:
            ds = DiagnosticStatus()
            ds.level = _STATUS_TO_LEVEL[r.status]
            ds.name = f'preflight/{r.name}'
            ds.message = r.message
            ds.hardware_id = 'nova-sm3'
            ds.values = [KeyValue(key='critical', value=str(r.critical))]
            arr.status.append(ds)
        self.status_pub.publish(arr)

        # Overall pass = every CRITICAL check is OK (warn does not block).
        critical_fails = [
            r for r in results
            if r.critical and r.status != CheckStatus.OK
        ]
        response.success = not critical_fails
        if response.success:
            response.message = (
                f'preflight PASS — {len(results)} check(s), all critical OK')
        else:
            names = ', '.join(r.name for r in critical_fails)
            response.message = (
                f'preflight FAIL — critical: [{names}]; '
                f'see ~/status topic for details')
        self.get_logger().info(f'>>> {response.message}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = PreflightNode()
    # MultiThreadedExecutor required so each check's spin doesn't
    # deadlock the service callback (see ReentrantCallbackGroup above).
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
