# Nova-SM3 LE Teensy firmware — skeleton

PlatformIO project for the Teensy 4.1 bus master (Pattern B per BOM v3.3).

## Compile-green target

```bash
cd firmware/teensy/firmware
pio run
```

On first build, PlatformIO will fetch `micro_ros_platformio` (~2-3 min). Subsequent builds are fast.

## Upload

Plug Teensy 4.1 USB-B into Mac (or Jetson). Then:

```bash
pio run -t upload
pio device monitor -b 115200
```

Upload uses `teensy-cli` (bundled with PlatformIO's teensy platform).

## Wiring (matches `src/main.cpp` pin constants)

| Function | Teensy pin | Notes |
|----------|-----------|-------|
| Bus UART RX | 7 (Serial2 RX) | from 74HC125 RX gate |
| Bus UART TX | 8 (Serial2 TX) | into 74HC125 TX gate |
| 74HC125 TX OE | 6 | HIGH = drive TX onto bus |
| 74HC125 RX OE | 5 | LOW = enable RX from bus |
| I²C SDA | 18 (Wire) | INA226 ×3 |
| I²C SCL | 19 (Wire) | INA226 ×3 |
| E-stop NC sense | 2 | INPUT_PULLUP, LOW = pressed |
| Battery-low (13.0V comparator) | 3 | INPUT_PULLDOWN, HIGH = below 13.0V |
| Heartbeat LED | 13 (LED_BUILTIN) | 1 Hz toggle |

Avoid Teensy `Serial1` (pins 0/1) for the bus — known half-duplex issues per Teensy forum. We use `Serial2` (pins 7/8).

## ROS 2 topics (matches `firmware/teensy/README.md` contract)

| Direction | Topic | Type | Rate |
|-----------|-------|------|------|
| Pub | `/joint_states` | `sensor_msgs/JointState` | 100 Hz target (currently stub) |
| Pub | `/estop` | `std_msgs/Bool` | event-driven (currently 1 Hz heartbeat) |
| Pub | `/battery_low` | `std_msgs/Bool` | event-driven (currently 1 Hz heartbeat) |
| Pub | `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | 10 Hz (currently stub) |
| Sub | `/joint_commands` | `sensor_msgs/JointState` | 100 Hz target |

## Stubs to fill in (TODO list in source)

- `service_bus_stub()` — port SCServo SDK to TeensyDuino, implement read + write to STS3215 via Serial2 + 74HC125 direction control
- `read_ina226_stub()` — integrate Rob Tillaart's INA226 library, read 3 rails, publish DiagnosticArray at 10 Hz
- Edge-trigger logic for `/estop` and `/battery_low` (currently published every NOVA_LOOP_HZ ticks)
- `/joint_commands` callback — buffer target positions, hand off to bus writer
- Acceptance gate verification: Teensy loop tick jitter p99 <100 µs over 60 s

## Build flags (from `platformio.ini`)

| Flag | Default | Purpose |
|------|---------|---------|
| `NOVA_BUS_BAUD` | 1 000 000 | Feetech bus baud. Drop to 500 000 / 250 000 if bus errors emerge. |
| `NOVA_LOOP_HZ` | 200 | Real-time tick rate. Bumpable to 500 once SDK port is solid. |
| `NOVA_USB_TRANSPORT` | (defined) | micro-ROS over USB-CDC. |

## Micro-ROS agent (on Jetson side)

For runtime testing, run a micro-ROS agent on the Jetson listening for USB-CDC:

```bash
# On Jetson — separate install task
sudo apt install -y ros-humble-micro-ros-agent     # if available
# OR build from source: github.com/micro-ROS/micro_ros_setup
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200
```

Teensy will appear as `/dev/ttyACM*` on the Jetson once plugged in.

> **Status:** Skeleton scaffolded 2026-05-19. Compile-green target. Real bus traffic + SDK port pending.
