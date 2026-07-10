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
**AUTHORITY (2026-07-02 rev 2): the mesh-verified spline-frame table in
`leg_v6/leg_v6_common.scad`** (from `feetech_servo_models/converted_stl/servo.stl`,
= `STS3215_03a v1` incl. horn+wheel bodies). Spline-relative, shaft = +Z, case
extends −X:

| Dim | Value | Status |
|---|---|---|
| Case box | x −35.2..+10.2 · y ±12.4 · z −15.5..+14.7 | ✅ mesh 2026-07-02 |
| Rear top cap ridge | to z 17.4 (x −34.8..−28.5, y ±7) | ✅ mesh |
| Output HORN disc | Ø20 × 2.5, z 14.7..17.2 (+boss to 20.2) | ✅ mesh |
| Bottom WHEEL disc | Ø20 × 2.1, z −17.7..−15.6 — **standard-fitted** | ✅ mesh |
| Disc screw pattern (BOTH discs) | 4× M2.5 on Ø14 BCD ±45° + center (horn ctr M3, wheel ctr M2.5) | ✅ mesh |
| Connector bay | rear-bottom to z −19.4 over x<−5.3, **FULL width ±12.35**; 2× 3-pin sockets mid-body facing rear | ✅ mesh (fit-gate catch) |
| **REAL case mounting** | the 4 case-screw columns (Ø2 self-tap, heads at the bay): (−8.3, ±10.2) & (−32.8, ±10.25) — use longer M2 through the printed floor | ✅ mesh |
| Spline offset from body center | +12.50 along the long axis | ✅ |
| Batch tolerance | ±0.10 | ✅ manufacturer |

> ⚠️ **Corrected 2026-07-02:** the earlier "body mount screws 9.9×9.9 square on
> both faces" row was a MISREAD of the STEP — those r1.25 circles are the
> horn/wheel **disc** holes (BCD14 at ±45° ≡ ±4.95 square). Screws driven there
> thread into nothing. Cost one full pocket redesign; see leg_v6 README rev 2.

---

## 2. Compute + perception

