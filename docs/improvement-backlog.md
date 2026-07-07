# Design Improvement Backlog

From the 2026-07-06 full-assembly review (post toe_v2 + shoulder rev4 +
load analysis). Ranked within group. Status legend: **NOW** (this batch),
**NEXT** (unblocked, do soon), **GATED** (blocked on listed trigger),
**DECISION** (needs a user call).

## Mechanical — cheap, high value

| # | Item | Why | Status |
|---|---|---|---|
| 1 | Shoulder flange bolt bosses 4→7 | weakest number on robot: lower flange inserts hold on 4 mm (SF 2.5 at 97 N prying). Upper bores already backed by the shear webs; only the LOWER pair needs pads. → SF ~5 | **NOW** |
| 2 | Breakaway fuses, D456 + L2 mounts | faceplant unbounded; a calibrated printed fuse (~4–6× the 0.72 N·m operating moment) dies instead of the sensor. Fuse = separate cheap part, not the mast | **NOW** |
| 3 | BOM: shell-side washers, nylocs, M3×14 csk foot bolts | spread loads into the unknown-material stock shell; hardware for shoulder rev4 feet | **NOW** |

## Mechanical — planned

| # | Item | Why | Status |
|---|---|---|---|
| 4 | Trunk shell v2 (own print, PA6-CF) | kills all drill-at-assembly (battery 6 + feet 4 holes), material unknown, bolt-on floor plate → integrated bosses. Inherits every measured number | **GATED**: first full assembly proves interfaces |
| 5 | Mass diet + real masses | servo holding torque is the platform limit; −100 g ≈ −2.4% torque everywhere. First: weigh printed set → URDF (CAD estimates land this batch, see 13) | **GATED**: scale session after print batch |
| 6 | Knee config: keep translated vs X-config | X = symmetric workspace, better fore-aft authority; costs IK + both ROM gate redos. Decide BEFORE gait tuning bakes in | **DECISION** |
| 7 | Shoe v2 (own TPU: 85A, sipes, flatter crown) | we own the toe interface now; crown r17→15.3 limits patch to ~8 mm | **GATED**: first-article stock-geometry print + θ pin |
| — | Inboard-jog tibia (d 64.3→3.3) | −0.6 N·m holding per hip, biggest thermal win | **GATED**: balance controller (84 mm track) |

## Electrical (v7 respin backlog — nova-proj/project-board-fab-readiness)

| # | Item | Why | Status |
|---|---|---|---|
| 8 | via annular loosen · per-leg INA226 · U8 bypass | leg-level current = contact detection + stall protection for free | **GATED**: v7 respin |

## Software / system (system-audit opens)

| # | Item | Why | Status |
|---|---|---|---|
| 9 | Firmware servo torque limits + E-stop limp | protects joints + servos better than plastic | **DONE 2026-07-06** (this lane): E-stop/battery latch now LIMPS the fleet; firmware per-joint raw ROM table (`joint_limits` topic, wide-open until post-homing publish via `safety_envelope/firmware_limits.py`); wrapper wires per-joint `effort`; haa default tightened ±45→±15 conservative (asymmetric 15/40 unlocks when `HAA_INBOARD_SIGN` filled at homing). Torque-limit 600‰ was already in firmware. **Remaining at calibration**: fill inboard signs + urdf_signs, publish the table |
| 10 | Contact detection from servo current | no foot sensors needed; pairs with per-leg INA (v7) | **GATED**: v7 boards (current-only version possible from servo telemetry sooner) |
| 11 | Jetson watchdog + joint-ID map | audit opens | **DONE 2026-07-06**: 3-layer watchdog (Restart=on-failure / WatchdogSec+`watchdog_node` sd_notify feeder / Tegra RuntimeWatchdogSec) — `deploy/nova-bringup.service` + setup-jetson §16; liveness+watchdog nodes added to the walk profile. Joint-ID map: `nova_ops/joint_map.py` loader + consistency tests locking yaml ↔ homing config ↔ limits grouping ↔ URDF. **At Jetson**: install the unit + RuntimeWatchdogSec, bench-verify the SIGSTOP restart |

## Hardware review, second pass (2026-07-06)

PCBs already ordered (JLCPCB 2026-07-01) — **none of these need a respin**;
item 14 is the only electrical one and it rides the existing I²C bus.

