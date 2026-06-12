# ⚡ ACTIVE PROJECT — nova_pcb_v6_power_v2 (forked from v1 2026-06-10 after safety-chain schematic fixes)

# nova_pcb_v6_power — GUI Routing Handoff

State at handoff: **DRC 0 errors, 50 ratsnest links** remaining. All headless-appropriate
power routing is done (RAW buck→INA hops, V12_JET / V12_L2 output rails, V7V5_LEG F.Cu
pour, J6 tap, V12_HIP INA→C5, V12_L2_RAW buck→inductor). The 50 remaining links are all
GUI-bound: the dense bottom-right logic cluster, plus 5 power/edge taps boxed behind
existing B.Cu walls or in the congested top THT cluster.

Inner planes (GND on GND.Cu/In, VBAT_PROTECTED on PWR.Cu/In) auto-connect every GND and
VBAT_PROTECTED THT pin — those are not in the ratsnest and need no routing.

## Netclasses (defined in `.kicad_pro`, not the board)

| Class | track | via | clearance | color | nets |
|---|---|---|---|---|---|
| HighCurrent | 3.0 | 1.4/0.7 | 0.3 | red | V7V5_LEG, V7V5_LEG_RAW, V12_HIP, V12_HIP_RAW |
| Power | 1.5 | 1.0/0.4 | 0.3 | amber | V12_JET(_RAW), V12_L2(_RAW), V5_AUX |
| Default | 0.2 | 0.6/0.3 | 0.2 | — | all signals |

Width basis (IPC-2221, external, 2 oz outer copper): 1.5 mm ≈ 7 A @ 20 °C rise;
3.0 mm ≈ 12 A @ 20 °C. Hip rail ~9 A and leg trunk ≥ hip, so those sit on HighCurrent.

> A netclass sets the **default width for new/rerouted copper only**. It does NOT resize
> existing traces — see Step 1.

## Pre-flight

1. Delete stale autosave files so KiCad won't offer a (stale) recovery:
   - `~_autosave-nova_pcb_v6_power.kicad_pcb.lck.orphaned`
   - `_autosave-nova_pcb_v6_power.kicad_pcb.orphaned`
2. Open board. **Board Setup → Net Classes** — confirm Default / HighCurrent / Power
   present and rails are colored.
3. Do not run the headless pcbnew/kicad-cli scripts while the GUI has the board open
   (and vice-versa). `/tmp/route.py` is idempotent from `/tmp/route_base.kicad_pcb` but
   will overwrite the board copper if re-run.

## Step 1 — widen existing power copper (netclass won't auto-resize)

Filter by net (or by netclass), select tracks, set width in Properties.

| Net | current | set to | note |
|---|---|---|---|
| V7V5_LEG (J6 tap + RAW hop) | 1.5 | 3.0 | LEG pour zone is already wide copper — leave it |
| V12_HIP (RAW hop + INA→C5) | 1.5 | 3.0 | |
| V12_L2_RAW (buck→L1) | 1.0 | 1.5 | |

Shortcut: filter ratsnest/selection by netclass `HighCurrent`, select all its tracks,
Properties → width 3.0.

## Step 2 — 5 power / edge taps (headless-blocked)

| Net | from | to | layer / width | note |
|---|---|---|---|---|
| VBAT | J1.1 (90, 65.05) | SW1.1 (113, 57) | F.Cu, 3.0+ | full battery current; set width manually |
| BATT_NEG | J1.2 (90, 57.85) | Q1.2 (129.54, 57) | F.Cu, 3.0+ | full battery return |
| V12_HIP | trackend (151, 118) | J7.1 (191, 85) | HighCurrent 3.0 | dodge JET B.Cu wall @ x188 |
| V7V5_LEG | trackend (187, 69) | J8.2 (191, 98.5) | HighCurrent 3.0 | right-edge stack — clear J7.1(191,85) between |
| BUS_SERVO | J20.6 (156.08, 126.35) | J8.3 (191, 96) | Default 0.2 | crosses L2/JET walls — F.Cu or via-hop |

