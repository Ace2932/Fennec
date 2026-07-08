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
| 6 | Knee config: keep translated vs X-config | analysis DONE (`docs/knee-config-analysis.md`, 2026-07-06): it's a **pure software sign choice** — both pose spaces already gate-verified, no reprints, no URDF change. X wins rear crouch margin (46° vs 10°) + robot-level symmetry + dog-like stand-up; costs 24 mm wider foot-exclusion. **REC: X-CONFIG**, reversible any time | **DECIDED 2026-07-06: X-CONFIG** (user call). Gait/IK lane implements: rear stance (−40,−80), per-leg knee-sign param, ≥40 mm foot-exclusion, rear-mirrored preview when gait starts |
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
| 15 | **Belly skid rails + collapse-pose check** | E-stop limp = collapse by design; pack bottom (z −35.9) is the lowest point on the robot — puncture = fire. TPU strips on the battery-tray bottom + TPU bumpers at knee outer faces; one-time CAD check of the limp resting pose (what touches first) | **RAILS DONE 2026-07-06**: `skid_rail.scad` ×2 TPU (lowest z −42.2). **⚠ REOPENED 2026-07-07 (user catch):** the `tibia_pad.scad` added on 07-06 was MISPLACED — it sat on the LATERAL mid-blade face (normal world +Y), so it never leads into the ground on any pose. `collapse_study.py` proof: across the whole fold ROM it's +22..69 mm ABOVE the real contact, AND a limp-folded leg hangs to z −56..−94, BELOW the rails (−42.2) — so the rails do NOT catch first for a passive limp. **tibia_pad RETIRED.** Real fix = **A + B**: **(A) controlled-limp SIT** — on a SOFT fault (watchdog/commanded E-stop, NOT power-loss) drive to ≈ haa +40°/hfe +40°/kfe −90° (legs splay+fold, lowest part clears the rail by +11 → belly settles on the rails; firmware lane, `collapse_study.py` = the pose proof). **(B) KNEE TPU bumper — BUILT + GATED 2026-07-07:** `knee_bumper.scad` (TPU, ~8 g) wraps the tibia knee-block's exposed lateral faces + bottom edge (x15..40), rides the kfe fold. Both gates green (exit 0): clears the femur fork through ±109° (v1's full-width wrap-under fouled it at x15..23/z-25 → pulled fwd to x24), chassis crouch clean. COVERAGE is partial by necessity — the primary strike (x-16..12) is the joint zone the fork occupies (self-guarding); the bumper covers the exposed forward case wall + the sit's outboard-face landing. Replaces the retired tibia_pad. Backlog #15's original "knee outer faces" intent was right; the mid-blade pad substitution was the error |
| 16 | **Trim l2_mast flange rear edge 63.3 → 63.0** | 0.2 gap to the shoulder deck-extension fin (63.5) is inside ±0.15 print tolerance — coin-flip interference at assembly. Other tight gaps checked: D456 stem 0.1 = designed register, riser 0.1-over-plateau = datum, shoe gaps = TPU. This is the only bad one | **DONE 2026-07-06**: flange+shaft rear 63.3→63.0 (0.5 gap), gate green |
| 17 | **Hip servo heat path** | HAA/HFE hold ~22% torque continuously in PA6-CF thermal blankets. Per-servo temp telemetry already streams at 5 Hz → MEASURE at first stand; if hips >55 °C sustained, thermal pad + alu spreader through the existing vent windows (zero reprint). Real fix long-term = inboard-jog tibia (see gated items) | **GATED**: first-stand thermal data |
| 18 | **Cable service loops at joints** | haa ±40° / kfe ±109° at trot ≈ 10⁵ flex cycles/hr — quadruped cables classically die at the hip. Printed clips defining ≥8× cable-Ø bend radius at each joint crossing + spiral wrap in flex zones; spec in the assembly checklist | **DONE 2026-07-06**: `leg_v6/cable_clip.scad` (TPU, print 20) — saddle + bell-mouth horns retrofitting the existing Ø3.2 zip-pair anchors, tie threads leg+clip together; placement + ≥40 mm loop rule + tug-test in leg_v6 README 'cable dressing'; spiral wrap BOM'd |
| 19 | **Battery precharge** | XT60→MRBF→switch: hot-plug arcing lands on the switch contacts (bulk caps + 12 servos downstream) — pits over time. 100 Ω/5 W precharge resistor bridging the switch, or XT90-S swap | **LOW** (BOM line, bench QoL) |

Verified NOT issues: E-stop already cuts leg/hip/L2 rails in hardware (NC
through the three buck ENs, Jetson stays up — power-budget checklist line
209 verifies at power-on); XT60+MRBF-30 fusing is properly sized/placed.

## Architectural (2026-07-06 third pass — "is there a better design")

| # | Item | Why | Status |
|---|---|---|---|
| 20 | **Series compliance: shoe v2 crush zone** | position servos can't do impedance; total leg compliance today ~1-2 mm TPU squish → touchdown spikes hit the gears rigidly. Engineered TPU rib voids in the shoe, ~5-8 N/mm (3-4 mm at 20 N trot, bottoms before 60 N peak), same toe_v2 interface. Gear protection + contact-signal ramp + stumble tolerance | **NEXT** after first-article stock shoe (folds into #7 shoe v2) |
| 21 | **Servo bus schedule: 17 Hz/joint feedback is the gait ceiling** | round-robin 1 servo/tick → 17 Hz state, 40 Hz cmd; full 12-poll = only 4.4 ms wire time. Poll 3-4/tick (~70 Hz full state) + cmd to 100 Hz; try Feetech SYNC_READ (~200 Hz). Prereq for dynamic gait + current-based contact detection | **DONE 2026-07-06**: 3 polls/tick (50 Hz/joint) + 100 Hz cmd broadcast (slew re-scaled 20/10ms = same 176°/s), joint_states already publishes 200 Hz; compiles teensy41_ci. **At bring-up**: check exec-time p99 (4/tick fits if clean), probe SYNC_READ 0x82 for ~200 Hz |
| 22 | **Per-leg power domains** | leg rail = one 10 A buck vs 21 A 8-servo stall (caps+torque-cap+stall-trip bridge it, coherent but shared-fate: one buck foldback sags all 8; one harness short drops the rail). v7: 4× per-leg bucks or high-side switches + per-leg INA → fault isolation + transient headroom | **GATED**: v7 respin (with leg-INA + IMU footprint) |

## Part-level (2026-07-06 fourth pass)

| # | Item | Why | Status |
|---|---|---|---|
| 23 | **Servo SKU/voltage audit** | BOM: legs "STS3215 19kg, 6-8.4V" @7.5V; hips "STS3215 30kg" @12V — a 7.4V-rated unit can't run 12V, so hips are either the 12V SKU (→ LABEL hip vs leg servos + spares, mixing = dead servo) or ALL units are 12V-rated (→ knees at 7.5V leave **+58% torque** unused). Options: verify+label now; leg rail 7.5→8.4V (+12%, in-spec, v7/adjustable buck); 12V knees if SKU allows (+58%, rail rework + gear-wear watch via temp/load telemetry) | **NOW at hardware session**: read the labels |
| 24 | **Material allocation: PETG-CF for flat chassis parts** | PA6-CF moisture swell (0.3-0.5%) + warp on big flats — riser is a 127mm lid whose only structural job is the tension tie. Riser, floor plate, battery pocket, l2_mast, d456 bracket → PETG-CF; legs/shoulders stay PA6-CF (impact+fatigue) | **NEXT**: decide before chassis print batch |
| 25 | **Servo bus connector retention** | 5264 inline plugs walking out under vibration = the classic bus-servo quadruped failure (limp one leg at a time). Zip anchors handle tension, not walk-out. Glue dab / printed clips + "tug-test all 24 ends" checklist line | **NEXT**: assembly checklist + tiny clip print |

Verified fine this pass: pocket vents (coax/femur/tibia all vented), joint
idler sides ride the Feetech wheel bearing, standoffs, bulk-cap placement.
Still open from leg_v6 doctrine: 25T horn-disc kit variant (blocker-grade).

## Stress audit both-directions (2026-07-06 fifth pass — real STL sections)

Tibia blade section-verified (9 stations, Green's-theorem props from the
mesh): peak 1.3 MPa bending + 1.6 MPa jog torsion, tip deflection 0.08 mm
at 60 N → SF ≈ 35, web clip cost nothing. Full member table in the pass
notes; only two actionable findings:

| # | Item | Why | Status |
|---|---|---|---|
| 26 | **Coax yoke arm root +50% section** | ONLY plastic member below SF 15: 14 MPa at the 4 mm root (20 N lateral/turning), SF ~3 wet and **~1.9 against PA6 fatigue** on a per-stride cyclic load. Root 4→6 + fillet → ~6 MPa | **DONE 2026-07-06**: tapered outboard doubler at the arm-bridge junction (taper clears the wheel-screw heads; shared ARM_THK untouched); mesh-verified 6.0 root, all gates green |
| 27 | **Mass diet targets + first-article static test** | LESS is safe in: tibia infill 40→25% (SF 35; ~8-10 g/leg), shoulder flange mid-panel windows (SF>150; ~15 g ×2), riser thin walls at PETG reprint (~25 g). NEVER: leg walls, femur (10 MPa, 2nd-tightest), coax, toe pocket ring. And calcs can't see a bad print: **first-article static test — 12 kg (3× robot) hung off one tibia toe + 5 N·m on a shoulder joint** before first walk | **GATED**: print batch / first article |

## Phase-4 arm (assessed 2026-07-06)

| # | Item | Why | Status |
|---|---|---|---|
| 28 | Arm go/no-go + prep flags | POSSIBLE (boards carry J14 + arm buck footprint + U12 INA + EN regate; IDs 13-18 + limits placeholders exist). Physics: +650 g (+15%), hips 22→~26% continuous (thermal), ~250 g payload @300 mm on the 7.5 V rail, extended-arm CoM shift ~45 mm. **GOOD IDEA ONLY behind two gates: stable trot, then balance controller** (which also unlocks inboard-jog = buys back the thermal cost). Design rules when it lands: mount over CoM, hard STOW pose enforced for all locomotion, consider lighter distal servos. Firmware: arrays 12→18 + joint_limits 36 floats (build flag). **⚠ CHECK at board bring-up: arm INA U12 address (memory says 0x45 = collides with the optional L2 INA)** | **GATED**: trot + balance controller |

## Integration audit (2026-07-06 — captivity / fit / wiring)

| # | Item | Why | Status |
|---|---|---|---|
| 29 | **Battery rattle + flange chafe** | 0.8 mm/side design slack all axes, strap only stops slide-out → 510 g rattles at trot; 0.25 gap to the shoulder flange bottoms (± print tol) = possible LiPo chafe on a structural edge | **DONE (BOM)**: 3 mm EVA pad on the tray floor (preload+damping) + felt/kapton on the flange bottom edges; pack caliper stays ⚠ |
| 30 | **Grommet chafe** | O12 flange grommets = bare printed PA6 edges carrying MOVING leg cables (haa swing, ~1e5 cycles/hr) | **DONE**: `leg_v6/grommet_insert.scad` TPU liner ×6 (slit = wraps a routed bundle), rounded lips both faces |
| 31 | **Inside-trunk harness plan** | stack↔grommets↔MRBF dressing unspecified — rat's nest risk; 5191 placement drives it | **GATED**: part-5/caliper session |
| 32 | **External WiFi antennas — decide** | The head EARS carry 2× SMA bulkhead provisions (Ø6.5, whip-up boss at each tip; riser bulkheads dropped) to relocate the Jetson's onboard WiFi out of the RF-lossy PA6-CF+CF chassis. But onboard WiFi already works (SSH-over-WiFi, `wlP1p1s0`) — external is a MAYBE. **Deciding test: bench WiFi range at distance/through-chassis.** If bad → order ~$25 (2× SMA bulkhead + 2× U.FL→SMA pigtail + 2× dual-band whip), verify the WiFi card exposes U.FL, route pigtails up the neck; the ears are then justified as antenna masts. If fine → the ears are decorative (drop or keep). | **GATED**: bench range test at bring-up |
| — | Watch items | riser lateral tabs 0.45 slack (shake test at FA); nylon-fuse mounts = low preload (check L2 point-cloud wobble at bring-up, VHB underlay if visible); **E-stop pod must exist before FIRST BUS POWER** (rides with hood — sequence the caliper session accordingly) | first-article / bring-up |

Captivity verified: stack/Jetson/riser/shoulders/servos all bolted;
switch (de-cased, under power board), bucks, MRBF all have designed homes.
Fit: all gated except the 5 known caliper unknowns.

## Process debt

| # | Item | Why | Status |
|---|---|---|---|
| 12 | Caliper session: Jetson heatsink, D456 rear pattern, 5191 slots | blocks hood + D456 print + riser finalize | **GATED**: user + calipers |
| 13 | Gate ROM + masses → URDF/firmware clamps | URDF still has 0.7/1.5/2.2 rad placeholders; gates are the authority (haa −15 inboard..+40 outboard, hfe −86..+50, kfe ±109) | **NOW** (ROM + CAD-estimate masses; refine masses at 5) |
