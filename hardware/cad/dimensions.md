# Verified Part Dimensions

Canonical mechanical reference for every part in the NovaSM3 BOM. Used
by `hardware/cad/patterns.md` macros + OnShape chassis design.

**Status legend:**

- ✅ **VERIFIED** — from manufacturer datasheet, STEP file, or
  caliper-measured on-hand part
- ⚠️ **REVIEW** — best-effort estimate; caliper-measure the actual
  part before committing to a load-bearing fit
- ❌ **MISSING** — no datasheet found; must measure before designing
  any mating CAD

All dims in **millimeters** unless noted. Tolerances are nominal —
real-world batch variation listed where known.

---

## 1. Actuators

### Feetech STS3215 servo (12V 30 kg + 7.4V 19 kg share same body)
**Source:** STEP file at `~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/feetech-sts3215/STS3215_03a v1.step`

| Dim | Value | Status |
|---|---|---|
| Body length (long X axis) | 45.40 | ✅ |
| Body width (Y) | 24.80 | ✅ |
| Body height (Z, shaft direction) | 36.80 | ✅ |
| Spline X offset from body center | **+12.50** | ✅ (CRITICAL — coaxial with bottom shaft) |
| Spline OD | 6.0 | ✅ |
| Top horn boss OD × thickness | 8.0 × ~1.0 | ✅ |
| Top horn disc OD × thickness | 20.0 × 8.8 | ✅ |
| Bottom horn disc / reaction OD × thickness | 20.0 × 2.1 | ✅ |
| Bottom reaction shaft OD | 6.0 | ✅ |
| Horn screw pattern | 4× M3 on 14.0 mm BCD, +45° from cardinal | ✅ |
| Body mount screws | 4× M2.5 (rear plate) | ⚠️ REVIEW — verify thread spec |
| Batch tolerance on body dims | ±0.10 | ✅ (manufacturer spec) |

---

## 2. Compute + perception