VBAT and BATT_NEG carry the highest current on the board but their real net names carry
the `/01 Battery Input + Reverse Protection/` sheet prefix, so they are not in the
HighCurrent patterns. Either route them at >=3.0 mm by hand, or add patterns `*VBAT` and
`*BATT_NEG` to HighCurrent in Board Setup.

## Step 3 — 45 signal links (bottom-right logic cluster, Default 0.2 mm, any layer)

Dense U8 (LVC safety chain) + resistor network + J20 connector zone. Left for interactive
routing; the B.Cu GND pour reflows around them.

| Net | links | | Net | links |
|---|---|---|---|---|
| +3V3 | 8 | | HARDCUT | 3 |
| V5_AUX | 7 (Power 1.5) | | VREF_G | 3 |
| EN_BUCKS | 5 | | VREF_H | 3 |
| I2C_SCL | 4 | | BATT_LOW | 3 |
| I2C_SDA | 4 | | EN_SW | 1 |
| VSENSE | 4 | | | |

Suggested order: I2C pair first (keep SCL/SDA adjacent and short), then EN_* enables,
then VREF_G/VREF_H/VSENSE (safety-chain sense lines — keep short and away from buck
switch nodes), +3V3 last to fill remaining gaps.

## Step 4 — close out

1. `B` to re-pour all zones.
2. Run DRC — expect 0 errors once all 50 links are routed.
3. Spot-check thermal reliefs on the bulk-cap and connector THT pads (hand-solderable).

## Step 5 — GUI footprint-fix session (DO BEFORE FAB — needs the physical parts in hand)

Three footprint corrections. All GUI-only (raw .kicad_pcb edits would orphan routed tracks).
Parts arrive: INA226 ×4 Thu 2026-06-11; DigiKey batch TBD.

### 5a. INA226 colocation (DRC error ×3) — `nova_v6:INA226_Module_Breakout`, U9/U10/U11
- **Defect:** pad 8 (Vbus) stacked on pad 9 (IN−) at identical XY (−8.5, 2.54) → "drilled holes
  co-located" DRC error on all three INA226 modules. Both pads = same net (V7V5_LEG / V12_JET /
  V12_HIP respectively), so electrically fine; mechanically two drills in one spot = unfabricable.
- **Fix depends on the physical module (GODIYMODULES 20A R002, arriving Thu):**
  1. Measure the real module: IN+/IN−/VBUS hole positions + header pitch.
  2. If VBUS is internally tied to IN− on the module (no separate VBUS hole): **delete pad 8** from
     the footprint (keep pad 9 IN−). Net stays connected via pad 9.
  3. If VBUS has its own hole: **move pad 8** to that real position.
  4. Edit the library footprint, then **Update Footprints from Library** to push to U9/U10/U11.
- ⚠️ Also confirm shunt reads **`R002`** (2 mΩ) before trusting any current reading. See order-list
  §3 INA226 for the I²C-0x40 + 2 mΩ calibration bench-test (CAL reg = 2560 / 0x0A00 @ 1 mA LSB).

### 5b. L1 inductor land — `Inductor_SMD:L_12x12mm_H8mm` — ✅ RESOLVED, no action
- **Part bought:** Bourns **SRR1260-220M** (12.5×12.5×6 mm). Verified against Bourns datasheet
  (REV. 03/26, p.2 Recommended Layout): pad size 2.9×5.4 mm at 6.8 mm gap = **9.7 mm**
  center-to-center. Footprint pads (measured in .kicad_pcb, ±4.95 mm) = 2.9×5.4 mm at **9.9 mm**.
- Pad size **identical**; spacing diff only 0.2 mm (0.1 mm per pad on a 2.9 mm pad) — within
  paste/placement tolerance. **Solder as-is. No footprint swap needed.** (Earlier ~9.4 mm figure
  was from an unverified search snippet — wrong.)
- Electrically fine: 22 µH, 4 A vs L2's ~1 A = 4× margin.

### 5c. J20 IDC box header — ✅ RESOLVED, part chosen
- Footprint `Connector_IDC:IDC-Header_2x06_P2.54mm_Vertical` (2×6, 12-pos, 2.54 mm, vertical THT).
- Würth `61201221621` does NOT exist in DigiKey's catalog — dropped. Ordered instead:
  **Adam Tech BHR-12-VUA** (12-pos, 2-row, 2.54 mm, shrouded 4-wall, vertical THT, 3 A) —
  verified exact match on DigiKey (PN 10414809). Sanity-check the bag says BHR-12-VUA at solder time.

