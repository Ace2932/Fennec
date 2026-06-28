# NovaSM3 — Modified Quadruped Robot with VLA Integration

> A modified [NovaSM3](https://github.com/cguweb-com/Arduino-Projects/tree/main/Nova-SM3) quadruped platform (by Chris Locke / [novaspotmicro.com](https://novaspotmicro.com/)) rebuilt around a unified Feetech STS3215 TTL servo bus, NVIDIA Jetson Orin Nano Super compute, and ROS 2 Humble — designed as a platform for Vision-Language-Action (VLA) model deployment, 3D SLAM, and autonomous mobile manipulation.

**Status:** 🔧 Phase 1 — hardware bring-up. Firmware critical-path green. PCB split into 2 boards: **logic board fab-ready** (routed, DRC/ERC clean); **power board** has the Phase-4 arm rail added (J14 + arm INA226 U12 + EN re-gate, F8'd) and needs placement+routing of those parts. URDF (`nova_description`) + Phase-2 leg IK/gait (`nova_locomotion`) scaffolded. **See [`STATUS.md`](./STATUS.md) for the live blockers / next-actions board.**
**Platform:** Quadruped (12 DOF) — arm (6-DOF, Phase 4 future) on shelf
**Compute:** NVIDIA Jetson Orin Nano Super 8GB
**Middleware:** ROS 2 Humble
**Last updated:** June 6, 2026 (BOM v3.4)

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
| Print materials | PLA / PETG | PA6-CF (structural) / PETG-CF (secondary) / TPU 95A (foot pads + strain relief) |
| Print feed | Direct from spool | **Creality SpacePi X4 dryer → 4 mm PTFE Bowden → P1S** (AMS HF bypassed for PA6-CF — re-absorbs moisture in AMS chamber, defeats pre-drying) |

### Why we're redesigning the PCB (v5.2b → v6)

After the v3.2 architecture audit, the stock Nova PCB v5.2b can't host the upgraded power tree (Pololu modules, INA226 telemetry, hard-cutoff MOSFET, E-stop chain) or the Pattern A/B bus master selector. The redesign retains the spirit of the stock board (Arduino Nano aux slot, battery input geometry) and adds the new safety + power architecture. Full feature set in [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md).

### What carries over from Nova v5.2b

- Arduino Nano slot for aux peripherals — **v3.5 cut**: OLED + WS2812B only (PIR / ultrasonic / MP3 / MPU-6050 removed; D456 + L2 perception stack covers their roles)
- Battery input + reverse polarity protection geometry (replicated with MOSFET-based reverse protection instead of diode)
- Power switch, voltmeter, fuse (MRBF-30 in Blue Sea 5191 block, OFF-board at pack — ~9 kA AIC @ 16.8 V clears this pack's ~1.5–3 kA dead-short with 3–4× margin; ANL's 6 kA rejected, Class T superseded 2026-06-12)

### What changes

- All 12 PWM servo output headers removed (Feetech bus is daisy-chain TTL, doesn't use PWM)
- XL4016 buck footprints → Pololu D42V110-class module footprints
- Add: SN74LVC125A half-duplex driver (Pattern B prep), INA226 ×3, E-stop chain, hard-cutoff MOSFET, **MRBF-30 fuse OFF-board** (Blue Sea 5191 at pack — F1 not on PCB), bulk caps at injection points, bus-integrity footprints (series R + ferrite beads), reserved arm-rail buck footprint

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
│ (depth + │ │  bench     │ │ ◄─ L2 ─►   │ │  • UART → SN74LVC125A → bus   │
│  RGB +   │ │  fallback) │ │            │ │  • INA226 I²C reader      │
│  IMU)    │ │            │ └────────────┘ │  • E-stop GPIO sense      │
└──────────┘ └────┬───────┘                │  • micro-ROS over USB     │
                  ↓                        └──┬────────────────────────┘
              (JP_BUS_MASTER                  │ UART → SN74LVC125A half-duplex
               solder bridge:                 │ (active v1 path)
               default = B,                   │
               flip to A for ID setup)        ▼
                                  ┌───────────────────────┐
                                  │ 12× STS3215 (TTL bus) │
                                  │ per-leg: FL1-3 FR4-6  │
                                  │ RL7-9 RR10-12 (h/f/t) │
                                  │  IDs 13-18: ⏸ arm    │
                                  │  (Phase 4 reserved)   │
                                  └───────────────────────┘

       ┌──── Arduino Nano (USB-serial bridge from Jetson:
       │                   OLED + WS2812B status LEDs) ────┐
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

**v1 build = 12 active servos** on a single daisy-chained TTL bus, 2 active servo-power voltage levels (7.5V leg, 12V hip) plus dedicated 12V/2.6A L2 LiDAR buck and 12V/3A Jetson buck. Bus master is the **Teensy 4.1 (Pattern B)** via a SN74LVC125A half-duplex driver. Bus IDs 13-18 and the 7.4V arm rail (D42V55F7 footprint) reserved on PCB v6 for Phase 4 arm install — populate-and-go.

### Bus master pattern

**Pattern B is v1 default.** Both paths live on PCB v6 via solder bridge `JP_BUS_MASTER`.

- **Pattern B (v1 active):** Teensy 4.1 hardware UART → SN74LVC125A quad tri-state buffer (half-duplex driver) → TTL bus pads. Bare-metal real-time loop at 200-500 Hz. Jetson sends joint targets via micro-ROS over USB; Teensy translates to bus reads/writes. Survives Jetson restarts, kernel preemption, CUDA stalls, journald flushes — none of which affect bus servicing. Solder bridge defaults to B.
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
│  • SN74LVC125A half-duplex TX/RX gating          │
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
| `unilidar_sdk2` | Unitree L2 SDK | ✅ Built green on Jetson (official `unitreerobotics/unilidar_sdk2`, **not discodyer fork** — official now bundles ROS 2 wrapper) |
| `unitree_lidar_ros2` | ROS 2 wrapper for L2 | ✅ Built + streaming. Use **Ace2932/unilidar_sdk2 `fix/imu-bridge-double-call` branch** — fixes upstream IMU bridge bug where `getImuData()` is called twice in `timer_callback()`, draining the SDK queue before publish. |
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
   │  MRBF-30 fuse (off-board) · MOSFET reverse-protection · MOSFET hard-cutoff @12.4V · E-stop NC (servo rails only)
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
| **Realistic total** | **~$2,963** (v3.4: XT60 via Ovonic, Bambu glue, XL4016 ×2 return save $58 total) |

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
- [x] Leg CAD complete — V5 OpenSCAD original-shell-carve (`hardware/cad/leg_v5/`, STS3215 cavity in original NovaSM3 STLs). Pending: caliper on-hand servos + first-article leg-joint print.
- [ ] Install KiCad 8.x + Pololu library on laptop; cache datasheets for offline use during away-week
- [ ] Back up LeRobot Pi SD contents
- [ ] Create NVIDIA Developer account, download JetPack 6.x image

**Week 2 (2026-05-22 → 2026-05-28):** detailed checklist in [`docs/checklists/week-2.md`](./docs/checklists/week-2.md)
- [ ] Carryover from Week 1: caliper pass + first-article leg print (V5 leg CAD itself is done)
- [ ] ROS 2 Humble + librealsense2 + unilidar_sdk2 on Jetson (Jetson already flashed + persistent — Week 1 head-start)
- [ ] PlatformIO + TeensyDuino + micro-ROS Teensy firmware skeleton (compile-green)
- [ ] KiCad install + Pololu library (PCB v6 prep for Week 3)
- [ ] Bambu Studio + PA6-CF drier preheat

**Week 3 — Away (2026-05-29 → 2026-06-05, laptop only):**
- [x] PCB v6 **schematic** captured in KiCad 9 (2026-06-03) — §1-§8 hierarchical, all 54 parts footprinted, pin-name wiring audit passed, ERC-clean (1 intentional warning: reserved arm rail). See [`hardware/pcb-mods/README.md`](./hardware/pcb-mods/README.md)
- [ ] PCB v6 **layout** + DRC + Gerber export in KiCad
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
- [ ] **Write Teensy firmware** (Pattern B critical path) — micro-ROS client + SCServo SDK port + SN74LVC125A TX/RX gating
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
- [ ] Body stabilization feedback via D456 IMU (MPU-6050 cut per BOM v3.5)
- [ ] Calibrate LiDAR ↔ RealSense extrinsics
- [ ] EKF fusion: D456 IMU + L2 IMU via `robot_localization` (MPU-6050 cut)
- [ ] RTAB-Map 3D SLAM on walking platform
- [ ] POINT-LIO comparison (LiDAR-IMU only)

### Phase 3 — Autonomy (weeks 9-12)

- [ ] Nav2 integration on legged platform
- [ ] Costmaps from D456 + L2
- [ ] Autonomous waypoint navigation
- [ ] Obstacle avoidance during walk
- [ ] Stair climbing test (gait variation)
- [ ] Telemetry dashboard

### Forward-looking backlog (opportunistic, not scheduled)

Quality-of-life software + operational features captured in [`docs/notes-qol-features.md`](./docs/notes-qol-features.md) and [`docs/notes-virtual-view-autocal.md`](./docs/notes-virtual-view-autocal.md). Pick up during Phase 1/2 idle time or batch into a "QoL sprint" once v1 walk gait is stable. Suggested rollout order (per `notes-qol-features.md`):

1. **Preflight health check** (`nova_ops`) — bus ping sweep, E-stop, battery latch. v1 ships 3 checks; rest land opportunistically. Highest payback during Phase 1 servo bring-up.
2. **`make deploy` for Teensy** — build on laptop, flash over Jetson USB, no chassis open. Needed by mid-Phase-1 firmware iteration.
3. **Always-on MCAP dashcam** with incident freeze on E-stop / fault / manual trigger. Required before first walk attempt.
4. **`nova bringup` launcher with profiles** (`bench` / `sensors` / `slam` / `walk` / `full` / `vla`) — pay back at ~6 launch files.
5. **Per-joint safety envelope** in the gait controller — position/velocity/load/temp clamping. Paired with first Phase 2 gait controller commit.
6. **Battery SoC widget** — gated on adding a 4th INA226 on battery feed (PCB v6 footprint already supports it).
7. **RGB status LED** on Arduino Nano — Phase 2 polish.
8. **Telemetry CSV writer** → optional Grafana later (resist Docker on Jetson).
9. **Bag replay harness** — Phase 3 when SLAM/Nav iteration is the bottleneck.
10. **Gazebo Fortress digital twin** — Phase 4 prep for VLA dev without HIL.

Plus auto-calibration routines (`nova_calibration` package): IMU bias zero on boot, servo zero-position auto-detect via jig, camera↔IMU + LiDAR↔IMU + LiDAR↔camera extrinsics. Foxglove bridge over Tailscale for remote browser viewing of URDF + sensors + plots.

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
5. **Sensor smoke test** — OLED + WS2812B via Arduino Nano USB-serial (PIR/ultrasonic/MPU/DFPlayer cut per BOM v3.5)

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
| 1 | Charger model | Resolved → ISDT 608AC | ~$60. AC mode ~55W ≈ 110 min for 4S 6000mAh. Charge / discharge / **storage** modes. Bag + XT60 jumper bought separately. |
| 2 | WiFi on P3766 kit | Resolved → 802.11ac/ab/gn included | Confirmed from NVIDIA P3766 datasheet (Developer Kit Content): "802.11ac/ab/gn wireless network interface controller". WiFi 5, **not** 6E. Antennas implied via product photos; verify-on-unbox. |
| 2b | Bluetooth presence on P3766 | **Resolved → BT 5.1 confirmed (Realtek)** | Verified 2026-05-17 on hardware: `hciconfig -a` shows `hci0` UP RUNNING, Manufacturer "Realtek Semiconductor Corporation", HCI Version 5.1, BD Address 9C:C7:D3:F6:AC:5C. `bluetoothctl list` confirms controller present. |
| 3 | L2 12V tap: shared with hip rail vs dedicated buck | **Resolved → dedicated D24V22F12** (v3.4) | Combined hip+L2 load was margin-thin on D42V110F12's 9A typ at 14.8V Vin derating. Split L2 to its own buck for $19 extra. Cleaner power, more hip-rail headroom. |
| 4 | SLAM stack: POINT-LIO vs RTAB-Map | Open | Compare during Phase 2 |
| 5 | Bus master: Pattern A (FE-URT-1) vs Pattern B (Teensy) | **Resolved → B is v1 default** | Linux jitter (USB-CDC 1-10 ms typical, 50 ms+ under load) is unacceptable at 100 Hz gait. Teensy bare-metal UART gives hard real-time. PCB v6 keeps Pattern A via `JP_BUS_MASTER` bridge for bench / ID setup / debug. Phase 1 acceptance gate (revised): Teensy loop p99 **<100 µs** + `/joint_commands` arrival ≥99% of 100 Hz + RTT sanity (median <5 ms, p99 <20 ms). |
| 6 | L2 mounting position | Resolved → top-center on riser | Symmetric 360° FOV, minimal yaw moment |
| 7 | Horn spline verification | Resolved → absorbed into leg redesign | |
| 8 | NVMe SSD purchase | Deferred → NAND shortage | May-2026 NAND flash shortage 2-3x'd 1TB SSD prices ($60→$165-220). Revisit when prices recover (<~$100 for 1TB) or storage becomes a measured bottleneck. Run from 128GB microSD until then. |
| 9 | v1 scope: arm included vs deferred | Resolved → arm deferred to Phase 4 | 12 active servos (4 hip + 8 femur/tibia). 6 arm servos on shelf. Bus IDs 13-18 + arm-rail buck footprint reserved on PCB v6. |
| 10 | Power rail strategy | Resolved → 4-buck Pololu split | XL4016 8A cont. inadequate. v3.4 active rails: D42V110F7 (leg 7.5V), D42V110F12 (hip 12V only), D24V22F12 (L2 12V dedicated), D42V55F12 (Jetson 12V). Arm rail D42V55F7 footprint reserved. See [`docs/power-budget.md`](./docs/power-budget.md). |
| 11 | Safety scope | Resolved → full | 608AC LVC alarm at 13.2V (warning) + 13.0V graceful-shutdown comparator → Jetson clean poweroff + 12.4V MOSFET hard-cutoff (autonomous backstop) + E-stop on leg/hip/L2 rail enables + INA226 ×3 per-rail telemetry. ~$37 BOM add. |
| 12 | Phase 4 COM-shift compensation | Open (Phase 4) | Arm extension + payload mass shifts support polygon; gait controller needs arm-state input to stay stable. Design when arm install begins. |
| 13 | Bus integrity strategy at 12 nodes / 1 Mbps | Open (measure first) | PCB v6 includes footprints for series R + ferrite beads + GND-plane reference (GND plane = single low-Z return). Single-ended TTL — **not** RS-485, so 120 Ω differential termination is not the right tool. Populate iteratively based on measured error rate; drop baud if needed. |

---

## References & Credits

- **Original NovaSM3** by Chris Locke (cguweb) — [GitHub](https://github.com/cguweb-com/Arduino-Projects/tree/main/Nova-SM3) · [novaspotmicro.com](https://novaspotmicro.com/) · [Discord](https://discord.gg/bJWgTMccUx) — base platform, chassis geometry, parts list. PCB v5.2/v5.3 reference via [PCBWay community share](https://www.pcbway.com/project/shareproject/NovaSM3_v5_2.html). Note: repo ships STL only, **no STEP** (re-model from STLs + datasheet + calipers for OnShape).
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
| 2026-05-17 | Jetson **full persistence verified across reboots**: JetPack 6.2.2, MAXN_SUPER (mode 2), `jetson_clocks.service` (systemd oneshot), DNS chattr-immutable, WiFi profile, BT. 8-point verification block lives in [`docs/setup-jetson.md`](./docs/setup-jetson.md) §11. |
| 2026-05-17 | **Week 1 substantially closed** — Jetson bring-up overtook the planned CAD-first sequence (no harm). CAD + KiCad + Teensy firmware skeleton carried to Week 2. New checklist at [`docs/checklists/week-2.md`](./docs/checklists/week-2.md). |
| 2026-05-17 | **ROS 2 Humble installed on Jetson via ros2-apt-source 1.2.0 deb (deb822 format, the new canonical method).** `ros-humble-desktop` + `python3-colcon-common-extensions` + `python3-rosdep` running. Talker/listener verified working over DDS. |
| 2026-05-17 | **Background research pass committed.** `docs/research/2026-05-17-notes.md` consolidates 14 topics: Unitree L2 SDK (use official, drop discodyer fork), POINT-LIO ROS 2 fork (dfloreaa), librealsense2 via jetsonhacks prebuilt modules, STS3215 libraries for Teensy, 74HC125 wiring, INA226 + LM393 design, MAXN_SUPER clocks verified (1.7 GHz / 1020 MHz), OpenVLA feasibility on 8GB. **Two safety/correctness fixes applied:** (a) **ANL → Class T 30A fuse** (LiPo needs 20 kA AIC, ANL only 6 kA), (b) **NovaSM3 repo URL corrected** to `cguweb-com/Arduino-Projects/Nova-SM3` (the old `SovGVD/NovaSM3` returns 404). |
| 2026-05-17 | **Unitree L2 stack built green on Jetson.** Cloned `unitreerobotics/unilidar_sdk2`, built C++ SDK + `unitree_lidar_ros2` ROS 2 wrapper. `colcon build` clean. Confirmed launch params + topics: `/unilidar/cloud` (cloud_scan_num: 18), `/unilidar/imu`, default IPs match BOM §5 (LiDAR 192.168.1.62, target 192.168.1.2 port 6101). Topic/frame mapping captured in [`docs/setup-network.md`](./docs/setup-network.md) for POINT-LIO + URDF integration. |
| 2026-05-17 | Network bundle ordered: gigabit 5-port unmanaged switch (TP-Link LS105G / NETGEAR GS305) + Cable Matters 10 Gbps snagless Cat 6 × 2-3 (1ft). $23 spend. Will unblock L2 standalone test via `ros2 launch unitree_lidar_ros2 launch.py` once delivered (~2 days). |
| 2026-05-18 | **XL4016 ×2 returned for $30 refund.** Originally specced in v3.0 BOM as the servo-rail buck pair. v3.2 audit caught the 8A continuous limit being inadequate for walking-gait + impact transients on either the 7.5V leg rail or the 12V hip rail — replaced with Pololu D42V110-class modules. XL4016 was kept in spares bin until now; return path cleaner. Realistic total $2,993 → $2,963. |
| 2026-05-18 | **Intel RealSense D456 full stack (Color + Depth + IMU) running on Jetson.** Step A: `librealsense2-utils` + `librealsense2-dev` via Intel apt repo (key FB0B24895113F120 fetched from keyserver.ubuntu.com). Step B: stock JetPack 6.2.2 kernel modules don't expose IMU — patched 3 in-tree drivers (uvc, IIO accel, IIO gyro) via `jetson-orin-librealsense` + rebuilt against L4T 36.5 sources via `jetson-orin-kernel-builder`, enabled `HID_SENSOR_HUB/ACCEL_3D/GYRO_3D` modules, ~25 min compile. Step C: `ros-humble-realsense2-camera` launched. Verified: Color 30 Hz, Depth 30 Hz, Accel 101 Hz, Gyro 200 Hz on actual hardware. Full procedure captured in [`docs/setup-jetson.md`](./docs/setup-jetson.md) §13. |
| 2026-05-18 | **Unitree L2 LiDAR streaming end-to-end.** Wired L2 ↔ Cat 6 ↔ gigabit switch ↔ Cat 6 ↔ Jetson `enP8p1s0` (192.168.1.2/24 static via `nmcli connection nova-lan`). Ping to L2 (192.168.1.62) at 0.1 ms. `ros2 launch unitree_lidar_ros2 launch.py` brings up `/unilidar/cloud` at **12 Hz, 5042 points/scan, frame_id `unilidar_lidar`**. Followup: `/unilidar/imu` topic advertised but no UDP frames arriving — driver `initialize_type` config may need tuning (non-blocking since D456 IMU at 200 Hz covers EKF). **Full v1 perception stack online:** RGB + depth + 2 IMUs + 3D LiDAR all in ROS 2. |
| 2026-05-19 | **POINT-LIO ROS 2 (dfloreaa fork) built green on Jetson** in 1:42 colcon. Phase 2 SLAM toolchain compile-ready. L2-specific config at `unilidar_l2.yaml` (scan_line 18, imu_time_inte 0.004 = 250 Hz). Runtime tests deferred until L2 IMU ROS bridge bug fixed OR `imu_en: false` LiDAR-only mode set. |
| 2026-05-19 | **Teensy 4.1 PlatformIO firmware skeleton compile-green on Mac** in 9.58 s (Flash 12.8 KB / 8 MB free; RAM1 487 KB / RAM2 512 KB free). Pin map + 74HC125 OE GPIO scaffolding + INA226 I²C placeholder + safety GPIO sense + 1 Hz LED heartbeat + USB-CDC log lines. micro-ROS lib_deps gated behind `NOVA_USE_MICRO_ROS` — Mac build path breaks on Python 3.14 + missing ROS dev libs; reinstate on Jetson for runtime testing. Repo path: `firmware/teensy/firmware/`. |
| 2026-05-19 | **Teensy firmware end-to-end on Jetson.** IntervalTimer ISR-driven 200 Hz tick → loop p99 = **1 µs** (50× under <100 µs acceptance gate). micro-ROS over USB-CDC + 20-topic contract live. `feetech::Bus` driver code-complete (untested on wire). |
| 2026-05-20 | **Firmware safety + telemetry batch:** safety FSM (E-stop + battery-low latch + `/safety_clear`), full STS3215 telemetry (pos+vel+load + voltage + temp @ 5 Hz), per-joint slew limiter on SYNC_WRITE broadcast, software watchdog (ISR-checked main-loop progress + AIRCR reset), boot-time servo ping sweep → first real `/servo_present_mask`, INA226 → `/power_rails` Float32MultiArray @ 10 Hz, `/firmware_version` + boot self-test for safety GPIOs, categorised bus errors (`/servo_err_timeout` + `/servo_err_bad_frame` + `/servo_err_servo`). CI green on every PR. |
| 2026-05-21 | Threadlocker (Loctite 243) + tape ordered. DP adapter dropped (headless SSH path validated). |
| 2026-05-23 | **L2 IMU bridge fixed** via Ace2932/unilidar_sdk2 fork — `/unilidar/imu` now publishes @ 250 Hz, POINT-LIO green end-to-end (init walks 1% → 100% within 250 ms). Per-room PCD capture procedure documented in `setup-jetson.md` §15. |
| 2026-05-23 | **AMS HF bypassed for PA6-CF print workflow** — feed direct from Creality SpacePi X4 → 4 mm PTFE Bowden → P1S. PA6-CF re-absorbs ambient moisture in AMS chamber within hours, defeating the 24 h pre-dry. SpacePi X4 keeps filament heated through the entire print. |
| 2026-05-23 | **Magigoo PA reinstated** in BOM. Bambu Lab liquid glue is not rated for PA / PA-CF per their product page; Bambu wiki PA6-CF guide explicitly calls for PA-specific glue stick. The −$15 substitution was a false economy vs the cost of a 10 h first-layer detachment. |
| 2026-05-24 | **Forward-looking feature notes committed** (PR #1, merge `8cb8b1e`): [`docs/notes-qol-features.md`](./docs/notes-qol-features.md) (preflight check, always-on MCAP dashcam with incident freeze, per-joint safety envelope, `nova bringup` launcher with profiles, `make deploy` for Teensy, bag replay harness, telemetry → CSV/Grafana, RGB status LED, battery SoC widget, Gazebo digital twin) and [`docs/notes-virtual-view-autocal.md`](./docs/notes-virtual-view-autocal.md) (Foxglove bridge over Tailscale, IMU bias zero on boot, servo zero-position auto-detect, camera/LiDAR/IMU extrinsic auto-cal). Notes only — opportunistic pickup during Phase 1/2 idle time. New packages proposed: `nova_ops` + `nova_calibration`. |
| 2026-05-26 | **Leg CAD done — V5 OpenSCAD original-shell-carve** ([`hardware/cad/leg_v5/`](./hardware/cad/leg_v5/README.md)). Reuses the original NovaSM3 STLs and carves an STS3215 cavity inside via boolean `difference()` — keeps the original shape, resizes the servo pocket. 9 STLs (shoulder + coax_L/R + femur_shell_L/R + femur_cover_L/R + tibia_L/R); femur prints as shell+cover sharing one cavity; tibia passive. Beat the from-scratch OnShape (V4) + CadQuery (V3.1) brackets → those archived. Pending: first-article print (coax X-bbox tight). |
| 2026-05-30 | **CAD docs reorganized:** V2/V3/V4 leg attempts moved to `hardware/cad/archive/`; `hardware/cad/README.md` + `docs/cad-tooling.md` reframed to the three-track model (V5 OpenSCAD = leg links, CadQuery = utility, OnShape = chassis). |
| TBD | Phase 0 → Phase 1 transition (parts in hand) |
| TBD | First successful walk gait |

---

*This is a learning project as much as a research one. Decisions and tradeoffs are documented openly so others can fork and adapt.*
