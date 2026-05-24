# CAD

Two tools, deliberately split:

- **OnShape** (browser, free public doc tier) — leg-joint kinematics, hip + femur + tibia multi-body assemblies, anything with mate relationships, chassis structural geometry. Source of truth for the kinematic stack.
- **parametric-3d-printing skill** (`~/.claude/skills/parametric-3d-printing/`, CadQuery-based) — utility parts: cable guides, sensor adapters, mount brackets, panel cutouts, foot pads, strain reliefs, PCB carriers, riser towers, connector pockets, print-test coupons. Anything single-body or single-assembly.

Project-specific macros live in `nova_sm3_patterns.md` inside the skill — Bambu P1S + PA6-CF tolerances, STS3215 dual-shaft mount, LiPo pocket, XT60 / XT30 / E-stop / RJ-45 cutouts, RealSense D456 + L2 LiDAR + Teensy + INA226 mounts, leg-rail star injection, TPU foot pads + strain reliefs. Read it before generating new utility parts.

## Will contain (in this directory)

- OnShape public doc URL (once created)
- Exported `*.step` + `*.stl` for assemblies
- Print orientation notes per part (fiber alignment for PA6-CF)
- `measurements.md` — caliper-measured servo + horn + bearing dims

## Reference geometry sources

- **STS3215** (19kg + 30kg variants) — pull STEP from GrabCAD or Feetech site, import to OnShape
- **NovaSM3 reference chassis** — `cguweb-com/Arduino-Projects/tree/main/Nova-SM3` (the `SovGVD/NovaSM3` URL in old docs was a misattribution; that repo does not exist). **STEP files NOT in repo — only STL.** For OnShape import: (a) import STL as static body, (b) re-model from STL + datasheet + caliper, or (c) contact Chris Locke for original Fusion source. See [`docs/research/2026-05-17-notes.md`](../../docs/research/2026-05-17-notes.md) §8.
- **Feetech 25T servo horns** — datasheet dims, model in OnShape from scratch
- **688ZZ ball bearings** (8 × 16 × 5 mm) — generic deep-groove, no STEP needed; press-fit pocket geometry is in `nova_sm3_patterns.md`
- **Calipers** for in-hand cross-check — STS3215 body tolerance is ±0.1 mm batch-to-batch, never trust a single datasheet number for press-fit work

## Print workflow

1. OnShape (kinematic) or CadQuery skill (utility) — design + export STL
2. Slice in Bambu Studio with PA6-CF profile (280 °C nozzle, hardened steel hotend, 100 % infill on structural)
3. **Filament feed:** Creality SpacePi X4 → 4 mm PTFE Bowden tube → P1S top-side input. **AMS HF bypassed** for PA6-CF — re-absorbs moisture in AMS chamber within hours, defeats the 24 h pre-dry. PA6-CF stays in the heated dryer chamber for the entire print.
4. Bed prep: textured PEI + **Magigoo PA glue stick** (Bambu liquid glue is not rated for PA / PA-CF — see BOM §8 note). 100 °C bed soak 15 min before first layer.
5. First-article gate on every structural part — print one, caliper, fit-test on real STS3215 + 688ZZ, then batch. Skip the batch if fit isn't clean.

## Files

- Source: OnShape public doc (link here once created)
- Exports: `*.step`, `*.stl` committed to this directory
- Sibling project folders (outside `proj/`): `~/codebases/NOVA/nova-sm3-upstream/` (Chris Locke STLs), `~/codebases/NOVA/nova_sts3215_redesign/` (OpenSCAD WIP), `~/codebases/NOVA/feetech_servo_models/`, `~/codebases/NOVA/Unitree_LiDAR/`
