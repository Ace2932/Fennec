# PCB Design Skill — Build Plan

**Date:** 2026-05-23
**Author:** Claude (research + draft)
**Status:** RESEARCH + PLAN, awaiting user review + Notion-page details before build starts.

---

## 0. Open inputs needed before build

- [x] **Notion page content** — received 2026-05-23. Status: Phase 1 firmware bring-up green (loop p99 = 1 µs), Phase 0 closing except PCB v6 schematic + spare-part backlog. Away-week 2026-05-29 → 2026-06-05 = laptop-only PCB v6 schematic work.
- [x] **PCB v6 design spec exists** at [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md) — 130 lines, 8 feature sections covering battery input + 4-rail power + bus distribution + Pattern B/A bridge + bus integrity + safety chain + aux MCU + connector convention. Skill templates map 1:1 to these sections.
- [x] Confirm scope: skill biased toward NOVA PCB v6 but generalizable. Templates parameterized so a non-NOVA quadruped (or any embedded-bus + safety-chain project) can reuse them.
- [x] Confirm install target: `~/.claude/skills/pcb-design/` mirrors `parametric-3d-printing` layout.
- [ ] **Notion MCP integration** — per Notion page, "Notion MCP server installed at user scope (needs `/mcp` auth)". Decision: skill calls Notion MCP if available to pull current project status; falls back to repo-only mode if unauth'd.

---

## 1. Tools landscape — 2026 state of the art

### 1.1 PCB editor — KiCad 9.x (only sane choice for this build)

| Option | Verdict for NOVA |
|---|---|
| **KiCad 9.x** | ✅ Chosen — open source, free, scriptable, used by upstream NovaSM3 PCB v5.2b reference. Pololu and Sparkfun publish KiCad libraries. |
| Altium Designer | ❌ $4k+ subscription, overkill |
| Eagle | ❌ Autodesk killed it (deprecation in favor of Fusion Electronics) |
| EasyEDA | ❌ JLCPCB-locked, weak for custom footprints |
| Fusion 360 Electronics | ❌ Subscription, weaker library ecosystem |

KiCad 9 adds an IPC-based Python API (replaces SWIG bindings), official `kicad-cli` for headless CI, and stable schematic/PCB JSON formats.

### 1.2 Automation + scripting layers

| Tool | Purpose | Use in skill |
|---|---|---|
| **`kicad-cli`** | Headless gerber/BOM/PDF export, DRC, ERC, schematic→netlist | Build pipeline — gerbers, BOM, fabrication outputs |
| **`kicad-python` (atait, IPC-based)** | Pythonic wrapper on KiCad 9 IPC API | Programmatic board edits — place components, route by net, query DRC results |
| **KiKit** | Panelization, fab-data bundles, V-cut/mousebite layout | PCBWay-ready panels with fiducials + frame |
| **kiauto** | GUI-driven KiCad scripting (xvfb) — useful when IPC API can't reach a feature yet | Fallback for legacy operations |
| **kibot** | YAML-driven CI for KiCad outputs | Optional — generates entire fab+assembly package from one config |

### 1.3 Existing MCP servers (don't reinvent)

Three KiCad MCPs exist already:

1. **Seeed-Studio/kicad-mcp-server** — actively maintained, schematic+PCB analysis, pin-level connectivity tracing, design validation, KiCad 9.0+. Most production-ready of the three.
2. **lamaalrajih/kicad-mcp** — project management, BOM, DRC, cross-platform.
3. **mixelpixx/KiCAD-MCP-Server** — component placement, routing, custom symbols/footprints.

**Plan: vendor `Seeed-Studio/kicad-mcp-server` as the primary tool layer.** Skill wraps the MCP with Nova-specific knowledge + workflow scripts. Avoids re-implementing schematic/PCB parsing.

### 1.4 Component libraries

| Source | What it covers | Status for NOVA |
|---|---|---|
| KiCad official lib | Generic passives, jellybean ICs, connectors | Default install |
| Pololu KiCad library | D42V110 / D42V55 / D24V22 bucks, motor drivers | Required — clone separately |
| Adafruit KiCad library | INA226, IMUs, sensors | Required — clone separately |
| Sparkfun KiCad library | E-stop variants, breakouts | Useful |
| Snapeda | Vendor parts (SN74LVC125A, LM393, MOSFETs) | Per-part download via web |
| UltraLibrarian / SamacSys | Same — vendor parts | Per-part download |

### 1.5 Manufacturing endpoints

| Vendor | API | Use |
|---|---|---|
| **PCBWay** | Web upload + quote (no public API for instant quote, but they accept KiCad ZIP directly) | Primary fab per BOM |
| JLCPCB | Web upload, has REST API for parts library lookup | Backup; cheaper for first prototypes if no assembly |
| OSH Park | Web only | Premium / purple boards for one-off |
| Macrofab | API exists, US-based assembly | Future if doing assembled boards |

