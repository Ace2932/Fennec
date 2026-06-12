# CAD

Three tracks, deliberately split. **Full setup guide:** [`docs/cad-tooling.md`](../../docs/cad-tooling.md).

- **OpenSCAD original-shell-carve — `leg_v5/`** — **source of truth for the leg links** (shoulder, coax, femur, tibia). Imports the original Chris Locke NovaSM3 STLs and carves an STS3215-sized cavity inside via boolean `difference()`, preserving the original outer shape. This is the canonical leg design — see [`leg_v5/README.md`](./leg_v5/README.md). Earlier OnShape/CadQuery leg attempts (V2/V3/V4) are superseded and parked in [`archive/`](./archive/README.md).
- **OnShape via [Jarvis OnShape MCP](https://github.com/ReshefElisha/jarvis-onshape-mcp)** (Claude Code plugin, ~60 tools + FeatureScript) — **chassis + multi-body kinematic assemblies**, anything with mate relationships, anything that imports reference STEPs (Jetson, L2, D456). Source of truth for the chassis/structural stack. (It lost the leg-link competition to V5 — original geometry mattered more than from-scratch brackets.)
- **parametric-3d-printing skill** (`~/.claude/skills/parametric-3d-printing/`, CadQuery-based) — utility parts: cable guides, sensor adapters, mount brackets, panel cutouts, foot pads, strain reliefs, PCB carriers, riser towers, connector pockets, print-test coupons. Anything single-body or single-assembly.

Project-specific macros live in [`hardware/cad/patterns.md`](./patterns.md) (version-controlled with this repo). Project-scoped skill at `.claude/skills/nova-sm3-cad/SKILL.md` auto-loads when working in this project — wraps the patterns file + delegates CadQuery code generation + STL export to the upstream `parametric-3d-printing` skill. Covers Bambu P1S + PA6-CF tolerances, STS3215 dual-shaft mount, LiPo pocket, XT60 / XT30 / E-stop / RJ-45 / USB / barrel cutouts, RealSense D456 + L2 LiDAR riser + Teensy + Arduino Nano + INA226 mounts, Pololu buck carriers + LC filter pocket, P3766 antenna mount, WS2812B status LED, leg-rail star injection, TPU foot pads + strain reliefs, servo zero-position calibration jig. Read it before generating new utility parts.

## Will contain (in this directory)

- OnShape public doc URL (once created)
- Exported `*.step` + `*.stl` for assemblies
- Print orientation notes per part (fiber alignment for PA6-CF)
- `measurements.md` — caliper-measured servo + horn + bearing dims

## Reference geometry sources

- **STS3215** (19kg + 30kg variants) — pull STEP from GrabCAD or Feetech site, import to OnShape
- **NovaSM3 reference chassis** — `cguweb-com/Arduino-Projects/tree/main/Nova-SM3` (the `SovGVD/NovaSM3` URL in old docs was a misattribution; that repo does not exist). **STEP files NOT in repo — only STL.** For OnShape import: (a) import STL as static body, (b) re-model from STL + datasheet + caliper, or (c) contact Chris Locke for original Fusion source. See [`docs/research/2026-05-17-notes.md`](../../docs/research/2026-05-17-notes.md) §8.
- **Feetech 25T servo horns** — datasheet dims, model in OnShape from scratch
- **688ZZ ball bearings** (8 × 16 × 5 mm) — generic deep-groove, no STEP needed; press-fit pocket geometry is in [`patterns.md`](./patterns.md) §6
- **Calipers** for in-hand cross-check — STS3215 body tolerance is ±0.1 mm batch-to-batch, never trust a single datasheet number for press-fit work

## Print workflow

1. OnShape (kinematic) or CadQuery skill (utility) — design + export STL
2. Slice in Bambu Studio with PA6-CF profile (280 °C nozzle, hardened steel hotend, 100 % infill on structural)
3. **Filament feed:** Creality SpacePi X4 → 4 mm PTFE Bowden tube → P1S top-side input. **AMS HF bypassed** for PA6-CF — re-absorbs moisture in AMS chamber within hours, defeats the 24 h pre-dry. PA6-CF stays in the heated dryer chamber for the entire print.
4. Bed prep: Bambu **Engineering Plate** (smooth) + **Magigoo PA glue stick** (Bambu liquid glue is not rated for PA / PA-CF — see BOM §8 note). 100 °C bed soak 15 min before first layer.
5. First-article gate on every structural part — print one, caliper, fit-test on real STS3215 + 688ZZ, then batch. Skip the batch if fit isn't clean.

## Files in this directory

- [`leg_v5/`](./leg_v5/) — canonical leg design (OpenSCAD `.scad` sources + 9 exported STLs). Start at [`leg_v5/README.md`](./leg_v5/README.md), iterate via [`leg_v5/ITERATE.md`](./leg_v5/ITERATE.md).
- [`dimensions.md`](./dimensions.md) — canonical part dims (✅ verified / ⚠️ review / ❌ missing). Wins on any conflict.
- [`patterns.md`](./patterns.md) — CadQuery macros for project utility parts.
- [`parametric-servo-fit.md`](./parametric-servo-fit.md) — PA6-CF press-fit clearance calibration (V5 pulls `CLR_BODY` from here). The OnShape-Variable-Studio parametric workflow it describes is superseded by V5's literal clearance.
- [`archive/`](./archive/README.md) — superseded leg designs V2/V3/V4 + the V4 OnShape build plan.
- Chassis OnShape exports (`*.step` / `*.stl`) will land here once the chassis doc is built.
- Sibling project folders (outside `proj/`): `~/codebases/NOVA/original_body_files/` (Chris Locke source STLs that V5 imports), `~/codebases/NOVA/feetech_servo_models/` (STS3215 STEP), `~/codebases/NOVA/Unitree_LiDAR/`
