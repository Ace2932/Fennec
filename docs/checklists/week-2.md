# Week 2 Checklist — 2026-05-22 → 2026-05-28

> Parent plan: [`../work-schedule.md`](../work-schedule.md) · Prev: [`week-1.md`](./week-1.md)
>
> Week 1 carryover: leg-joint CAD + first-article print, KiCad install, PlatformIO setup.

---

## 1. Carryover from Week 1 — CAD + first-article print

### OnShape setup
- [ ] Create OnShape free account (public docs for free tier)
- [ ] Create doc: `NovaSM3 LE — Leg Joints v1`
- [ ] Import STS3215 19kg STEP (GrabCAD or Feetech) → tab 1
- [ ] Import STS3215 30kg STEP → tab 2
- [ ] Import Feetech 25T horn STEP → tab 3
- [ ] Import NovaSM3 chassis STLs from `cguweb-com/Arduino-Projects/Nova-SM3/STL Files/` → tab 4 (STEP not available — STLs are static reference)
- [ ] Paste OnShape URL into [`../../hardware/cad/README.md`](../../hardware/cad/README.md)

### Caliper measurement pass
- [ ] STS3215 19kg: body LWH, mounting hole pitch + diameter, output shaft, back-shaft length + diameter
- [ ] STS3215 30kg: same measurements
- [ ] 25T horn: spline OD + tooth count, screw hole pitch, hub OD, thickness
- [ ] Strain-relief geometry for daisy-chain cables at servo entry
- [ ] Record in `hardware/cad/measurements.md` (create as you measure)

### Leg-joint first-article (hip pocket = highest stakes)
- [ ] Sketch hip pocket in OnShape against STS3215 30kg STEP
- [ ] Export hip pocket STL
- [ ] Slice in Bambu Studio: PA6-CF, 100% infill on load-bearing zones, fiber-aware orientation
- [ ] Pre-dry PA6-CF 24h before printing
- [ ] Magigoo PA or Bambu liquid glue on textured PEI plate (gate per BOM §8 fallback note)
- [ ] Print one hip pocket
- [ ] Fit-check on real STS3215 30kg with calipers — clearance, M3 hole alignment, horn-spline depth
- [ ] Iterate 2-3 times until clean

### Once hip pocket geometry locked
- [ ] Femur U-bracket (19kg)
- [ ] Tibia
- [ ] Ankle / foot attachment

---

## 2. Jetson Phase 1 software install (during prints)

### ROS 2 Humble on Jetson ✅ (done 2026-05-17)
- [x] SSH in: `ssh aiden@nova-jetson.local` (or 10.0.1.135)
- [x] Run persistence verification block per [`../setup-jetson.md`](../setup-jetson.md) §11 — baseline confirmed
- [x] ROS 2 Humble apt install via the new **ros2-apt-source deb package** (the legacy `curl ros.key + sources.list` approach is deprecated as of 2024-2025 — ROS docs now point at the deb method):
  ```bash
  # ros2-apt-source 1.2.0 (jammy) installed via:
  curl -L -o /tmp/ros2-apt-source.deb https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.2.0/ros2-apt-source_1.2.0.jammy_all.deb
  sudo dpkg -i /tmp/ros2-apt-source.deb
  sudo apt update
  sudo apt install -y ros-humble-desktop python3-colcon-common-extensions python3-rosdep python3-argcomplete
  ```
- [x] `sudo rosdep init && rosdep update`
- [x] Source line added to `~/.bashrc`
- [x] Talker/listener verified working — `demo_nodes_py listener` heard `demo_nodes_cpp talker` end-to-end via DDS
- [ ] `ros2 doctor` review (run when convenient — warnings about network interfaces are typical, not blockers)

### Sensor SDKs
- [x] `librealsense2` ARM64 via Intel apt repo ✅ 2026-05-18 (Intel does ship ARM64 binaries via `librealsense.intel.com/Debian/apt-repo` — no source build needed). Key gotcha: Intel rotated the apt signing key (FB0B24895113F120), fetch from keyserver.ubuntu.com.
- [x] **Kernel HID-sensor module patch path** for D456 IMU ✅ 2026-05-18. Stock JetPack 6.2.2 modules don't expose accel/gyro streams. Patched 3 in-tree drivers (uvc, IIO accel, IIO gyro) via [`jetson-orin-librealsense/build/patch-for-realsense.sh`](https://github.com/jetsonhacks/jetson-orin-librealsense) + rebuilt against L4T 36.5 sources via [`jetson-orin-kernel-builder`](https://github.com/jetsonhacks/jetson-orin-kernel-builder). Set `HID_SENSOR_HUB`, `HID_SENSOR_ACCEL_3D`, `HID_SENSOR_GYRO_3D` to `=m`. Full procedure in [`../setup-jetson.md`](../setup-jetson.md) §13.
- [x] `ros-humble-realsense2-camera` install ✅ 2026-05-18
- [x] D456 standalone smoke test ✅ 2026-05-18 — `rs-enumerate-devices` lists all 3 modules (Stereo, RGB, Motion). Motion Module shows Accel @ 400/200/100 Hz + Gyro @ 400/200 Hz.
- [x] Clone `unilidar_sdk2` from Unitree GitHub (`unitreerobotics/unilidar_sdk2`), build the C++ SDK ✅ 2026-05-17
- [x] Build bundled `unitree_lidar_ros2` package via `colcon build --packages-select unitree_lidar_ros2` ✅ 2026-05-17. Launch params + topics captured in [`../setup-network.md`](../setup-network.md).
- [x] L2 standalone test ✅ 2026-05-18: `ros2 launch unitree_lidar_ros2 launch.py` → `/unilidar/cloud` streaming at 12 Hz (5042 points/scan, frame_id `unilidar_lidar`). Wiring: L2 ↔ Cable Matters Cat 6 ↔ switch port ↔ Cat 6 ↔ Jetson `enP8p1s0` (192.168.1.2/24 static via `nmcli connection nova-lan`). 0.1 ms ping. L2 powered via included 12V wall adapter for this test. **Open followup:** `/unilidar/imu` topic advertised but no IMU UDP frames received from L2 — driver `initialize_type: 2` may need adjustment, or L2 firmware needs IMU enable. D456 IMU at 200 Hz covers EKF needs, so non-blocking. rviz2 in launch.py auto-spawn fails over SSH (no X11) — expected, can run rviz2 separately when display available.

