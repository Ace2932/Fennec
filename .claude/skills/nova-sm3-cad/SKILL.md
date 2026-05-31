---
name: nova-sm3-cad
description: "Use this skill when designing a 3D-printable utility part for the NovaSM3 quadruped build (this project). Triggers: any mention of a NovaSM3 part, Feetech STS3215 mount, 688ZZ bearing seat, hip pocket, femur U-bracket, tibia, foot pad, LiPo pocket, XT60/XT30/E-stop/RJ-45 panel cutout, Pololu buck carrier, INA226 mount, Teensy 4.1 / Arduino Nano footprint, RealSense D456 bracket, Unitree L2 LiDAR riser, LC filter pocket, MPU-6050 mount, leg-rail star injection, cable strain relief, WS2812B status LED, servo zero-position calibration jig, antenna mount; or any CAD work in ~/codebases/NOVA/proj/. Do NOT use for: the leg links shoulder/coax/femur/tibia (use the V5 OpenSCAD original-shell-carve at hardware/cad/leg_v5/ instead), the chassis + multi-body assemblies (use OnShape via Jarvis MCP), or non-NovaSM3 robotics work (use the upstream parametric-3d-printing skill alone)."
---

# NovaSM3 CAD Patterns

Project-scoped wrapper that pulls in the canonical CAD pattern reference
from this repo (`hardware/cad/patterns.md`) and the upstream parametric-
3d-printing skill.

## How to use

1. **For utility parts on NovaSM3** (cable guides, sensor adapters, mount
   brackets, panel cutouts, foot pads, strain reliefs, PCB carriers, riser
   towers, connector pockets, print-test coupons, calibration jigs):
   - Read `hardware/cad/patterns.md` first for project-pinned macros
     (Bambu P1S + PA6-CF profile, STS3215 dual-shaft mount, LiPo pocket,
     XT60 / XT30 / E-stop / RJ-45 / USB / barrel cutouts, RealSense D456 +
     L2 LiDAR + Teensy + INA226 mounts, leg-rail star injection with cap
     pockets, TPU foot pads + cable strain reliefs, Pololu buck carriers,
     LC filter pocket, P3766 antenna mount, WS2812B status LED, servo
     zero-position calibration jig, first-article validation gate, fiber-
     orientation comment convention).
   - Fall back to the upstream skill at
     `~/.claude/skills/parametric-3d-printing/robotics_patterns.md` for
     general primitives (Feetech STS3215 generic pocket, Dynamixel XL330/
     XL430, bearing seats, carbon-tube clamps, GT2 idlers, M-series screw
     bosses).
   - Use the CadQuery + preview-iterate loop from the upstream skill's
     `SKILL.md` for the actual code generation + STL export.

