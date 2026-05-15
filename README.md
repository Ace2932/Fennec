# NovaSM3 — Modified Quadruped Robot with VLA Integration

> A modified [NovaSM3](https://github.com/SovGVD/NovaSM3) quadruped platform rebuilt around a unified Feetech STS3215 TTL servo bus, NVIDIA Jetson Orin Nano Super compute, and ROS 2 Humble — designed as a platform for Vision-Language-Action (VLA) model deployment, 3D SLAM, and autonomous mobile manipulation.

**Status:** 🔧 Phase 1 — Build & Bring-Up
**Platform:** Quadruped (12 DOF) — arm (6-DOF, Phase 4 future) on shelf
**Compute:** NVIDIA Jetson Orin Nano Super 8GB
**Middleware:** ROS 2 Humble
**Last updated:** May 15, 2026 (BOM v3.2)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Differences from Stock NovaSM3](#differences-from-stock-novasm3)
3. [Hardware Architecture](#hardware-architecture)
4. [Software Architecture](#software-architecture)
5. [Power System](#power-system)
6. [Network Topology](#network-topology)
7. [Bill of Materials](#bill-of-materials)
8. [Build Roadmap](#build-roadmap)
9. [Pre-Assembly Test Sequence](#pre-assembly-test-sequence)
10. [Setup Guide](#setup-guide)
11. [Open Decisions](#open-decisions)
12. [References & Credits](#references--credits)

---

## Project Overview

This project is a heavily modified fork of the open-source NovaSM3 quadruped, redesigned to serve as a research platform for embodied AI. Stock Nova uses PWM hobby servos and a Raspberry Pi running custom locomotion code. This build replaces:

- **12 servos** with Feetech STS3215 TTL bus servos for unified protocol, real-time joint feedback (position, load, temperature, voltage), and elimination of PWM wiring complexity. Six additional STS3215 (arm) remain on shelf for Phase 4.
- **The Pi** with an NVIDIA Jetson Orin Nano Super (67 TOPS sparse INT8 / ~33 TOPS dense; 8GB RAM tight but workable for VLA inference + ROS 2 + SLAM — see Phase 4 notes)
- **The stock perception** with Intel RealSense D456 (depth + RGB + IMU) and Unitree L2 4D LiDAR (360° × 96° FOV, 30m range)
- **The stock locomotion stack** with ROS 2 Humble + Nav2 + RTAB-Map / POINT-LIO

The arm is carried over from a prior SO-ARM101 build, also Feetech-based. **v1 build scope: quadruped only (12 servos active).** Arm install + integration is Phase 4 future work — bus IDs 13-18 and the 7.4V arm-rail buck footprint are reserved on the PCB v6 redesign so the future install is a populate-and-go.

### Goals

- ✅ Unified TTL servo bus across locomotion (12 servos v1; future-ready for 18 with arm)
- 🔧 ROS 2 locomotion via micro-ROS bridge to Teensy 4.1 (or direct via FE-URT-1)
- 📋 3D SLAM using LiDAR + visual-inertial fusion (POINT-LIO baseline, RTAB-Map comparison)
- 📋 Autonomous navigation (Nav2) on legged platform with stair climbing
- 📋 VLA fine-tuning and deployment for mobile manipulation tasks
- 📋 Open-source documentation of every design decision for community reuse

---

## Differences from Stock NovaSM3

| Subsystem | Stock NovaSM3 | This Build |
|-----------|---------------|------------|
| Compute (main) | Raspberry Pi 4 | NVIDIA Jetson Orin Nano Super 8GB |
| Compute (MCU) | Teensy 4.0 | Teensy 4.1 (more RAM + SD slot) |
| Aux MCU | Arduino Nano | Arduino Nano (kept, peripherals only) |
| Locomotion servos | 12× PWM hobby servos | 12× Feetech STS3215 (4× 12V/30kg hip, 8× 7.4V/19kg femur/tibia) |
| Arm | None (stock) | 6× Feetech STS3215 from SO-ARM101 — **on shelf, Phase 4** |
| Servo protocol | PWM (one signal per servo) | TTL half-duplex serial bus (daisy-chained) |
| Perception | None / optional | RealSense D456 + Unitree L2 LiDAR |
| Middleware | Custom Arduino loops | ROS 2 Humble + micro-ROS |
| Power | 3S 11.1V LiPo | 4S 14.8V LiPo + Pololu D42V110-class buck rails (7.4V leg, 12V hip+L2, 12V Jetson, 5V aux). XL4016 dropped after capacity audit. |
| Print materials | PLA / PETG | PA6-CF / PETG-CF / TPU 95A |

### Why we're redesigning the PCB (v5.2b → v6)

After the v3.1 architecture audit, the stock Nova PCB v5.2b can't host the upgraded power tree (Pololu modules, INA226 telemetry, hard-cutoff MOSFET, E-stop chain) or the Pattern A/B bus master selector. The redesign retains the spirit of the stock board (Arduino Nano aux slot, battery input geometry) and adds the new safety + power architecture. Full feature set in [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md).

### What carries over from Nova v5.2b

- Arduino Nano slot for aux peripherals (PIR, ultrasonic, OLED, RGB LEDs, MP3, IMU)
- Battery input + reverse polarity protection geometry (replicated with MOSFET-based reverse protection instead of diode)
- Power switch, voltmeter, fuse (rating revised to ANL 30A)

### What changes

- All 12 PWM servo output headers removed (Feetech bus is daisy-chain TTL, doesn't use PWM)
- XL4016 buck footprints → Pololu D42V110-class module footprints
- Add: 74HC125 half-duplex driver (Pattern B prep), INA226 ×3, E-stop chain, hard-cutoff MOSFET, ANL fuse holder, bulk caps at injection points, bus-integrity footprints (series R + ferrite beads), reserved arm-rail buck footprint

---

## Hardware Architecture

### Block diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                  NVIDIA Jetson Orin Nano Super 8GB                 │
│                          (ROS 2 Humble)                            │
│   • Locomotion, Nav2, SLAM, VLA inference, sensor fusion           │
│   • Built-in WiFi 5 (802.11ac/ab/gn) per NVIDIA P3766 spec sheet   │
└──┬──────────┬─────────────┬─────────────┬───────────────────────────┘
   │ USB-C    │ USB 3.1     │ Ethernet    │ USB
   │          │             │             │
┌──▼───────┐ ┌▼───────────┐ ┌▼───────────┐ ┌▼─────────────────────┐
│ Realsense│ │ FE-URT-1   │ │ Gig switch │ │ Teensy 4.1            │
│ D456     │ │ USB→TTL    │ │            │ │  • aux I/O (v1)       │
│ (depth + │ │ (bus       │ │ ◄─ L2 ─►   │ │  • INA226 I²C reader  │
│  RGB +   │ │  master    │ │            │ │  • E-stop GPIO        │
│  IMU)    │ │  Pattern A)│ └────────────┘ │  • 74HC125 → bus      │
└──────────┘ └────┬───────┘                │    (Pattern B prep)   │
                  │                        └──┬────────────────────┘
                  │ TTL half-duplex           │ I²C / GPIO
                  │ (solder-bridge select)    │
        ┌─────────▼─────────┐         ┌──────▼──────────────────┐
        │ 12× STS3215       │         │ Arduino Nano            │
        │ daisy-chained     │         │ (aux only:              │
        │  IDs 1-4:  hips   │         │  PIR, OLED, RGB, MP3,   │
        │  IDs 5-12: f/tib  │         │  ultrasonic, MPU-6050)  │
        │  IDs 13-18: ⏸    │         │                         │
        │  (arm, Phase 4)   │         └─────────────────────────┘
        └───────────────────┘
```

### Servo configuration

| Joint group | Count | Servo | Voltage | Bus IDs | Status |
|-------------|-------|-------|---------|---------|--------|
| Hips | 4 | STS3215 30kg | 12V | 1-4 | v1 active |
| Femur + tibia | 8 | STS3215 19kg | 7.4V | 5-12 | v1 active |
| Arm (shoulder + elbow) | 3 | STS3215 19kg | 7.4V | 13-15 | ⏸ Phase 4 — reserved |
| Arm (wrist + gripper) | 3 | STS3215 19kg | 7.4V | 16-18 | ⏸ Phase 4 — reserved |

**v1 build = 12 active servos** on a single daisy-chained TTL bus, 2 active voltage rails (7.4V leg, 12V hip+L2). Bus IDs 13-18 and the 7.4V arm rail (D42V55F7 footprint) reserved on PCB v6 for Phase 4 arm install — populate-and-go.

### Bus master pattern

Two viable patterns. **PCB v6 supports both via solder-bridge selector** — no chassis teardown to migrate.

- **Pattern A (v1 default):** Jetson → USB → FE-URT-1 → TTL bus. Simple, matches SO-ARM101 architecture. **Real risk is not "Jetson restart kills servo commands" — it's Linux jitter.** USB-CDC latency on Jetson is 1-10 ms typical, 50 ms+ under load (CUDA kernel preemption, journald flushes, kworker spikes). At 100 Hz gait, 100 ms = robot on the floor.
- **Pattern B (footprint-ready):** Teensy 4.1 UART → 74HC125 half-duplex driver → same bus pads as FE-URT-1. Hard real-time, survives Jetson restarts and kernel preemption. PCB v6 routes both paths; a solder bridge selects which master drives the bus.

**Migration criterion:** measure gait-loop p99 latency once 12-servo bus is live (Pre-Assembly §12 step 3). If p99 >5 ms or stalls observed, flip the solder bridge. Zero hardware rework.

---

## Software Architecture

### ROS 2 stack (target)

```
┌──────────────────────────────────────────────┐
│             Application Layer                │
│  • Behavior tree / mission FSM               │
│  • VLA policy node                           │
│  • Teleop bridge                             │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│            Navigation Layer                  │
│  • Nav2 (planning + control)                 │
│  • robot_localization (EKF)                  │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│              Perception Layer                │
│  • RTAB-Map / POINT-LIO (3D SLAM)            │
│  • realsense2_camera                         │
│  • unitree_lidar_ros2                        │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│            Locomotion Layer                  │
│  • Gait controller (8-phase walk)            │
│  • 3-DOF-per-leg IK solver                   │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│               Hardware Layer                 │
│  • Feetech SCServo SDK (joint state + cmd)   │
│  • micro-ROS bridge (Teensy ↔ Jetson)        │
│  • IMU driver, peripheral I/O                │
│  • INA226 per-rail telemetry → diagnostics   │
└──────────────────────────────────────────────┘
```

### Key software components

| Component | Purpose | Status |
|-----------|---------|--------|
| ROS 2 Humble | Middleware | 📋 Install on Jetson |
| `librealsense2` | RealSense SDK | 📋 ARM64 build |
| `realsense2_camera` | ROS 2 wrapper for D456 | 📋 apt install |
| `unilidar_sdk2` | Unitree L2 SDK | 📋 Clone from GitHub |
| `unitree_lidar_ros2` (discodyer) | ROS 2 wrapper for L2 | 📋 Clone + build |
| POINT-LIO | LiDAR-inertial SLAM | 📋 Eval first |
| RTAB-Map | Visual-LiDAR SLAM | 📋 Compare with POINT-LIO |
| Nav2 | Autonomous navigation | 📋 Phase 3 |
| robot_localization | EKF sensor fusion | 📋 Phase 2 |
| micro-ROS (Teensy) | Embedded ROS 2 | 📋 Phase 2 |
| SCServo SDK | Feetech bus driver | ⚠️ Already familiar from SO-ARM101 |

---

## Power System

### Voltage rails

```
4S LiPo 14.8V nominal (12.8-16.8V)
   │  ANL 30A fuse · MOSFET reverse-protection · MOSFET hard-cutoff @12.4V · E-stop NC (servo rails only)
   │
   ├── Pololu D42V110F7  ──► 7.4V/10A+ ──► 8× STS3215 19kg femur/tibia
   │       (star injection at 4 points along chain, bulk caps near point of load)
   │
   ├── Pololu D42V110F12 ──► 12V/10A+ ──┬── 4× STS3215 30kg hips
   │                                     └── (LC filter) ──► Unitree L2 LiDAR (12V/1A)
   │
   ├── Pololu D42V55F12  ──► 12V/~3A  ──► Jetson Orin Nano (barrel jack)
   │
   ├── [reserved D42V55F7] ► 7.4V/3-8A ──► 6× STS3215 arm (Phase 4 — footprint unstuffed)
   │
   └── UBEC 5V/5A ──► 5V rail ──► Ethernet switch, fans, aux 5V peripherals

   INA226 ×3 (leg 7.4V, hip+L2 12V, Jetson 12V) ──► I²C ──► Teensy 4.1 ──► ROS 2 diagnostics
```

### Notes

- All rails share a common ground
- Jetson MAXN peak power ~25W → ~2.1A at 12V. **Pololu D42V55F12** derates to ~3A continuous at 14.8V Vin (4.5A typ headline is at 42V in) → ~1.4× headroom. Min Vin 12V — set LiPo LVC alarm at 3.3V/cell = 13.2V to stay above dropout.
- **Leg rail D42V110F7** (~10A+ cont. at 14.8V Vin) sized for walking-gait avg 5-8A with bulk caps absorbing 25-40A impact transients near each star injection point. See [`docs/power-budget.md`](./docs/power-budget.md).
- **Hip+L2 rail D42V110F12** (~10A+ cont.) sized for 4× 30kg hips peak ~12A + L2 1A.
- **MOSFET hard-cutoff at 12.4V** is the autonomous safety net independent of the charger's LVC alarm. E-stop kills only the leg + hip rail enables — Jetson stays alive for post-mortem debug.
- L2 self-heats below 30°C ambient; ~30-60s delay before point cloud output on cold boots
- LC filter on the L2 12V tap is required to prevent hip-servo current noise from causing UDP packet loss

### Battery safety

- Always charge inside a LiPo safe bag
- Two 4S packs alternated; storage-charge to 3.8V/cell if unused >1 week
- Label packs (A/B) with first-use date; track cycle counts

---

## Network Topology

```
                          ┌─────────────────┐
                          │  Dev laptop     │
                          │  (Mac)          │
                          │  Static IP:     │
                          │  192.168.1.10   │
                          └────────┬────────┘
                                   │
                                   │ Cat6
┌──────────────────────────┐       │       ┌────────────────────────┐
│ Unitree L2 LiDAR         │       │       │ Jetson Orin Nano       │
│ Static IP: 192.168.1.62  ├───────┼───────┤ eth0: 192.168.1.2/24   │
│ UDP target port: 6101    │   Gigabit     │ wlan0: DHCP from home  │
└──────────────────────────┘   switch      └────────────────────────┘
                            (5-port unmanaged)
```

- L2 → UDP port 6101 on the Jetson
- Jetson's `eth0` needs a manual static IP because L2 is not a DHCP client/server
- WiFi (built-in WiFi 5 / 802.11ac module on P3766 kit) handles dev SSH access + internet, leaving Ethernet free for the LiDAR. BT presence not explicitly listed in spec — verify on arrival.

---

## Bill of Materials

Full BOM lives in [`BOM.md`](./BOM.md). High-level summary:

| Category | Cost |
|----------|------|
| Compute + perception | ~$1,300 (NVMe deferred — NAND shortage) |
| Servos | ~$320 active (12-servo v1) + 6 SO-ARM101 carryover on shelf |
| Power + safety | ~$335 (Pololu rails + INA226 + E-stop + MOSFET hard-cutoff) |
| Mechanical + hardware | ~$110 |
| Sensors (stock Nova) | ~$76 |
| Filament + Bambu accessories | ~$700 |
| Wiring + consumables | ~$80 |
| **Realistic total** | **~$2,993** (v3.2: Pololu rail redesign + full safety scope) |

---

## Build Roadmap

### Phase 0 — Pre-build setup (current)

- [x] Define modified BOM (v3.2: Pololu rails + safety + arm deferred)
- [x] Validate component compatibility (Jetson power rail, Feetech bus, L2 ethernet)
- [x] Pick LiPo charger → **ISDT 608AC**
- [x] Power rail audit (XL4016 → Pololu D42V110-class)
- [x] Confirm v1 scope = quadruped only (arm → Phase 4)
- [ ] Order remaining parts (switch, Pololu bucks ×3, charger bundle, safety parts, accessories) — NVMe deferred
- [ ] Design PCB v6 — see [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md)
- [x] Set up GitHub repo with this README and BOM
- [ ] Back up LeRobot Pi SD contents
- [ ] Create NVIDIA Developer account, download JetPack 6.x image

### Phase 1 — Hardware bring-up (weeks 1-4)

- [ ] Flash JetPack 6.x to microSD; firmware update Jetson if needed
- [ ] Boot Jetson, complete Ubuntu setup
- [ ] Verify pre-installed WiFi works; install AX210NGW only if missing. Confirm BT presence.
- [ ] Install ROS 2 Humble + librealsense2 + unilidar_sdk2 (run from 128GB microSD; NVMe deferred)
- [ ] D456 standalone test (`realsense-viewer`)
- [ ] L2 standalone test (included 12V adapter + rviz2)
- [ ] Print parts: Bambu P1S + PA6-CF (dry 24h before each print)
- [ ] Bench-validate Pololu D42V55F12 / D42V110F7 / D42V110F12 / UBEC 5V (per BOM §12 step 2)
- [ ] Verify E-stop chain + MOSFET hard-cutoff @ 12.4V + INA226 I²C reads
- [ ] Set Feetech servo IDs **1-12** (v1 active), label each. IDs 13-18 reserved for Phase 4.
- [ ] Single-servo SCServo SDK test from Jetson via FE-URT-1
- [ ] Full 12-servo daisy chain ping test
- [ ] **Measure gait-loop p99 latency @ 100 Hz** → resolves Pattern A vs B (solder bridge flip if >5 ms)
- [ ] Assemble legs (redesigned for STS3215 dimensions)
- [ ] Assemble chassis, mount L2 on top-center riser
- [ ] Network setup: eth0 static 192.168.1.2; verify L2 UDP flow
- [ ] Arduino Nano: strip code to aux peripherals only
- [ ] Stand / sit test on hardware (no walk yet)

### Phase 2 — Locomotion (weeks 5-8)

- [ ] Implement 3-DOF-per-leg IK solver (reference mogar/spot_micro)
- [ ] 8-phase walk gait controller on Jetson via Teensy micro-ROS bridge
- [ ] Stand, sit, walk validated on hardware
- [ ] MPU-6050 body stabilization feedback
- [ ] Calibrate LiDAR ↔ RealSense extrinsics
- [ ] EKF fusion: MPU-6050 + D456 IMU via `robot_localization`
- [ ] RTAB-Map 3D SLAM on walking platform
- [ ] POINT-LIO comparison (LiDAR-IMU only)

### Phase 3 — Autonomy (weeks 9-12)

- [ ] Nav2 integration on legged platform
- [ ] Costmaps from D456 + L2
- [ ] Autonomous waypoint navigation
- [ ] Obstacle avoidance during walk
- [ ] Stair climbing test (gait variation)
- [ ] Telemetry dashboard

### Phase 4 — Arm install + Manipulation + VLA (future, after Phase 3 stable)

Split into two sub-phases since hardware-arm-install precedes any manipulation software.

**Phase 4a — Arm hardware install:**
- [ ] Populate D42V55F7 arm-rail buck on PCB v6
- [ ] Install 6× STS3215 arm servos (carried from SO-ARM101), assign bus IDs 13-18
- [ ] Mechanical mount of arm to chassis (CAD pending)
- [ ] Full 18-servo daisy-chain ping test
- [ ] Bench-validate arm rail under realistic load

**Phase 4b — Manipulation + VLA software:**
- [ ] Arm joint state integration into unified URDF
- [ ] MoveIt 2 motion planning for arm
- [ ] **COM-shift compensation** in gait controller (arm extension + payload mass shifts support polygon — gait controller needs arm-state input)
- [ ] VLA model selection (OpenVLA / Pi0 / RT-2 class). Constraint: 8 GB RAM shared with ROS 2 + SLAM + RealSense full rate. OpenVLA INT4 fits but tight; budget memory carefully.
- [ ] Data collection harness for in-house fine-tuning
- [ ] On-device VLA inference (TensorRT-optimized)
- [ ] Mobile manipulation demo: navigate to object, grasp, transport

---

## Pre-Assembly Test Sequence

Before assembling any subsystem into the chassis, validate on the bench. Catching a bad part on the desk is minutes; catching it after assembly is hours.

1. **Jetson desk bring-up** — Firmware update → JetPack flash → Ubuntu setup → SDK installs → individual sensor smoke tests (NVMe migration deferred — see BOM §1)
2. **Power rail validation** — Each buck/converter loaded with realistic current draw before being committed to the chassis
3. **Servo bring-up** — Single-servo bench tests before daisy-chaining; full chain ping before powered movement
4. **Network smoke test** — Static IPs, L2 UDP packet flow, simultaneous SSH-over-WiFi
5. **Sensor smoke test** — I2C addresses, PIR/ultrasonic returns, OLED + RGB

Full test sequence and acceptance criteria in [`BOM.md`](./BOM.md) Section 12.

---

## Setup Guide

> 📋 To be written as components arrive. Will include:
> - JetPack 6.x flash + firmware update procedure
> - NVMe rootfs migration (when NAND prices recover; see BOM §1)
> - Built-in WiFi 5 setup + BT verification
> - ROS 2 Humble + sensor SDK install scripts
> - Feetech servo ID assignment procedure
> - Network static IP configuration
> - URDF + xacro for the modified platform
> - Calibration procedures (servo zero-positioning, sensor extrinsics)

---

## Open Decisions

| # | Decision | Status | Notes |
|---|----------|--------|-------|
| 1 | Charger model | Resolved → ISDT 608AC | ~$60. AC mode ~55W ≈ 75 min for 4S 4000mAh. Charge / discharge / **storage** modes. Bag + XT60 jumper bought separately. |
| 2 | WiFi on P3766 kit | Resolved → 802.11ac/ab/gn included | Confirmed from NVIDIA P3766 datasheet (Developer Kit Content): "802.11ac/ab/gn wireless network interface controller". WiFi 5, **not** 6E. Antennas implied via product photos; verify-on-unbox. |
| 2b | Bluetooth presence on P3766 | Open | BT not explicitly listed in NVIDIA datasheet. Third-party teardowns suggest the module is RTL8822CE (WiFi 5 + BT 5.0) but unverified from NVIDIA. Verify on arrival via `hciconfig` / `bluetoothctl list`. |
| 3 | L2 12V tap: shared with hip rail vs dedicated buck | Open | Bench-test servo noise before deciding |
| 4 | SLAM stack: POINT-LIO vs RTAB-Map | Open | Compare during Phase 2 |
| 5 | Bus master: Pattern A (Jetson direct) vs Pattern B (Teensy) | Resolved → A default, B PCB-ready | PCB v6 hosts both via solder-bridge selector. Migration criterion: gait-loop p99 latency >5 ms during Pre-Assembly §12 step 3 → flip bridge. Zero hardware rework. |
| 6 | L2 mounting position | Resolved → top-center on riser | Symmetric 360° FOV, minimal yaw moment |
| 7 | Horn spline verification | Resolved → absorbed into leg redesign | |
| 8 | NVMe SSD purchase | Deferred → NAND shortage | May-2026 NAND flash shortage 2-3x'd 1TB SSD prices ($60→$165-220). Revisit when prices recover (<~$100 for 1TB) or storage becomes a measured bottleneck. Run from 128GB microSD until then. |
| 9 | v1 scope: arm included vs deferred | Resolved → arm deferred to Phase 4 | 12 active servos (4 hip + 8 femur/tibia). 6 arm servos on shelf. Bus IDs 13-18 + arm-rail buck footprint reserved on PCB v6. |
| 10 | Power rail strategy | Resolved → Pololu D42V110-class modules | XL4016 8A cont. inadequate for walking-gait + impact transients. Replaced with D42V110F7 (leg) + D42V110F12 (hip+L2) + D42V55F12 (Jetson). Arm rail D42V55F7 footprint reserved. See [`docs/power-budget.md`](./docs/power-budget.md). |
| 11 | Safety scope | Resolved → full | 608AC LVC alarm + E-stop on servo rails + INA226 per-rail telemetry + MOSFET hard-cutoff @ 12.4V. ~$30 BOM add. |
| 12 | Phase 4 COM-shift compensation | Open (Phase 4) | Arm extension + payload mass shifts support polygon; gait controller needs arm-state input to stay stable. Design when arm install begins. |
| 13 | Bus integrity strategy at 12 nodes / 1 Mbps | Open (measure first) | PCB v6 includes footprints for series R + ferrite beads + star ground. Single-ended TTL — **not** RS-485, so 120 Ω differential termination is not the right tool. Populate iteratively based on measured error rate; drop baud if needed. |

---

## References & Credits

- **Original NovaSM3** by SovGVD — [GitHub](https://github.com/SovGVD/NovaSM3) — base platform, PCB design, chassis geometry
- **mogar/spot_micro** — ROS 2 reference for quadruped IK and gait
- **discodyer/unitree_lidar_ros2** — ROS 2 wrapper for Unitree L2
- **Feetech SCServo SDK** — TTL bus driver
- **NVIDIA Jetson AI Lab** — JetPack documentation, VLA model deployment guides
- **POINT-LIO** — Unitree-recommended LiDAR-inertial SLAM
- **Nova Discord community** — Build gotchas, assembly tips

---

## Project Status Log

| Date | Milestone |
|------|-----------|
| 2026-05-15 | BOM v3 finalized, README v1 created |
| 2026-05-15 | BOM v3.1 — NVMe deferred (NAND shortage), charger resolved to ISDT 608AC, WiFi confirmed included |
| 2026-05-15 | D24V50F12 → D42V55F12 buck swap (older Pololu family deprecated) |
| 2026-05-15 | BOM v3.2 — v1 scope narrowed to quadruped only; arm to Phase 4. Power rails redesigned (XL4016 → Pololu D42V110-class). Full safety scope adopted (LVC + E-stop + INA226 + MOSFET hard-cutoff). PCB v5.2b → v6 redesign. |
| TBD | Phase 0 → Phase 1 transition (parts in hand) |
| TBD | First successful walk gait |

---

*This is a learning project as much as a research one. Decisions and tradeoffs are documented openly so others can fork and adapt.*
