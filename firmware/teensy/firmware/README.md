# Nova-SM3 LE Teensy firmware — skeleton (micro-ROS enabled)

PlatformIO project for the Teensy 4.1 bus master (Pattern B per BOM v3.3).

## Status — 2026-05-20

End-to-end micro-ROS round-trip green on Jetson; 20-topic contract implemented; bus + INA226 driver paths code-complete (compile-green skeletons, untested on wire).

- Teensy → XRCE-DDS over USB-CDC → `micro_ros_agent` → ROS 2 Humble
- IntervalTimer ISR-driven 200 Hz tick. Skeleton-only p99 = 1 µs (=50× under the <100 µs gate). Real numbers will grow once a servo is on the bus and reads stop timing out — `/loop_exec_p99_us` is the topic to watch.
- 18 publishers + 2 subscribers wired (see "ROS 2 topics" below). Heartbeat → joint-state-from-bus → joint-command-to-bus loop is closed in code.
- Safety FSM with E-stop + battery-low latch, `/safety_clear` reset path, boot self-test seeding.
- GitHub Actions CI green on every PR (Arduino-only env).

Awaiting bench hardware: 74HC125 driver board, real STS3215 on the TTL bus, INA226 breakouts on the 7.5 V / 12 V / 12 V rails.

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
| Bus UART RX | 0 (Serial1 RX) | from SN74LVC125A RX gate |
| Bus UART TX | 1 (Serial1 TX) | into SN74LVC125A TX gate |
| Bus driver TX OE̅ | 2 | **active-LOW**: LOW = enable TX onto bus |
| Bus driver RX OE̅ | 3 | **active-LOW**: LOW = enable RX from bus |
| I²C SDA | 18 (Wire) | INA226 ×3 (×4 with L2) |
| I²C SCL | 19 (Wire) | INA226 ×3 (×4 with L2) |
| E-stop NC sense | 5 | INPUT_PULLUP, NC contact (J21). Idle (closed) = LOW; pressed OR wire-break/unplug = HIGH (fail-safe) |
| Battery-low (13.0V comparator) | 4 | INPUT_PULLDOWN, HIGH = below 13.0V |
| Heartbeat LED | 13 (LED_BUILTIN) | 1 Hz toggle |

Pin numbers reconciled to the `nova_pcb_v6_logic` board routing 2026-06-14 and are the
source of truth (match `src/main.cpp` lines 81–92). The bus runs on **Serial1 (pins 0/1)** as
routed on v6 — half-duplex direction is handled by the SN74LVC125A gates via the OE̅ pins above,
not by relying on the UART. (An earlier draft used Serial2 7/8; that is obsolete.)

## ROS 2 topics (current implementation)

Group by purpose. All `std_msgs/Int32` counters are monotonic from boot unless noted.

### Liveness + identity
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/heartbeat` | `Int32` | 1 Hz | increments each beat |
| Pub | `/firmware_version` | `String` | 0.1 Hz | `"nova-teensy <git-sha> loop=<hz>Hz"` |

### Loop-quality telemetry (ISR-driven tick)
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/loop_max_us` | `Int32` | 1 Hz | max ISR-to-handler response latency (window) |
| Pub | `/loop_p99_us` | `Int32` | 1 Hz | p99 of response latency, 2 µs buckets 0..128 µs |
| Pub | `/loop_exec_max_us` | `Int32` | 1 Hz | max handler-body exec time (window) |
| Pub | `/loop_exec_p99_us` | `Int32` | 1 Hz | p99 of handler exec, 10 µs buckets 0..640 µs |
| Pub | `/tick_missed_count` | `Int32` | 1 Hz | ISR fires that found prev tick still pending (=0 in healthy state) |

### Joint I/O
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/joint_states` | `sensor_msgs/JointState` | 200 Hz | 12 joints — raw position, velocity, load from STS3215 round-robin (~17 Hz per joint) |
| Sub | `/joint_commands` | `sensor_msgs/JointState` | 100 Hz target | latches into `latched_cmd_position[]`; broadcast to bus at 40 Hz via SYNC_WRITE when `safety_state == NORMAL` |
| Pub | `/joint_cmd_rx_count` | `Int32` | 1 Hz | sub-callback fire counter (host-side ack) |
| Pub | `/servo_present_mask` | `Int32` | 1 Hz | bit i = joint i has answered at least once since boot |

### Bus diagnostics
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/servo_read_err_count` | `Int32` | 1 Hz | aggregate of the three categorised errors below |
| Pub | `/servo_err_timeout` | `Int32` | 1 Hz | no servo response inside the read window |
| Pub | `/servo_err_bad_frame` | `Int32` | 1 Hz | checksum / header garbled — bus-integrity signal |
| Pub | `/servo_err_servo` | `Int32` | 1 Hz | servo responded with non-zero error byte (overheat/overload/voltage) |