2. **For the leg links** (shoulder, coax, femur, tibia):
   - Do NOT use this skill, and do NOT model from scratch. The canonical
     design is **V5 OpenSCAD original-shell-carve** at `hardware/cad/leg_v5/`:
     import the original NovaSM3 STL, carve an STS3215 cavity via boolean
     `difference()`. Read `hardware/cad/leg_v5/README.md` + `ITERATE.md`.
   - Build: `cd hardware/cad/leg_v5 && ./build_all.sh`. Edit cavity placement
     in the per-part `.scad` (femur's is shared via `femur_params.scad`).

3. **For the chassis + multi-body assemblies** (chassis-to-shoulder bolt
   patterns, sensor mount-to-chassis interfaces, anything where mate
   relationships drive geometry or that imports a reference STEP like the
   Jetson):
   - Do NOT use this skill. Use **OnShape via Jarvis OnShape MCP**
     (Claude Code plugin: `/plugin install github:ReshefElisha/jarvis-onshape-mcp`).
     ~60 MCP tools, FeatureScript escape hatch, multi-view renders.
   - Full setup + boundary documented in
     `docs/cad-tooling.md` (Jarvis install + API keys + reference-STEP catalog).
   - Reference STEPs (Jetson P3766, archived leg V3.1) import into the OnShape
     workspace; rejected leg attempts live in `hardware/cad/archive/`.

## Reference

- **CAD tooling setup:** `docs/cad-tooling.md` (three-track workflow:
  V5 OpenSCAD legs + CadQuery utility + Jarvis OnShape MCP chassis)
- **Canonical leg design:** `hardware/cad/leg_v5/README.md` + `ITERATE.md`
- Canonical macros: `hardware/cad/patterns.md` (in this repo, version-
  controlled, source of truth)
- Canonical part dimensions: `hardware/cad/dimensions.md`
  (✅ VERIFIED / ⚠️ REVIEW / ❌ MISSING)
- Upstream CadQuery skill: `~/.claude/skills/parametric-3d-printing/`
- Project CAD workflow notes: `hardware/cad/README.md`
- BOM ground truth: `BOM.md`
- Print recipes + filament feed: see "3D Printing" section in the Notion
  page or `BOM.md` §8

## Mandatory Validation Gates (after every export)

The upstream `run_cadquery_model.py --strict` only checks watertight,
which is NOT enough — a mesh with two disconnected closed surfaces is
still watertight. Run both checks before claiming an STL is ready:

```python
import trimesh
m = trimesh.load("part.stl", force="mesh")
assert m.is_watertight, "non-watertight"
parts = m.split(only_watertight=False)
assert len(parts) == 1, f"BUG: {len(parts)} disconnected pieces"
```

If `parts > 1`, the part has floating geometry (yoke arms, heatset
bosses, link beams) that won't print as a single piece. Common cause:
sub-1 mm boolean overlap. Fix: use **≥ 5 mm overlap on every structural
union**.

See `hardware/cad/patterns.md` "Connectivity Validation (MANDATORY)"
for the full convention.

## TTL Daisy-Chain Wire Routing

Servo bodies are wrapped by shells, but the Feetech daisy-chain cable
must pass IN + OUT of every shell. Defaults:

- `WIRE_SLOT_W = 14 mm` (fits 2 × JST 3-pin XH cables side-by-side)
- `WIRE_SLOT_H = 5 mm`
- Place IN slot on one end face, OUT slot on the opposite end face
- For yoke joints: notch the yoke arm inner face so the cable can pass
  out toward the downstream link
- For shoulder chassis-mount slabs: pass-through through the slab from
  chassis side to coax side

## Original NovaSM3 STL References (for proportions only)

The original NovaSM3 STLs at `~/codebases/NOVA/original_body_files/` are
sized for SMALL PWM hobby servos (~20 mm body width), NOT Feetech STS3215
(~25 mm body width × 45 mm length). When designing STS3215-native parts,
match the **leg LENGTH proportions** from the originals but expect the
cavity dimensions to be ~2× larger. Do not blindly clone original
bounding boxes — they were dimensioned for a smaller servo class.

## Key Constraints (NovaSM3 v1)

- **Printer:** Bambu Lab P1S, hardened steel hotend (CF eats brass), AMS
  HF bypassed
- **Feed path:** Creality SpacePi X4 dryer → 4 mm PTFE Bowden → P1S top
  input (PA6-CF stays in the heated dryer the entire print)
- **Structural material:** PA6-CF, 280 °C nozzle, 100 °C bed soak 15 min,
  24 h dryer @ 70 °C pre-print, **Magigoo PA** on textured PEI (Bambu
  liquid glue NOT rated for PA per Bambu product page), 100 % infill on
  load-bearing, fiber alignment > infill %
- **Tolerances:** see `hardware/cad/patterns.md` §2 (NovaSM3 calibration
  constants — PA6-CF press-fit numbers differ from PLA defaults)
- **Servos:** Feetech STS3215, ±0.1 mm batch tolerance → first-article
  every structural part
- **Bearings:** 688ZZ (8 × 16 × 5 mm)
- **Bus IDs:** 1-4 hips, 5-12 femur/tibia, 13-18 reserved (Phase 4 arm)
