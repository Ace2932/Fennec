# NovaSM3 — Modified Quadruped Robot with VLA Integration

> A modified [NovaSM3](https://github.com/SovGVD/NovaSM3) quadruped platform rebuilt around a unified Feetech STS3215 TTL servo bus, NVIDIA Jetson Orin Nano Super compute, and ROS 2 Humble — designed as a platform for Vision-Language-Action (VLA) model deployment, 3D SLAM, and autonomous mobile manipulation.

**Status:** 🔧 Phase 1 — Build & Bring-Up
**Platform:** Quadruped (12 DOF) + 6-DOF arm
**Compute:** NVIDIA Jetson Orin Nano Super 8GB
**Middleware:** ROS 2 Humble
**Last updated:** May 15, 2026 (BOM v3.1)

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

- **All 18 servos** with Feetech STS3215 TTL bus servos for unified protocol, real-time joint feedback (position, load, temperature, voltage), and elimination of PWM wiring complexity
- **The Pi** with an NVIDIA Jetson Orin Nano Super (67 TOPS, suitable for VLA inference on-board)
- **The stock perception** with Intel RealSense D456 (depth + RGB + IMU) and Unitree L2 4D LiDAR (360° × 96° FOV, 30m range)
- **The stock locomotion stack** with ROS 2 Humble + Nav2 + RTAB-Map / POINT-LIO

The arm is carried over from a prior SO-ARM101 build, also Feetech-based, allowing all 18 joints to live on a single daisy-chained TTL bus.

### Goals

- ✅ Unified TTL servo bus across locomotion + manipulation (18 servos, one protocol)
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
| Arm | None (stock) | 6× Feetech STS3215 (carried over from SO-ARM101) |
| Servo protocol | PWM (one signal per servo) | TTL half-duplex serial bus (daisy-chained) |
| Perception | None / optional | RealSense D456 + Unitree L2 LiDAR |
| Middleware | Custom Arduino loops | ROS 2 Humble + micro-ROS |
| Power | 3S 11.1V LiPo | 4S 14.8V LiPo + dual-rail (6.8V + 12V) |
| Print materials | PLA / PETG | PA6-CF / PETG-CF / TPU 95A |

### What is reused from the Nova PCB

The NovaSM3 v5.2b PCB is retained for:
- Battery input + reverse polarity protection
- One of the 12A buck converter footprints (6.8V rail)
- Power switch, voltmeter, fuse
- Arduino Nano slot for aux peripherals (PIR, ultrasonic, OLED, RGB LEDs, MP3, IMU)

### What is bypassed on the Nova PCB

- All 12 PWM servo output headers (Feetech bus doesn't use PWM)
- Any Teensy code driving Servo.h / PWMServo.h

---

## Hardware Architecture

### Block diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                  NVIDIA Jetson Orin Nano Super 8GB                 │
│                          (ROS 2 Humble)                            │
│   • Locomotion, Nav2, SLAM, VLA inference, sensor fusion           │
│   • Built-in WiFi 5 (802.11ac) + antennas (included in P3766 kit)  │
└──┬──────────┬─────────────┬─────────────┬───────────────────────────┘
   │ USB-C    │ USB 3.1     │ Ethernet    │ USB
   │          │             │             │
┌──▼───────┐ ┌▼───────────┐ ┌▼───────────┐ ┌▼─────────┐
│ Realsense│ │ FE-URT-1   │ │ Gig switch │ │ Teensy   │
│ D456     │ │ USB→TTL    │ │            │ │ 4.1      │
│ (depth + │ │            │ │ ◄─ L2 ─►   │ │ (μROS)   │
│  RGB +   │ └────┬───────┘ └────────────┘ └──┬───────┘
│  IMU)    │      │                           │
└──────────┘      │ TTL half-duplex           │ I2C / GPIO
                  │                           │
        ┌─────────▼─────────┐         ┌──────▼──────┐
        │ 18× STS3215       │         │ Arduino Nano│
        │ daisy-chained     │         │ (aux only:  │
        │                   │         │  PIR, OLED, │
        │ IDs 1-12: legs    │         │  RGB, MP3,  │
        │ IDs 13-18: arm    │         │  ultrasonic,│
        │                   │         │  MPU-6050)  │
        └───────────────────┘         └─────────────┘
```

### Servo configuration

| Joint group | Count | Servo | Voltage | Bus IDs |
|-------------|-------|-------|---------|---------|
| Hips | 4 | STS3215 30kg | 12V | 1-4 |
| Femur + tibia | 8 | STS3215 19kg | 7.4V | 5-12 |
| Arm (shoulder + elbow) | 3 | STS3215 19kg | 7.4V | 13-15 |
| Arm (wrist + gripper) | 3 | STS3215 19kg (existing) | 7.4V | 16-18 |

All 18 share a single daisy-chained TTL bus. Power is split across two voltage rails but data is unified.

### Bus master pattern

Two viable patterns; **Pattern A is current**:

- **Pattern A (current):** Jetson → USB → FE-URT-1 → TTL bus. Simple, matches SO-ARM101 architecture. Acceptable latency for walking gaits. Risk: Jetson restart kills servo commands.
- **Pattern B (future):** Teensy 4.1 owns the bus via hardware UART + half-duplex driver circuit; Jetson sends joint targets via micro-ROS. Hard real-time, survives Jetson restarts. Requires building a half-duplex driver (1 transistor or TXS0108).

Migration to B happens only if measured latency or robustness becomes a problem.

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
│  • Gait controller                           │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│              Perception Layer                │
│  • RTAB-Map / POINT-LIO (3D SLAM)            │
│  • realsense2_camera                         │
│  • unitree_lidar_ros2                        │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│               Hardware Layer                 │
│  • Feetech SCServo SDK (joint state + cmd)   │
│  • micro-ROS bridge (Teensy ↔ Jetson)        │
│  • IMU driver, peripheral I/O                │
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
   │
   ├── XL4016 #1 ──► 6.8V rail ──► 14× STS3215 7.4V/19kg (8 leg + 6 arm)
   │
   ├── XL4016 #2 ──► 12V rail  ──┬── 4× STS3215 12V/30kg (hips)
   │                              └── (LC filter) ──► Unitree L2 LiDAR (12V/1A)
   │
   ├── Pololu D24V50F12 ──► 12V ──► Jetson Orin Nano (barrel jack, 7-20V tolerant)
   │
   └── UBEC 5V/5A ──► 5V rail ──► Ethernet switch, fans, aux 5V peripherals
```

### Notes

- All rails share a common ground
- Jetson MAXN peak power ~25W → ~2.1A at 12V (well within Pololu D24V50F12 5A rating)
- L2 self-heats below 30°C ambient; ~30-60s delay before point cloud output on cold boots
- LC filter on the L2 12V tap is required if shared with the hip servo rail to prevent servo current noise from causing UDP packet loss

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
| Servos | ~$320 (+ 6 carried over from SO-ARM101) |
| Power + safety | ~$215 |
| Mechanical + hardware | ~$110 |
| Sensors (stock Nova) | ~$76 |
| Filament + Bambu accessories | ~$700 |
| Wiring + consumables | ~$80 |
| **Realistic total** | **~$2,805** (ISDT 608AC charger) |

---

## Build Roadmap

### Phase 0 — Pre-build setup (current)

- [x] Define modified BOM
- [x] Validate component compatibility (Jetson power rail, Feetech bus, L2 ethernet)
- [x] Pick LiPo charger → **ISDT 608AC**
- [ ] Order remaining parts (switch, D24V50F12, charger bundle, accessories) — NVMe deferred
- [ ] Set up GitHub repo with this README and BOM
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
- [ ] Bench-validate Pololu D24V50F12, XL4016 #1/#2, UBEC 5V
- [ ] Set Feetech servo IDs 1-18, label each
- [ ] Single-servo SCServo SDK test from Jetson via FE-URT-1
- [ ] Full 18-servo daisy chain ping test
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

### Phase 4 — Manipulation + VLA (weeks 13+)

- [ ] Arm joint state integration into unified URDF
- [ ] MoveIt 2 motion planning for arm
- [ ] VLA model selection (OpenVLA / Pi0 / RT-2 class)
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
| 2 | WiFi on P3766 kit | Resolved → included with dev kit | 802.11ac/abgn pre-installed per official spec. WiFi 5, **not** 6E. Order AX210NGW only if missing on arrival. |
| 2b | Bluetooth presence on P3766 | Open | BT not explicitly listed in NVIDIA spec — verify on arrival |
| 3 | L2 12V tap: shared with hip rail vs dedicated buck | Open | Bench-test servo noise before deciding |
| 4 | SLAM stack: POINT-LIO vs RTAB-Map | Open | Compare during Phase 2 |
| 5 | Bus master: Pattern A (Jetson direct) vs Pattern B (Teensy) | Resolved → A | Migrate to B only if measured latency problems |
| 6 | L2 mounting position | Resolved → top-center on riser | Symmetric 360° FOV, minimal yaw moment |
| 7 | Horn spline verification | Resolved → absorbed into leg redesign | |
| 8 | NVMe SSD purchase | Deferred → NAND shortage | May-2026 NAND flash shortage 2-3x'd 1TB SSD prices ($60→$165-220). Revisit when prices recover (<~$100 for 1TB) or storage becomes a measured bottleneck. Run from 128GB microSD until then. |

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
| 2026-05-15 | BOM v3.1 — NVMe deferred due to NAND shortage, charger resolved to ISDT 608AC, WiFi confirmed included |
| TBD | Phase 0 → Phase 1 transition (parts in hand) |
| TBD | First successful walk gait |

---

*This is a learning project as much as a research one. Decisions and tradeoffs are documented openly so others can fork and adapt.*
