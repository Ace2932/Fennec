# Week 1 Checklist — 2026-05-15 → 2026-05-22

Actionable items to land before Week 2 prints + Week 3 away-week PCB work. Tick as you go; commit progress.

> Parent plan: [`../work-schedule.md`](../work-schedule.md)

---

## 1. Cache reference material (optional convenience)

Internet works during away-week, so this is a convenience-only step (faster lookups, no provider dependency, archive against link-rot). Skip if pressed for time. Pattern: `~/Downloads/nova-offline-cache/` (or wherever convenient — won't be tracked in this repo, too binary-heavy).

### Datasheets
- [ ] STS3215 19kg (Feetech)
- [ ] STS3215 30kg (Feetech)
- [ ] Feetech 25T servo horn dims
- [ ] Pololu D42V110F7 — leg 7.4V rail
- [ ] Pololu D42V110F12 — hip 12V rail
- [ ] Pololu D24V22F12 — L2 LiDAR 12V dedicated rail (v3.4 addition)
- [ ] Pololu D42V55F12 — Jetson 12V rail
- [ ] Pololu D42V55F7 — arm 7.4V (Phase 4 reserved)
- [ ] 74HC125 (TI SN74HC125 SOIC-14)
- [ ] INA226 (TI)
- [ ] TL431 OR LM393 (whichever comparator family)
- [ ] MOSFET candidate (e.g. IRLB3034PBF or chosen part)
- [ ] Teensy 4.1 pinout
- [ ] Arduino Nano pinout
- [ ] Jetson Orin Nano carrier board spec (NVIDIA P3766)
- [ ] Unitree L2 LiDAR spec
- [ ] Intel RealSense D456 spec

### Reference designs
- [ ] NovaSM3 v5.2b schematic PDF (SovGVD GitHub)
- [ ] NovaSM3 v5.2b PCB source/Gerbers if available
- [ ] 74HC125 half-duplex bus driver example schematic (any community reference)

### CAD STEPs
- [ ] STS3215 19kg STEP (GrabCAD or Feetech)
- [ ] STS3215 30kg STEP
- [ ] Feetech 25T horn STEP
- [ ] NovaSM3 v5.2b chassis STEP (SovGVD)

---

## 2. Software installs (laptop)

- [ ] KiCad 8.x → `brew install --cask kicad`
- [ ] Pololu KiCad library → clone, configure library paths in KiCad
- [ ] Teensy KiCad library (community: `blackketter/Teensy_Library` or similar)
- [ ] PlatformIO VS Code extension
- [ ] TeensyDuino (auto-installed via PlatformIO `platform = teensy`)
- [ ] micro-ROS for Teensy → clone `micro-ROS/micro_ros_platformio` now (in case offline later)
- [ ] Bambu Studio (latest) — for slicing leg prints
- [ ] Balena Etcher → `brew install --cask balenaetcher` (for JetPack SD flash)
- [ ] CH340 macOS driver (Arduino Nano)

---

## 3. Accounts + downloads

- [ ] NVIDIA Developer account (developer.nvidia.com)
- [ ] JetPack 6.x microSD image → save to `~/Downloads/jetpack-6.x-orin-nano-sd.img.xz`. Verify SHA.
- [ ] Feetech FD debug software (Windows-only .exe — stash on USB stick or in a Windows VM/Parallels)
- [ ] PCBWay account (for Week 4+ PCB submit)
- [ ] Confirm OnShape free account works for public docs

---

## 4. OnShape setup

- [ ] Create OnShape doc: `NovaSM3 LE — Leg Joints v1` (public, this repo links to it)
- [ ] Tab 1: STS3215 19kg STEP imported
- [ ] Tab 2: STS3215 30kg STEP imported
- [ ] Tab 3: 25T horn STEP imported
- [ ] Tab 4: NovaSM3 chassis STEP (reference only — left/right reuse)
- [ ] Paste OnShape URL into [`../../hardware/cad/README.md`](../../hardware/cad/README.md) line `OnShape public doc (link here once created)`

---

## 5. Caliper measurement pass

Cross-check datasheet dims against on-hand servos. Note any deltas.

- [ ] STS3215 19kg body LWH
- [ ] STS3215 19kg mounting hole pitch + diameter
- [ ] STS3215 19kg output shaft diameter
- [ ] STS3215 19kg back-shaft length + diameter
- [ ] STS3215 30kg body LWH
- [ ] STS3215 30kg mounting hole pitch + diameter
- [ ] STS3215 30kg output shaft + back-shaft
- [ ] 25T horn spline OD + tooth count
- [ ] 25T horn screw hole pitch + hub OD + thickness
- [ ] Strain-relief geometry for daisy-chain cables at servo entry

Record in OnShape as named dimensions (so part variants reference one source). Mirror into `hardware/cad/measurements.md` for offline reference.

---

## 6. Leg-joint CAD — first article

- [ ] Sketch hip pocket in OnShape (12V 30kg servo)
- [ ] Sketch femur U-bracket (7.4V 19kg)
- [ ] Sketch tibia
- [ ] Sketch ankle / foot attachment
- [ ] Export hip pocket STL
- [ ] Slice in Bambu Studio: PA6-CF, 100% infill on load-bearing zones, fiber alignment per print orientation note
- [ ] **Drier 24h before printing** (PA6-CF hygroscopic)
- [ ] Magigoo PA on textured PEI plate
- [ ] Print one hip pocket
- [ ] Fit-check on real STS3215 30kg
- [ ] Iterate (clearance, tolerance) until clean — DO NOT batch-print before fitment validated

---

## 7. Backups before reformatting

- [ ] LeRobot Pi SD card image → `sudo dd if=/dev/diskN of=~/Backups/lerobot-pi-128gb-2026-05-XX.img bs=4M status=progress`
- [ ] Verify with `shasum -a 256`
- [ ] Confirm restore works on a spare card (optional but recommended)

---

## 8. Repo housekeeping

- [ ] Create `hardware/cad/measurements.md` with caliper readings as you go
- [ ] Update `hardware/cad/README.md` with OnShape URL once doc exists
- [ ] Update this file's checkboxes via commits as items land

---

## Out-of-scope for Week 1 (defer to Week 2)

- Jetson flash + first boot (better with full shop access, not laptop-only)
- ROS 2 / librealsense2 / unilidar_sdk2 installs on Jetson
- Teensy firmware coding (skeleton in Week 2; needs prereqs from Week 1 cache done)
- PCB schematic work (Week 3 away-week — Week 1 is just the install + cache pass)

---

## Out-of-scope full stop for Week 1

- Servo bench bring-up via FE-URT-1 (FE-URT-1 may not have arrived; also gated on Teensy firmware existing in Pattern B path)
- Network setup, L2 standalone test (Phase 1 hardware bring-up)
- Ordering remaining parts (do this **after** confirming Ovonic kit contents for the XT60 verify-on-arrival items)

---

> **Status:** drafted at v0.3.1-pattern-b-default. Tick items via commits; close out when ≥80% done and Week 2 prereqs are clear.