---

## 2. Recommended skill architecture

### 2.1 Directory layout (mirrors `parametric-3d-printing`)

```
~/.claude/skills/pcb-design/
├── SKILL.md                          # main entry, ~2000 words, triggers + workflow
├── README.md                         # human docs
├── requirements.txt                  # Python deps (kicad-python, kikit, kibot)
├── pcb_design_skeleton.py            # scaffolds a new KiCad project from template
├── erc_drc_runner.py                 # headless ERC/DRC via kicad-cli
├── bom_export.py                     # generates BOM CSV in PCBWay/JLCPCB format
├── gerber_pack.py                    # kicad-cli gerber → zipped + fiducial-checked
├── design_review.md                  # checklist for pre-fab review (track-width, clearance, current capacity)
├── library_setup.sh                  # clones Pololu, Adafruit, Sparkfun libraries to standard location
├── docs/
│   ├── nova_pcb_v6_topology.md       # Nova-specific schematic topology + net naming
│   ├── power_rail_layout.md          # PCB v6 power-plane stackup + bulk-cap injection
│   ├── safety_chain_wiring.md        # E-stop + comparator + MOSFET schematic patterns
│   ├── teensy_bus_routing.md         # SN74LVC125A + Serial1 + bus trace impedance
│   └── pcbway_submit_checklist.md    # what to verify before clicking buy
├── templates/
│   ├── nova_pcb_v6.kicad_project     # starter project w/ stack-up + DRC rules pre-set
│   ├── power_module_subschematic/    # reusable Pololu D42V buck wrapper sheet
│   ├── ina226_subschematic/          # reusable 3-rail telemetry block
│   └── safety_chain_subschematic/    # comparator + MOSFET + E-stop chain
└── tests/
    └── test_drc_clean.py             # CI hook to verify templates pass DRC
```

### 2.2 SKILL.md frontmatter (draft)

```yaml
---
name: pcb-design
description: "Use this skill when the user wants to design, modify, review, or manufacture a printed circuit board. Triggers: any mention of 'PCB', 'KiCad', 'schematic', 'gerber', 'PCBWay', 'JLCPCB', 'DRC', 'ERC', 'BOM', 'footprint', 'symbol', 'stackup', 'trace width', 'via', 'plane', 'NovaSM3 PCB v6'; requests to add a power rail, route a bus, place an IC, run design rule checks, generate fab outputs, panelize, or submit to a fab house. Also fires for component-selection questions tied to a PCB (e.g. 'which buck for this rail', 'INA226 shunt sizing'). Do NOT use for: breadboard or perfboard prototyping, FPGA RTL design, mechanical CAD (handled by [[parametric-3d-printing]] skill), or generic component-shopping with no PCB in scope."
---
```

### 2.3 Body sections (per Anthropic skill guide — 1500-2000 word body)

1. **Project bootstrap** — `kicad-cli` invocation that creates a new project from `templates/nova_pcb_v6.kicad_project`, layered onto Pololu/Adafruit library symlinks.
2. **Schematic-first workflow** — capture power tree → control nets → bus distribution → safety chain. Reuse subschematics from `templates/`.
3. **Layout rules** — 4-layer stackup (sig/GND/PWR/sig), GND-plane reference (FE-URT-1; solid GND plane = single low-Z return), bulk-cap injection at the 4 quadrant points per `docs/power_rail_layout.md`.
4. **DRC + ERC** — `erc_drc_runner.py` invocation, expected pass criteria, common failure patterns (silkscreen overlap, clearance violations on power planes).
5. **Fab output** — `gerber_pack.py` + `bom_export.py` + PCBWay manifest. Pre-submit checklist from `docs/pcbway_submit_checklist.md`.
6. **Nova-specific patterns** — link to the four Nova doc files; specifically call out: `JP_BUS_MASTER` solder bridge default to Pattern B, INA226 I²C address jumpers, comparator trip-point divider math.

### 2.4 MCP integration

Skill assumes `Seeed-Studio/kicad-mcp-server` is installed and configured in `~/.claude/settings.json`. SKILL.md instructions reference the MCP's tools (e.g. `mcp__kicad__list_nets`, `mcp__kicad__trace_connectivity`, `mcp__kicad__run_drc`) rather than reimplementing them.

If user doesn't have the MCP installed, the skill's first step is `library_setup.sh` which also installs the MCP via uv / pip + adds the entry to `settings.json`.

---

## 3. Nova-specific knowledge baked into the skill

These come straight from [`BOM.md`](../BOM.md) / [`docs/order-list.md`](./order-list.md) / [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md) and prevent re-deriving them on each PCB design session. **Each row maps to a v6 spec section + a skill template file.**

