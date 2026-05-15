# Teensy 4.1 Firmware

## v1 role: BUS MASTER (Pattern B default) + safety monitor

Critical-path Phase 1 deliverable. The Teensy owns the Feetech servo bus in v1 — Jetson sends joint targets over micro-ROS, Teensy translates to bus reads/writes in a bare-metal real-time loop.

### Responsibilities

- **Bus master:** Hardware UART → 74HC125 half-duplex driver → 12-servo Feetech TTL bus at 1 Mbps (drop to 500k / 250k if bus errors emerge during bring-up)
- **Direction control:** GPIO drives 74HC125 OE pins for TX/RX gating on the shared half-duplex line
- **Real-time loop:** 200-500 Hz tick. Read joint states (position, load, temp, voltage), publish `/joint_states`. Apply latest `/joint_commands`. Hard deadline per tick.
- **Safety monitor:** INA226 ×3 I²C reads (leg / hip+L2 / Jetson rails) → `/diagnostics`. E-stop GPIO sense — when pressed, halts servo commands and publishes E-stop event.
- **micro-ROS client over USB** to Jetson

### Pattern A fallback path

When `JP_BUS_MASTER` solder bridge is flipped to A, the bus is driven by FE-URT-1 (Jetson direct). Teensy stays alive for INA226 + E-stop duties but stops driving the 74HC125. Used for:
- Initial servo ID assignment from workstation (Feetech FD / SCServo SDK Python)
- Debug if Teensy firmware misbehaves
- Post-mortem bus traffic inspection

### Phase 1 acceptance gate

ROS 2 → Teensy → bus → return **p99 latency <2 ms** at 100 Hz across all 12 servos. Measured via timestamped echo from `/joint_commands` round-trip. Pattern A is not a workaround if this misses — debug Teensy firmware.

## Stack

- **PlatformIO** project (favored over Arduino IDE for dependency management)
- **TeensyDuino** core
- **micro-ROS for Teensy** client library
- **SCServo SDK port** for TeensyDuino (port of the Feetech Python SDK / C++ reference) — or hand-rolled minimal driver targeting STS3215 protocol
- Real-time priority on UART ISRs + DMA-driven TX/RX where possible

## ROS 2 topic contract

| Direction | Topic | Type | Rate |
|-----------|-------|------|------|
| Pub | `/joint_states` | `sensor_msgs/JointState` | 100 Hz |
| Pub | `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | 10 Hz (INA226 readings) |
| Pub | `/estop` | `std_msgs/Bool` | event-driven |
| Sub | `/joint_commands` | `sensor_msgs/JointState` (position field) | 100 Hz target |

## Open questions for firmware phase

- DMA vs ISR for UART TX/RX (DMA preferred for jitter; ISR simpler)
- Per-servo poll interval — round-robin all 12 vs prioritize legs over arm/idle joints
- Failure-mode behavior: lost servo response → retry budget → flag dead in `/joint_states`
- micro-ROS QoS profile for `/joint_commands` (reliable vs best-effort)

Resolve during firmware bring-up.

---

> **Status:** v1 active path. Critical-path Phase 1 deliverable. No firmware code committed yet — design spec only.
