# NovaSM3 Quadruped Build — BOM v3.1 (Committed)

**Last updated:** May 15, 2026
**Supersedes:** BOM v3
**Status:** Final committed parts list. All "optional" items resolved — either committed or deferred. Charger resolved to ISDT 608AC. NVMe deferred due to May-2026 NAND shortage.

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
| NovaSM3 PCB v5.2b | $60 | ✅ To order from PCBWay |
| FE-URT-1 USB→TTL Feetech interface | $20 | ✅ Ordered |

**Feetech bus architecture: Pattern A confirmed for now** — FE-URT-1 → USB → Jetson directly drives the 18-servo bus. No Teensy half-duplex circuit until/unless latency becomes a measured problem.

---

## 3. Power

### Main power chain

| Item | Price | Status |
|------|-------|--------|
| 4S LiPo 14.8V 4000mAh (×2) | $130 | ✅ Owned |
| XT60 plug + high-current switch | $15 | ✅ Ordered |
| Lighted rocker switch 12V | $5 | ✅ Ordered |
| Mini digital voltmeter | $10 | ✅ Ordered |
| XL4016 12A buck (×2) — 6.8V servo + 12V hip rails | $30 | ✅ Ordered |
| XL6009 buck-boost | $10 | ✅ Owned — spare, no allocated role |
| **Pololu D24V50F12 — 12V/5A buck for Jetson** | **$20** | 🆕 Order — replaces UBEC for Jetson |
| UBEC 5V/5A | $15 | ✅ Owned — repurposed for 5V peripherals (Ethernet switch, fans, aux sensors) |
| PCB terminals + misc boards | $8 | ✅ Ordered |
| Dip switches + resistors + buttons | $8 | ✅ Ordered |

### Battery charging + safety

| Item | Price | Status |
|------|-------|--------|
| **ISDT 608AC charger** | **$60** | 🆕 Order — AC mode caps ~55W ≈ 75 min for 4S 4000mAh pack (fine for dev workflow). Includes charge / discharge / **storage** modes (storage critical for keeping unused pack healthy >1 week). |
| **LiPo safe bag** | **$15** | 🆕 Order separately — 608AC does not include one |
| **XT60 jumper** | **$5** | 🆕 Order — 608AC does not include one |
| XT60 charging lead | $8 | 🆕 Order |

### Final power rail map

```
4S LiPo (12.8-16.8V) ──┬── XL4016 #1 → 6.8V rail → 8x femur/tibia STS3215 (19kg)
                       │                          → 6x arm STS3215 (19kg)
                       │
                       ├── XL4016 #2 → 12V rail → 4x hip STS3215 (30kg)
                       │                       └── (LC filter tap) → Unitree L2 LiDAR
                       │
                       ├── Pololu D24V50F12 → 12V → Jetson barrel jack
                       │
                       └── UBEC 5V/5A → 5V rail → Ethernet switch, fans, aux 5V peripherals
```

---

## 4. Servos (Feetech TTL Unified Bus)

| Item | Price | Status |
|------|-------|--------|
| STS3215 12V 30kg × 4 (hips) | $120 | ✅ Ordered |
| STS3215 7.4V 19kg × 8 (femur + tibia) | $200 | ⚠️ Have ~6, order remaining |
| STS3215 7.4V 19kg × 6 (arm, from SO-ARM101) | $0 | ✅ Carry over |
| Feetech TTL daisy-chain cables | $20 | ✅ Ordered |
| Feetech 25T servo horns × 12 | $35 | ✅ Ordered — *horn fitment integrated into leg redesign* |
| Feetech FD debugging software (Windows) | Free | 🆕 Download — for ID setup |

**Process:** Set unique bus IDs (1-12 locomotion, 13-18 arm) before chaining. Label each servo physically.

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
   - Bench-test Pololu D24V50F12: 4S in → 12V out, loaded with Jetson MAXN
   - Bench-test XL4016 #1 set to 6.8V, loaded with one STS3215
   - Bench-test XL4016 #2 set to 12V, loaded with one 30kg hip STS3215
   - Bench-test 5V UBEC loaded with Ethernet switch

3. **Servo bring-up**
   - Power one servo at a time, assign IDs 1-18, label each
   - Single-servo SCServo SDK Python test via FE-URT-1 → Jetson
   - Full 18-servo daisy chain: continuity check unpowered, then ping-all powered

4. **Network**
   - Configure Jetson eth0 static 192.168.1.2/24
   - Verify L2 → switch → Jetson UDP packet flow on port 6101
   - Verify SSH-over-WiFi still works while LiDAR streams

5. **Sensor smoke test**
   - MPU-6050 on Arduino Nano I2C
   - PIRs, ultrasonics, OLED, RGB LEDs, DFPlayer — one at a time

---

## 13. Cost Summary

### Committed net adds (this audit)

| Category | Amount |
|----------|--------|
| DP adapter | $10 |
| Pololu D24V50F12 | $20 |
| Ethernet switch + Cat6 + LC filter parts | $26 |
| Threadlocker + tape | $18 |
| Magigoo PA | $15 |
| ISDT 608AC + LiPo safe bag + XT60 jumper + XT60 charging lead | $88 |
| **Subtotal (608AC charger path)** | **~$187** |

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

- **Already-owned/ordered:** ~$2,650
- **Committed net adds (608AC path):** ~$187
- **Realistic total spend:** **~$2,805**
- **Grant ask with buffer (~25% for reprints, shipping batches, contingency):** **~$3,510**

---

## 14. Pending Items

- [ ] Verify included WiFi 5 module works on Jetson arrival; confirm BT presence
- [ ] Order remaining STS3215 19kg servos to complete 8-count for legs

---

*This is the working order list. Anything not here is either already owned, deferred, or rejected.*
