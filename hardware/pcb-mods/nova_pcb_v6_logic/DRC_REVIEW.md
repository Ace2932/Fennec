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
guessed. Each embedded footprint was sliced out of `nova_pcb_v6_logic.kicad_pcb`
(the `(footprint "<lib>:<name>" ... )` s-expression, matched paren-for-paren)
and diffed field-by-field against the stock `.kicad_mod` — pad `at`/`size`/
`drill`/`shape`/`layers`/`roundrect_rratio`, and every silkscreen+fab
`fp_line`/`fp_poly` coordinate — not just byte-diffed as flat text, since a
harmless reordering of otherwise-identical entities would show as a false
byte-diff. Stock files:
`/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/{Connector_IDC,Connector_JST,Connector_PinHeader_2.54mm,Package_SO}.pretty/*.kicad_mod`;
`U6` against this repo's own `nova_pcb_v6_logic/nova_v6.pretty/Teensy_4.1.kicad_mod`.

| ref | footprint | verdict / what differs |
|-----|-----------|-------------------------|
| `J20` | `IDC-Header_2x06_P2.54mm_Vertical` | **INTENTIONAL, CHARACTERIZED — not a missing triangle.** The pin-1 polarity-marker triangle (`(-4.68,-0.5)→(-4.68,0.5)→(-3.68,0)`) **is present**, byte-for-byte, and all 30 silkscreen/fab `fp_line` segments match the stock `Connector_IDC` copy as a set (they're just written in a different order in the file — same widths/layers/coordinates, no geometry change). The real diff: **all 12 pads carry an explicit `(at x y 180)` rotation** where stock has `(at x y)` (no rotation token) — position/size/drill/shape/`roundrect_rratio` otherwise identical. Harmless: pad 1 is a 1.7×1.7 roundrect and pads 2-12 are 1.7×1.7 circles, both rotationally symmetric about their own center, so a 180° spin is a geometric no-op. |
| `J11` | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | **CHARACTERIZED.** Same root cause as `J20`: all 3 pads carry the same phantom `(at x y 180)` token (position/size/drill/shape otherwise identical); all 34 silkscreen/fab `fp_line` segments are byte-identical to stock `Connector_JST`, same order. Pad 1 is a roundrect, pads 2-3 are ovals (1.7×1.95) — an oval centered at its own origin is unchanged by a 180° spin about that center, so this is also a no-op. |
| `J10` | `PinHeader_1x07_P2.54mm_Vertical` | **CHARACTERIZED.** Same phantom `(at x y 180)` on all 7 pads vs stock `Connector_PinHeader_2.54mm`; all 15 `fp_line` segments byte-identical, same order. Pad 1 is a 1.7×1.7 square (rect), pads 2-7 circles — both symmetric under 180°, no-op. |
| `U6` | `Teensy_4.1` (lib `nova_v6`) | **INTENTIONAL, CHARACTERIZED.** This is the custom Teensy 4.1 socket footprint itself, hand-edited after being drawn — its own descr says *"Pads 1-9 = the 9 used signals on sensible main-header pins (GPIO firmware-flexible) ... Pin order from PJRC card11a rev4 -- VERIFY vs board before fab"* (#401's subject). Re-diffed: pad names/count genuinely diverge from the repo's own `nova_v6.pretty/Teensy_4.1.kicad_mod` (e.g. `T3V3O` and other renamed/added pads) — this is not the rotation-token artifact seen on the other six refs. The mismatch is `nova_v6`'s own stored library copy diverging from the placed, hand-tuned instance — expected and load-bearing; see BUILD_PLAN.md §6 gate 9b. |
| `JP1` | `PinHeader_1x03_P2.54mm_Vertical` | **CHARACTERIZED.** Same phantom `(at x y 180)` on all 3 pads vs stock `Connector_PinHeader_2.54mm` (this is the `JP_BUS_MASTER` solder-bridge jumper); all 15 `fp_line` segments byte-identical, same order. Pad 1 rect, pads 2-3 circles — symmetric under 180°, no-op. |
| `U7` | `SOIC-14_3.9x8.7mm_P1.27mm` (lib `Package_SO`) | **CHARACTERIZED — not "byte-identical pads."** Same phantom `(at x y 180)` on all 14 pads vs stock `Package_SO` (position 1.95×0.6 roundrect, `roundrect_rratio 0.25`, otherwise identical); all 18 `fp_line` + both `fp_poly` entities byte-identical, same order/points. A roundrect with a uniform corner ratio is symmetric under 180° rotation about its own center regardless of aspect ratio, so this is also a no-op. |
| `J9` | `PinHeader_1x02_P2.54mm_Vertical` | **CHARACTERIZED.** Same phantom `(at x y 180)` on both pads vs stock `Connector_PinHeader_2.54mm`; all 15 `fp_line` segments (including the pin-1 chamfer) byte-identical, same order. Pad 1 rect, pad 2 circle — symmetric under 180°, no-op. |

`J20`/`J11`/`J10`/`JP1`/`U7`/`J9` share one root cause: every pad in these six
embedded footprints carries an explicit `(at x y 180)` rotation the stock
library copy doesn't have. In every case the affected pad shape (circle,
square/rect, oval, or uniform-ratio roundrect) is rotationally symmetric about
its own center, so the extra rotation changes nothing drawn or electrical —
it just makes `lib_footprint_mismatch` fire. Silkscreen/fab graphics are
geometrically identical in all six (same segments/points; `J20`'s are simply
stored in a different order in the file, everything else stored in the same
order as stock).

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