## Step 6 — Safety-chain fixes (schematic DONE 2026-06-10, board sync PENDING)

Electrical review found the e-stop non-functional (Pololu internal 100k EN→VIN pull-ups defeat
R10's 100k pulldown; disable needs EN <0.3V) and the hard cutoff sparing the Jetson rail (pack
drains below 12.4V if Jetson hangs). Fixed in schematic:

- **Q3 (BSS138_estop):** D=EN_BUCKS, S=GND, G=EN_SW. R13 repurposed as 10k pull-up EN_SW→V5_AUX;
  SW2 (NC e-stop) now shorts EN_SW→GND. Pressed OR wire break → Q3 pulls EN <0.3V. Fail-safe.
  R10 deleted (was useless against internal pull-ups).
- **Q4 (BSS138_jetcut):** D=EN_JET (new net → U4 pin 3, was hard-tied VBAT_PROTECTED), S=GND,
  G=HARDCUT. Battery <12.4V now kills Jetson rail too; e-stop still spares it (per spec §6).
- **R16 100k:** HARDCUT→GND. Defines Q2/Q4 gates off when V5_AUX/UBEC absent.
- **C8, C9 (470 µF 25V):** input bulk across VBAT_PROTECTED/GND — damps battery-lead LC ring at
  the off-board buck terminal landings (Pololu recommendation for long input leads).

All parts already in the DigiKey order (BSS138 ×10, 100k ×10, 470 µF ×10). ERC clean (1 expected
V7V5_ARM warning). **Board sync:** pcbnew → F8 (Update PCB from Schematic) → place Q3/Q4/R16 near
Q2, C8/C9 near U1–U5 terminal landings → route. Bench-verify e-stop + simulated-LVC before first
servo power.

### Close out (repeat Step 4)
`B` re-pour → DRC 0 errors → spot-check thermals → generate Gerbers → fab.


## Step 7 — v2 headless routing session (2026-06-10) — DONE except cluster internals

Placement redone power-flow-first (caps at injection points, INA columns aligned, L2 filter at
load). All copper wiped + rerouted headless. **DRC: 0 errors.** Routed: full power tree (battery
loop, leg RAW+pour, hip RAW doubled F+B through the 1.8mm squeeze, hip main on B, JET, L2 chain,
V5_AUX spine, J8 leg tap) + signals: I2C SCL/SDA (corridors y67.7/y67.0 + south lane y94.5 +
J20 risers), EN_BUCKS (F lane y98.27 + both feeders), BUS_SERVO (J20.6→J8.3 via C6-gap hop),
BATT_LOW (J20.9→R8.2→R15.1, 3 vias). Q3/Q4/R16 were on F after F8 — FLIPPED to B (cluster side).
R16 moved to (138.3,129.6).

### Remaining: 34 ratsnest links — ALL inside the B-side SMD cluster (x86-146, y124-140)
GUI interactive session (push-and-shove, B.Cu, 0.25mm, clearance 0.2):
- **+3V3 (8)**: J20.5 → R8.1/R11.1/R12.1 (local) + INA pads U9.6, U10.2, U10.6, U11.1, U11.6
  (the INA legs need hops over the I2C corridors — use short F segments north of y67 or vias)
- **HARDCUT (5)**: U8.7 + Q2.1 (west) → R9.2, R14.1, Q4.1 (144.94,134.55), R16.1 (139.12,129.6)
  — suggest F lane ~y126.6 with vias (F is empty below the pour edge y126)
- **VSENSE (4)**: R2.2–R3.1–C7.1–U8.2/U8.6 · **VREF_G (3)**: R15.2–R4.2–R5.1–U8.3
- **VREF_H (3)**: R14.2–R6.2–R7.1–U8.5 · **V5_AUX stubs (4)**: R4.1, R6.1, R9.1, U8.8 → spine
- **EN_SW (2)**: R13.1 → Q3.1 (137.24,135.35) + SW2.2 (145,57) — long haul north, F via x143.2
  corridor is clear (verified)
