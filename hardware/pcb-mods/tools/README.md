# pcb-mods/tools

Headless KiCad helpers for the NOVA v6 boards. Compiled from the repeated
patterns in the 2026-06 PCB review sessions so they aren't re-derived each time.

## board_health.py — one-shot pre-fab report

```bash
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY hardware/pcb-mods/tools/board_health.py hardware/pcb-mods/nova_pcb_v6_logic/nova_pcb_v6_logic.kicad_pcb
```

Reports, in one pass:
1. **Lock guard** — refuses to vouch for the board if `*.lck` / `~_autosave*.lck` exist or KiCad is running (never edit a live board headless).
2. **DRC** (errors only) + **ERC** (violation-type counts).
3. **Footprint + value** list.
4. **Off-board connector pinouts** — the *board-expects* side of the connector mating audit (`docs/pre-power-on-validation.md §1c`); verify each against the physical part.
5. **Zones / planes** (net, layer, filled?).
6. **Single-pad / dangling nets.**
7. **Trace width per named net** (spot thin power traces; confirm planes carry current, not traces).

Exit code != 0 on DRC errors, unconnected items, or a lock present.

## Hard-won rules (see memory `feedback-kicad-headless`)

- **Close KiCad fully before any headless board/schematic write.**
- **Add a part to a finished board incrementally** — place footprint + hand-route only its nets. Do NOT full-re-route (Freerouting fragments the GND pour → zone-island / starved-thermal whack-a-mole).
- **Footprint pad geometry ≠ schematic symbol** (R_0603 pads are horizontal ~1.65 mm apart).
- **Teensy 4.1 footprint pad names ≠ physical pins** — map geometrically via the T-named reference pads.

## Headless reference snippets

- DRC: `kicad-cli pcb drc --severity-error --exit-code-violations board.kicad_pcb`
- Gerbers: `kicad-cli pcb export gerbers --output fab/ board.kicad_pcb` + `... export drill --excellon-separate-th`
- Freerouting (autoroute from scratch): `pcbnew.ExportSpecctraDSN(b,'x.dsn')` → `java -jar freerouting-2.2.4.jar -de x.dsn -do x.ses -mp 100` → `pcbnew.ImportSpecctraSES(b,'x.ses')` → `ZONE_FILLER(b).Fill(b.Zones())`. Only for from-scratch routing, never to add one part to a routed board.
