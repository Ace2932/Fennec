# 🧊 FROZEN 2026-06-10 — work continues in ../nova_pcb_v6_power_v2/ (identical fork incl. Step-6 safety fixes). Do not edit this project.

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
