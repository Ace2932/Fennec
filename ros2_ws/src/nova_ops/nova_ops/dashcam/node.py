"""Dashcam node — always-on MCAP rosbag with circular retention + incident
freeze on safety triggers.

Subscriptions:
  /estop          (Bool, edge)    — engaged -> trigger incident bundle
  /safety_state   (Int32, edge)   — non-zero -> trigger incident bundle
  /battery_low    (Bool, edge)    — engaged -> trigger incident bundle

Services:
  ~/freeze (std_srvs/Trigger) — manual incident bundle freeze

Parameters:
  bag_dir         (str)   default ~/.nova/dashcam/buffer
  incident_dir    (str)   default /var/log/nova/incidents
  retention_mb    (int)   default 2048 (2 GB rolling buffer)
  max_bag_seconds (int)   default 60
  topics          (str[]) default = topics.V1_TOPICS

Usage:
  ros2 run nova_ops dashcam_node
  ros2 launch nova_ops dashcam.launch.py
  ros2 service call /dashcam/freeze std_srvs/srv/Trigger    # manual
"""
import os
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, Int32
from std_srvs.srv import Trigger

from .topics import V1_TOPICS
from .recorder import Recorder
from .janitor import Janitor
from .incident import write_bundle, DEFAULT_INCIDENT_ROOT


class DashcamNode(Node):

    def __init__(self):
        super().__init__('dashcam')

        # Declare parameters
        self.declare_parameter(
            'bag_dir',
            str(Path.home() / '.nova' / 'dashcam' / 'buffer'))
        self.declare_parameter('incident_dir', str(DEFAULT_INCIDENT_ROOT))
        self.declare_parameter('retention_mb', 2048)
        self.declare_parameter('max_bag_seconds', 60)
        self.declare_parameter('topics', V1_TOPICS)

        bag_dir = Path(self.get_parameter('bag_dir').value)
        incident_dir = Path(self.get_parameter('incident_dir').value)
        retention_bytes = int(
            self.get_parameter('retention_mb').value) * 1024 * 1024
        max_bag_seconds = int(self.get_parameter('max_bag_seconds').value)
        topics = list(self.get_parameter('topics').value)

        # Recorder
        self.recorder = Recorder(
            out_dir=bag_dir, topics=topics,
            max_bag_duration=max_bag_seconds)
        if not Recorder.available():
            self.get_logger().error(
                'ros2 bag CLI not on PATH; dashcam will not record')
        else:
            self.recorder.start()
            self.get_logger().info(
                f'dashcam recorder started: {len(topics)} topic(s) -> {bag_dir}')

        # Janitor
        self.janitor = Janitor(
            root=bag_dir,
            retention_bytes=retention_bytes,
            log=lambda m: self.get_logger().info(m),
        )
        self.janitor.start()

        self.incident_dir = incident_dir
        self.bag_dir = bag_dir

        # Subscriptions: edge-driven safety topics
        edge_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(Bool, '/estop',
                                  self._on_estop, edge_qos)
        self.create_subscription(Int32, '/safety_state',
                                  self._on_safety_state, edge_qos)
        self.create_subscription(Bool, '/battery_low',
                                  self._on_battery_low, edge_qos)

        # Service for manual freeze
        self.create_service(Trigger, '~/freeze', self._on_freeze)

        # Debounce — don't fire multiple incidents on the same fault
        # within debounce_sec.
        self._last_incident_ns = 0
        self._debounce_ns = 5 * 1_000_000_000  # 5 s

        self.get_logger().info(
            f'dashcam node up. incidents -> {incident_dir}. '
            f'manual freeze: ros2 service call /dashcam/freeze')

    # ------- Triggers -------

    def _maybe_freeze(self, trigger: str, detail: str) -> None:
        now = self.get_clock().now().nanoseconds
        if now - self._last_incident_ns < self._debounce_ns:
            self.get_logger().info(
                f'incident trigger {trigger!r} suppressed (debounce)')
            return
        self._last_incident_ns = now
        self.get_logger().warn(f'FREEZE on {trigger}: {detail}')
        self._freeze_now(trigger=trigger, detail=detail)

    def _on_estop(self, msg: Bool) -> None:
        if msg.data:
            self._maybe_freeze('estop', 'E-stop engaged')

    def _on_safety_state(self, msg: Int32) -> None:
        if msg.data != 0:
            names = {1: 'ESTOP_LATCHED', 2: 'BATTERY_LOW_LATCHED',
                     3: 'FAULT_OTHER'}
            self._maybe_freeze(
                'safety_state',
                f'safety_state={msg.data} ({names.get(msg.data, "?")})')

    def _on_battery_low(self, msg: Bool) -> None:
        if msg.data:
            self._maybe_freeze(
                'battery_low',
                'battery comparator latched (≤ 13.0 V)')

    def _on_freeze(self, request, response):
        try:
            out = self._freeze_now(trigger='manual',
                                   detail='manual via service')
            response.success = True
            response.message = f'incident bundle -> {out}'
        except Exception as e:
            response.success = False
            response.message = f'freeze failed: {type(e).__name__}: {e}'
            self.get_logger().error(response.message)
        return response

    # ------- Freeze impl -------

    def _freeze_now(self, trigger: str, detail: str) -> Path:
        # Stop the recorder so the active bag is flushed and copyable.
        # The recorder restarts immediately after, beginning a new rolling
        # window for any subsequent triggers.
        self.get_logger().info('stopping recorder for incident copy...')
        self.recorder.stop()
        try:
            out = write_bundle(
                bag_root=self.bag_dir,
                incident_root=self.incident_dir,
                trigger=trigger,
                extra_metadata={'detail': detail},
            )
            self.get_logger().info(f'incident bundle written: {out}')
            return out
        finally:
            # Restart recorder
            try:
                self.recorder.start()
                self.get_logger().info('recorder restarted')
            except Exception as e:
                self.get_logger().error(f'recorder restart failed: {e}')

    # ------- Shutdown -------

    def destroy_node(self):
        try:
            self.janitor.stop()
        except Exception:
            pass
        try:
            self.recorder.stop()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DashcamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