- **BATT_LOW (2)**: U8.1 → net · **EN_JET (1)**: Q4.3 (143.06,135.5) → U4.3 (164,98.27) — region
  x150-168/y95-131 is congested; suggest B exit east + F riser x146.3→y121→(150.9)→y104.5 lane
  was abandoned for crossings; route interactively
- **R2.1 (1)**: VBAT_PROTECTED → via to In2 plane (drop via anywhere near (101,137))

After: B re-pour → DRC → Gerbers. Power tree is final — do not reroute it casually; the F/B
layer assignments dodge specific walls (JET y79.54 F, HIP staircase B, V5 spine B, EN lane F).


## Step 8 — INA226 modules → OFF-BOARD (2026-06-11, measured + converted)

Physical GODIY/MJKDZ module ≠ guessed footprint (21.8×25.5, right-angle header GND/SCL/SDA/VCC,
screw terminals V− | Current −/+ | V+, R002 shunt ✓, A0/A1 4-way solder jumpers, addr default 0x40).
Flat/vertical board-mount both failed (25.5 > 20mm mezzanine gap / no room in INA band) →
**modules mount off-board (buck holder), wired into the rail like the bucks.**

Done in schematic+board (ERC clean, DRC 0 errors):
- U9/U10/U11 footprints stripped to the 4-pad I2C header (pads 4-7, SAME XY → I2C routing untouched)
- A0/A1/ALERT + Vbus/Vin± pins no-connected (addresses set by on-module jumpers:
  U9 leave=0x40 · U10 move A0 blob to VCC=0x41 · U11 move A1 blob to VCC=0x44 — sharpie-label!)
- Landing pin-4 nets renamed RAW→clean (U1→V7V5_LEG, U2→V12_HIP, U4→V12_JET); RAW nets gone
- All RAW tracks deleted; new clean joins: U2.4→hip B main, U4.4→JET F main; C3 pour stub

**Bench wiring per module:** buck VOUT wire → Current+ · Current− → wire → board landing pad 4 ·
jumper V+ screw → Current− (VBUS tap) · beep-test V−↔GND-pin; if isolated, V− → board GND ·
4-wire dupont from module header → board U9/U10/U11 header.

**GUI worklist (now ~22):** the SMD-cluster links + EN_JET finish + R2.1 plane via, PLUS:
- **LEG pour split at x≈142 seam** (left block ↔ top corridor are 2 fill islands; headless bridge
  attempts kept landing in carve-fenced pockets — fix visually: draw a short fat V7V5_LEG track
  through visibly-filled copper across the neck near (140-150, 68-75), or nudge the I2C corridor
  carves; then B re-pour)
- 4 dangling-track/via warnings = in-progress GUI work, clean as you finish


## Step 9 — ✅ ROUTING COMPLETE (2026-06-12, headless, collision-checked)

All cluster signal nets routed headless via a pre-commit collision checker (every planned
segment/via verified against all board copper + rotation-aware pad rects before commit;
~180 plan items, 0 conflicts at write). Architecture: horizontal lanes on B.Cu at y137.5
(VSENSE) / 138.1 (VREF_H) / 138.7 (VREF_G) / 139.3 (HARDCUT) / 139.9 (BATT_LOW), F.Cu
verticals, Ø0.45/0.25 via pairs at pad-drops and lane junctions (Ø0.6/0.3 in open areas).
V5_AUX: spine gap bridged x114.5 B.Cu 1.5 mm; branches join the y124 spine (R4/R6 web
y137.3 + F feed x125.5; U8.8 F-run arcing the x103 mounting hole; R9.1 F bridge x134.0).
EN_JET crosses the SCL rework all-B at y121.3, descends F x165.9. BATT_LOW reaches J20.9
all-B from the east (no vias). EN_SW full chain routed top-to-bottom.

**Board-setup change:** min via 0.45 mm / min through-drill 0.25 mm (was 0.5/0.3) to admit
the cluster via pairs. Within PCBWay standard capability (min via 0.4/0.2) — no upcharge.

### Final state: **DRC 0 errors · 0 unrouted nets · 2 zone-island seams (GUI one-liners)**
1. V7V5_LEG pour F.Cu island link (~x142 seam) — draw one 3.0 mm track through visibly
   filled copper across the neck near (140-150, 68-75).
