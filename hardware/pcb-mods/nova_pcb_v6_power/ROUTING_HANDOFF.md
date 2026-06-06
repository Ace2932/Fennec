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
