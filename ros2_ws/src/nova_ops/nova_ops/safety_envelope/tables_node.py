"""Publish the firmware protection tables to the Teensy (#185).

The Teensy holds two tables it cannot compute itself: the per-joint raw ROM
window (`joint_limits`) and the posture-aware hfe backstop (`hfe_envelope`).
Both boot WIDE OPEN and stay that way until the host sends them. Nothing sent
them — `build_joint_limits_data` and `build_hfe_envelope_data` had no callers
outside tests — so every firmware-side protection this project has built was
inert on the robot, leaving the Jetson-side wrapper as the only layer.

THREE THINGS HERE ARE DELIBERATE AND NOT OBVIOUS.

1. IT RE-PUBLISHES, IT DOES NOT LATCH. The intuitive design is a TRANSIENT_LOCAL
   publisher that late joiners pick up. That silently fails: the firmware
   subscribes with rclc_subscription_init_default, i.e. RELIABLE + VOLATILE, and
   a VOLATILE subscriber receives no historical samples. Publisher and
   subscriber still MATCH, so it looks wired up — the table just never arrives
   if the Teensy was not listening at that instant. preflight/checks/estop.py
   already records the underlying hazard ("micro-ROS ... patchy TRANSIENT_LOCAL
   support on Humble"), and main.cpp says the consequence outright: "RAM-only:
   host re-publishes on reconnect". So this re-sends on a timer. The payloads
   are 96 B and ~1.5 kB; at 0.2 Hz that is noise.

2. THE TABLES ARE BUILT ONCE, AT STARTUP. Re-reading the calibration file on
   every tick would let a mid-run edit change the joint limits underneath a
   moving robot. A new homing run needs a restart of this node, which is a
   visible act. The tables are bytes after that, and re-publishing identical
   bytes is idempotent in the firmware.

3. IT PUBLISHES ITS OWN STATE, because arming is not a boolean. A PARTIAL
   calibration still yields a useful per-joint table — every homed joint gets
   its real window — and the firmware accepts it exactly like a complete one,
   bumping the same counter. So "the firmware accepted a table" does not mean
   "every joint is protected". `firmware_tables_state` carries what was
   actually sent, so a partially-armed robot cannot read as armed (#187).
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import Float32MultiArray, String

from .calibration_io import DEFAULT_CALIBRATION_PATH, read_calibration
from .firmware_limits import build_firmware_tables, calibration_state


class FirmwareTablesNode(Node):
    def __init__(self):
        super().__init__("firmware_tables")
        self.declare_parameter("calibration_path", DEFAULT_CALIBRATION_PATH)
        self.declare_parameter("republish_period_s", 5.0)

        # Match the micro-ROS subscriber exactly: RELIABLE + VOLATILE. See (1).
        to_teensy = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        # The status topic is consumed by host nodes (preflight), not the
        # Teensy, so latching is both safe and useful here.
        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._limits_pub = self.create_publisher(
            Float32MultiArray, "joint_limits", to_teensy
        )
        self._env_pub = self.create_publisher(
            Float32MultiArray, "hfe_envelope", to_teensy
        )
        self._state_pub = self.create_publisher(
            String, "firmware_tables_state", latched
        )

        path = self.get_parameter("calibration_path").value
        calib = {}
        try:
            calib = read_calibration(path)
        except Exception as exc:  # noqa: BLE001
            # A malformed artifact must not be interpreted. Publishing nothing
            # keeps the robot on the firmware's wide-open boot table, which is
            # the honest state; publishing a guess would move the guard and the
            # command together.
            self.get_logger().error(
                f"calibration at {path} is unreadable: {exc}. "
                f"NO firmware tables will be published — the Teensy stays "
                f"wide open. Fix the file and restart this node."
            )

        self._limits, self._env, self._state = build_firmware_tables(calib)
        _, missing = calibration_state(calib)
        self._missing = missing
        self._announce(path)

        period = float(self.get_parameter("republish_period_s").value)
        self.create_timer(period, self._publish)
        self._publish()  # do not wait a period

    def _announce(self, path: str) -> None:
        if self._state == "uncalibrated":
            self.get_logger().warn(
                f"no usable calibration at {path}: the Teensy keeps its "
                f"wide-open boot table (0..4095, posture backstop OFF). This "
                f"is expected before homing and NOT safe to drive on."
            )
        elif self._state == "partial":
            self.get_logger().warn(
                f"PARTIAL calibration: bus IDs {self._missing} are not homed. "
                f"Publishing the per-joint table anyway — the homed joints get "
                f"real windows — but those IDs stay wide open, and the posture "
                f"backstop is WITHHELD entirely (it needs both joints of a leg "
                f"to bound that leg at all)."
            )
        else:
            self.get_logger().info(
                "calibration complete: publishing per-joint limits + posture "
                "envelope; re-publishing so an agent restart re-arms."
            )

    def _publish(self) -> None:
        if self._limits is not None:
            self._limits_pub.publish(Float32MultiArray(data=self._limits))
        if self._env is not None:
            self._env_pub.publish(Float32MultiArray(data=self._env))
        self._state_pub.publish(
            String(data=f"{self._state};missing={sorted(self._missing)}")
        )


def main(args=None):
    rclpy.init(args=args)
    node = FirmwareTablesNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
