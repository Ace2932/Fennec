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

## ✅ Resolved 2026-06-12 (gaps from software review — both shipped same day)

1. **Command-staleness failsafe — IMPLEMENTED.** After `NOVA_CMD_STALE_TIMEOUT_US`
   (default 500 ms) without a fresh `/joint_commands`, the latched targets are overwritten
   with the latest MEASURED positions (freeze-in-place; the slew limiter makes it a gentle
   decel) and `/command_stale` (Bool, edge-published) goes true. Recovery is automatic on
   the next fresh command. Deviation from the original spec: freeze-at-measured instead of
   "slew to neutral stand" — calibration offsets live on the Jetson, so raw stand-pose
   values are meaningless at this layer.
2. **Boot-broadcast gate — bonus bug found during implementation.** `broadcast_servo_commands()`
   used to SYNC_WRITE the all-zeros latched array at 40 Hz from power-on — on real hardware
   that slams all 12 joints to raw position 0 before the first command. Now gated on
   `joint_cmd_rx_count > 0`: the bus is never written until the host has commanded at
   least once.
3. **`/battery_low` → poweroff — IMPLEMENTED in nova_ops** (`battery_shutdown_node`,
   §10 in `ros2_ws/src/nova_ops/README.md`; sudoers prereq in `docs/setup-jetson.md` §15).

Adversarial review, same day — three more, all fixed:

4. **74HC125 OE polarity inverted** (`feetech_bus.h set_tx/set_rx`). The '125's
   output-enables are ACTIVE-LOW; firmware drove both HIGH for TX / both LOW for RX.
   Net effect on real hardware: TX buffer tri-stated during transmit (bus never driven)
   AND the idle-high UART driving the bus through the TX gate during receive (contention
   with every servo response). Verified against the logic-board netlist (U7 gate1
   OE̅=OE_TX, gate2 OE̅=OE_RX, no inverters) and corrected. **Bench-verify with a scope
   on first contact anyway** — this is the highest-consequence polarity on the board.
5. **SYNC_WRITE stack buffer overflow.** 12-servo goal broadcast = 44-byte frame into a
   `MAX_FRAME_LEN`(=38)-byte stack array — 6 bytes of stack smashed at 40 Hz. Invisible
   with ≤10 servos on a bench, memory corruption with the full fleet. `MAX_PARAM_BYTES`
   32→40 plus an explicit frame-size guard in `sync_write_goal_positions()`.
6.5 **(pass 2) Cold-boot brick.** micro-ROS init ran in `setup()` BEFORE the tick timer,
   and `RCCHECK` bricked into a while(1) on failure — but the agent lives on the Jetson,
   which boots 30-60 s after the Teensy. Every real robot power-up bricked the firmware
   (no watchdog running yet) until a manual power cycle; dev flashing masked it because
   the agent was already up. `rclc_support_init` now retries forever with a 2 Hz LED blink.
   Motion is impossible pre-agent anyway (broadcast gates on first command) and the
   hardware safety chain is autonomous.
6.6 **(pass 2, nova_calibration) Hard-stop probe goal runaway.** The probe advanced its
   goal open-loop; against a compliant stop (printed PA6 flexes) load could sit below
   threshold while the goal ran to the 0/4095 clamp, grinding gears at rising torque.
   Goal now leashed to `leash_raw`(=24) past the last measured position — worst-case
   torque bounded, compliant stops resolve as TIMEOUT instead of silent grinding.
   Regression-tested (`test_hard_stop.py`, 7/7).
6. **Edge-only safety topics blinded late joiners.** `/estop`, `/battery_low`,
   `/safety_state`, `/command_stale` published only on change — a respawned
   battery_shutdown node (or preflight on a quiet bus) could never learn an
   already-latched state. All four now also re-publish at 1 Hz from the heartbeat.

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