### Safety
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/estop` | `Bool` | edge-change | raw GPIO (LOW = pressed) — direct view of source |
| Pub | `/battery_low` | `Bool` | edge-change | raw GPIO (HIGH = below 13.0 V) |
| Pub | `/safety_state` | `Int32` | edge-change | latched FSM: 0=NORMAL, 1=ESTOP_LATCHED, 2=BATTERY_LOW_LATCHED, 3=FAULT_OTHER |
| Sub | `/safety_clear` | `Bool` | event | `data=true` requests latch clear; FSM refuses while underlying signals still asserted |

### Protection tables pushed from the host (added to this contract 2026-08-10)

The host owns the numbers; the Teensy enforces them. Each table has a matching
`*_rx` counter above so you can prove a pushed table actually landed rather than
assuming it.

⚠️ **QoS is load-bearing here, and it is deliberately NOT latched.** The intuitive
design is a TRANSIENT_LOCAL publisher so a rebooting Teensy picks up the tables on
connect — but micro-ROS TRANSIENT_LOCAL support is patchy, so
`nova_ops/safety_envelope/tables_node.py` instead uses **RELIABLE + VOLATILE**
(matching `rclc_subscription_init_default` exactly) and **re-publishes every 5 s**
(`republish_period_s`). Do not "improve" this to a latched publisher without
testing a Teensy reboot: the failure mode is silent, and the firmware would run on
its built-in defaults instead of the calibrated tables.

| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Sub | `/joint_limits` | `Float32MultiArray` | re-published every 5 s | per-joint min/max position table. Ack: `/joint_limits_rx` |
| Sub | `/hfe_envelope` | `Float32MultiArray` | re-published every 5 s | posture-aware hfe envelope (a scalar per-joint clamp cannot express a limit that depends on the other two joints). Ack: `/hfe_envelope_rx`; clamps counted on `/hfe_envelope_clamps` |
| Sub | `/limp_pose` | `Float32MultiArray` | re-published every 5 s | the pose the firmware drives to when it limps. Ack: `/limp_pose_rx` |

### Power telemetry
| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/power_rails` | `Float32MultiArray` | 10 Hz | 9 floats: `[leg_v, leg_a, leg_w, hip_v, hip_a, hip_w, jetson_v, jetson_a, jetson_w]` — read by index, no MultiArrayLayout dims populated |
| Pub | `/servo_voltage` | `Float32MultiArray` | 5 Hz | 12 floats, per joint, volts (`PRESENT_VOLTAGE` raw × 0.1). **Added to this table 2026-08-10 — published since the servo-health work landed (`main.cpp:1493`) but never in the contract, so downstream guessed the name.** |
| Pub | `/servo_temperature` | `Float32MultiArray` | 5 Hz | 12 floats, per joint, °C (`REG_PRESENT_TEMPERATURE` 0x3F, u8). Feeds the firmware-local overtemp guard at `NOVA_OVERTEMP_C` 70 °C, which trips limp ahead of the servo's own ~80 °C cutoff (`main.cpp:333`). **Same omission.** |

JointState `name[]` and `frame_id` are intentionally empty — URDF joint-name binding lands when the gait controller is on the Jetson.

### Safety-table acks + envelope + IMU (added to this contract 2026-08-10)

These were **published but undocumented**. Not a paperwork problem:
`nova_ops/dashcam/topics.py` says in its own docstring that it takes topic names from
this README, so a missing row makes downstream GUESS — which is how `/servo_voltage`
and `/servo_temperature` came to be recorded by nothing while the dashcam waited on
invented names. `test_firmware_topic_contract.py` now fails if a publisher is missing here.

