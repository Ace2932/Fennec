# NovaSM3 CAD Tooling

Canonical guide to the two-track CAD workflow.

## TL;DR

| Task class | Tool | Why |
|------------|------|-----|
| **Utility parts** — cable clips, foot pads, panel cutouts, sensor brackets, calibration jigs, single-body adapters | **CadQuery + parametric-3d-printing skill** | Fast iteration; Python; clean STL preview loop; reusable macros in `hardware/cad/patterns.md` |
| **Chassis + kinematic assemblies** — chassis trunk, leg-joint multi-body mates, sensor-mount-to-chassis interfaces, anything that imports reference STEPs (Jetson, L2, D456) | **OnShape via [Jarvis OnShape MCP](https://github.com/ReshefElisha/jarvis-onshape-mcp)** + FeatureScript | Real BREP, real mates, real interference checks. Claude drives via MCP; ~60 tools + FeatureScript escape hatch for custom features. |

## Jarvis OnShape MCP — Claude-driven OnShape

`github.com/ReshefElisha/jarvis-onshape-mcp` — Claude Code plugin that
gives an LLM ~60 tools spanning sketches, extrudes, fillets, patterns,
mates, parametric variables, plus a FeatureScript escape hatch for the
weird stuff. Multi-view PNG renders come back as image content so the
model can see the part it just built. License: MIT.

### Why it matters for this project

We already wrestled with the leg V3.1 CadQuery design — body-shell
booleans, 1mm-overlap fusion bugs, gap-carve through-bodies, manual
mate transforms in `build_all.py`. CadQuery is the right tool for
single-body utility parts but the wrong tool for a 4-piece kinematic
leg assembly + chassis with imported sensor STEPs.

OnShape is the right tool for the kinematic / chassis level. With
Jarvis MCP we get the OnShape benefits (real parametric BREP, mate
relationships, interference checks, multi-body assemblies, imported
STEPs) AND keep the conversational Claude workflow.

### Setup

Prereqs:

- `uv` package manager:  `brew install uv`
- Claude Code with plugin support
- Active OnShape account (free public-doc tier is fine)

1. **Get OnShape API keys.** Go to https://dev-portal.onshape.com →
   create a new API key pair → copy both Access Key + Secret Key
   (the secret is shown once; save it somewhere safe).

2. **Install the plugin in Claude Code:**

   ```
   /plugin install github:ReshefElisha/jarvis-onshape-mcp
   ```

   The plugin will prompt for `ONSHAPE_API_KEY` + `ONSHAPE_API_SECRET`
   and store them in the OS keychain.

3. **Verify:** ask Claude something like:
   *"List my OnShape documents."*

   You should get a tool-call → list of your docs. If you don't, check
   the plugin output for missing-env-var or auth errors.

### Tool surface (high level)

| Group | Examples |
|-------|----------|
| Document | `create_document`, `find_part_studios`, `get_elements` |
| Sketch | `create_sketch`, `rectangle`, `circle`, `line`, `arc` |
| Feature | `create_extrude`, `create_fillet`, `create_boolean`, patterns |
| Assembly | `add_instance`, `create_mates`, interference checks |
| Rendering | `render_views` (multi-view PNG), `crop_image`, `compare_to_reference` |
| Variables | `create_variable_studio`, `set_variable` (parametric iteration) |
| FeatureScript | `write_featurescript_feature` (custom features) |
| Export | STL, STEP, GLTF |

## How to use the dual-track workflow

### When making a utility part (cable clip, foot pad, panel cutout)

1. Invoke the `parametric-3d-printing` skill (auto-triggers on "STL",
   "3D print", servo names, etc.)
2. Skill reads `hardware/cad/patterns.md` + `~/.claude/skills/parametric-3d-printing/robotics_patterns.md` for project-pinned macros
3. Writes CadQuery script under `claude_generated_files/` (or
   `proj/hardware/cad/<part>/` if it's going in the repo)
4. Runs `~/.claude/skills/parametric-3d-printing/run_cadquery_model.py
   <script> --preview --strict` to render multi-view PNG + check
   watertightness
5. Also run `python check_connectivity.py` if there are unions (catches
   disconnected-component bugs `--strict` misses)
6. Output: STL + STEP exported per `leg_v3/build_all.py` pattern

### When making a chassis or kinematic-assembly part

1. Ensure Jarvis OnShape MCP is installed (one-time setup above)
2. Make sure the reference STEPs are in your OnShape doc:
   - Jetson Orin Nano Super (P3766) — you imported this 2026-05-24
   - V3.1 leg STEPs from `proj/hardware/cad/leg_v3/*.step`
   - Future: PCB v6 STEP (KiCad away-week deliverable)
3. Drive design in Claude Code: *"Open document `<name>` and add a
   chassis trunk 200×120×35 mm centered on the world origin. Add
   M3 mounting hole patterns at the four corners for the shoulder
   pieces — pattern derived from the shoulder STEP's mount slab."*
4. Claude calls tools; OnShape regenerates; multi-view PNGs come
   back; iterate
5. Export STEP for archival → commit to `proj/hardware/cad/chassis/`
6. Export STL for printing

### Hand-off between the two tracks

- **OnShape → CadQuery skill:** export STEP from OnShape, drop in
  `proj/hardware/cad/<part>/reference.step`, CadQuery imports via
  `cq.importers.importStep()` for dimensional reference (already done
  for the STS3215 envelope — see `leg_v3/leg_common.py`)
- **CadQuery skill → OnShape:** STEP files in `hardware/cad/leg_v3/`
  already export. Drag-and-drop into OnShape, or use Jarvis MCP's
  document import tools

## Project canonical list of references in OnShape

When you build the chassis doc, include these reference STEPs as
static bodies so dims drive off real geometry:

| Reference | Status |
|-----------|--------|
| Jetson Orin Nano Super Dev Kit (P3766) | ✅ imported by user 2026-05-24 |
| Unitree L2 LiDAR (placeholder — Unitree doesn't publish STEP) | ⚠️ model from dims in `dimensions.md` §2: 75×75×65, 4× M3 on 22.5 mm square |
| RealSense D456 (Intel STEP available) | TODO — pull from Intel D4xx CAD downloads |
| Feetech STS3215 STEP (from GrabCAD / Feetech) | ✅ available at `~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/feetech-sts3215/STS3215_03a v1.step` |
| Leg V3.1 STEPs (shoulder, coax, femur, tibia, covers) | ✅ at `proj/hardware/cad/leg_v3/*.step` |
| PCB v6 STEP | 📋 KiCad away-week deliverable |
| LiPo Ovonic 4S 4000 mAh | ⚠️ approximate box from `dimensions.md` §5 |
| 688ZZ bearing | ⚠️ trivial — 8 × 16 × 5 mm flat ring |
| Pololu D42V110 / D24V22F12 / D42V55F12 | ⚠️ approximate boxes from `dimensions.md` §4 |
| TP-Link LS105G PCB (case-removed) | ❌ caliper-measure after case removal |
| ISDT 608AC | not on robot, skip |

## Alternatives to Jarvis MCP

Other OnShape MCP servers exist (`hedless/onshape-mcp`,
`altendky/onshape-mcp`, `clarsbyte/onshape-mcp`) but Jarvis is the
most complete + has the vision-decomposition skill + truth-telling
returns. Default to Jarvis unless you hit a wall.

Pure-Python OnShape automation (no LLM): `kyle-tennison/onpy` is a
parametric Python API similar to CadQuery but driving OnShape's
backend. Useful for batch scripts that don't need conversational
iteration.

OnShape's own [FeatureScript LLM tooling](https://www.onshape.com/en/blog/ai-artificial-intelligence-cloud-native-cad-pdm-platform)
is rolling into Feature Studio natively — keep an eye on that for
custom-feature authoring without leaving OnShape.

## Boundary clarification (cuts down arguments later)

**CadQuery / parametric-3d-printing skill = utility parts.**
Single body, single STL out, single load path. Cable clips, foot pads,
panel cutouts, calibration jigs, brackets that mount to one face.

**OnShape via Jarvis MCP = chassis + kinematic assemblies.**
Multi-body, mates between parts, imports reference STEPs, needs
interference checks, drives parametric variables for re-spinning
based on real measured dims.

When in doubt, ask: "is this one printed part with one orientation,
or is it part of a multi-piece assembly where the mate matters?" If
one part → CadQuery. If multi-piece → OnShape.

## See also

- `hardware/cad/README.md` — high-level CAD workflow
- `hardware/cad/dimensions.md` — canonical part dimensions (✅/⚠️/❌)
- `hardware/cad/patterns.md` — CadQuery macros for project parts
- `.claude/skills/nova-sm3-cad/SKILL.md` — project skill triggers
- Reshef Elisha's writeup: https://reshef.io/a/20260420_onshape_mcp/
