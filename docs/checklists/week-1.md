# Week 1 Checklist — 2026-05-15 → 2026-05-22

> **Status: substantially done (closed 2026-05-17).** See close-out at bottom for what carried over to Week 2.
>
> Parent plan: [`../work-schedule.md`](../work-schedule.md) · Next: [`week-2.md`](./week-2.md)

---

## 1. Cache reference material (optional convenience)

Internet works during away-week, so this is a convenience-only step (faster lookups, no provider dependency, archive against link-rot). Skip if pressed for time. Pattern: `~/Downloads/nova-offline-cache/` (or wherever convenient — won't be tracked in this repo, too binary-heavy).

### Datasheets
- [ ] STS3215 19kg (Feetech)
- [ ] STS3215 30kg (Feetech)
- [ ] Feetech 25T servo horn dims
- [ ] Pololu D42V110F7 — leg 7.5V rail (STS3215 7.4V nominal)
- [ ] Pololu D42V110F12 — hip 12V rail
- [ ] Pololu D24V22F12 — L2 LiDAR 12V dedicated rail (v3.4 addition)
- [ ] Pololu D42V55F12 — Jetson 12V rail
- [ ] Pololu D42V55F7 — arm 7.5V (Phase 4 reserved)
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

- [x] NVIDIA Developer account (developer.nvidia.com)
- [x] JetPack 6.2.1 microSD image downloaded + flashed via Balena Etcher
- [x] **Bonus done early: JetPack 6.2.1 booted, upgraded apt to 6.2.2 (L4T 36.5), MAXN_SUPER set, BT confirmed (Realtek BT 5.1).** See [`setup-jetson.md`](../setup-jetson.md) for verified procedure.
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

- [x] LeRobot Pi SD card image → compressed with pigz at `/Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz` (2026-05-16)
- [x] Verify with `shasum -a 256`
  - SHA256: `39b571261b0cf24e8d55682b97e1932c1f0cfcfc76fa9c50d332c0924928f832`
- [ ] Confirm restore works on a spare card (optional but recommended)

Restore command (if ever needed):
```bash
gunzip -c /Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz | sudo dd of=/dev/rdiskN bs=4m
```

---

## 8. Repo housekeeping

- [ ] Create `hardware/cad/measurements.md` with caliper readings as you go
- [ ] Update `hardware/cad/README.md` with OnShape URL once doc exists
- [ ] Update this file's checkboxes via commits as items land

---

## Out-of-scope for Week 1 (defer to Week 2)

- ~~Jetson flash + first boot~~ — **DONE early on 2026-05-17** (with the shop, not laptop-only as planned). JetPack 6.2.2, MAXN_SUPER, BT confirmed.
- ROS 2 / librealsense2 / unilidar_sdk2 installs on Jetson
- Teensy firmware coding (skeleton in Week 2; needs prereqs from Week 1 cache done)
- PCB schematic work (Week 3 away-week — Week 1 is just the install + cache pass)

---

## Out-of-scope full stop for Week 1

- Servo bench bring-up via FE-URT-1 (FE-URT-1 may not have arrived; also gated on Teensy firmware existing in Pattern B path)
- Network setup, L2 standalone test (Phase 1 hardware bring-up)
- Ordering remaining parts (do this **after** confirming Ovonic kit contents for the XT60 verify-on-arrival items)

---

> **Status:** updated at v0.3.2-l2-dedicated. Tick items via commits; close out when ≥80% done and Week 2 prereqs are clear.

---

## Close-out (2026-05-17)

### Done
- ✅ LeRobot Pi SD backed up (`docs/backups.md`)
- ✅ Jetson Orin Nano: SD flashed, JetPack 6.2.1 → 6.2.2 apt-upgrade, MAXN_SUPER, BT confirmed (resolves Open Decision 2b), DNS chattr-locked, jetson_clocks systemd service running, full persistence verified across reboots (`docs/setup-jetson.md` §11)
- ✅ Three first-boot networking gotchas documented (`docs/setup-network.md`)
- ✅ NVIDIA Dev account + JetPack download

### Carried over to Week 2
Original Week 1 plan front-loaded **OnShape leg-joint CAD + first-article print**. Got displaced by deep-dive Jetson bring-up instead. Carryover:
- OnShape doc creation + STEP imports (STS3215 19kg + 30kg, 25T horn, NovaSM3 chassis)
- Caliper measurement pass on on-hand servos + horns
- Hip pocket first-article CAD → print → fitment iteration
- KiCad 8.x + Pololu library install on Mac (PCB v6 prep for Week 3 away-week)
- PlatformIO + TeensyDuino + micro-ROS clone (firmware skeleton prep)
- Bambu Studio install + PA6-CF drier preheat

Order doesn't matter for the project as long as CAD finishes before Week 2 prints + KiCad install before Week 3 away-week.

### Lessons
- **Internet + DNS on Jetson is fragile** — three separate gotchas in one bring-up (oem-config WPA bug, l4tbr0 route hijack, NM-not-writing-resolv.conf). Full recovery sequence now in `docs/setup-network.md`.
- **The "Super" power mode is index 2**, not 0. Mode 0 on the Orin Nano Super is 15W, mode 1 is 25W. MAXN_SUPER (mode 2) is required for the full 67 TOPS.
- **Heredoc `<<EOF` paste-mangling** breaks systemd unit parsing silently. Always `cat -A` after creating service files to confirm clean line termination.
- **chattr +i is the durable fix** when NetworkManager won't write resolv.conf. Brute-force but reliable.
