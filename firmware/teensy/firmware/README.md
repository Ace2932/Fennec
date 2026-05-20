# Nova-SM3 LE Teensy firmware — skeleton (micro-ROS enabled)

PlatformIO project for the Teensy 4.1 bus master (Pattern B per BOM v3.3).

## Status — 2026-05-19

End-to-end micro-ROS round-trip green on Jetson:

- Teensy → XRCE-DDS over USB-CDC → `micro_ros_agent` → ROS 2 Humble
- 200 Hz tick, p99 = 5050 µs (= 50 µs late at 99th pct, **2× under the <100 µs gate**)
- Topic contract live: 7 pubs + 1 sub. Callback round-trip verified.

Bus servicing + INA226 reads are still stubs — see TODO list below.

## Where to build

**Jetson only.** Mac builds of `micro_ros_platformio` fail on Python 3.14 + missing ROS dev libs. The Jetson (Python 3.10 + Humble) is the supported build host. See `docs/setup-jetson.md` §14 for the one-time bring-up recipe.

The Mac compile-green path stays available — comment out the `NOVA_USE_MICRO_ROS` flag + `lib_deps` line in `platformio.ini` to reproduce Arduino-only builds.

## Build & flash (Jetson)

```bash
cd ~/code/LE_NOVA/firmware/teensy/firmware
pio run                  # build
pkill -f micro_ros_agent # free /dev/ttyACM0
pio run -t upload        # flash
# then restart the agent — see docs/setup-jetson.md §14.7
```

## Build size baseline (2026-05-19, micro-ROS + topic contract)

- FLASH: 111 KB code + 16 KB data + 8 KB headers → 7.99 MB free of 7.75 MB total (1.7% used)
- RAM1: 38 KB vars + 109 KB code + 22 KB padding → 354 KB free
- RAM2: 12 KB → 512 KB free

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

## ROS 2 topics (current implementation)

| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/heartbeat` | `std_msgs/Int32` | 1 Hz | increments, liveness signal |
| Pub | `/loop_max_us` | `std_msgs/Int32` | 1 Hz | worst tick period over last 1 s |
| Pub | `/loop_p99_us` | `std_msgs/Int32` | 1 Hz | p99 tick period over last 1 s (100 µs buckets) |
| Pub | `/joint_states` | `sensor_msgs/JointState` | 200 Hz | 12 joints, currently zeros |
| Pub | `/estop` | `std_msgs/Bool` | edge-change | published only on state transition |
| Pub | `/battery_low` | `std_msgs/Bool` | edge-change | published only on state transition |
| Pub | `/joint_cmd_rx_count` | `std_msgs/Int32` | 1 Hz | callback-fire counter, lets the host see cmds arrived |
| Sub | `/joint_commands` | `sensor_msgs/JointState` | 100 Hz target | no-op callback latches positions to `latched_cmd_position[]` |

JointState `name[]` and `frame_id` are intentionally empty — URDF joint-name binding lands when the gait controller is on the Jetson.

## Stubs to fill in (TODO list in source)

- `service_bus_stub()` — port SCServo SDK to TeensyDuino, implement read + write to STS3215 via Serial2 + 74HC125 direction control
- `read_ina226_stub()` — integrate Rob Tillaart's INA226 library, read 3 rails, publish DiagnosticArray at 10 Hz
- `latched_cmd_position[]` consumer — hand off to the bus writer once SDK is in
- Real GPIO inputs for `/estop` and `/battery_low` — currently the pins are read but no hardware is wired to them
- DiagnosticArray pub
- Acceptance gate verification (60 s window, p99 <100 µs) once real bus + I²C traffic added

## Build flags (from `platformio.ini`)

| Flag | Default | Purpose |
|------|---------|---------|
| `NOVA_BUS_BAUD` | 1 000 000 | Feetech bus baud. Drop to 500 000 / 250 000 if bus errors emerge. |
| `NOVA_LOOP_HZ` | 200 | Real-time tick rate. Bumpable to 500 once SDK port is solid. |
| `NOVA_USE_MICRO_ROS` | (defined) | Enables micro-ROS transport + pubs/subs. Comment out for Arduino-only Mac builds. |

## Smoke test from host

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/local_setup.bash
ros2 topic echo /heartbeat                    # 1 Hz tick
ros2 topic echo /loop_p99_us --once           # ~5050 us baseline
ros2 topic pub --once /joint_commands sensor_msgs/msg/JointState \
  '{position: [0.1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}'
ros2 topic echo /joint_cmd_rx_count --once    # increments per cmd
```
