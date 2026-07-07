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
| 9 | Firmware servo torque limits + E-stop limp | protects SF-2.5 joint + servos better than plastic | **NEXT** (firmware lane) |
| 10 | Contact detection from servo current | no foot sensors needed; pairs with per-leg INA (v7) | **GATED**: v7 boards (current-only version possible from servo telemetry sooner) |
| 11 | Jetson watchdog + joint-ID map | audit opens | **NEXT** (firmware/ops lane) |

## Process debt

| # | Item | Why | Status |
|---|---|---|---|
| 12 | Caliper session: Jetson heatsink, D456 rear pattern, 5191 slots | blocks hood + D456 print + riser finalize | **GATED**: user + calipers |
| 13 | Gate ROM + masses → URDF/firmware clamps | URDF still has 0.7/1.5/2.2 rad placeholders; gates are the authority (haa −15 inboard..+40 outboard, hfe −86..+50, kfe ±109) | **NOW** (ROM + CAD-estimate masses; refine masses at 5) |
