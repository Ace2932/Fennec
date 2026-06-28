# Phase 0 → Phase 1 Work Schedule (3 weeks)

Sequencing constraint: one solid week starting **2026-05-29** the user is away from the shop — **laptop + internet only, no printer / no hardware**. Plan front-loads physical work (leg-joint CAD → prints) and reserves the away-week for browser/laptop work that can't proceed if the printer or bench parts are needed.

Constraints recap:
- ✅ Bambu P1S + PA6-CF / PETG-CF / TPU 95A on hand
- ✅ STS3215 19kg ×6, 30kg hips ×4, 25T horns ×12 on hand (calipers too)
- ✅ Jetson Orin Nano Super on hand but **not yet flashed/booted**
- ✅ Teensy 4.1 on hand
- ⚠️ FE-URT-1, Arduino Nano: ordered, on-hand-by-then TBD
- ⚠️ Pololu rails + safety parts + switch: not yet ordered (see [`order-list.md`](./order-list.md))
- ✅ Internet available during away-week — OnShape, KiCad downloads, package installs, Git all work normally

Open option for away-week (decide by end of Week 2): leave Jetson running at home with SSH-over-WiFi (Tailscale recommended) so remote ROS 2 / sensor SDK install work is possible during away. Risks: thermal trip if room hot, no physical reset if locked. Default = Jetson off during away.

---

## Week 1 — 2026-05-15 → 2026-05-22 (this week)

> **Detailed actionable checklist:** [`checklists/week-1.md`](./checklists/week-1.md)

**Primary: leg-joint CAD on OnShape**

