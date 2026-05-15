# NovaSM3 Quadruped Build — BOM v3.3 (Committed)

**Last updated:** May 15, 2026
**Supersedes:** BOM v3.2
**Status:** v1 scope narrowed to **quadruped only** (12 servos active). Arm (6 STS3215) demoted to Phase 4 future work; bus IDs 13-18 + arm-rail buck footprint reserved on PCB redesign. Power rails redesigned around Pololu modules after XL4016 capacity audit. Full safety scope: LVC alarm + E-stop + INA226 per-rail telemetry + MOSFET hard-cutoff. **Bus master: Pattern B is v1 default** — Teensy 4.1 UART → 74HC125 half-duplex driver → bus. Pattern A (FE-URT-1 → bus) kept as bench/debug fallback via solder bridge.

---

## 1. Compute + Perception

| Item | Price | Status |
|------|-------|--------|
| Unitree L2 3D LiDAR | $451 | ✅ Ordered (DLZ-3974) |
| NVIDIA Jetson Orin Nano Super Dev Kit 8GB | $249 | ✅ Owned |
| Intel RealSense D456 | $584 | ✅ Ordered (#000187781) |
| WiFi/BT module | $0 | ✅ Included — Jetson Orin Nano Super Dev Kit (P3766) ships with 802.11ac/abgn WiFi pre-installed per official spec. WiFi 5 (ac), **not** WiFi 6E. BT not explicitly listed in spec — verify on arrival. If somehow missing, order AX210NGW + U.FL antennas separately (~$30). |
| **DisplayPort cable OR DP→HDMI adapter** | **$10** | 🆕 Order |
| LeRobot Pi's 128GB Amazon Basics microSD | $0 | ✅ Reuse — back up LeRobot configs first. **128GB enough for Phase 1-2.** NVMe migration deferred until NAND prices recover or storage becomes a measured bottleneck. |

**Compute subtotal of new adds: $10**

> **NVMe deferred (May 2026):** AI-data-center-driven NAND flash shortage has 2-3x'd consumer SSD prices. 1TB Crucial P3 Plus that quoted $60-80 in early 2026 is now $165-220 retail. Kingston: NAND wafer costs +246% since 2024. TrendForce: client SSD +40% QoQ in Q1 2026. Relief not expected until late 2026 / 2027-2028. See Deferred section for revisit triggers.

---

## 2. Control + Electronics

| Item | Price | Status |
|------|-------|--------|
| Teensy 4.1 (with pins) | $50 | ✅ Owned |
| Arduino Nano (ELEGOO 3-pack, CH340) | $15 | ✅ Ordered |
| ~~NovaSM3 PCB v5.2b~~ → **NovaSM3 PCB v6 (custom redesign)** | $60 (est.) | 🆕 Design + order from PCBWay — see [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md) for feature set |
| FE-URT-1 USB→TTL Feetech interface | $20 | ✅ Ordered |
| **74HC125 quad tri-state buffer** (Pattern B half-duplex driver) | $1 | 🆕 Order — **populated on PCB; v1 default active**. Drives the Feetech bus from Teensy 4.1 UART. Solder bridge `JP_BUS_MASTER` defaults to B; flip to A only for bench bring-up or debug fallback via FE-URT-1. Buy 5 (cheap, easy to fry). |
| **E-stop button (panel-mount, latching, NC contact)** | $10 | 🆕 Order |
| **INA226 current/voltage monitor × 3** | $9 | 🆕 Order — one per active rail (leg 7.4V, hip 12V, Jetson 12V). I²C to Teensy. |
| **Comparator + MOSFET parts for hard-cutoff at 12.4V** | $10 | 🆕 Order — autonomous LVC backstop independent of charger alarm |

**Feetech bus architecture: Pattern B is v1 default.**
- **Pattern B (v1 active):** Teensy 4.1 hardware UART → 74HC125 half-duplex driver → 12-servo TTL bus. Bare-metal real-time. Jetson sends joint targets via micro-ROS over USB; Teensy translates to bus writes at 200-500 Hz. Survives Jetson restarts, kernel preemption, CUDA stalls, journald flushes — none of which affect bus servicing. Solder bridge `JP_BUS_MASTER` defaults to B.
- **Pattern A (bench / debug fallback):** FE-URT-1 → USB → Jetson directly drives the bus. Flip `JP_BUS_MASTER` to A for: initial servo ID assignment from a workstation (before Teensy firmware is ready), debug if Teensy firmware misbehaves, or post-mortem inspection of bus traffic. Not the runtime path.

Why B as default (revised from v3.2): Linux is not a real-time OS. USB-CDC latency on Jetson is 1-10 ms typical, 50 ms+ under load (CUDA kernel preemption, kworker spikes). At 100 Hz gait, a 100 ms stall = robot on the floor. Teensy bare-metal UART has hard real-time guarantees by construction. Defaulting to A would force a measure-then-migrate decision in Phase 1; defaulting to B skips that risk for the cost of populating one IC and writing the firmware in Phase 1.

Cost of Pattern B as default: 74HC125 must be populated (~$1, already in §2 above) + Teensy firmware becomes a Phase 1 critical-path deliverable (was a Phase 2+ stub).

---

## 3. Power

### Main power chain (v3.2 — Pololu redesign)

XL4016 ×2 dropped from active design after capacity audit: 8A continuous rating is insufficient for walking-gait current (8-12A avg, 25-40A impact transients per leg-rail load profile). See [`docs/power-budget.md`](../docs/power-budget.md) for math. XL4016 boards stay in spares bin for low-current aux duty.

| Item | Price | Status |
|------|-------|--------|
| 4S LiPo 14.8V 4000mAh (×2) | $130 | ✅ Owned |
| XT60 plug + high-current switch | $15 | ✅ Ordered |
| Lighted rocker switch 12V | $5 | ✅ Ordered |
| Mini digital voltmeter | $10 | ✅ Ordered |
| ~~XL4016 12A buck (×2)~~ | $30 | ⚠️ Already ordered — relegated to spares (8A cont. inadequate for servo rails). |
| XL6009 buck-boost | $10 | ✅ Owned — spare, no allocated role |
| **Pololu D42V110F7 — 7.4V leg rail (10A+ cont.)** | **$60** | 🆕 Order — drives 8× femur/tibia STS3215 (19kg). 12-60V Vin, headroom for 25-40A impact transients via bulk caps at injection points. |
| **Pololu D42V110F12 — 12V hip+L2 rail (10A+ cont.)** | **$60** | 🆕 Order — drives 4× hip STS3215 (30kg) + Unitree L2 LiDAR via LC filter tap. |
| **Pololu D42V55F12 — 12V Jetson rail** | **$32** | 🆕 Order — replaces deprecated D24V50F12. Derates to ~3A cont. at 14.8V Vin → ~1.4× headroom over Jetson MAXN 2.1A. Min Vin 12V → **LVC alarm at 13.2V**. Reverse-polarity protected. |
| **Pololu D42V55F7 — 7.4V arm rail (future)** | **$0** | ⚠️ **Footprint reserved on PCB v6; don't populate until Phase 4 arm install.** Estimated cost when ordered: ~$32. |
| UBEC 5V/5A | $15 | ✅ Owned — 5V peripherals (Ethernet switch, fans, aux sensors) |
| Bulk caps for rail injection points (1000 µF / 25V × 4) | $4 | 🆕 Order with electronics — soaks servo impact transients near point of load |
| PCB terminals + misc boards | $8 | ✅ Ordered |
| Dip switches + resistors + buttons | $8 | ✅ Ordered |

### Battery charging + safety

| Item | Price | Status |
|------|-------|--------|
| **ISDT 608AC charger** | **$60** | 🆕 Order — AC mode caps ~55W ≈ 75 min for 4S 4000mAh pack (fine for dev workflow). Includes charge / discharge / **storage** modes (storage critical for keeping unused pack healthy >1 week). |
| **LiPo safe bag** | **$15** | 🆕 Order separately — 608AC does not include one |
| **XT60 jumper** | **$5** | ⚠️ Verify Ovonic 4S kit on arrival — likely supplied. Order only if missing. |
| XT60 charging lead | $8 | ⚠️ Verify Ovonic 4S kit on arrival — likely supplied (XT60 ↔ JST-XH balance). Order only if missing. |

### Final power rail map (v3.2)

```
4S LiPo (12.8-16.8V) ──┬── Pololu D42V110F7  → 7.4V/10A+ → 8× femur/tibia STS3215 (19kg)
                       │                                   ↑ star injection: 4 points across chain
                       │
                       ├── Pololu D42V110F12 → 12V/10A+  ─┬→ 4× hip STS3215 (30kg)
                       │                                  └→ Unitree L2 LiDAR (LC filter)
                       │
                       ├── Pololu D42V55F12  → 12V/~3A   → Jetson barrel jack
                       │
                       ├── [reserved arm rail]            → 7.4V/3-8A → 6× arm STS3215 (Phase 4)
                       │   (D42V55F7 footprint, unstuffed)
                       │
                       └── UBEC 5V/5A        → 5V        → Ethernet switch, fans, aux 5V peripherals
```

**Power tree safety chain:**
- 608AC charger LVC alarm: **3.3V/cell = 13.2V** pack (above D42V55F12 dropout knee)
- MOSFET hard-cutoff: **12.4V pack** (autonomous backstop, comparator-driven, breaks main battery feed)
- Panel-mount E-stop: NC contact in series with the **servo-rail enable lines only** — kills D42V110F7 + D42V110F12 outputs while Jetson rail stays live for debug
- INA226 per active rail (3×): I²C → Teensy → ROS 2 diagnostics topic
- ANL 30A fuse on battery feed (sized for hip-rail worst case ~15A + headroom)

---

## 4. Servos (Feetech TTL Unified Bus)

**v1 scope: 12 active servos** (4 hip + 8 femur/tibia). Arm (6× STS3215) deferred to Phase 4 — kept on shelf, bus IDs 13-18 reserved, arm-rail PCB footprint reserved.

| Item | Price | Status |
|------|-------|--------|
| STS3215 12V 30kg × 4 (hips) | $120 | ✅ Ordered — bus IDs 1-4 |
| STS3215 7.4V 19kg × 8 (femur + tibia) | $200 | ⚠️ Have ~6, order remaining 2 — bus IDs 5-12 |
| STS3215 7.4V 19kg × 6 (arm) | $0 | ⏸ **Phase 4 future** — carry over from SO-ARM101, IDs 13-18 reserved, not on bus for v1 |
| Feetech TTL daisy-chain cables | $20 | ✅ Ordered |
| Feetech 25T servo horns × 12 | $35 | ✅ Ordered — *horn fitment integrated into leg redesign* |
| Feetech FD debugging software (Windows) | Free | 🆕 Download — for ID setup |

**Process:** Set unique bus IDs (**1-12 active** for v1 quadruped; 13-18 reserved for Phase 4 arm) before chaining. Label each servo physically.

### Bus integrity (12 nodes @ 1Mbps over ~2 m harness)

PCB v6 includes footprints for the following bus-integrity mitigations (populate per measured bus error rate):
- **Series R** (22-100 Ω, 0603) at FE-URT-1 output — slope rate-limiting
- **Ferrite bead** at each servo entry — common-mode noise rejection
- **Star ground** at FE-URT-1 — eliminates daisy-chain ground-loop pickup

Note: Feetech bus is single-ended half-duplex TTL UART. 120 Ω differential termination (RS-485 trick) is NOT appropriate here. If bus errors persist after the above, drop baud 1M → 500k → 250k.

---

## 5. Networking (Unitree L2 + Dev Access)

| Item | Price | Status |
|------|-------|--------|
| **Gigabit Ethernet switch (5-port)** — TP-Link LS105G or NETGEAR GS305 | **$15** | 🆕 Order |
| **Short Cat6 cables × 2 (0.5m)** | **$8** | 🆕 Order |
| Small inductor + capacitor (LC filter for L2 12V) | $3 | 🆕 Order with electronics |

**Topology:**
```
L2 (192.168.1.62) ─┐
                   ├─→ Gigabit switch ─→ Jetson eth0 (static 192.168.1.2/24)
Dev laptop ────────┘
```

Switch can be pulled out of its case to save ~60% volume inside the chassis if needed. Powered from the 5V UBEC rail (~3W draw).

---

## 6. Mechanical Hardware

| Item | Price | Status |
|------|-------|--------|
| M3/M4/M5/M6 stainless hex screw kit | $35 | ✅ Ordered |
| 8x16x5mm ball bearings × 8 | $15 | ✅ Ordered |
| Standoffs, zip ties, heat shrink (assorted) | $30 | ✅ Ordered |
| **Threadlocker (Loctite 243 blue)** | **$8** | 🆕 Order |
| **Electrical tape + Kapton tape** | **$10** | 🆕 Order |

---

## 7. Stock NovaSM3 Sensors

| Item | Price | Status |
|------|-------|--------|
| GY-521 MPU-6050 IMU | $8 | ✅ Ordered |
| DFPlayer Mini Pro + 4Ω speaker | $20 | ✅ Ordered |
| WS2812B RGB LEDs × 4 | $8 | ✅ Ordered |
| SSD1331 96×64 OLED | $18 | ✅ Ordered |
| HC-SR04 ultrasonic × 2 | $10 | ✅ Ordered |
| MH-SR602 PIR motion sensor × 3 | $12 | ✅ Ordered |

---

## 8. Bambu P1S Printing

| Item | Price | Status |
|------|-------|--------|
| PA6-CF Nylon CF × 2 spools | $170 | ✅ Ordered |
| PETG-CF × 1 spool (brick red) | $40 | ✅ Ordered |
| TPU 95A × 1 spool (yellow) | $45 | ✅ Ordered |
| PETG accent × 1 spool (white) | $30 | ✅ Ordered |
| Bambu AMS HF + setup tools | $180 | ✅ Ordered |
| Bambu P1-series hardened steel hotend | $40 | ✅ Ordered |
| Creality SpacePi X4 filament dryer | $170 | ✅ Ordered |
| **Magigoo PA glue stick** | **$15** | 🆕 Order |

---

## 9. Wiring + Consumables

| Item | Price | Status |
|------|-------|--------|
| 18AWG silicone wire | $18 | ✅ Ordered |
| 22AWG hookup wire | $15 | ✅ Ordered |
| JST / Dupont connector kit | $30 | ✅ Ordered — verify crimper included |

---

## 10. Mechanical Decisions (Resolved)

- **L2 mounting:** top-center of chassis, on a riser ~5-10cm above the highest obstruction (arm shoulder, body panels). Centerline placement for symmetric 360° coverage and minimal yaw moment during body sway.
- **Leg redesign:** in progress in CAD. Absorbs horn-spline fitment, servo pocket geometry for STS3215 dimensions, and dual-axis back-shaft U-brackets.
- **Servo bracket fitment:** validated as part of leg redesign — no separate test print needed.

---

## 11. Software / Accounts Checklist

Pre-hardware setup (do now):

- [ ] NVIDIA Developer account
- [ ] JetPack 6.x SD card image download
- [ ] Balena Etcher
- [ ] Feetech FD debug software (Windows or VM)
- [ ] Arduino IDE + Teensyduino
- [ ] CH340 macOS driver
- [ ] PCBWay account
- [ ] Nova Discord access
- [ ] GitHub repo for project
- [ ] Back up LeRobot Pi SD contents to Mac before reformatting

Post-Jetson-flash install list (Phase 1):

- [ ] ROS 2 Humble (Jetson native)
- [ ] librealsense2 SDK (ARM64 build)
- [ ] `ros-humble-realsense2-camera`
- [ ] Unitree unilidar_sdk2 + ROS 2 wrapper (discodyer fork)
- [ ] POINT-LIO and/or RTAB-Map
- [ ] robot_localization (EKF)
- [ ] Nav2
- [ ] micro-ROS Teensy setup
- [ ] VSCode + Remote-SSH on Mac for Jetson dev

---

## 12. Pre-Assembly Test Sequence

1. **Jetson desk bring-up**
   - Update Orin Nano firmware to JetPack-6.x-compatible version
   - Verify included WiFi module works (WiFi 5 / 802.11ac); confirm BT presence
   - Flash JetPack 6.x SD, boot, complete Ubuntu setup, WiFi up
   - (Skip NVMe migration — deferred due to NAND shortage; run from 128GB microSD)
   - Install ROS 2 Humble + sensor SDKs
   - Test D456 standalone (`realsense-viewer`)
   - Test L2 standalone with included 12V wall adapter → point cloud in rviz2

2. **Power rail validation (with one LiPo, second still wrapped)**
   - Charge LiPo to full inside the safe bag
   - Bench-test Pololu D42V55F12 (Jetson 12V): 4S in → 12V out, loaded with Jetson MAXN. **Sweep Vin from 16.8V down to 13.2V** and confirm 12V rail stays clean (no >100 mV droop, no oscillation) — validates dropout-knee setpoint.
   - Bench-test Pololu D42V110F7 (leg 7.4V): load with 1× then 4× then 8× STS3215 19kg in a walking-gait stand-in (alternating PWM positions @ 2 Hz). Watch for thermal rise, voltage sag, and rail oscillation under transient steps.
   - Bench-test Pololu D42V110F12 (hip+L2 12V): load with 1× 30kg hip + L2 LiDAR. Verify LC filter cleans the L2 tap (scope before/after).
   - Bench-test 5V UBEC loaded with Ethernet switch.
   - Verify E-stop physically opens the leg + hip rail enable lines (Jetson rail stays alive).
   - Verify MOSFET hard-cutoff trips at 12.4V Vin (use bench supply to sweep down; restore battery only after verifying).
   - Verify INA226 per-rail I²C reads sane current/voltage values under load.

3. **Servo bring-up**
   - **Bridge in Pattern A** (temporary) for initial ID assignment: power one servo at a time, assign IDs **1-12 for v1** (4 hips, 8 femur/tibia), label each. IDs 13-18 reserved for future arm. Use FE-URT-1 + SCServo SDK Python from workstation — simpler than booting micro-ROS for ID setup.
   - **Flip `JP_BUS_MASTER` to Pattern B** (v1 default). Teensy firmware running: micro-ROS + half-duplex driver via 74HC125.
   - Single-servo test via Teensy: subscribe to `/joint_commands`, publish `/joint_states`. Verify with `ros2 topic echo` from Jetson.
   - Full 12-servo daisy chain: continuity check unpowered, then ping-all powered via Teensy.
   - **Verify** gait-loop p99 latency: ROS 2 → Teensy → bus → return at 100 Hz across all 12 servos. **Pass criterion: p99 <2 ms** (well within Teensy bare-metal capability). If p99 misses, debug Teensy firmware before chassis assembly — do not fall back to Pattern A as a workaround.

4. **Network**
   - Configure Jetson eth0 static 192.168.1.2/24
   - Verify L2 → switch → Jetson UDP packet flow on port 6101
   - Verify SSH-over-WiFi still works while LiDAR streams

5. **Sensor smoke test**
   - MPU-6050 on Arduino Nano I2C
   - PIRs, ultrasonics, OLED, RGB LEDs, DFPlayer — one at a time

---

## 13. Cost Summary

### Committed net adds (v3.2 audit)

| Category | Amount |
|----------|--------|
| DP adapter | $10 |
| Pololu D42V55F12 (Jetson 12V) | $32 |
| **Pololu D42V110F7 (leg 7.4V)** | **$60** |
| **Pololu D42V110F12 (hip+L2 12V)** | **$60** |
| Ethernet switch + Cat6 + LC filter parts | $26 |
| Threadlocker + tape | $18 |
| Magigoo PA | $15 |
| ISDT 608AC + LiPo safe bag + XT60 jumper + XT60 charging lead | $88 |
| **74HC125 + E-stop + INA226 ×3 + hard-cutoff parts + bulk caps** | **$34** |
| **Subtotal** | **~$343** |

Sunk cost note: XL4016 ×2 ($30) already ordered — moved to spares bin, not refunded. New PCB v6 design cost (PCBWay) absorbs the v5.2b $60 line. Net forward spend ≈ $343.

### Deferred (order when you actually need them)

- **NVMe SSD (Crucial P3 Plus 1TB or equivalent)** — deferred due to May-2026 NAND flash shortage (1TB now $165-220 vs $60-80 pre-shortage). Revisit triggers:
  - SD card fills up
  - Docker build times become painful
  - SD card dies
  - 1TB NVMe street price recovers to <~$100
- Spare STS3215 19kg servo — when one dies
- Spare bearings — when you ruin a press-fit
- Logic analyzer — when the Feetech bus is misbehaving
- Spare build plate — when current one is scratched up

*Calipers: already on hand.*

### Project total estimate

- **Already-owned/ordered:** ~$2,650 (includes XL4016 ×2 sunk to spares)
- **Committed net adds (v3.2):** ~$343
- **Realistic total spend:** **~$2,993**
- **Grant ask with buffer (~25% for reprints, shipping batches, contingency):** **~$3,740**

---

## 14. Pending Items

- [ ] Verify included WiFi works on Jetson arrival (802.11ac/ab/gn confirmed from NVIDIA spec); confirm BT presence (not explicitly in spec)
- [ ] Order remaining STS3215 19kg servos to complete 8-count for legs (v1 = 12 active total)
- [ ] Design PCB v6 — see [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md)
- [ ] Write Teensy firmware (Pattern B bus driver + micro-ROS) — see [`firmware/teensy/README.md`](../firmware/teensy/README.md). **Critical path for Phase 1.**
- [ ] Verify Pattern B gait-loop p99 <2 ms across 12-servo bus (Phase 1 acceptance gate)

---

*This is the working order list. Anything not here is either already owned, deferred, or rejected.*
