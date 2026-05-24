"""Preflight CLI wrapper.

Calls the /preflight/run service, pretty-prints per-check breakdown to
stdout, exits non-zero on fail (so bringup launchers can gate on it).

Usage:
    ros2 run nova_ops preflight
    ros2 run nova_ops preflight --quick    # (future: skip slow checks)
"""
import argparse
import sys

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus


# ANSI color helpers
_RESET = '\033[0m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'
_RED = '\033[31m'
_GREY = '\033[90m'


def _level_label(level: int) -> str:
    if level == DiagnosticStatus.OK:
        return f'{_GREEN}OK   {_RESET}'
    if level == DiagnosticStatus.WARN:
        return f'{_YELLOW}WARN {_RESET}'
    if level == DiagnosticStatus.ERROR:
        return f'{_RED}FAIL {_RESET}'
    if level == DiagnosticStatus.STALE:
        return f'{_GREY}STALE{_RESET}'
    return f'?{level}'


def _print_status(arr: DiagnosticArray) -> None:
    print('Preflight breakdown:')
    for st in arr.status:
        name = st.name.removeprefix('preflight/')
        print(f'  [{_level_label(st.level)}] {name:14s}  {st.message}')


class _CliNode(Node):
    def __init__(self):
        super().__init__('preflight_cli')
        self.client = self.create_client(Trigger, '/preflight/run')
        self.latest_status = None
        self.create_subscription(
            DiagnosticArray, '/preflight/status',
            self._on_status, 10)

    def _on_status(self, msg):
        self.latest_status = msg


def main():
    parser = argparse.ArgumentParser(
        description='Run the NovaSM3 preflight checks and exit non-zero on fail')
    parser.add_argument('--quick', action='store_true',
                        help='skip slow checks (network ping, topic liveness wait)')
    parser.add_argument('--timeout', type=float, default=30.0,
                        help='service-call timeout in seconds (default 30)')
    args = parser.parse_args()
    # NOTE: --quick is reserved for v2 check set; v1 ignores it but accepts the flag.

    rclpy.init()
    node = _CliNode()

    if not node.client.wait_for_service(timeout_sec=3.0):
        print(f'{_RED}preflight service /preflight/run not reachable{_RESET}',
              file=sys.stderr)
        print('  start the node:  ros2 run nova_ops preflight_node',
              file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        return 2

    req = Trigger.Request()
    future = node.client.call_async(req)

    end_ns = node.get_clock().now().nanoseconds + int(args.timeout * 1e9)
    while rclpy.ok() and not future.done():
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.get_clock().now().nanoseconds > end_ns:
            print(f'{_RED}timeout waiting for preflight service response{_RESET}',
                  file=sys.stderr)
            node.destroy_node()
            rclpy.shutdown()
            return 3

    resp = future.result()
    # Spin a bit more so the status topic message arrives
    end_ns = node.get_clock().now().nanoseconds + int(1.5 * 1e9)
    while rclpy.ok() and node.latest_status is None \
            and node.get_clock().now().nanoseconds < end_ns:
        rclpy.spin_once(node, timeout_sec=0.1)

    if node.latest_status is not None:
        _print_status(node.latest_status)
    else:
        print(f'{_GREY}(no /preflight/status received; summary only){_RESET}')

    print()
    if resp.success:
        print(f'{_GREEN}{resp.message}{_RESET}')
        rc = 0
    else:
        print(f'{_RED}{resp.message}{_RESET}')
        rc = 1

    node.destroy_node()
    rclpy.shutdown()
    return rc


if __name__ == '__main__':
    sys.exit(main())