| Topic | What the skill knows | v6 spec § | Template file |
|---|---|---|---|
| Battery input + reverse-prot + MRBF fuse | XT60 panel-mount in, MOSFET reverse-prot (no diode), MRBF-30 fuse off-board (Blue Sea 5191, ~9 kA AIC @ 16.8 V; Class T superseded 2026-06-12, ANL's 6 kA rejected), high-current switch | §1 | `templates/battery_input_subschematic/` |
| Power rails | 4S LiPo 12.8-16.8V → 5 buck rails (D42V110F7 / D42V110F12 / D24V22F12 / D42V55F12 + reserved arm-rail D42V55F7) | §2 | `templates/power_rails_subschematic/` |
| Servo bus distribution | Single signal bus, 4 power injection points along leg trunk, 1000 µF bulk caps at each injection point, GND-plane reference (FE-URT-1), hip rail injects at chassis floor | §3 | `templates/bus_distribution_subschematic/` |
| Bus master Pattern B / A bridge | Teensy UART → SN74LVC125A quad tri-state buffer (half-duplex driver) → bus pads. OE pins drive TX/RX direction. `JP_BUS_MASTER` solder bridge: B default, A fallback to FE-URT-1 direct | §4 | `templates/bus_master_subschematic/` |
| Bus integrity footprints | Series R (22-100Ω 0603) at SN74LVC125A output, ferrite bead at each servo entry, GND-plane reference (GND plane = single low-Z return). Single-ended TTL — NOT RS-485, no 120 Ω term. Populate iteratively per measured error rate. | §5 | `templates/bus_integrity_subschematic/` |
| Safety chain | 13.2V LVC alarm (charger), 13.0V graceful → LM393 comparator → Teensy GPIO → `/battery_low`, 12.4V MOSFET hard-cutoff, E-stop NC in series with leg+hip+L2 EN pins (Jetson stays live), INA226 ×3 (+ optional 4th) on I²C | §6 | `templates/safety_chain_subschematic/` |
| Aux MCU + peripherals | Arduino Nano slot (PIR, ultrasonic, OLED, RGB, DFPlayer, MPU-6050), Teensy 4.1 footprint (INA226 reader + E-stop GPIO + SN74LVC125A OE) | §7 | `templates/aux_mcu_subschematic/` |
| Connector convention | JST-XH 2.54 low-current signals, XT30 servo power trunks, XT60 panel-mount battery, all keyed | §8 | global design rules |
| Stackup + ground | 4-layer (top sig / GND / PWR / bottom sig), GND-plane reference (FE-URT-1), 2 oz copper, ENIG finish, PCBWay default | §"Design workflow" | `templates/nova_pcb_v6.kicad_project` |
| Acceptance gate (firmware, informs PCB) | Loop p99 < 100 µs — PCB must not compromise bus integrity. Series R + ferrite footprints reserved per [[project-deferred]] #13. | firmware/teensy/README.md | docs/acceptance_gate_constraints.md |

---

## 4. Build sequence (when user approves)

### Phase 1 — scaffolding (½ day)

1. Create `~/.claude/skills/pcb-design/` directory structure
2. Install Python deps (`kicad-python`, `kikit`, `kibot`) into a dedicated venv at `~/.claude/skills/pcb-design/.venv/`
3. Pull `Seeed-Studio/kicad-mcp-server`, configure in `~/.claude/settings.json`
4. Clone Pololu + Adafruit + Sparkfun KiCad libraries to `~/kicad-libs/` and symlink into KiCad's library manager
5. Write minimal `SKILL.md` + `README.md`

### Phase 2 — Nova templates (1 day)

1. Build starter `kicad_project` template for Nova PCB v6 (correct stackup, DRC rules per Pololu D42V110 footprint requirements, board outline matching v5.2b mounting holes)
2. Write 3 sub-schematic templates: power module wrapper, INA226 block, safety chain
3. Write Nova-specific doc files in `docs/` (referenced inline from SKILL.md so Claude reads on demand)

### Phase 3 — automation scripts (½ day)

1. `pcb_design_skeleton.py` — scaffolds new project from template
2. `erc_drc_runner.py` — wraps `kicad-cli sch erc` + `kicad-cli pcb drc`, parses output, returns clean/dirty + diff
3. `bom_export.py` — `kicad-cli sch export bom` + PCBWay/JLCPCB column mapping
4. `gerber_pack.py` — `kicad-cli pcb export gerbers` + drill files + `.zip` + PCBWay manifest

### Phase 4 — integration + tests (½ day)

1. `tests/test_drc_clean.py` — load the Nova template, run DRC, expect zero violations
2. CI hook — `.github/workflows/pcb-drc.yml` runs the test on every PR that touches `hardware/`
3. Manual test: run the skill end-to-end on the actual NovaSM3 PCB v6 schematic (incomplete) → expect ERC to surface known holes (intentional during away-week schematic work)

### Phase 5 — away-week rehearsal (½ day, ahead of 2026-05-29)

1. Walk through scaffolding a fresh project from skill
2. Verify all 4 Nova subschematics drop in cleanly
3. Confirm DRC + ERC pipeline works
4. Confirm gerber export produces valid PCBWay-acceptable ZIP

**Total estimated build time: ~2.5 dev days.**
Recommendation: complete Phases 1-2 before away-week (so the schematic work has clean templates to start from); Phases 3-4 during away-week; Phase 5 as confidence check.

---

## 5. Risks + open decisions

| Risk | Mitigation |
|---|---|
| KiCad 9 IPC API is new (released early 2026), some features still buggy | Use `kicad-cli` for the critical fab-output path; reserve Python API for nice-to-have automation |
| Pololu lib doesn't include the exact D42V55F12 footprint | Build it from datasheet PDF; ship in `templates/footprints/` so other Nova builders get it free |
| Seeed MCP version drifts away from KiCad 9.x | Pin MCP version in `library_setup.sh`; upgrade with deliberate testing |
| User installs newer KiCad later, breaks templates | `kicad-cli version` check at skill init; warn if mismatch |
| Mac KiCad install missing CLI on PATH | Skill bootstrap symlinks `kicad-cli` from `/Applications/KiCad/KiCad.app/Contents/MacOS/` |

Open decisions for user input (with my recommendations):

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| 1 | MCP choice | **Seeed-Studio/kicad-mcp-server** | Most prod-ready, KiCad 9.0+, actively maintained, pin-level connectivity tracing matters for Pattern B bus debugging |
| 2 | Notion page integration | **Skill calls Notion MCP at runtime IF available; falls back to repo-only mode if no `/mcp` auth.** | Notion MCP already installed at user scope per Notion page. Best of both — auto-pulls fresh status when available, doesn't break if unauth'd. |
| 3 | CAD workflow boundary | **PCB stays in `hardware/pcb-mods/` subtree. Mechanical chassis CAD stays with `parametric-3d-printing` skill (already has `robotics_patterns.md`).** | Clean separation. Skills can cross-reference (e.g. PCB skill asks parametric-3d-printing for mounting-hole pattern dimensions). |
| 4 | Library install location | **`~/kicad-libs/` (reusable across projects), symlinked into KiCad's library manager. Templates ship as symlinks.** | Future projects (LeRobot adapter PCB, sensor breakouts) reuse the same Pololu / Adafruit / Sparkfun libs without duplication. |
| 5 | Naming | **`pcb-design`** | Generic naming matches `parametric-3d-printing` convention (skill is task-defined, not tool-defined). KiCad-specifics live inside the skill body, not the name. |

KiCad version note: Notion page mentions "KiCad 8.x + Pololu library install (PCB v6 prep)" in Phase 0 remaining. **Recommend KiCad 9.x** (released early 2025, current stable) since:
- New IPC API enables better automation
- `kicad-cli` is more capable
- Backward-compatible with KiCad 8 schematics/PCBs
- All 3 MCP servers target 9.x

If you've already started in KiCad 8, no migration cost — opens fine in 9.

---

## 6. Sources

- [KiCad 9 Python API official docs](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html)
- [KiCad CLI reference](https://docs.kicad.org/master/en/cli/cli.html)
- [Seeed-Studio kicad-mcp-server (recommended MCP)](https://github.com/Seeed-Studio/kicad-mcp-server)
- [lamaalrajih kicad-mcp](https://github.com/lamaalrajih/kicad-mcp)
- [mixelpixx KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)
- [KiKit (panelization + fab-data)](https://pypi.org/project/kikit/)
- [kicad-python (IPC API wrapper)](https://github.com/atait/kicad-python)
- [Claude Code Skills documentation](https://code.claude.com/docs/en/skills)
- [Anthropic skills repository](https://github.com/anthropics/skills)
- [`parametric-3d-printing` skill (sibling, same author)](file:///Users/afox/.claude/skills/parametric-3d-printing/SKILL.md) — structural reference for this skill

---

## 7. Next action

Notion content received + PCB v6 design spec read. All 5 open decisions have recommended answers above.

User to:

1. Confirm or override the 5 recommendations in §5
2. Approve Phase 1-2 to start before away-week (2026-05-29 = 6 days from now)
3. Decide on Notion MCP — auth now via `/mcp` so skill can read live status, or skip and stay repo-only?

Then Claude builds. Phase 1-2 (skeleton + Nova templates) target completion by 2026-05-28 so the away-week schematic work has a working template to start from.