- [ ] Pull STS3215 19kg + 30kg STEP from GrabCAD or Feetech site; import to OnShape
- [ ] Pull NovaSM3 reference geometry from [`cguweb-com/Arduino-Projects/tree/main/Nova-SM3/STL Files`](https://github.com/cguweb-com/Arduino-Projects/tree/main/Nova-SM3) (STL only — no STEP available; import to OnShape as static reference body)
- [ ] Caliper-measure on-hand servos (back-shaft length, mounting hole pitch, horn spline) and cross-check against datasheet
- [ ] Sketch leg-joint kinematics: hip pocket, femur U-bracket, tibia, ankle attachment
- [ ] First-article print of one hip pocket on Bambu P1S (PA6-CF, drier 24h first) → fitment check on real servo
- [ ] Iterate fitment until clean — slip-fit on horn spline, snug fit on servo body, M3 thru-holes line up

**Secondary: Phase 1 prerequisites that don't need parts on hand**

- [ ] Install KiCad 8.x on laptop + Pololu KiCad library
- [ ] Download datasheet PDFs to offline cache: SN74LVC125A, INA226, TL431/LM393, MOSFET candidates (IRLB3034 etc.), STS3215, Pololu D42V110/D42V55, Jetson Orin Nano carrier board spec
- [ ] Bookmark NovaSM3 v5.2/v5.3 PCB reference at [PCBWay community share](https://www.pcbway.com/project/shareproject/NovaSM3_v5_2.html) (no GitHub schematic available)
- [ ] Create NVIDIA Developer account + download JetPack 6.x SD image to laptop
- [ ] Back up LeRobot Pi SD contents to Mac before reformatting

**Defer:** Jetson flash, ROS 2 install, sensor SDK builds — Week 2 work, only after CAD prereqs are out of the way.

---

## Week 2 — 2026-05-22 → 2026-05-28

**Primary: finish leg-CAD, queue prints, start Phase 1 software prereqs**

- [ ] Finish all 4 leg variants in OnShape (hip + femur + tibia + ankle; left/right mirror)
- [ ] Export STLs, slice in Bambu Studio, queue for printing (PA6-CF, 100% infill on load-bearing parts)
- [ ] Set up first long print queue → 2-4 prints per day depending on part size

**Secondary (during prints):**

- [ ] **Flash Jetson** with JetPack 6.x microSD; firmware update if needed; complete Ubuntu first boot
- [ ] Verify built-in WiFi works (802.11ac/ab/gn per NVIDIA spec); confirm BT presence
- [ ] Install ROS 2 Humble on Jetson (apt-based ARM64)
- [ ] Install `librealsense2` SDK on Jetson + `ros-humble-realsense2-camera`
- [ ] Clone + build `unilidar_sdk2` + `unitree_lidar_ros2` (discodyer fork) on Jetson
- [ ] D456 standalone smoke test via `realsense-viewer` on Jetson
- [ ] **Set up PlatformIO** on laptop with TeensyDuino + micro-ROS Teensy client — write firmware skeleton (no servo testing yet; just compile-green)
- [ ] Pull example `unitree_lidar_ros2` rosbags from upstream — replay-mode SLAM testing prep
- [ ] Scaffold `ros2_ws/src/nova_description` URDF skeleton (uses leg-CAD dims once frozen)

---

## Week 3 — 2026-05-29 → 2026-06-05 (AWAY WEEK — laptop + internet, no shop)

**Primary: PCB v6 schematic + layout in KiCad**

Per [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md):

- [ ] Schematic capture in KiCad — all 8 sections of the feature set (battery input, 4 active rails + reserved 5th, bus distribution, Pattern A/B selector, bus integrity, safety chain, aux MCU, mechanical)
- [ ] Footprint placement on board outline
- [ ] Power planes + 4-layer stackup (top sig, GND, PWR, bottom sig)
- [ ] GND-plane reference (FE-URT-1; solid GND plane = single low-Z return)
- [ ] DRC + ERC clean
- [ ] Gerber export ready for PCBWay quote

**Secondary if PCB stalls or finishes early:**

- [ ] Continue OnShape leg/chassis CAD (browser, fine with internet)
- [ ] Continue Teensy PlatformIO firmware (compiles + uROS work; no servo test possible without bench)
- [ ] URDF / xacro work using Week 1 leg dims
- [ ] ROS 2 package scaffolding for `nova_gait`, `nova_ik`, `nova_servo_bus`
- [ ] If remote-Jetson option chosen (Tailscale SSH): ROS 2 install + sensor SDK builds + clones

**Hard-blocked during away (need physical access):**
- ❌ 3D printing
- ❌ Bench measurement of new components
- ❌ Servo bring-up via FE-URT-1 (no servos on bench)
- ❌ Any soldering / hardware assembly

---

## Week 4+ — 2026-06-06 onward

Back to shop. Resume hardware path:
- Bench-validate prints from Week 2's print queue against on-hand servos
- Finalize PCB Gerbers → submit to PCBWay (~$60, 1-2 week lead time)
- Continue Phase 1 hardware bring-up (sensors, daisy-chain, Teensy firmware vs real servos)
- Once PCB arrives: SMD population, bench-test each rail, full integration

---

## Critical-path risk register

| Risk | Mitigation |
|------|------------|
| Jetson flash hits firmware update gotcha → bricked/long-recovery | Flash on Week 2 with shop access (USB recovery, second SD). Don't first-attempt during away-week. |
| Leg-joint first-article doesn't fit servo → respin → behind schedule | Print one early, iterate before queueing all 12 prints. Don't batch-print before fitment validated. |
| Teensy firmware deeper than 1-2 weeks (Phase 1 critical path) | Start skeleton in Week 2 (parallel work during prints). Bring-up parallelizable with sensor SDK installs. |
| FE-URT-1 not arrived for ID assignment | Servos can be ID-programmed via any TTL adapter (workstation USB-serial → 5V level shift). Have one as a backup. |
| Remote-Jetson option chosen but Jetson hangs / overheats / loses WiFi during away | Default to Jetson off. Only enable remote-SSH path if confidence is high (Tailscale set up, thermal verified, room temp stable). Have a remote-reset option (smart plug). |

---

> **Status:** updated at v0.3.2-l2-dedicated. Update with actual completion dates as work lands.
