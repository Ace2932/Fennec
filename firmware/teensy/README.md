# Teensy 4.1 Firmware

## v1 role: BUS MASTER (Pattern B default) + safety monitor

Critical-path Phase 1 deliverable. The Teensy owns the Feetech servo bus in v1 — Jetson sends joint targets over micro-ROS, Teensy translates to bus reads/writes in a bare-metal real-time loop.

### Responsibilities

- **Bus master:** Hardware UART → 74HC125 half-duplex driver → 12-servo Feetech TTL bus at 1 Mbps (drop to 500k / 250k if bus errors emerge during bring-up)
- **Direction control:** GPIO drives 74HC125 OE pins for TX/RX gating on the shared half-duplex line
- **Real-time loop:** 200-500 Hz tick. Read joint states (position, load, temp, voltage), publish `/joint_states`. Apply latest `/joint_commands`. Hard deadline per tick.
- **Safety monitor:**
  - INA226 ×3 I²C reads (leg / hip / Jetson rails; optional 4th on L2 rail) → `/diagnostics`
  - E-stop GPIO sense — when pressed, halts servo commands and publishes E-stop event
  - **Battery low GPIO sense** — 13.0V comparator output → debounce → publish `/battery_low` (Jetson subscribes, runs `systemctl poweroff` for clean SD unmount before the 12.4V hard cutoff fires)
- **micro-ROS client over USB** to Jetson

### Pattern A fallback path

When `JP_BUS_MASTER` solder bridge is flipped to A, the bus is driven by FE-URT-1 (Jetson direct). Teensy stays alive for INA226 + E-stop duties but stops driving the 74HC125. Used for:
- Initial servo ID assignment from workstation (Feetech FD / SCServo SDK Python)
- Debug if Teensy firmware misbehaves
- Post-mortem bus traffic inspection

### Phase 1 acceptance gate (revised — see BOM §12 step 3)

Pattern B guarantees bus-servicing isolation on the Teensy side, not full RTT through Linux. Three criteria:

1. **Mandatory:** Teensy local loop tick jitter **p99 <100 µs** over 60 seconds. This is what bare-metal bus servicing actually buys.
2. **Mandatory:** `/joint_commands` arrival rate **≥99% of 100 Hz target** over 60 seconds. Jetson + uROS healthy, command dropouts <1%.
3. *(Sanity)* End-to-end RTT median **<5 ms**, p99 **<20 ms** — Linux-bounded by USB-CDC + uROS; informational, not pass/fail.

If (1) misses → debug Teensy firmware (DMA vs ISR, UART config, ISR priority). If (2) misses → debug Jetson uROS / USB cable / CPU contention. Pattern A is not a workaround.

## Stack

- **PlatformIO** project (favored over Arduino IDE for dependency management)
- **TeensyDuino** core
- **micro-ROS for Teensy** client library
- **SCServo SDK port** for TeensyDuino (port of the Feetech Python SDK / C++ reference) — or hand-rolled minimal driver targeting STS3215 protocol
- Real-time priority on UART ISRs + DMA-driven TX/RX where possible

## ROS 2 topic contract

> ⚠️ This table is the original plan; the implementation diverged (better). Actual contract:
> `/joint_states` carries raw units (position 0..4095, effort = raw load 0..1000, servo id=i+1);
> telemetry is discrete topics (`/power_rails`, `/servo_voltage`, `/servo_temperature`,
> `/servo_present_mask`, per-class `/servo_err_*`, loop histogram stats) instead of one
> DiagnosticArray; plus `/safety_state` Int32 (latched FSM) alongside the raw `/estop` /
> `/battery_low` edge publishes, and `/safety_clear` sub. `nova_calibration`'s README documents
> the raw-unit convention — treat the code + that README as the contract until this table is
> rewritten.

| Direction | Topic | Type | Rate |
|-----------|-------|------|------|
| Pub | `/joint_states` | `sensor_msgs/JointState` | 100 Hz |
| Pub | `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | 10 Hz (INA226 readings) |
| Pub | `/estop` | `std_msgs/Bool` | event-driven |
| Pub | `/battery_low` | `std_msgs/Bool` | event-driven (13.0V trigger) |
| Sub | `/joint_commands` | `sensor_msgs/JointState` (position field) | 100 Hz target |

## 🔴 TODO before first battery walk (gaps found 2026-06-12 software review)

1. **Command-staleness failsafe (this firmware).** If `/joint_commands` stops arriving
   (USB cable out, Jetson panic, agent crash), the tick loop currently re-broadcasts the
   last target forever — robot frozen mid-step, torque held, until LVC. Add: no command
   for N ms (start: 500 ms) → slew to neutral stand pose → reduce torque; publish a
   `command_stale` flag. The inverse direction is already covered (ISR watchdog resets a
   wedged Teensy; Jetson sees heartbeat drop).
2. **`/battery_low` → poweroff subscriber (nova_ops, not here).** Firmware publishes the
   13.0 V event but nothing on the Jetson subscribes — the documented
   "`systemctl poweroff` before the 12.4 V hard cutoff" node was never implemented.
   Without it the two-stage LVC chain degrades to a hard power yank mid-SD-write.
   Tracked in `ros2_ws/src/nova_ops/README.md`.

## Open questions for firmware phase

- DMA vs ISR for UART TX/RX (DMA preferred for jitter; ISR simpler)
- Per-servo poll interval — round-robin all 12 vs prioritize legs over arm/idle joints
  (current: 1 servo/tick = 16.7 Hz per joint; budget fits 2/tick if closed-loop work
  ever needs faster feedback)
- Failure-mode behavior: lost servo response → retry budget → flag dead in `/joint_states`
- micro-ROS QoS profile — recommended resolution: `/joint_commands` best-effort keep-last-1
  (stale commands are worse than none), safety/state topics reliable

Resolve during firmware bring-up.

---

> **Status (2026-05-23):** Firmware end-to-end on Jetson, 20-topic contract live, **loop p99 = 1 µs** (50× under <100 µs acceptance gate) after IntervalTimer ISR-driven 200 Hz tick replaced polled loop. Recent additions (2026-05-19 → 2026-05-21): safety FSM (E-stop + battery-low latch + `/safety_clear`), full STS3215 telemetry (pos+vel+load + voltage + temp @ 5 Hz), per-joint slew limiter on SYNC_WRITE broadcast, software watchdog (ISR-checked main-loop progress + AIRCR reset on hang), boot-time servo ping sweep populating real `/servo_present_mask`, INA226 → `/power_rails` Float32MultiArray @ 10 Hz, `/firmware_version` + boot self-test for safety GPIOs, categorised bus errors (timeout / bad_frame / servo). CI green on every PR.
>
> **Untested on wire** (skeletons compile-green, behavior unverified): `feetech::Bus` SYNC_WRITE broadcast against real STS3215, INA226 I²C reads against real breakouts, 74HC125 half-duplex driver gating. Phase 1 bench bring-up gate: re-measure `/loop_exec_p99_us` once real bus + I²C are in the hot path (skeleton 1 µs will grow). Live TODO in `firmware/teensy/firmware/README.md`.