2. GND pour B.Cu island link — same, one track through filled copper. Then `B` re-pour, DRC.
Warnings (cosmetic/expected): 13 lib_footprint_mismatch (modified INA headers), 1
silk_over_copper, 1 track_dangling (leftover fragment — delete or ignore).

45°-corner polish: select power tracks → right-click → Fillet/Chamfer tracks (cosmetic only;
all current-capacity work is already in widths/doubling, verified IPC-2152).

After seams: final DRC → Gerbers (`kicad-cli pcb export gerbers` + drill) → PCBWay.


## Step 10 — Amazon-part authenticity bench checks (DO BEFORE FIRST POWER)

DigiKey parts (16 lines, see `Complete_Digikey_Order_NOVA.csv`) are authorized-channel —
no checks needed. Amazon parts have **no traceability**; specs below are seller claims until
measured. Ranked by consequence of a fake:

### 10a. Q1 — IRLB3034 (Amazon 5-pack) — HIGHEST PRIORITY
Pass element of the battery hard cutoff; carries full ~15 A. Fake (relabeled smaller die) =
10× Rds(on) → ~4.5 W instead of 0.45 W at 15 A → thermal runaway on the protection part itself.
Test ALL 5, keep the best 2 (one spare):
1. **Gate threshold:** DMM diode mode or bench supply — Vgs ramp, drain conducts ~1.4–2.5 V.
2. **Rds(on) at Vgs = 4.5 V:** force known current (e.g. 1 A from bench supply through drain),
   measure Vds with DMM. Expect ≤ 2 mΩ → 2 mV @ 1 A (datasheet max 1.7 mΩ @ 10 V, ~2 mΩ @ 4.5 V).
   Fake readout: tens of mV. Use 4-wire/Kelvin probing — lead resistance swamps 2 mΩ otherwise.
3. **Consistency:** all 5 within ~30% of each other. Wide spread = mixed/fake batch.

### 10b. C1–C5 — FymuSing 1000 µF/25 V (Amazon, no datasheet exists)
Bulk transient absorbers at star injection points; ±20% tolerable, but verify they're not
hollow-spec: LCR/component tester (TC1/T7 ~$15 or DE-5000):
- Capacitance ≥ 800 µF (-20% floor)
- ESR < 100 mΩ (generic 1000µF/25V typically 20–60 mΩ)
- Test all 5 + spares; reject any outlier. Mark measured values on the can with sharpie.

### 10c. INA226 modules ×4 (GODIY) — shunt verified, chip unverified
R002 shunt already confirmed (photo + physical). TI silicon could be clone. Cal test per module
(after Step 8 wiring, before trusting telemetry):
1. I2C scan → addr responds (0x40/0x41/0x44 per jumper card above).
2. Manufacturer ID reg 0xFE = 0x5449 ("TI"), Die ID reg 0xFF = 0x2260. Clone often fails this.
3. Known load (e.g. 1 A from bench supply), CAL = 2560 (0x0A00) @ 1 mA LSB → current reg within
   5%. Off by 50× = R100 shunt snuck in; off by random = clone ADC.

### 10d. XT30/XT60 (SoloGood "AMASS") — clone check
- Genuine: **AMASS molded logo** on housing, tight mate (no wiggle), gold contacts uniform.
- Under first servo load test: IR-gun or finger-check each connector — warm = loose contact,
  re-crimp or swap. Order-list warning stands: clones run hot under servo transients.

### 10e. Low risk, quick checks
- **Blue Sea Contura SW1:** continuity both positions; no warmth at 15 A (UL-listed, rarely faked).
- **Mxuteuk e-stop SW2:** beep test NC contact: closed at rest, OPEN pressed + stays open until
  twist-release. Wire break must read as pressed (fail-safe direction — matches Q3 inverter design).
- **Pololu bucks:** bought direct from Pololu — genuine. Standard bring-up sweep only (Step 8 card).

Order of operations: 10a–10b on the bench BEFORE soldering anything; 10c after Step 8 wiring;
10d–10e during first power-up. Then proceed to the Step 8 bench validation sweeps.