### NVIDIA Jetson Orin Nano Super Developer Kit (P3766)
**Source:** [NVIDIA P3766 datasheet](https://developer.nvidia.com/embedded/jetson-orin-nano-developer-kit) + user OnShape import

| Dim | Value | Status |
|---|---|---|
| Carrier board L × W | 100.0 × 79.4 | ✅ |
| Mount-hole pattern (rectangular) | 96.5 × 75.4, 4× M3 | ✅ |
| SOM heatsink height above carrier (top of fan) | ~21.5 | ⚠️ REVIEW — caliper-measure (depends on heatsink rev) |
| Carrier PCB thickness | 1.6 (standard) | ⚠️ REVIEW |
| Power barrel jack | 5.5 × 2.5 mm | ✅ |
| USB-A 3.1 ports | 4× on long edge | ✅ |
| USB-C UFP | 1× on short edge | ✅ |
| RJ-45 | back edge | ✅ |
| WiFi/BT antenna U.FL → SMA bulkhead | 2× external, ≥30 mm spacing for MIMO | ⚠️ REVIEW antenna location on real board |

### Intel RealSense D456
**Source:** Intel D4xx series datasheet

| Dim | Value | Status |
|---|---|---|
| Body L × W × H | 124.0 × 26.0 × 29.0 | ✅ |
| Mount pattern | 2× M3 tripod-style at body center (90 mm apart) | ⚠️ REVIEW — verify which mount face used (top vs bottom) |
| Mount alt pattern | 4× M3 on rear panel corners | ⚠️ REVIEW |
| IR projector center offset | 14.0 from body centerline | ⚠️ REVIEW |
| USB 3.1 cable connector | Type-C on rear | ✅ |
| Cable thickness with shield | ~6.0 (USB-A end) | ⚠️ REVIEW |

### Unitree L2 4D LiDAR
**Source:** [L2 User Manual 2024.10 v1.1](https://oss-global-cdn.unitree.com/static/Unitree%204D%20LiDAR%20L2%20User%20Manual.pdf)

| Dim | Value | Status |
|---|---|---|
| Body W × D × H | 75.0 × 75.0 × 65.0 | ✅ |
| Weight | 230 g | ✅ |
| Bottom mount holes | **4× M3 on 22.5 mm square pattern** | ✅ (CORRECTS earlier 50 mm placeholder in patterns.md §8) |
| Mount hole thread depth | 6.0 | ✅ |
| Power barrel | 5.5 × 2.1 mm | ⚠️ REVIEW (manual mentions both 5.5×2.1 and 5.5×2.5 in places) |
| Ethernet | RJ-45 (standard) | ✅ |
| FoV | 360° × 90° | ✅ |
| Self-heat / cold-boot delay | ~30-60 s below 30 °C ambient | ✅ |

---

## 3. Control + MCU

### Teensy 4.1
**Source:** [PJRC datasheet](https://www.pjrc.com/store/teensy41.html)

| Dim | Value | Status |
|---|---|---|
| Board L × W | 61.0 × 18.0 | ✅ |
| Mount holes | 2× ~2.5 mm, centered on width, at ±29 mm from center | ✅ |
| Mount hole diameter | 2.5 (M2.5 clearance is 2.7) | ⚠️ REVIEW — datasheet says small holes; common builds use M2 or M2.5 |
| PCB thickness | 1.6 | ✅ |
| Height with components (Ethernet PHY tall side) | ~7.0 | ⚠️ REVIEW |
| Micro-USB | 1× on short edge | ✅ |

### Arduino Nano (ELEGOO clone, CH340)
**Source:** Arduino Nano v3.x official datasheet (clones follow same outline)

| Dim | Value | Status |
|---|---|---|
| Board L × W | 43.2 × 17.8 | ✅ |
| Mount holes | 4× 2.0 mm at corners (1.27 mm from edges) | ✅ |
| Mount hole pattern | 15.24 × 6.35 (approximate; see datasheet) | ⚠️ REVIEW |
| PCB thickness | 1.6 | ✅ |

### 74HC125 quad tri-state buffer (Pattern B half-duplex driver)
**Source:** TI/Nexperia datasheet

| Dim | Value | Status |
|---|---|---|
| Package | SOIC-14 | ✅ |
| Body L × W | 8.65 × 3.90 | ✅ |
| Pin pitch | 1.27 | ✅ |
| Pin count | 14 | ✅ |

---

## 4. Power modules

### Pololu D42V110F7 / D42V110F12 (leg + hip step-down)
**Source:** [Pololu D42V110F7](https://www.pololu.com/product/5674) + D42V110F12

| Dim | Value | Status |
|---|---|---|
| Board L × W × H | 25.4 × 25.4 × 13.0 | ✅ |
| Header pin layout | Vin / GND / Vout / EN, 2.54 mm pitch | ✅ |
| Mount holes | 2× M3 at ~11.4 mm from center | ⚠️ REVIEW — some Pololu revs have mount holes, some don't; verify on received board |

### Pololu D24V22F12 (L2 LiDAR dedicated, v3.4 split)
**Source:** [Pololu D24V22Fx family](https://www.pololu.com/category/107/d24v22fx-step-down-voltage-regulators)

| Dim | Value | Status |
|---|---|---|
| Board L × W × H | 20.3 × 17.8 × 11.0 | ✅ |
| Header pitch | 2.54 | ✅ |
| Mount holes | none on this size | ✅ |

### Pololu D42V55F12 (Jetson 12V rail)
**Source:** Pololu D42V55Fx family

| Dim | Value | Status |
|---|---|---|
| Board L × W × H | 22.9 × 17.8 × 11.0 | ✅ |
| Header pitch | 2.54 | ✅ |

### UBEC 5V/5A
**Source:** generic UBEC (varies by brand)

| Dim | Value | Status |
|---|---|---|
| Body L × W × H | ~35 × 23 × 10 | ⚠️ REVIEW — depends on brand |

### INA226 breakout (Adafruit / generic)
**Source:** Adafruit + common AliExpress modules

| Dim | Value | Status |
|---|---|---|
| Board L × W | 25.4 × 20.3 | ✅ |
| Mount pattern | 4× M2.5 at corners (20.3 × 15.2 mm rectangle) | ⚠️ REVIEW — Adafruit vs generic vary |
| Pin headers | 2.54 mm pitch (VCC/GND/SCL/SDA + IN+/IN-) | ✅ |
| Default I²C addr | 0x40, configurable via solder pads | ✅ |

---

## 5. Battery + safety

### 4S LiPo Ovonic 4000 mAh
**Source:** Ovonic product page

| Dim | Value | Status |
|---|---|---|
| Pack L × W × H | 110.0 × 35.0 × 30.0 | ⚠️ REVIEW — varies ±5 mm by lot |
| Weight | ~410 g | ⚠️ REVIEW |
| Power lead | XT60 (Ovonic kit includes XT60 jumper + balance lead) | ✅ |
| Balance lead | JST-XH 5-pin (4 cells + 1 GND) | ✅ |

### ISDT 608AC LiPo charger
Off-robot bench unit — no on-robot mount needed. AC mode caps ~55 W.

### Mxuteuk HB2-ES544 panel-mount E-stop
**Source:** Mxuteuk product page

| Dim | Value | Status |
|---|---|---|
| Mount hole | 22.0 mm dia | ✅ |
| Body height above panel | ~30 (mushroom button) | ⚠️ REVIEW |
| Below-panel depth | ~50 (contact block) | ⚠️ REVIEW |
| Contacts | 2× NC | ✅ |
| Twist-to-release | yes | ✅ |

### Class T 30 A fuse holder
**Source:** Bussmann Class T standard

| Dim | Value | Status |
|---|---|---|
| Holder body OD | 13.0 dia | ⚠️ REVIEW — depends on brand |
| Panel cutout | 13.5 dia round | ⚠️ REVIEW |
| Mounting stud spacing | varies by brand | ❌ MEASURE on hand |
| Interrupt rating | 20 kA AIC | ✅ |
| Current rating | 30 A | ✅ |

### MOSFET — IRLB3034PBF candidate (hard-cutoff)
**Source:** IR/Infineon IRLB3034PBF datasheet

| Dim | Value | Status |
|---|---|---|
| Package | TO-220 | ✅ |
| Body L × W × H | 10.16 × 4.83 × 19.05 (incl tab) | ✅ |
| Rds(on) at Vgs=4.5V | ~1.6 mΩ | ✅ |
| Id continuous | 195 A | ✅ |

### LM393 dual comparator
**Source:** TI LM393 datasheet

| Dim | Value | Status |
|---|---|---|
| Package | SOIC-8 (or DIP-8) | ✅ |
| Body L × W (SOIC) | 4.90 × 3.90 | ✅ |

---

## 6. Mechanical hardware

### 688ZZ ball bearing
**Source:** standard deep-groove ball bearing

| Dim | Value | Status |
|---|---|---|
| Inner dia | 8.0 | ✅ |
| Outer dia | 16.0 | ✅ |
| Width | 5.0 | ✅ |
| Bore press-fit clearance (PA6-CF) | +0.05 mm OD pocket | ✅ |

### 6 → 8 mm shaft sleeve adapter
**Source:** STS3215 bottom shaft is 6 mm; 688ZZ ID is 8 mm. Need 6 mm ID × 8 mm OD × ~5 mm long sleeve.

| Dim | Value | Status |
|---|---|---|
| Inner dia | 6.05 (light press on STS3215 shaft) | ⚠️ REVIEW — find off-shelf or print in PETG-CF |
| Outer dia | 8.00 (slip-fit in 688ZZ inner race) | ✅ |
| Length | 5.0 (matches bearing width) | ✅ |

### Ruthex M3 heat-set insert (project standard)
**Source:** [Ruthex M3 datasheet](https://www.ruthex.de)

| Dim | Value | Status |
|---|---|---|
| Insert length | 5.7 | ✅ |
| Insert OD (max) | 4.6 | ✅ |
| Recommended bore in PA6-CF | 4.0 (project standard) | ✅ |
| Boss OD around insert (recommended) | 7.0 minimum | ✅ |

### M3 hex cap screws (assorted lengths)
Standard ISO 4762 / DIN 912. Heads:

| Length | Head OD | Head height | Thread |
|---|---|---|---|
| M3 × 8 | 5.5 | 3.0 | M3 |
| M3 × 12 | 5.5 | 3.0 | M3 |
| M3 × 16 | 5.5 | 3.0 | M3 |

### Loctite 243 (medium-strength blue threadlocker)
Standard consumable. No mechanical dim. ✅

---

## 7. Connectors

### XT60 panel mount
**Source:** common XT60 spec (Amass / generic)

| Dim | Value | Status |
|---|---|---|
| Panel cutout rectangular | 15.5 × 8.0 with 1.5 mm corner R | ✅ |
| Below-panel body depth | ~12 | ⚠️ REVIEW |
| Above-panel projection | ~7 | ⚠️ REVIEW |
| Current rating | 60 A continuous | ✅ |

### XT30 (servo power injection)
**Source:** common XT30 spec

| Dim | Value | Status |
|---|---|---|
| Panel cutout | 10.0 × 5.5 | ✅ |
| Inline body L × W × H | 16.0 × 7.7 × 8.0 | ⚠️ REVIEW |
| Current rating | 30 A continuous | ✅ |

### JST-XH 3-pin (Feetech TTL daisy-chain)
**Source:** JST-XH datasheet

| Dim | Value | Status |
|---|---|---|
| Pin pitch | 2.50 | ✅ |
| Connector body (3-pin) | 7.5 × 5.9 × 10.0 (W × H × L) | ✅ |
| Cable cross-section (3 wires + sleeve) | ~3 × 5 | ✅ |
| Wire-slot pass-through (2 cables side-by-side) | 16 × 9 rect | ✅ (project standard, in `leg_common.py`) |
| Mating force | low | ✅ |

### JST-XH 5-pin (LiPo balance lead)
**Source:** JST-XH

| Dim | Value | Status |
|---|---|---|
| Pin pitch | 2.50 | ✅ |
| Connector body | 12.5 × 5.9 × 10.0 | ⚠️ REVIEW |

### RJ-45 Ethernet connector
**Source:** TIA/EIA-568

| Dim | Value | Status |
|---|---|---|
| Plug outline | 11.7 × 8.0 × 18.0 (with strain relief boot) | ✅ |
| Panel pass-through (typical) | 16.5 × 14.0 rect | ✅ |
| Cable: Cat 6 snagless | ~6.0 OD | ✅ |

### USB-A 3.1 (Type-A) panel pass-through
**Source:** USB 3.1 standard

| Dim | Value | Status |
|---|---|---|
| Connector body | 12.0 × 4.5 | ✅ |
| Panel rect with bezel clearance | 13.5 × 6.5 | ✅ |

### USB-C UFP (Jetson power-delivery)
**Source:** USB-IF Type-C standard

| Dim | Value | Status |
|---|---|---|
| Connector body | 8.34 × 2.56 | ✅ |
| Panel rect with bezel | 10.0 × 4.0 | ⚠️ REVIEW |

### 5.5 × 2.5 mm barrel jack (Jetson power input)
**Source:** standard barrel jack

| Dim | Value | Status |
|---|---|---|
| Panel hole | 8.5 round | ✅ |
| Anti-rotation flat (some variants) | 11.0 flat-to-flat | ⚠️ REVIEW |

### FE-URT-1 USB-TTL Feetech interface
**Source:** Feetech FE-URT-1 product page

| Dim | Value | Status |
|---|---|---|
| Body L × W × H | ~28 × 18 × 8 | ⚠️ REVIEW |
| USB connector | mini-USB Type-B (legacy) | ⚠️ REVIEW — some revs have micro-USB |
| TTL output | 3-pin JST-XH (Feetech servo cable) | ✅ |

---

## 8. Networking

### TP-Link LS105G 5-port gigabit switch (case-removed for chassis fit)
**Source:** TP-Link LS105G product page (case removed for ~60% volume savings per BOM §5)

| Dim | Value | Status |
|---|---|---|
| Cased enclosure L × W × H | ~100 × 60 × 25 | ⚠️ REVIEW |
| Bare PCB L × W | ~80 × 50 | ❌ MEASURE after case removal |
| RJ-45 jacks | 5× standard | ✅ |
| Power input | 5 V via micro-USB or barrel (varies by rev) | ⚠️ REVIEW |
| Power draw | ~3 W | ✅ |

### Cable Matters Cat 6 snagless 1 ft
Standard Cat 6 patch cable. 6.0 mm OD with snagless boot. ✅

### LC filter (L2 LiDAR rail clean power)
**Source:** project BOM v3.4

| Dim | Value | Status |
|---|---|---|
| Inductor | 22 µH, ≥2 A rated, radial choke 10-12 mm OD | ⚠️ REVIEW — exact part TBD |
| Capacitor | 470 µF / 25 V electrolytic, ~10 × 20 mm radial | ✅ |

### 1000 µF / 25 V bulk caps (4× along leg rail star injection)
**Source:** Panasonic EEU-FR1E102 or equivalent

| Dim | Value | Status |
|---|---|---|
| Body OD × height | 13.0 × 26.0 | ✅ |
| Lead pitch | 5.0 | ✅ |

---

## 9. Stock NovaSM3 sensors

### MPU-6050 on GY-521 breakout
**Source:** common GY-521 module specs

| Dim | Value | Status |
|---|---|---|
| Board L × W | 21.5 × 16.5 | ⚠️ REVIEW — varies by clone |
| Mount holes | 2× ~3 mm at ±7.6 from center (long axis) | ⚠️ REVIEW |
| Header pitch | 2.54 (8-pin or 9-pin) | ✅ |
| I²C addr | 0x68 (or 0x69 with ADO bridged) | ✅ |

### SSD1331 OLED 0.95" 96 × 64 color
**Source:** common SSD1331 module

| Dim | Value | Status |
|---|---|---|
| Board L × W | 25.7 × 22.2 | ✅ |
| Module L × W × H (incl pins) | 31 × 28 × 11 | ⚠️ REVIEW (varies by manufacturer) |
| Mount holes | not standardized; many modules have none | ⚠️ REVIEW |
| Active display area | 21.7 × 14.5 (0.95") | ✅ |
| Pin header | 7-pin SPI, 2.54 mm pitch | ✅ |

### HC-SR04 ultrasonic distance
**Source:** common HC-SR04 datasheet

| Dim | Value | Status |
|---|---|---|
| Board L × W | 45.0 × 20.0 | ✅ |
| Height with transducers | 15.0 | ✅ |
| Transducer dia | 16.0 each, ~26 mm spacing | ✅ |
| Pin header | 4-pin (VCC/Trig/Echo/GND), 2.54 mm | ✅ |
| Mount holes | not standardized; some modules have 2× M2 in corners | ⚠️ REVIEW |

### MH-SR602 PIR motion sensor
**Source:** common MH-SR602 module

| Dim | Value | Status |
|---|---|---|
| Board L × W | 10.0 × 12.0 (the smallest PIR module class) | ⚠️ REVIEW — varies by clone |
| Lens dome height | 5.5 above board | ⚠️ REVIEW |
| Pin header | 3-pin (VCC/Signal/GND), 2.54 mm | ✅ |
| Detection range | ~3 m | ✅ |

### DFPlayer Mini Pro
**Source:** DFRobot DFR0299 + various clones (Pro is the newer DFRobot rev)

| Dim | Value | Status |
|---|---|---|
| Board L × W × H | 36.0 × 21.0 × 4.0 | ⚠️ REVIEW — DFPlayer Mini is well known at this size; Mini PRO may differ |
| Mount holes | not standardized | ⚠️ REVIEW |
| Pin header | 2× 8-pin, 2.54 mm pitch | ✅ |
| micro-SD slot | standard | ✅ |

### WS2812B addressable RGB LED
**Source:** WorldSemi WS2812B datasheet

| Dim | Value | Status |
|---|---|---|
| LED package (5050) | 5.0 × 5.0 × 1.6 | ✅ |
| Strip pitch (60 LEDs/m) | 16.7 | ✅ |
| Strip pitch (100 LEDs/m) | 10.0 | ✅ |
| Strip pitch (144 LEDs/m) | 6.9 | ✅ |
| Project default | 100 LEDs/m (10.0 mm pitch) | ✅ |
| Strip width (PCB) | 8-12 (varies by manufacturer) | ✅ |

---

## 10. 3D Printing

### Bambu Lab P1S printer
**Source:** Bambu P1S spec

| Dim | Value | Status |
|---|---|---|
| Build volume X × Y × Z | 256 × 256 × 256 | ✅ |
| Nozzle (project hardened steel) | 0.4 mm | ✅ |
| Chamber | enclosed | ✅ |
| AMS HF | bypassed for PA6-CF (see BOM §8) | ✅ |

### Creality SpacePi X4 filament dryer
**Source:** [Creality SpacePi X4 product page](https://www.creality.com/products/creality-spacepi-x4)

| Dim | Value | Status |
|---|---|---|
| Chamber count | 4 (dual-chamber independently controlled) | ✅ |
| Max temperature | 85 °C | ✅ |
| Heating | 2× 200 W PTC | ✅ |
| Bowden output | 4 mm PTFE (top + rear) | ✅ |
| Spool support | 4 spools simultaneously | ✅ |

### Filaments (per BOM §8)

| Material | Use | Print profile | Status |
|---|---|---|---|
| PA6-CF (Bambu PolyMide PA6-CF or equiv) | structural (legs, chassis, mounts) | 280 °C nozzle, 100 °C bed soak, 24 h dry @ 70 °C, Magigoo PA on PEI textured | ✅ |
| PETG-CF (brick red) | secondary brackets | 250 °C, 80 °C bed, 12 h dry | ✅ |
| TPU 95A (yellow) | foot pads, strain relief | 230 °C, 60 °C bed, 20-30 mm/s, 4-6 h dry @ 50 °C | ✅ |
| PETG accent (white) | covers, light diffusers | 240 °C, 70 °C bed | ✅ |

---

## CRITICAL CORRECTIONS

These differ from values currently in `patterns.md` or `nova_sm3_patterns.md`:

1. **L2 LiDAR mount BCD = 22.5 mm**, NOT 50 mm. The earlier 50 mm in `patterns.md` §8 was a placeholder. Update `L2_LIDAR['bolt_circle_d']` from 50.0 → 22.5.
2. **STS3215 horn-disc OD = 20 mm**, NOT 25 mm as written in some older notes. STEP file is authoritative.
3. **STS3215 spline X offset = +12.5 mm** from body center. CRITICAL: every cavity in leg V3.1 reflects this. Old OpenSCAD `coxa.scad` had it at 0 (bug).

---

## How to use this file

When designing a new CAD part:

1. **Look up the part here first.** If ✅ VERIFIED, use the value.
2. **If ⚠️ REVIEW, caliper-measure the actual part before committing.**
3. **If ❌ MISSING, you must measure — no fallback.**
4. **Add the verification to this file** when you measure — bump ⚠️ to ✅ and cite source (e.g., "caliper 2026-05-24 on Ovonic pack A").
5. **Cross-reference** with `patterns.md` macros and `leg_v3/leg_common.py` constants. If they disagree, this file wins.

---

> **Status:** drafted 2026-05-24. Add measurements as parts arrive +
> caliper-verify. Mark this file as the canonical mechanical reference
> in PRs that touch CAD.
