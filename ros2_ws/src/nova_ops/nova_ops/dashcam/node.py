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
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus

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
                'ros2 bag + MCAP storage not available; dashcam will not '
                'record. Install:  sudo apt install ros-humble-rosbag2-'
                'storage-mcap')
        else:
            self.recorder.start()
            # Verify the recorder actually stayed up (fast-fail catch).
            self.create_timer(1.0, self._verify_recorder_once)
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

        # Subscriptions: edge-driven safety topics.
        # VOLATILE to match micro-ROS publisher defaults. TRANSIENT_LOCAL
        # would QoS-mismatch and never receive — see preflight/checks/estop.py
        # for the long version.
        edge_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Bool, '/estop',
                                  self._on_estop, edge_qos)
        self.create_subscription(Int32, '/safety_state',
                                  self._on_safety_state, edge_qos)
        self.create_subscription(Bool, '/battery_low',
                                  self._on_battery_low, edge_qos)
        # /diagnostics ERROR also triggers a freeze (per spec).
        # DiagnosticArray defaults to a 10-depth volatile QoS for the
        # standard aggregator; matching here.
        self.create_subscription(DiagnosticArray, '/diagnostics',
                                  self._on_diagnostics, 10)

        # Service for manual freeze
        self.create_service(Trigger, '~/freeze', self._on_freeze)

        # Per-trigger-source debounce — don't fire multiple incidents
        # from the SAME source within debounce_sec, but a different
        # source firing during that window still triggers its own
        # incident (we want both reasons captured).
        self._last_incident_ns: dict = {}
        self._debounce_ns = 5 * 1_000_000_000  # 5 s

        self.get_logger().info(
            f'dashcam node up. incidents -> {incident_dir}. '
            f'manual freeze: ros2 service call /dashcam/freeze')

    # ------- Recorder health -------

    _verified_recorder = False

    def _verify_recorder_once(self):
        if self._verified_recorder:
            return
        self._verified_recorder = True
        if not self.recorder.healthy():
            self.get_logger().error(
                'recorder subprocess exited within 1 s — likely MCAP '
                'storage plugin missing or topic list rejected. Install:  '
                'sudo apt install ros-humble-rosbag2-storage-mcap')

    # ------- Triggers -------

    def _maybe_freeze(self, trigger: str, detail: str) -> None:
        now = self.get_clock().now().nanoseconds
        last = self._last_incident_ns.get(trigger, 0)
        if now - last < self._debounce_ns:
            self.get_logger().info(
                f'incident trigger {trigger!r} suppressed (per-source debounce)')
            return
        self._last_incident_ns[trigger] = now
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

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        for st in msg.status:
            if st.level == DiagnosticStatus.ERROR:
                self._maybe_freeze(
                    f'diagnostics:{st.name}',
                    f'{st.name}: {st.message}')
                return  # one trigger per array

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
        # Don't stop the recorder — let it keep writing the current bag.
        # The COPY of the rolling buffer may include a final bag that's
        # still being written (i.e., truncated at copy time). That's
        # acceptable: the trigger time itself is captured in the older
        # complete bags; the current bag at trigger gets cut off after
        # the trigger by however long the copytree takes (~hundreds of ms
        # for 2 GB local copy). We mark this in metadata.
        #
        # Pause the janitor first so it doesn't delete out from under us.
        self.janitor.stop()
        try:
            out = write_bundle(
                bag_root=self.bag_dir,
                incident_root=self.incident_dir,
                trigger=trigger,
                extra_metadata={
                    'detail': detail,
                    'recorder_running_during_copy': self.recorder.running,
                },
            )
            self.get_logger().info(f'incident bundle written: {out}')
            return out
        finally:
            # Resume janitor
            try:
                self.janitor.start()
            except Exception as e:
                self.get_logger().error(f'janitor restart failed: {e}')

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
