# NovaSM3 — Modified Quadruped Robot with VLA Integration

> A modified [NovaSM3](https://github.com/SovGVD/NovaSM3) quadruped platform rebuilt around a unified Feetech STS3215 TTL servo bus, NVIDIA Jetson Orin Nano Super compute, and ROS 2 Humble — designed as a platform for Vision-Language-Action (VLA) model deployment, 3D SLAM, and autonomous mobile manipulation.

**Status:** 🔧 Phase 0 — Pre-build setup (CAD + parts ordering)
**Platform:** Quadruped (12 DOF) — arm (6-DOF, Phase 4 future) on shelf
**Compute:** NVIDIA Jetson Orin Nano Super 8GB
**Middleware:** ROS 2 Humble
**Last updated:** May 16, 2026 (BOM v3.4)

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
- **The Pi** with an NVIDIA Jetson Orin Nano Super (67 TOPS sparse INT8 / ~33 TOPS dense; 8GB RAM tight but workable for VLA inference + ROS 2 + SLAM — see Phase 4 notes). Real-time servo bus is offloaded to a Teensy 4.1 (Pattern B); Jetson runs ROS 2 + perception only.
- **The stock perception** with Intel RealSense D456 (depth + RGB + IMU) and Unitree L2 4D LiDAR (360° × 96° FOV, 30m range)
- **The stock locomotion stack** with ROS 2 Humble (Jetson) + Teensy bus master (Pattern B) + Nav2 + RTAB-Map / POINT-LIO

The arm is carried over from a prior SO-ARM101 build, also Feetech-based. **v1 build scope: quadruped only (12 servos active).** Arm install + integration is Phase 4 future work — bus IDs 13-18 and the 7.5V arm-rail buck footprint (D42V55F7) are reserved on the PCB v6 redesign so the future install is a populate-and-go.

### Goals

- ✅ Unified TTL servo bus across locomotion (12 servos v1; future-ready for 18 with arm)
- 🔧 ROS 2 locomotion via micro-ROS bridge to Teensy 4.1 (Teensy owns the Feetech bus in Pattern B; FE-URT-1 retained as bench fallback)
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
| Power | 3S 11.1V LiPo | 4S 14.8V LiPo + Pololu buck rails (7.5V leg / 12V hip / 12V L2 dedicated / 12V Jetson / 5V aux). XL4016 dropped after capacity audit. |
| Print materials | PLA / PETG | PA6-CF / PETG-CF / TPU 95A |

### Why we're redesigning the PCB (v5.2b → v6)

After the v3.2 architecture audit, the stock Nova PCB v5.2b can't host the upgraded power tree (Pololu modules, INA226 telemetry, hard-cutoff MOSFET, E-stop chain) or the Pattern A/B bus master selector. The redesign retains the spirit of the stock board (Arduino Nano aux slot, battery input geometry) and adds the new safety + power architecture. Full feature set in [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md).

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
│   • Nav2, SLAM, VLA inference, sensor fusion                       │
│   • Sends /joint_commands to Teensy via micro-ROS over USB         │
│   • Built-in WiFi 5 (802.11ac/ab/gn) per NVIDIA P3766 spec sheet   │
└──┬──────────┬─────────────┬─────────────┬───────────────────────────┘
   │ USB-C    │ USB 3.1     │ Ethernet    │ USB (micro-ROS transport)
   │          │             │             │
┌──▼───────┐ ┌▼───────────┐ ┌▼───────────┐ ┌▼─────────────────────────┐
│ Realsense│ │ FE-URT-1   │ │ Gig switch │ │ Teensy 4.1 (BUS MASTER v1)│
│ D456     │ │ (debug/    │ │            │ │  • Real-time gait loop    │
│ (depth + │ │  bench     │ │ ◄─ L2 ─►   │ │  • UART → 74HC125 → bus   │
│  RGB +   │ │  fallback) │ │            │ │  • INA226 I²C reader      │
│  IMU)    │ │            │ └────────────┘ │  • E-stop GPIO sense      │
└──────────┘ └────┬───────┘                │  • micro-ROS over USB     │
                  ↓                        └──┬────────────────────────┘
              (JP_BUS_MASTER                  │ UART → 74HC125 half-duplex
               solder bridge:                 │ (active v1 path)
               default = B,                   │
               flip to A for ID setup)        ▼
                                  ┌───────────────────────┐
                                  │ 12× STS3215 (TTL bus) │
                                  │  IDs 1-4:  hips       │
                                  │  IDs 5-12: f/tib      │
                                  │  IDs 13-18: ⏸ arm    │
                                  │  (Phase 4 reserved)   │
                                  └───────────────────────┘

       ┌──── Arduino Nano (separate I²C, aux only:
       │                   PIR, OLED, RGB, MP3, ultrasonic, MPU-6050) ────┐
       │                                                                  │
       └──────────────────────────────────────────────────────────────────┘
```

### Servo configuration

| Joint group | Count | Servo | Voltage | Bus IDs | Status |
|-------------|-------|-------|---------|---------|--------|
| Hips | 4 | STS3215 30kg | 12V | 1-4 | v1 active |
| Femur + tibia | 8 | STS3215 19kg | 7.4V | 5-12 | v1 active |
| Arm (shoulder + elbow) | 3 | STS3215 19kg | 7.4V | 13-15 | ⏸ Phase 4 — reserved |
| Arm (wrist + gripper) | 3 | STS3215 19kg | 7.4V | 16-18 | ⏸ Phase 4 — reserved |

**v1 build = 12 active servos** on a single daisy-chained TTL bus, 2 active servo-power voltage levels (7.5V leg, 12V hip) plus dedicated 12V/2.6A L2 LiDAR buck and 12V/3A Jetson buck. Bus master is the **Teensy 4.1 (Pattern B)** via a 74HC125 half-duplex driver. Bus IDs 13-18 and the 7.4V arm rail (D42V55F7 footprint) reserved on PCB v6 for Phase 4 arm install — populate-and-go.

### Bus master pattern

**Pattern B is v1 default.** Both paths live on PCB v6 via solder bridge `JP_BUS_MASTER`.

- **Pattern B (v1 active):** Teensy 4.1 hardware UART → 74HC125 quad tri-state buffer (half-duplex driver) → TTL bus pads. Bare-metal real-time loop at 200-500 Hz. Jetson sends joint targets via micro-ROS over USB; Teensy translates to bus reads/writes. Survives Jetson restarts, kernel preemption, CUDA stalls, journald flushes — none of which affect bus servicing. Solder bridge defaults to B.
- **Pattern A (bench / debug fallback):** Jetson → USB → FE-URT-1 → TTL bus. Use for: initial servo ID assignment with the Feetech FD / SCServo SDK Python tools from a workstation (simpler than booting micro-ROS for ID setup), debug if Teensy firmware misbehaves, post-mortem inspection of bus traffic. Flip `JP_BUS_MASTER` to A.

**Why B as default (decision history):** Linux is not a real-time OS. USB-CDC latency on Jetson runs 1-10 ms typical, 50 ms+ under load. **What Pattern B actually buys:** bus-servicing isolation on the Teensy side — UART transactions to all 12 servos complete on time even when Jetson is jittery, so the bus doesn't time out and servos don't fault. The gait controller still runs on Jetson and publishes targets at 100 Hz, so Jetson's command rate is still Linux-bounded; the Teensy oversamples at 200-500 Hz against the last received target, holding it through Jetson stalls. A 100 ms Linux freeze becomes "robot pauses mid-step," not "bus dies and robot falls." v3.2 originally defaulted to A with "migrate if measurement forces it" — v3.3 flips to B-default because the migration cost is just populating one $1 IC + Phase 1 firmware work, and skipping the measure-then-migrate path eliminates a Phase 2 surprise. See Open Decisions row 5.

**Phase 1 acceptance gate (revised):** Pattern B's real guarantee is bus-servicing isolation on the Teensy side, not full RTT through Linux. Two mandatory criteria + one sanity check:
1. **Teensy local loop tick jitter p99 <100 µs** over 60 seconds (bare-metal — easy if firmware is right)
2. **`/joint_commands` arrival rate ≥99% of 100 Hz target** over 60 seconds (Jetson + uROS healthy)
3. *(Sanity)* End-to-end RTT median <5 ms, p99 <20 ms — Linux-bounded, not a hard pass/fail

If (1) misses → debug Teensy firmware (DMA vs ISR, UART config). If (2) misses → debug Jetson uROS / USB cable / CPU contention. If only (3) is high → accept: Teensy holds last command under Jetson jitter, robot stays stable.

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
│            Locomotion Layer (Jetson)         │
│  • Gait controller (8-phase walk)            │
│  • 3-DOF-per-leg IK solver                   │
│  • Publishes /joint_commands                 │
│  • Subscribes /joint_states                  │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│        Bus Master Layer (Teensy 4.1)         │
│  • micro-ROS client (USB transport)          │
│  • SCServo SDK port — Feetech bus driver     │
│  • 74HC125 half-duplex TX/RX gating          │
│  • Real-time loop @ 200-500 Hz               │
│  • INA226 I²C reader → /diagnostics          │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│              Hardware Layer                  │
│  • Feetech STS3215 bus (12 servos v1)        │
│  • IMU driver, aux peripheral I/O            │
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
| SCServo SDK (Teensy port) | Feetech bus driver running on Teensy in Pattern B | ⚠️ Already familiar from SO-ARM101 — port to TeensyDuino in Phase 1 |

---

## Power System

### Voltage rails

```
4S LiPo 14.8V nominal (12.8-16.8V)
   │  ANL 30A fuse · MOSFET reverse-protection · MOSFET hard-cutoff @12.4V · E-stop NC (servo rails only)
   │
   ├── Pololu D42V110F7  ──► 7.5V/10A ──► 8× STS3215 19kg femur/tibia
   │       (star injection at 4 points along chain, bulk caps near point of load)
   │
   ├── Pololu D42V110F12 ──► 12V/9A   ──► 4× STS3215 30kg hips ONLY
   │
   ├── Pololu D24V22F12  ──► 12V/2.6A ──► Unitree L2 LiDAR (1A, LC filter on output)
   │
   ├── Pololu D42V55F12  ──► 12V/~3A  ──► Jetson Orin Nano (barrel jack)
   │
   ├── [reserved D42V55F7] ► 7.5V/3-8A ──► 6× STS3215 arm (Phase 4 — footprint unstuffed)
   │
   └── UBEC 5V/5A ──► 5V rail ──► Ethernet switch, fans, aux 5V peripherals

   INA226 ×3 (leg 7.5V, hip 12V, Jetson 12V) ──► I²C ──► Teensy 4.1 ──► ROS 2 diagnostics
   13.0V comparator ──► Teensy GPIO ──► /battery_low ──► Jetson clean shutdown
   12.4V comparator ──► MOSFET ──► breaks battery feed (autonomous backstop)
```

### Notes

- All rails share a common ground
- Jetson MAXN peak power ~25W → 2.1A at 12V, plus USB peripherals (D456 streaming ~2-3W, FE-URT-1 ~0.5W) → **~2.5A continuous worst case**. **Pololu D42V55F12** derates to ~3A continuous at 14.8V Vin (4.5A typ headline is at 42V Vin) → **~1.2× headroom**. Modest, not generous; watch thermal under sustained VLA inference + RealSense stream + Nav2 planning. Min Vin 12V — set LiPo LVC alarm at 3.3V/cell = 13.2V to stay above dropout.
- **Leg rail D42V110F7** (10A typ @ 42V Vin, derates at 14.8V Vin) sized for walking-gait avg 5-8A with bulk caps absorbing 25-40A impact transients near each star injection point. See [`docs/power-budget.md`](./docs/power-budget.md).
- **Hip rail D42V110F12** (9A typ @ 42V Vin) sized for 4× 30kg hips only — sustained avg ~8A. L2 LiDAR was moved off this rail to a dedicated D24V22F12 buck (v3.4) because combined hip+L2 load was margin-thin under 14.8V Vin derating.
- **L2 LiDAR rail D24V22F12** (2.6A / 12V / 36V Vin max) — dedicated buck for the LiDAR's 1A draw with LC filter on output. Clean power, no servo transient ringing.
- **Battery low-voltage chain** (ordered by trip point):
  1. **13.2V** — 608AC charger LVC alarm beeps (user-facing warning)
  2. **13.0V** — graceful-shutdown comparator → Teensy `/battery_low` topic → Jetson `systemctl poweroff` (clean SD unmount). ~30-60s window before hard cutoff.
  3. **12.4V** — autonomous MOSFET hard-cutoff on battery feed (drops everything; Jetson should already be shut down per #2)
- **E-stop** kills leg + hip + L2 rail enables (LiDAR stops spinning) — Jetson rail stays alive for post-mortem debug + telemetry capture.
- L2 self-heats below 30°C ambient; ~30-60s delay before point cloud output on cold boots
- LC filter sits on the D24V22F12 output to clean any switching ripple before the L2 input (UDP packet loss is the failure mode)

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
| Power + safety | ~$338 (Pololu rails + INA226 + E-stop + MOSFET hard-cutoff + graceful-shutdown comparator) |
| Mechanical + hardware | ~$110 |
| Sensors (stock Nova) | ~$76 |
| Filament + Bambu accessories | ~$700 (− Magigoo via Bambu liquid glue substitution) |
| Wiring + consumables | ~$80 |
| **Realistic total** | **~$2,993** (v3.4: XT60 via Ovonic + Bambu glue substitution save $28) |

---

## Build Roadmap

### Phase 0 — Pre-build setup (current)

3-week sequenced plan in [`docs/work-schedule.md`](./docs/work-schedule.md). Front-loads leg-joint CAD + prints; reserves 2026-05-29 away-week for laptop-only PCB schematic work in KiCad.

- [x] Define modified BOM (v3.4: Pattern B default, Pololu 4-buck split incl. dedicated L2, full safety, arm deferred)
- [x] Validate component compatibility (Jetson power rail, Feetech bus, L2 ethernet)
- [x] Pick LiPo charger → **ISDT 608AC**
- [x] Power rail audit (XL4016 → Pololu D42V110-class)
- [x] Confirm v1 scope = quadruped only (arm → Phase 4)
- [x] Bus master decision → Pattern B (Teensy + 74HC125) v1 default
- [x] Set up GitHub repo with this README and BOM

**Week 1 (2026-05-15 → 2026-05-22):**
- [ ] OnShape: import STS3215 + NovaSM3 reference geometry, caliper-measure on-hand servos, first-article leg-joint print
- [ ] Install KiCad 8.x + Pololu library on laptop; cache datasheets for offline use during away-week
- [ ] Back up LeRobot Pi SD contents
- [ ] Create NVIDIA Developer account, download JetPack 6.x image

**Week 2 (2026-05-22 → 2026-05-28):**
- [ ] Finish leg CAD, queue all 12 prints
- [ ] During prints: flash Jetson, install ROS 2 Humble + sensor SDKs, smoke-test D456
- [ ] PlatformIO + TeensyDuino + micro-ROS Teensy firmware skeleton (compile-green, no servo test yet)

**Week 3 — Away (2026-05-29 → 2026-06-05, laptop only):**
- [ ] PCB v6 schematic + layout in KiCad — see [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md)
- [ ] Backup: continue Teensy firmware / URDF / ROS 2 scaffolding if PCB stalls or finishes early

**Week 4+ (back to shop):**
- [ ] Bench-validate prints; submit Gerbers to PCBWay (~$60); continue Phase 1 hardware bring-up
- [ ] Order remaining parts (switch, Pololu bucks ×4, charger bundle, safety parts, accessories) — NVMe deferred

### Phase 1 — Hardware bring-up (weeks 1-4)

- [ ] Flash JetPack 6.x to microSD; firmware update Jetson if needed
- [ ] Boot Jetson, complete Ubuntu setup
- [ ] Verify pre-installed WiFi works; install AX210NGW only if missing. Confirm BT presence.
- [ ] Install ROS 2 Humble + librealsense2 + unilidar_sdk2 (run from 128GB microSD; NVMe deferred)
- [ ] D456 standalone test (`realsense-viewer`)
- [ ] L2 standalone test (included 12V adapter + rviz2)
- [ ] Print parts: Bambu P1S + PA6-CF (dry 24h before each print)
- [ ] Bench-validate Pololu D42V55F12 / D42V110F7 / D42V110F12 / D24V22F12 / UBEC 5V (per BOM §12 step 2)
- [ ] Verify E-stop chain + MOSFET hard-cutoff @ 12.4V + INA226 I²C reads
- [ ] **Write Teensy firmware** (Pattern B critical path) — micro-ROS client + SCServo SDK port + 74HC125 TX/RX gating
- [ ] ID setup pass: flip `JP_BUS_MASTER` to A (FE-URT-1), assign servo IDs **1-12** (v1 active), label each. IDs 13-18 reserved for Phase 4.
- [ ] Flip `JP_BUS_MASTER` back to B (default). Verify Teensy firmware drives single servo, then full 12-servo chain.
- [ ] **Acceptance gate** (two mandatory + one sanity, see "Bus master pattern" section): Teensy tick jitter p99 <100 µs + `/joint_commands` arrival ≥99% of 100 Hz + RTT median <5 ms / p99 <20 ms. Pattern A is not a workaround if (1) or (2) miss.
- [ ] Assemble legs (redesigned for STS3215 dimensions)
- [ ] Assemble chassis, mount L2 on top-center riser
- [ ] Network setup: eth0 static 192.168.1.2; verify L2 UDP flow
- [ ] Arduino Nano: strip code to aux peripherals only
- [ ] Stand / sit test on hardware (no walk yet)

### Phase 2 — Locomotion (weeks 5-8)

- [ ] Implement 3-DOF-per-leg IK solver (reference mogar/spot_micro)
- [ ] 8-phase walk gait controller on Jetson — publishes `/joint_commands` to Teensy via micro-ROS
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
| 2b | Bluetooth presence on P3766 | **Resolved → BT 5.1 confirmed (Realtek)** | Verified 2026-05-17 on hardware: `hciconfig -a` shows `hci0` UP RUNNING, Manufacturer "Realtek Semiconductor Corporation", HCI Version 5.1, BD Address 9C:C7:D3:F6:AC:5C. `bluetoothctl list` confirms controller present. |
| 3 | L2 12V tap: shared with hip rail vs dedicated buck | **Resolved → dedicated D24V22F12** (v3.4) | Combined hip+L2 load was margin-thin on D42V110F12's 9A typ at 14.8V Vin derating. Split L2 to its own buck for $19 extra. Cleaner power, more hip-rail headroom. |
| 4 | SLAM stack: POINT-LIO vs RTAB-Map | Open | Compare during Phase 2 |
| 5 | Bus master: Pattern A (FE-URT-1) vs Pattern B (Teensy) | **Resolved → B is v1 default** | Linux jitter (USB-CDC 1-10 ms typical, 50 ms+ under load) is unacceptable at 100 Hz gait. Teensy bare-metal UART gives hard real-time. PCB v6 keeps Pattern A via `JP_BUS_MASTER` bridge for bench / ID setup / debug. Phase 1 acceptance: p99 <2 ms ROS 2 → Teensy → bus. |
| 6 | L2 mounting position | Resolved → top-center on riser | Symmetric 360° FOV, minimal yaw moment |
| 7 | Horn spline verification | Resolved → absorbed into leg redesign | |
| 8 | NVMe SSD purchase | Deferred → NAND shortage | May-2026 NAND flash shortage 2-3x'd 1TB SSD prices ($60→$165-220). Revisit when prices recover (<~$100 for 1TB) or storage becomes a measured bottleneck. Run from 128GB microSD until then. |
| 9 | v1 scope: arm included vs deferred | Resolved → arm deferred to Phase 4 | 12 active servos (4 hip + 8 femur/tibia). 6 arm servos on shelf. Bus IDs 13-18 + arm-rail buck footprint reserved on PCB v6. |
| 10 | Power rail strategy | Resolved → 4-buck Pololu split | XL4016 8A cont. inadequate. v3.4 active rails: D42V110F7 (leg 7.5V), D42V110F12 (hip 12V only), D24V22F12 (L2 12V dedicated), D42V55F12 (Jetson 12V). Arm rail D42V55F7 footprint reserved. See [`docs/power-budget.md`](./docs/power-budget.md). |
| 11 | Safety scope | Resolved → full | 608AC LVC alarm at 13.2V (warning) + 13.0V graceful-shutdown comparator → Jetson clean poweroff + 12.4V MOSFET hard-cutoff (autonomous backstop) + E-stop on leg/hip/L2 rail enables + INA226 ×3 per-rail telemetry. ~$37 BOM add. |
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
| 2026-05-15 | BOM v3.3 — Bus master flipped: **Pattern B (Teensy + 74HC125) is v1 default**. Pattern A (FE-URT-1) kept as bench / debug fallback via solder bridge. Teensy firmware becomes Phase 1 critical path. |
| 2026-05-15 | 3-week work schedule committed ([`docs/work-schedule.md`](./docs/work-schedule.md)): leg-joint CAD on OnShape now, prints week 2, PCB v6 schematic in KiCad during 2026-05-29 away-week. |
| 2026-05-16 | BOM v3.4 — L2 LiDAR split off hip rail onto dedicated D24V22F12 buck after Pololu datasheet check showed D42V110F12's 9A typ @ 42V Vin derates below combined hip+L2 ~9A load at 14.8V Vin. +$19. |
| 2026-05-16 | Two-pass internal audit: Pass 1 swept 7.4V/7.5V mismatches + stale version markers + stale L2 references + section numbering; Pass 2 reframed Phase 1 acceptance gate (Teensy tick jitter + uROS arrival rate, not RTT), clarified Pattern B benefit framing, extended E-stop to kill L2 rail too, added 13.0V graceful-shutdown comparator before 12.4V hard cutoff, noted pre-PCB ID-setup path, reconciled Jetson headroom (~1.2× incl. peripherals). +$3 safety, total ~$3,015. |
| 2026-05-16 | Order status updates: ISDT 608AC + LiPo safe bag + Mxuteuk HB2-ES544 E-stop ordered. Ovonic 4S kit confirmed to include XT60 jumper + charging lead (−$13). Bambu Lab Liquid Glue substituted for Magigoo PA (−$15, with print-test gate to fallback if PA6-CF adhesion fails). Realistic total $3,015 → $2,993. |
| 2026-05-16 | LeRobot Pi SD backed up to `~/Backups/lerobot-pi-128gb-2026-05-16.img.gz` (SHA256 recorded in [`docs/backups.md`](./docs/backups.md)). Card reformatted for Jetson. |
| 2026-05-17 | Jetson Orin Nano Super: flashed JetPack 6.2.1 SD image → apt full-upgrade → **JetPack 6.2.2 / L4T 36.5 running**. MAXN_SUPER power mode set (mode 2 on this Dev Kit, not 0). Three first-boot networking gotchas hit + documented in [`docs/setup-network.md`](./docs/setup-network.md): (1) oem-config WPA association fails — skip + connect from CLI; (2) l4tbr0 USB-C bridge hijacks default route — unplug or lower WiFi metric; (3) NetworkManager doesn't write `/etc/resolv.conf` on this image — manually populate + `chattr +i` to lock immutable. |
| 2026-05-17 | **Open decision 2b resolved:** Bluetooth confirmed present on P3766 — Realtek, BT 5.1, `hci0` up. |
| TBD | Phase 0 → Phase 1 transition (parts in hand) |
| TBD | First successful walk gait |

---

*This is a learning project as much as a research one. Decisions and tradeoffs are documented openly so others can fork and adapt.*