### SLAM stack (eval phase)
- [ ] Clone POINT-LIO (rosbag replay first — no live LiDAR needed)
- [ ] Clone RTAB-Map (apt install or build from source)
- [ ] Pull example `unitree_lidar_ros2` rosbags from upstream for replay testing

---

## 3. Teensy firmware skeleton (compile-green target)

- [ ] On Mac: install PlatformIO VS Code extension
- [ ] Clone `micro-ROS/micro_ros_platformio` to `~/code/`
- [ ] Create new PlatformIO project: `~/code/nova-teensy-firmware`
  - Board: `teensy41`
  - Framework: `arduino`
  - Library deps: micro-ROS for Teensy
- [ ] Write firmware skeleton per [`../../firmware/teensy/README.md`](../../firmware/teensy/README.md):
  - micro-ROS client setup over USB-CDC
  - Topic publishers: `/joint_states`, `/diagnostics`, `/estop`, `/battery_low`
  - Topic subscriber: `/joint_commands`
  - Real-time loop scaffold @ 200 Hz (no actual servo I/O yet)
  - 74HC125 OE pin GPIO scaffolding (no actual bus reads/writes yet)
- [ ] Compile-green (no servo hardware to test against yet)
- [ ] Flash to Teensy 4.1 over USB, verify it enumerates as `/dev/cu.usbmodem*` from Mac

---

## 4. KiCad + Pololu library install on Mac (PCB v6 prep for Week 3 away-week)

- [ ] `brew install --cask kicad`
- [ ] Clone `github.com/pololu/kicad-libraries`
- [ ] KiCad → Preferences → Manage Symbol Libraries + Footprint Libraries → add Pololu paths
- [ ] Test: open a new schematic, find a Pololu D42V110F12 module symbol
- [ ] Teensy 4.1 KiCad symbol/footprint — find a community one
- [ ] 74HC125 symbol — built into KiCad's `74xx` library
- [ ] INA226 — in KiCad's standard libs or Adafruit's
- [ ] Bookmark NVIDIA Orin Nano carrier board reference + NovaSM3 v5.2/v5.3 PCB on [PCBWay community share](https://www.pcbway.com/project/shareproject/NovaSM3_v5_2.html) for later reference

---

## 5. Bambu Studio + filament prep

- [ ] Download + install Bambu Studio (latest)
- [ ] Confirm AMS HF profile matches your spool loadout
- [ ] Run PA6-CF in Creality SpacePi X4 drier 24h before first print
- [ ] Confirm hardened steel hotend installed in P1S (PA6-CF requires it)
- [ ] First-article print test: pre-existing benchy STL in PA6-CF to confirm hotend + drier + Magigoo/Bambu glue combo holds

---

## 6. Network setup for Phase 1 LiDAR

- [ ] Order remaining hardware bundle (Pololu ×4, switch, Cat6 cables, LC parts, threadlocker, tape, DP adapter — see [`../order-list.md`](../order-list.md))
- [ ] When switch arrives: bench-verify all 5 ports link-up with one Cat6
- [ ] When ready: configure Jetson `enP8p1s0` static IP 192.168.1.2/24 (don't disturb the working WiFi profile)

---

## Acceptance gates for Week 2 close-out

- [ ] OnShape doc exists with all 4 reference STEPs imported
- [ ] At least hip pocket first-article prints successfully + fits real servo (femur/tibia can carry to Week 3-4)
- [ ] Jetson runs ROS 2 talker/listener cleanly
- [ ] D456 streams in `realsense-viewer` on Jetson
- [ ] Teensy firmware skeleton compiles + flashes
- [ ] KiCad opens with Pololu lib loaded (PCB v6 work-ready for away-week)

---

## Out-of-scope for Week 2 (defer to Week 3 or later)

- Full 12-servo daisy chain testing (no FE-URT-1 on hand yet, may slip)
- L2 LiDAR full integration (waits for switch + Cat6 cables + power delivery test)
- PCB v6 schematic capture (Week 3 away-week work — Week 2 just gets KiCad ready)
- Phase 1 acceptance gate (Teensy tick jitter measurement) — needs servos + PCB
- Nav2 / SLAM / EKF — Phase 2

---

> **Status:** drafted at v0.3.3-audit-pass2 close-of-Week-1. Tick items via commits.