| Direction | Topic | Type | Rate | Notes |
|-----------|-------|------|------|-------|
| Pub | `/command_stale` | `Bool` | on-change + 1 Hz refresh | command-watchdog state. Edge-only would blind any subscriber that (re)starts after the edge, hence the re-publish |
| Pub | `/joint_limits_rx` | `Int32` | 1 Hz | count of accepted joint-limit tables — host-side ack that a pushed table landed |
| Pub | `/hfe_envelope_rx` | `Int32` | 1 Hz | same ack for the posture-aware hfe envelope |
| Pub | `/limp_pose_rx` | `Int32` | 1 Hz | same ack for the limp-pose table |
| Pub | `/hfe_envelope_clamps` | `Int32` | 1 Hz | running count of commands the hfe envelope actually clamped — the "is this guard firing" signal |
| Pub | `/imu` | `sensor_msgs/Imu` | **100 Hz**, gated on `imu_ok` | ICM-42688-P. `orientation` carries the `TiltFilter` quaternion (yaw deliberately 0 — proj_grav is yaw-invariant); `angular_velocity` rad/s; `linear_acceleration` m/s². **Rate FIXED 2026-08-10.** It published at 1 Hz because the block sat inside `HEARTBEAT_PERIOD_MS`, while `policy_node` consumes gyro + projected gravity as obs dims 0..5 at `control_hz` 50 — the policy would have seen the same attitude for 50 consecutive ticks. Now its own `IMU_PERIOD_MS` block at 100 Hz (2× control rate). The chip is read at 200 Hz regardless (`poll_imu`, every tick), so every published sample is fresh. Still untested against a real part — the IMU is not owned yet |

## Stubs to fill in (status 2026-05-20)

- ✅ Bus driver — `feetech::Bus` in `feetech_bus.h` handles PING / READ_DATA / WRITE_DATA / SYNC_WRITE with 74HC125 OE control + Serial2 timing. Per-tick round-robin read of 6 bytes (pos+vel+load) from one servo + decimated SYNC_WRITE broadcast of goal positions. **Untested on hardware until 74HC125 + STS3215 on bench.**
- ✅ INA226 — Rob Tillaart's lib via PlatformIO `lib_deps`; round-robin one rail per tick; `/power_rails` Float32MultiArray @ 10 Hz. **Untested until INA226 boards arrive.**
- ✅ `latched_cmd_position[]` consumer — wired through `broadcast_servo_commands()` SYNC_WRITE, gated on `safety_fsm.motion_enabled()`.
- ✅ Edge-change publish for `/estop` and `/battery_low` + latched `/safety_state` FSM with `/safety_clear` reset path.
- ⏳ Voltage + temperature telemetry — `REG_PRESENT_VOLTAGE` (0x3E) + `REG_PRESENT_TEMPERATURE` (0x3F). Add a second 2-byte read in `poll_one_servo()` or a separate sweep tick. Currently unread.
- ⏳ DiagnosticArray proper — `/power_rails` is a fixed-layout Float32MultiArray shortcut. A `diagnostic_msgs/DiagnosticArray` consumer makes `rqt_robot_monitor` work natively.
- ⏳ Acceptance gate verification (60 s window, loop p99 <100 µs) on real bench with real bus + I²C + servos answering. Skeleton baseline (stubs only) measured at 1 µs p99; real numbers grow once bus reads + I²C polls + executor spin are in the hot path.

## Build flags (from `platformio.ini`)

| Flag | Default | Purpose |
|------|---------|---------|
| `NOVA_BUS_BAUD` | 1 000 000 | Feetech bus baud. Drop to 500 000 / 250 000 if bus errors emerge. |
| `NOVA_LOOP_HZ` | 200 | Real-time tick rate. Bumpable to 500 once SDK port is solid. |
| `NOVA_USE_MICRO_ROS` | (defined in `teensy41`, not in `teensy41_ci`) | Enables micro-ROS transport + pubs/subs. |
| `NOVA_INA226_L2` | (undefined) | Opt-in 4th INA226 on the L2 LiDAR rail (0x45). |
| `NOVA_BUILD_GIT_SHA` | auto (`git rev-parse --short HEAD`) | Embedded into `/firmware_version` String. |

### Build envs

- `[env:teensy41]` — production / Jetson build. Includes `micro_ros_platformio` + `NOVA_USE_MICRO_ROS`. Used by `pio run -t upload`.
- `[env:teensy41_ci]` — Arduino-only CI build (used by `.github/workflows/firmware-compile.yml`). No micro-ROS lib pull, finishes in seconds, exercises every non-ROS code path (feetech, INA226, ISR tick, safety FSM, histograms).

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