### NVIDIA Jetson Orin Nano Super Developer Kit (P3766)
**Source:** [NVIDIA P3766 datasheet](https://developer.nvidia.com/embedded/jetson-orin-nano-developer-kit) + user OnShape import

| Dim | Value | Status |
|---|---|---|
| Carrier board L × W | 100.0 × 79.4 | ✅ |
| Mount-hole pattern (rectangular) | 96.5 × 75.4, 4× M3 | ✅ |
| SOM heatsink height above carrier (top of fan) | **34.9** | ✅ CALIPER 2026-07-07 (top of fan above the board; was ~21.5 guess — +13.4). ⚠ heatsink top = 78.2 board plane + 34.9 = **113.1** would POKE the L2 mast plate. **RESOLVED 2026-07-07:** the bespoke tray+hood is retired; the board+heatsink now live in the official case on the deck (case row below), the L2 mast base was compacted into the front strip, and its plate lifted to z113.4. See chassis README "Jetson enclosure decision" + `chassis/place_case.py` |
| Official Jetson case (OfficialPrintProfile) | **110.3 × 93.9 × 38.2** enclosure; **PORTS on the 93.9-wide END face** (normal along the 110.3 long axis), heatsink block on the OPPOSITE end; hex vents all sides, board mounts inside on its own bosses; bottom vented (mount via 4 solid corners) | ✅ CALIPER 2026-07-07 (mesh said 110.5×95.2×38.5 — use these calipered numbers). Adopted, replaces the bespoke hood |
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
| Body L × W × H | **123.8 × 26.0 × 29.0** | ✅ CALIPER 2026-07-07 (facing forward) |
| **Mount pattern (back face)** | **2× M3, 94.4 apart** center-to-center, on the back-face centerline (±47.2 along length, width-centered) | ✅ CALIPER 2026-07-07 — the design's guessed 4×-corner (±54) pattern is WRONG, it's these 2 |
| **Chassis mount** | `chassis/head.scad` — camera seats on a **27° DOWN-tilted** front face (back-face ctr at trunk 70,0,105.5), forward of the chassis so near-ground is in frame (replaces the retired periscope). Right-angle USB-C (BOM) | ✅ 2026-07-07 (head_study.py: 0 leg-sweep hits at front hfe −50) |
| ~~Mount alt pattern 4×~~ | retired — real back mount is the 2× above | ✅ |
| IR projector center offset | 14.0 from body centerline | ⚠️ REVIEW |
| USB 3.1 cable connector | Type-C on rear | ✅ |
| Cable thickness with shield | ~6.0 (USB-A end) | ⚠️ REVIEW |

### Unitree L2 4D LiDAR
**Source:** [L2 User Manual 2024.10 v1.1](https://oss-global-cdn.unitree.com/static/Unitree%204D%20LiDAR%20L2%20User%20Manual.pdf)

| Dim | Value | Status |
|---|---|---|
| Body W × D × H | 75.0 × 75.0 × 65.0 | ✅ |
| Weight | 230 g | ✅ |
| Bottom mount holes | **4× M3 on a Ø51 bolt circle** (holes at the 4 diagonals, R25.5·cos45 = ±18 → a 36 mm axis-aligned square), depth 6 | ✅ **CONFIRMED from the manual drawing** (2024.10 v1.1 p10, "L2 Mechanical Dimensions": Ø51 BCD, "4× M3 ▽6"). Matches the model exactly (`l2_adapter.scad`/`head.scad` L2_BCD=18). Supersedes the earlier "22.5 mm square" (wrong — 22.5° is the SLOT clocking angle, not a square) and the "50 mm" placeholder. |
| Positioning slots | **4× slots, 3.5 mm wide, on Ø60**, clocked 22.5° off the M3 holes | ✅ manual p10 — anti-rotation datum (optional; `l2_adapter` uses the 4× M3 only, no slot pins) |
| Mount hole thread depth | 6.0 | ✅ |
| Power barrel | **3.5 × 1.35 mm** | ✅ CALIPER 2026-07-07 — the OEM connector that SHIPPED with the L2 measures 3.4 OD (3.5×1.35 class); supersedes the manual's ambiguous 5.5×2.1/2.5. The purchased 3.5×1.35 bare-wire pigtail matches → wires to the 12V L2 rail. Mast bore unaffected (molded housing ~Ø8 passes; RJ45 11.7×8 is the binding constraint) |
| Ethernet | RJ-45 (standard) | ✅ |
| FoV | 360° × 90° | ✅ |
| **Chassis mount** | `chassis/head.scad` CROWN via `l2_adapter.scad` — 4× M3 on 36 mm square (±18), bolted from BELOW the crown plate; optical center at trunk z~154 (crown seat top 122). Replaces the retired standalone `l2_mast.scad`. 360° ring clear (nearest structure 36 mm below); rear-down cone blind only below −83° (Jetson case) | ✅ 2026-07-07 (head_study.py) |
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

### SN74LVC125A quad tri-state buffer (Pattern B half-duplex driver)
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
**Source:** Pololu dimension drawing **reg34c** (15 Oct 2025, items 5668-5686), category 370

| Dim | Value | Status |
|---|---|---|
| Board L × W | **31.8 × 43.2** | ✅ (reg34c — CORRECTS earlier 25.4×25.4) |
| Mount holes | **4× ⌀2.18** (#2 / M2) on 25.4 × 38.9 rectangle | ✅ (reg34c) |
| Power holes | 4× ⌀2.2 THT (14 AWG), top→bottom VIN GND GND VOUT, vertical span 17.94 | ✅ (reg34c) |
| Signal holes | 14× ⌀1.02 on 2.54 grid (2×7) — carries EN + VRP/PG + duplicate power | ✅ count (reg34c); per-hole pin map ⚠️ VERIFY on board |
| Height (with components) | ~13-15 | ⚠️ REVIEW — caliper total Z on received board |

### Pololu D24V22F12 (L2 LiDAR dedicated, v3.4 split)
**Source:** Pololu dimension drawing **reg19a** (12 Nov 2015, items 2855/2857-2861), category 192

| Dim | Value | Status |
|---|---|---|
| Board L × W | **17.8 × 17.8** | ✅ (reg19a — CORRECTS earlier 20.3×17.8) |
| Mount holes | **2× ⌀2.18** (#2 / M2) diagonal on 13.2 × 13.2 | ✅ (reg19a — CORRECTS earlier "none") |
| Connector | 6× ⌀1.02; main row L→R **PG · EN(SHDN) · VIN · GND · VOUT** + 6th GND offset | ✅ order (reg19a + photo 0J6897); verify L→R vs module |
| Header pitch | 2.54 | ✅ |
| Height (tall caps above PCB) | 6.0 | ✅ (reg19a profile); +~3 header pins below |

### Pololu D42V55F12 (Jetson 12V rail) / D42V55F7 (arm, Phase 4 DNP)
**Source:** Pololu dimension drawing **reg34a** (18 Jun 2025, items 5570-5579), category 354

| Dim | Value | Status |
|---|---|---|
| Board L × W | **25.4 × 25.4** | ✅ (reg34a — CORRECTS earlier 22.9×17.8) |
| Mount holes | **3× ⌀2.18** (#2 / M2) on 21.1 × 21.1, top-left corner omitted | ✅ (reg34a) |
| Connector | 2×6 ⌀1.02; cols L→R **VOUT · GND · VIN · VRP · PG · EN** (power dup both rows) | ✅ order (reg34a + photo 0J15502); verify L→R vs module |
| Header pitch | 2.54 | ✅ |
| Height (standoff) | 6.1 (F7 & F12 are both ≤12V) | ✅ (reg34a profile) |

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

**v3.5+ (2026-06-04): all 3 rails (U9 leg / U10 hip / U11 Jetson) use this identical module** — no bare VSSOP-10 chip + external 2512 shunt (R13/R14 deleted from schematic). The onboard shunt must be **2 mΩ** (a "20A INA226" board); cheap 0.1 Ω "meter" modules saturate >0.8 A and are useless on 8-12 A rails. KiCad footprint: `nova_v6:INA226_Module_Breakout`. Module internal shunt bridges each rail's `*_RAW`↔clean nets (high-side sense).

---

## 5. Battery + safety

### 4S LiPo Ovonic 6000 mAh 120C
**Source:** Ovonic product page

| Dim | Value | Status |
|---|---|---|
| Pack L × W × H | **155.0 × 46.8 × 35.0** | ✅ CALIPER 2026-07-07 (width +0.8 vs the 46 listing; L/H matched). battery_pocket CLR tightened 0.8→0.6/side → cavity re-cut, chassis gate re-run clean |
| Weight | 510 g | ✅ listing (1.12 lb) |
| Balance lead | JST-XHR-5P (4S) | ✅ listing |
| Power lead | XT60 (Ovonic kit includes XT60 jumper + balance lead) | ✅ |
| Balance lead | JST-XH 5-pin (4 cells + 1 GND) | ✅ |

### ISDT 608AC LiPo charger
Off-robot bench unit — no on-robot mount needed. AC mode caps ~55 W.

### Blue Sea 5191 MRBF terminal block (battery-lead fuse holder)

| Dim | Value | Status |
|---|---|---|
| Body L × W × H | **61.6 × 20.0 × 46.5** | ✅ CALIPER 2026-07-07. **MOUNT = ASSEMBLY-TIME EXTERNAL** (2026-07-07): no clean captive spot exists — belly = leg-crouch space, rear-center = shoulder flange, trunk = mezzanine stack (all gate-verified). Bracket/zip-tie to the rear-shoulder exterior or trunk rear at assembly, near the battery-lead entry |
| Terminal / fuse tab width | 16.0 (within the 20 width) | ✅ CALIPER 2026-07-07 |
| Terminal STUD Ø | **7.8** (→ **M8**) | ✅ CALIPER 2026-07-07 — battery + output ring terminals = M8 lugs |
| Terminal hole Ø | 10.1 | ✅ CALIPER 2026-07-07 — clearance/boot hole around the M8 stud |
| Base mount hole Ø | **11.1** | ✅ CALIPER 2026-07-07 — the L-bracket foot hole that bolts to the floor plate (big → takes up to ~M10, or a printed post + M6 with a washer; floor_plate gets this hole + a 61.6×20 pocket) |

### Mxuteuk HB2-ES544 panel-mount E-stop
**Source:** Mxuteuk product page

| Dim | Value | Status |
|---|---|---|
| Mount hole | 22.0 mm dia | ✅ |
| Body height above panel | ~30 (mushroom button) | ⚠️ REVIEW |
| Below-panel depth | ~50 (contact block) | ⚠️ REVIEW |
| Contacts | 2× NC | ✅ |
| Twist-to-release | yes | ✅ |

### Class T 30 A fuse holder — ⚠️ SUPERSEDED 2026-06-12 (fuse is now MRBF-30)
> Fuse changed to **MRBF-30 in a Blue Sea 5191 terminal block** (off-board, bolts to chassis at the pack — no printed holder needed). The Class-T-holder dims below are obsolete; kept only if a Class T is ever re-adopted (e.g. paralleled packs). Same applies to the `patterns.md` Class-T-holder generator.

**Source:** Bussmann Class T standard
**Mounting: OFF-BOARD (2026-06-04)** — inline bolt-down block in the battery→PCB XT60 lead near the pack; **not a PCB footprint** (F1 removed from `nova_pcb_v6`). At-source placement protects the battery cable too. Dimensions below are for chassis/lead mounting, not a board cutout.

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

### Leg kinematics — axis-to-axis link lengths (B2 pass, 2026-07-01)
**Source:** original NovaSM3 STLs (leg_v5 preserves stock pivots) via trimesh
slice-circle bore detection (1 mm slice steps, circle fit σ<0.15 mm). Feeds
`nova.urdf.xacro` + `leg_ik.LegParams` (guarded by `test_urdf_sync`).

| Dim | Value | Status |
|---|---|---|
| Femur length (hfe→kfe axis) | **106.9** | ✅ hfe = STS horn axis (49.5, z10) in LeftFemur local (cavity spline, user-confirmed overlay); kfe = knee bore (−56.71, z22.02) + M2.5-square pattern ctr (−56.72, z22.05). In-plane components Δx 106.21 / Δz 12.02 — 12 mm kink absorbed into hfe zero-cal |
| Tibia length (kfe→foot post ctr) | **129.0** | ✅ kfe = STS spline (62.5, 0) in RightTibia local (confirmed placement); foot = Ø7 post at (−66.5, 3.3), full-height cylinder z 0–19.3 |
| Tibia toe-tip extreme (kfe→tip) | 138.0 | ✅ vertex (−75.46, 0.47); foot cap radius ≈ 9 over post ctr |
| Max leg reach (femur+tibia) | 235.9 | ✅ derived |
| Hip lateral offset chain (haa→foot plane, IK "d") | **64.3** = 24.6 (haa→hfe) + 9.2 (hfe→kfe) + 30.5 (tibia S-curve) | ✅ MEASURED 2026-07-02 from the official **Assembly_NOVA_SM3 Fusion/A360 share** (novaspotmicro.com embeds it) via viewer instance-tree world transforms — the 25t servo-horn instances mark every joint axis. Front-right leg: haa horn (−31.6, −185.4, −98.6) axis∥Y · hfe horn (−56.2, −155.4, −108.1) axis∥X · kfe horn (−65.4, −79.8, −182.3) · foot ctr (−95.9, −149.5, −285.9) |
| hfe drop below haa | 9.5 | ✅ same source |
| Hip grid: haa fore-aft × lateral spacing | **282.4 × 78.1** (half: 141.2 / 39.05) | ✅ same source; front/rear + left/right symmetric about (7.45, −14.2) |
| Assembly cross-check of femur length | 105.9 (vs 106.9 bore-metric) | ✅ bbox-center precision ±0.7 — bore metric kept |
| Joint ranges haa/hfe/kfe | 0.7 / 1.5 / 2.2 rad | ⚠️ REVIEW — conservative placeholders, verify vs collision in sim/first-article |
| hfe sw ROM (chassis gate) | fold **+50°** (both) · protraction **−50° FRONT / −86° REAR** | ✅ 2026-07-07 — FRONT protraction capped −50 so the forward head (head.scad, x70..100 z80..120) clears the front-leg sweep; rear keep −86. Wired: URDF `hfe_ext_front`/`hfe_ext` + `check_fit.py` HEAD case. Gait uses −30..−50, still a strong stride |

### SM3_Foot shoe (stock TREAD CRESCENT on the toe_v2 seat)
**Source:** mesh survey 2026-07-06 **v3** (`SM3_Foot.stl`, polar slice
sweep — scripted, supersedes v2's eyeballed radii; v2's "pad setback"
story remains RETRACTED). Shoe local frame: crescent center (0, +7),
band axis = z. Angles below = azimuth about the crescent center.

| Dim | Value | Status |
|---|---|---|
| Shoe envelope | 37 × 20 × 20 | ✅ mesh |
| Form | tread crescent in the SWING plane; THREE mating features: inner face, edge lips, 2 key tabs; post hole stays exposed | ✅ mesh + photo |
| Crescent center (shoe local x,y) | (0, +7.0) → mounts ON the Ø7 post (129, 0) | ✅ mesh |
| Inner face (core band) | **r 12.53** (min 12.529, p50 12.60), spans z ±7.3 | ✅ mesh v3 |
| Retention lips | **r 10.35–10.42**, both band edges (z ±7.3..±10), az 209–330 only (band bottom); snap over the seat-disc faces | ✅ mesh v3 |
| Key tabs (2, L-hooks) | mid-band only, z ±2.4 (4.8 tall); tips reach **r 6.88**; centers at band-ctr ±80.4° (shoe az 189.4 / 350.2); material spans 34.6° / 31° | ✅ mesh v3 |
| Tread outer radius | ≈ 16.0–16.8 (ribbed) | ✅ mesh |
| Band angular span | 208° (az 166→14, ctr 270; opening faces the blade neck) | ✅ mesh v3 |
| Band width | 20 = toe tab thickness 20.1 (flush) | ✅ |

> **toe_v2 seat (tibia.scad)**: core disc r 12.35 × 14.2 (0.18 / 0.2-side
> clearance, rim-chamfered 1.0 for snap-over) + full-width boss r 10.15
> under the lips + two sector key pockets (floor r 6.6, half-angle 19°,
> 6.0 tall, symmetrized about band center so L-mirror fits the same shoe).
> **Gate: `leg_v6/check_shoe.py`** (sampled shoe mesh vs tibia solid: zero
> penetration + seat-gap median < 0.4; in build_all.sh).
>
> Contact stays plumb under the post (the IK foot point) for any forward
> lean to ~80°: the tread is a constant-radius band about the post, by
> construction. Reprint in TPU 95A keeps the same interface.
>
> Mount (v6 tibia local): `T(129, 0, −30.5) · rotZ(54°) · T(0, −7, 0)` —
> **θ = 54 EXACTLY** now (band ctr 270 + 54 = −36 = stance-plumb; the key
> pockets fix it; residual rotational slop ±~2°).

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

### 1000 µF / 25 V bulk caps (5× at rail star injection: 4× leg V7V5_LEG + 1× hip V12_HIP)
**Source:** height-reduced radial, Ø12.5 × 16 mm (Rubycon ZLH `25ZLH1000MEFC12.5X16`); shortened from 20-26 mm to fit the 46.9 mm mezzanine stack — Ø12.5 unchanged, so footprint is unchanged

| Dim | Value | Status |
|---|---|---|
| Body OD × height | 12.5 × 16.0 | ✅ — low-profile ZLH (Ø unchanged, height 16 mm) |
| Lead pitch | 5.0 | ✅ |
| Footprint | `Capacitor_THT:CP_Radial_D12.5mm_P5.00mm` | ✅ |

---

## 9. Stock NovaSM3 sensors (v3.5 BOM cut — only OLED + WS2812B remain active)

**Cut for v1 (2026-05-24):** MPU-6050, HC-SR04, MH-SR602 PIR, DFPlayer +
speaker. Already owned — stay on shelf, no chassis cutouts or active
mounts. Dims kept here only for future re-introduction reference.

### Active

### ⏸ Cut from v1 (on shelf)

### MPU-6050 on GY-521 breakout (CUT v1)
**Source:** common GY-521 module specs

| Dim | Value | Status |
|---|---|---|
| Board L × W | 21.5 × 16.5 | ⚠️ REVIEW — varies by clone |
| Mount holes | 2× ~3 mm at ±7.6 from center (long axis) | ⚠️ REVIEW |
| Header pitch | 2.54 (8-pin or 9-pin) | ✅ |
| I²C addr | 0x68 (or 0x69 with ADO bridged) | ✅ |

### ✅ Active in v1

### SSD1331 OLED 0.95" 96 × 64 color (ACTIVE)
**Source:** common SSD1331 module

| Dim | Value | Status |
|---|---|---|
| Board L × W | 25.7 × 22.2 | ✅ |
| Module L × W × H (incl pins) | 31 × 28 × 11 | ⚠️ REVIEW (varies by manufacturer) |
| Mount holes | not standardized; many modules have none | ⚠️ REVIEW |
| Active display area | 21.7 × 14.5 (0.95") | ✅ |
| Pin header | 7-pin SPI, 2.54 mm pitch | ✅ |

### HC-SR04 ultrasonic distance (CUT v1)
**Source:** common HC-SR04 datasheet

| Dim | Value | Status |
|---|---|---|
| Board L × W | 45.0 × 20.0 | ✅ |
| Height with transducers | 15.0 | ✅ |
| Transducer dia | 16.0 each, ~26 mm spacing | ✅ |
| Pin header | 4-pin (VCC/Trig/Echo/GND), 2.54 mm | ✅ |
| Mount holes | not standardized; some modules have 2× M2 in corners | ⚠️ REVIEW |

### MH-SR602 PIR motion sensor (CUT v1)
**Source:** common MH-SR602 module

| Dim | Value | Status |
|---|---|---|
| Board L × W | 10.0 × 12.0 (the smallest PIR module class) | ⚠️ REVIEW — varies by clone |
| Lens dome height | 5.5 above board | ⚠️ REVIEW |
| Pin header | 3-pin (VCC/Signal/GND), 2.54 mm | ✅ |
| Detection range | ~3 m | ✅ |

### DFPlayer Mini Pro (CUT v1)
**Source:** DFRobot DFR0299 + various clones (Pro is the newer DFRobot rev)

| Dim | Value | Status |
|---|---|---|
| Board L × W × H | 36.0 × 21.0 × 4.0 | ⚠️ REVIEW — DFPlayer Mini is well known at this size; Mini PRO may differ |
| Mount holes | not standardized | ⚠️ REVIEW |
| Pin header | 2× 8-pin, 2.54 mm pitch | ✅ |
| micro-SD slot | standard | ✅ |

### WS2812B addressable RGB LED (ACTIVE)
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
| PA6-CF (Bambu PolyMide PA6-CF or equiv) | structural (legs, chassis, mounts) | 280 °C nozzle, 100 °C bed soak, 24 h dry @ 70 °C, Magigoo PA on Engineering Plate (smooth) | ✅ |
| PETG-CF (brick red) | secondary brackets | 250 °C, 80 °C bed, 12 h dry | ✅ |
| TPU 95A (yellow) | foot pads, strain relief | 230 °C, 40-45 °C bed (Engineering Plate smooth — glue as release, remove cold), 20-30 mm/s, 4-6 h dry @ 50 °C | ✅ |
| PETG accent (white) | covers, light diffusers | 240 °C, 70 °C bed | ✅ |

---

## 11. Stock trunk shell — SM3_Frame_ChassisTrunk

**Source:** mesh survey 2026-07-06 (`chassis/measure_trunk.py` on
`original_body_files/SM3_Frame_ChassisTrunk.stl`). Frame: floor bottom z=0,
+x = FRONT (the printed "F" arrow), y lateral. **The old "~118×100×40
interior" assumption was WRONG — the trunk is an open frame, not a tub.**
The ends are open above the floor (closed at assembly by the v6 shoulder
flanges); nothing exists above z 29.0 except the four corner wedges.

| Dim | Value | Status |
|---|---|---|
| Outer envelope | 127.0 × 110.0 × 46.91 | ✅ mesh |
| Floor slab top | z 3.9 (large rear + corner cutouts below) | ✅ mesh |
| Side walls | 6.0 thick; inner faces y ±48.93; **top z 29.0** | ✅ mesh |
| Side-wall notch | x 18.2..31.2 down to z 12.5, BOTH walls | ✅ mesh |
| Interior clear width | 97.86 (mezzanine 90 fits, 3.9/side) | ✅ mesh |
| Corner wedges | 4× leaning slabs (~35°, ~5.7 thick), wall top → plateau | ✅ mesh |
| Wedge plateau tabs | z 46.91, x ±(53.3..63.5), y ±(29.9..36.0) | ✅ mesh |
| Wedge windows | ~9.4 × 6.4 under each tab @ ctr (y ±34.5, z 43.5) — stock cover hooks, unused | ✅ mesh |
| Shoulder bolt bores | Ø3.16 along x at (y ±51.75, z 5.0 & 24.0), 6.5 deep, both ends | ✅ mesh (matches shoulder.scad) |
| Floor holes (stock mounts) | 3× Ø4 @ (−37.9/−32.9/−27.9, +43.8) · 2× Ø4 @ (−9.1, +28/+33) | ✅ mesh |

> ⚠ **Stack-corner conflict:** the 112-long mezzanine's corners intersect the
> leaning slabs at |x| 53.3..56 over the slabs' FULL height (z 29..46.9).
> Disposition: hand-trim the four slab inner ends back to |x| ≥ 56.5 when
> the fabbed boards arrive (slabs only ever supported the stock covers; the
> riser seats on the wall tops + plateau tabs). `chassis/check_fit.py`
> enforces the zone.

---

## CRITICAL CORRECTIONS

These differ from values currently in `patterns.md` or `nova_sm3_patterns.md`:

1. **L2 LiDAR mount = 36 mm square** (±18; ≡ Ø51 bolt-circle at 45°), per the L2 3D model / `l2_adapter.scad`. NOT 22.5 mm, NOT the older 50 mm placeholder. ⚠ physical-measure pending (user to confirm). Update `L2_LIDAR['bolt_circle_d']` to the Ø51-at-45° form.
2. **STS3215 horn-disc OD = 20 mm**, NOT 25 mm as written in some older notes. STEP file is authoritative.
3. **STS3215 spline X offset = +12.5 mm** from body center. CRITICAL: every cavity in leg V3.1 reflects this. Old OpenSCAD `coxa.scad` had it at 0 (bug).
4. **STS3215 horn screws are M2.5, NOT M3.** STEP shows holes at r=1.25 mm (∅2.5 = M2.5 clearance). Older notes / `patterns.md` calling them M3 are wrong. BCD measured at 13.86 mm (call it 14 mm).
5. **STS3215 body Z (between horn faces) = 34.3 mm**, not 36.8. Older 36.8 figure conflated body height with bbox-including-horn-discs. Bbox total Z = 39.6 (39.6 - 34.3 = 5.3 mm of horn-disc stack on top + bottom). Use 34.3 for bracket pocket depth.
6. **patterns.md §3 mount_x_pitch=49 / mount_y_pitch=10 IS WRONG** — body is only 45.4 mm long, so 49 mm pitch is impossible. ✅ **RESOLVED (2026-06-07, see note 9):** STEP inspected — real pattern is a **9.9 × 9.9 mm square** of 4× M2.5, centered on the spline axis. Update `patterns.md` mount macro to this; do NOT use the old 49×10 numbers.
7. **Pololu buck board sizes in §4 were pre-drawing estimates — all three corrected** from the Pololu dimension drawings (reg19a / reg34a / reg34c): D42V110 = **31.8 × 43.2** (was 25.4×25.4, badly wrong), D24V22 = **17.8 × 17.8** (was 20.3×17.8; also has 2× ⌀2.18 mounts, not "none"), D42V55 = **25.4 × 25.4** (was 22.9×17.8). Chassis buck-carrier pockets must use the corrected sizes. Connector L→R pin orders now recorded per buck — **verify against the physical module before PCB fab** (a wrong order is a coordinate swap in `nova_v6.pretty`).
8. **Class-T fuse is OFF-board + all 3 INA226 are modules (2026-06-04).** F1 fuse block dropped from the PCB (now an inline block in the battery lead); leg/hip INA226 (U9/U10) changed from bare VSSOP-10 + external 2 mΩ 2512 shunt to the same `INA226_Module_Breakout` U11 uses, and shunts R13/R14 were deleted. Board now carries **zero fine-pitch (VSSOP-10) parts**. Schematic done + ERC-clean; `.kicad_pcb` needs **Update PCB from Schematic (F8)** to realize it.
9. **STS3215 body mount-screw pattern extracted from STEP (2026-06-07).** Parsed the 18× r=1.25 mm (∅2.5 = M2.5) circles in `STS3215_03a v1.step` → a **9.9 × 9.9 mm square** of 4 holes, centered on the spline axis (x=12.5, y=0): (x,y) = {7.55, 17.45}×{±4.95}, present on **both** shaft-normal faces. Top face holes sit at R≈7 — **inside the ∅20 horn disc, so unusable**; mount through the **bottom (back-shaft) face**. Implemented as `sts3215_mount_holes()` in `leg_v5_screwlock/sts3215_mount.scad`. Closes note 6.

---

## How to use this file

When designing a new CAD part:

1. **Look up the part here first.** If ✅ VERIFIED, use the value.
2. **If ⚠️ REVIEW, caliper-measure the actual part before committing.**
3. **If ❌ MISSING, you must measure — no fallback.**
4. **Add the verification to this file** when you measure — bump ⚠️ to ✅ and cite source (e.g., "caliper 2026-05-24 on Ovonic pack A").
5. **Cross-reference** with `patterns.md` macros, `leg_v5/leg_v5_common.scad` (canonical leg dims), and `archive/leg_v3/leg_common.py` constants. If they disagree, this file wins.

---

> **Status:** drafted 2026-05-24. Add measurements as parts arrive +
> caliper-verify. Mark this file as the canonical mechanical reference
> in PRs that touch CAD.
