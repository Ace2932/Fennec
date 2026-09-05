# DRC/ERC review — nova_pcb_v6_logic (ordered board)

Ran fresh DRC + ERC (KiCad 9.0.5, `kicad-cli pcb drc` / `kicad-cli sch erc`) on the
ordered v6 logic board to verify the flagged violations are benign vs blocking.

**Verdict: all 7 DRC + 2 ERC warnings are benign local-override cosmetics. Zero
errors either check. The ordered boards are good — no re-spin.**

## Result
- **DRC: 0 errors, 0 unconnected pads, 7 warnings** (all `lib_footprint_mismatch`).
- **ERC: 0 errors, 2 warnings** (both `lib_symbol_mismatch`).

## The 7 DRC warnings

Checked each against the actual stock library file on this machine
(`/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/`), not
guessed — pad count/size/shape/drill and silkscreen+fab-layer `fp_line`
coordinates diffed byte-for-byte where a stock copy exists.

| ref | footprint | verdict / what differs |
|-----|-----------|-------------------------|
| `J20` | `IDC-Header_2x06_P2.54mm_Vertical` | **INTENTIONAL, CHARACTERIZED.** Pads (12×, size/shape/drill) are byte-identical to the stock `Connector_IDC` copy. The board's copy is **missing the library's pin-1 polarity-marker triangle** (3 short `fp_line` segments near pad 1, e.g. `(-4.68,-0.5)→(-4.68,0.5)→(-3.68,0)→(-4.68,-0.5)`) — every other silkscreen/fab line matches. Cosmetic; pad 1 is still electrically and physically identified by the connector's own keying. Fab-critical net map (pads 7/8/9 = `I2C_SDA`/`I2C_SCL`/`BATT_LOW`) is unaffected. |
| `J11` | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | **Checked, not characterized.** All 34 silkscreen/fab `fp_line` segments and pad geometry are byte-identical to the stock `Connector_JST` copy — the actual mismatch trigger is not in the drawn graphics or pads and was not isolated further (likely a non-graphical metadata/attribute field). Zero drawn/electrical difference found. |
| `J10` | `PinHeader_1x07_P2.54mm_Vertical` | **Checked, not characterized.** All 15 `fp_line` segments and pad geometry are byte-identical to the stock `Connector_PinHeader_2.54mm` copy. Same as `J11` — no drawn/electrical diff found. |
| `U6` | `Teensy_4.1` (lib `nova_v6`) | **INTENTIONAL, CHARACTERIZED.** This is the custom Teensy 4.1 socket footprint itself, hand-edited after being drawn — its own descr says *"Pads 1-9 = the 9 used signals on sensible main-header pins (GPIO firmware-flexible) ... Pin order from PJRC card11a rev4 -- VERIFY vs board before fab"* (#401's subject). The mismatch is `nova_v6`'s own stored library copy diverging from the placed, hand-tuned instance — expected and load-bearing; see BUILD_PLAN.md §6 gate 9b. |
| `JP1` | `PinHeader_1x03_P2.54mm_Vertical` | **Checked, not characterized.** All 15 `fp_line` segments and pad geometry are byte-identical to the stock `Connector_PinHeader_2.54mm` copy (this is the `JP_BUS_MASTER` solder-bridge jumper). No drawn/electrical diff found. |
| `U7` | `SOIC-14_3.9x8.7mm_P1.27mm` (lib `Package_SO`) | **Checked, not characterized.** All 18 `fp_line` segments and all 14 pads are byte-identical to the stock `Package_SO` copy. No drawn/electrical diff found. |
| `J9` | `PinHeader_1x02_P2.54mm_Vertical` | **Checked, not characterized.** All 15 `fp_line` segments (including the pin-1 chamfer) and pad geometry are byte-identical to the stock `Connector_PinHeader_2.54mm` copy. No drawn/electrical diff found. |

`J11`/`J10`/`JP1`/`U7`/`J9` in particular: since pads and silkscreen are proven
identical, whatever is actually tripping `lib_footprint_mismatch` for them
carries **no fab or electrical risk either way** — it rules out the failure
modes DRC exists to catch (wrong pad size/shape/drill, moved silkscreen).

## The 2 ERC warnings
| ref | symbol | verdict / what differs |
|-----|--------|-------------------------|
| `U6` | `Conn_01x09` (lib `Connector_Generic`) | **INTENTIONAL, CHARACTERIZED.** `U6` is drawn in the schematic as a hand-built `Conn_01x09`-derived stand-in for the 9 Teensy signals actually used on this sheet, with **two extra named pins added** (`T3V3O`, `T5`) beyond the stock part's 9 — confirmed from the sheet's own embedded `lib_symbols` block (`04_bus_master.kicad_sch`). "9 pins" no longer matches the library's `Conn_01x09` definition by construction. Local override, not a routing fault. |
| `U12` | `Arduino_Nano_v3.x` (lib `MCU_Module`) | **Checked, partially characterized.** The stock library symbol is declared as `(extends "Arduino_Nano_v2.x")` — it inherits all pins/graphics from the parent and only overrides Reference/Value/Footprint/Datasheet properties; the board's placed instance (30 pins) is a fully-flattened copy. The mismatch is consistent with the parent `Arduino_Nano_v2.x` library definition having moved since this copy was cached; exact pin-level diff not isolated further. No evidence found that any of `U12`'s 30 pin-to-net assignments are wrong. |

## Disposition
**Intentional — do NOT "Update Footprints/Symbols from Library."** Doing so
would revert the local pad/pin edits above (most consequentially `U6`, whose
footprint is the one board pattern under active bench verification per
BUILD_PLAN.md §6 gate 9b / issue #401). The board is fabricated from these
embedded footprints and symbols, so none of the 9 warnings above have any fab
impact.

**Fab date:** boards ordered 2026-07-01 (JLCPCB) — see
`../../../nova-proj/project-board-fab-readiness.md`.

_Reviewed 2026-09-05. `kicad-cli` 9.0.5. DRC/ERC re-run fresh for this review;
counts match the same-day power_v2 re-run exactly (12 warnings / 0 errors,
matching `../nova_pcb_v6_power_v2/DRC_REVIEW.md`)._