| # | Item | Why | Status |
|---|---|---|---|
| 14 | **Dedicated IMU near CoM** (ICM-42688-P breakout, ~$12) | MPU-6050 cut (2026-05-24) assumed D456/L2 IMUs suffice — that predates gait planning AND the breakaway masts: those IMUs are high, vibration-rich, USB/Ethernet latency, and mounted on parts designed to pop off in a fall. Balance loop needs rigid CoM-mounted attitude at 1 kHz on the Teensy. **Wiring: shares the INA226 I²C bus** (addr 0x68 clear of 0x40/41/44/45; 140 kbps of 400 kHz), 4 wires to interboard I²C or Teensy through-hole pins; mounts on the mezzanine (stack ctr x −3.5 ≈ CoM). Verify socket/pin access when boards arrive. Permanent footprint → v7 respin list | **NEXT**: BOM add + bench-wire at board bring-up |
| 15 | **Belly skid rails + collapse-pose check** | E-stop limp = collapse by design; pack bottom (z −35.9) is the lowest point on the robot — puncture = fire. TPU strips on the battery-tray bottom + TPU bumpers at knee outer faces; one-time CAD check of the limp resting pose (what touches first) | **NEXT** (CAD, cheap) |
| 16 | **Trim l2_mast flange rear edge 63.3 → 63.0** | 0.2 gap to the shoulder deck-extension fin (63.5) is inside ±0.15 print tolerance — coin-flip interference at assembly. Other tight gaps checked: D456 stem 0.1 = designed register, riser 0.1-over-plateau = datum, shoe gaps = TPU. This is the only bad one | **NEXT** (5-min CAD + regate) |
| 17 | **Hip servo heat path** | HAA/HFE hold ~22% torque continuously in PA6-CF thermal blankets. Per-servo temp telemetry already streams at 5 Hz → MEASURE at first stand; if hips >55 °C sustained, thermal pad + alu spreader through the existing vent windows (zero reprint). Real fix long-term = inboard-jog tibia (see gated items) | **GATED**: first-stand thermal data |
| 18 | **Cable service loops at joints** | haa ±40° / kfe ±109° at trot ≈ 10⁵ flex cycles/hr — quadruped cables classically die at the hip. Printed clips defining ≥8× cable-Ø bend radius at each joint crossing + spiral wrap in flex zones; spec in the assembly checklist | **NEXT** (spec + small clips w/ leg print batch) |
| 19 | **Battery precharge** | XT60→MRBF→switch: hot-plug arcing lands on the switch contacts (bulk caps + 12 servos downstream) — pits over time. 100 Ω/5 W precharge resistor bridging the switch, or XT90-S swap | **LOW** (BOM line, bench QoL) |

Verified NOT issues: E-stop already cuts leg/hip/L2 rails in hardware (NC
through the three buck ENs, Jetson stays up — power-budget checklist line
209 verifies at power-on); XT60+MRBF-30 fusing is properly sized/placed.

## Architectural (2026-07-06 third pass — "is there a better design")

| # | Item | Why | Status |
|---|---|---|---|
| 20 | **Series compliance: shoe v2 crush zone** | position servos can't do impedance; total leg compliance today ~1-2 mm TPU squish → touchdown spikes hit the gears rigidly. Engineered TPU rib voids in the shoe, ~5-8 N/mm (3-4 mm at 20 N trot, bottoms before 60 N peak), same toe_v2 interface. Gear protection + contact-signal ramp + stumble tolerance | **NEXT** after first-article stock shoe (folds into #7 shoe v2) |
| 21 | **Servo bus schedule: 17 Hz/joint feedback is the gait ceiling** | round-robin 1 servo/tick → 17 Hz state, 40 Hz cmd; full 12-poll = only 4.4 ms wire time. Poll 3-4/tick (~70 Hz full state) + cmd to 100 Hz; try Feetech SYNC_READ (~200 Hz). Prereq for dynamic gait + current-based contact detection | **NEXT** (pure firmware, local compile) |
| 22 | **Per-leg power domains** | leg rail = one 10 A buck vs 21 A 8-servo stall (caps+torque-cap+stall-trip bridge it, coherent but shared-fate: one buck foldback sags all 8; one harness short drops the rail). v7: 4× per-leg bucks or high-side switches + per-leg INA → fault isolation + transient headroom | **GATED**: v7 respin (with leg-INA + IMU footprint) |

## Process debt

| # | Item | Why | Status |
|---|---|---|---|
| 12 | Caliper session: Jetson heatsink, D456 rear pattern, 5191 slots | blocks hood + D456 print + riser finalize | **GATED**: user + calipers |
| 13 | Gate ROM + masses → URDF/firmware clamps | URDF still has 0.7/1.5/2.2 rad placeholders; gates are the authority (haa −15 inboard..+40 outboard, hfe −86..+50, kfe ±109) | **NOW** (ROM + CAD-estimate masses; refine masses at 5) |
