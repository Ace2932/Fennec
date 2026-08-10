"""OLED status node — STUB.

⚠️ Note what this is talking to. `setup.py` registers it as
`ros2 run nova_ops oled_status`, so it LOOKS runnable; the Arduino Nano
sketch it writes to does not exist (firmware/arduino-nano/ contains a
README and no source). Running it writes bytes at /dev/ttyUSB0 that
nothing reads. The display itself is wanted but has no bracket yet —
oled_mount is DELETED (#35, 2026-08-10); the display now mounts on oled_tray
(#35, open).

Bridges Jetson ROS 2 topics to the Arduino Nano (USB-serial) which
drives the SSD1331 96×64 OLED + WS2812B LEDs.

Per BOM v3.5 cut (2026-05-24), Arduino Nano's role is reduced to:
  - SSD1331 OLED via SPI (battery, IP, gait state, fault)
  - WS2812B LED strip via 1 GPIO (status colors per
    docs/notes-qol-features.md §8)

This node subscribes to the relevant ROS 2 topics, packs a small
frame, and writes it over /dev/ttyUSB0 to the Nano at 115200 baud.

Topics consumed:
  /battery_low       (Bool)   safety
  /safety_state      (Int32)  0/1/2/3 -> color
  /firmware_version  (String) shown briefly at boot
  /joint_cmd_rx_count (Int32) gait liveness
  /power_rails       (Float32MultiArray) battery V from leg_v slot[0]

Topics published (future):
  /battery_soc       (BatterySoc, custom msg)   if §9 Option B lands

Protocol to Nano (text-line, simplest):
  STATE <0..3>\\n          - sets LED color
  LINE 0 "NOVA v3.4 OK"\\n  - 4 line slots, 16-char max
  LINE 1 "BAT 87% 14.2V"\\n
  ...

Status: NOT YET IMPLEMENTED. Stub registers the entry point + topic
subscriptions so the package builds; serial write is a no-op until
the Nano sketch exists.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, Int32, String, Float32MultiArray


class OledStatusNode(Node):

    def __init__(self):
        super().__init__('oled_status')

        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('serial_baud', 115200)
        self.declare_parameter('refresh_hz', 1.0)

        self._serial_port = self.get_parameter('serial_port').value
        self._serial_baud = int(self.get_parameter('serial_baud').value)

        # State cache populated by subscribers
        self.battery_low = None
        self.safety_state = None
        self.firmware_version = None
        self.cmd_rx_count = None
        self.leg_voltage = None

        edge_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Bool, '/battery_low',
                                  lambda m: setattr(self, 'battery_low', m.data),
                                  edge_qos)
        self.create_subscription(Int32, '/safety_state',
                                  lambda m: setattr(self, 'safety_state', m.data),
                                  edge_qos)
        self.create_subscription(String, '/firmware_version',
                                  lambda m: setattr(self, 'firmware_version', m.data),
                                  10)
        self.create_subscription(Int32, '/joint_cmd_rx_count',
                                  lambda m: setattr(self, 'cmd_rx_count', m.data),
                                  10)
        self.create_subscription(Float32MultiArray, '/power_rails',
                                  self._on_power, 10)

        self.create_timer(1.0 / float(self.get_parameter('refresh_hz').value),
                          self._on_tick)

        self.get_logger().info(
            f'oled_status STUB up. Serial bridge to Arduino Nano on '
            f'{self._serial_port} @ {self._serial_baud} baud (not yet wired). '
            f'BOM v3.5 role: drives SSD1331 + WS2812B.')

    def _on_power(self, msg):
        # /power_rails layout: [leg_v, leg_a, leg_w, hip_v, hip_a, hip_w, ...]
        if len(msg.data) >= 1:
            self.leg_voltage = msg.data[0]

    def _on_tick(self):
        # Build the OLED frame (4 lines). Not yet wired to serial.
        frame = self._build_frame()
        # TODO: open self._serial_port (pyserial) and write frame
        # For now, log every 10 ticks at DEBUG level only.
        pass

    def _build_frame(self) -> list:
        state_names = {0: 'OK', 1: 'ESTOP', 2: 'BATT_LOW', 3: 'FAULT'}
        state_label = state_names.get(self.safety_state or 0, '?')

        # Line 0: header + state
        line0 = f'NOVA {state_label[:10]}'
        # Line 1: battery
        if self.leg_voltage is not None:
            line1 = f'BAT {self.leg_voltage:.1f}V'
        else:
            line1 = 'BAT ---'
        # Line 2: IP (TODO: read from os)
        line2 = 'IP 192.168.1.2'
        # Line 3: gait liveness
        if self.cmd_rx_count is not None:
            line3 = f'CMD #{self.cmd_rx_count}'
        else:
            line3 = 'CMD ---'

        return [line0[:16], line1[:16], line2[:16], line3[:16]]


def main(args=None):
    rclpy.init(args=args)
    node = OledStatusNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
