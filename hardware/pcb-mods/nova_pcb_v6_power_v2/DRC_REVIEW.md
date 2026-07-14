# DRC review — nova_pcb_v6_power_v2 (ordered board)

Ran fresh DRC (KiCad 9.0.5, `kicad-cli pcb drc`) on the ordered v6 power_v2 board
to verify the 12 flagged violations are benign vs blocking.

**Verdict: all 12 are benign cosmetic warnings. Zero errors. The ordered boards
are good — no re-spin.**

## Result
- **0 errors, 0 unconnected, 0 schematic-parity, 0 clearance/track violations.**
- Clearance IS enforced (board `min_clearance=0` is just "no global floor";
  netclasses govern: Default 0.2 mm, Power 0.3 mm / 1.5 mm track, HighCurrent
  0.3 mm / 3.0 mm track). DRC evaluated against these — clean.
- 12 warnings, all cosmetic (below).

## The 12 warnings
| type | n | refs | verdict |
|------|---|------|---------|
| lib_footprint_mismatch | 9 | H1–H4, M1, J2, SW1, SW2, Q1 | **INTENTIONAL** — local footprint edits (SW1/SW2 drill, pad overrides, via annular per the KiCad-headless notes) diverge from the stock library. The board is fabricated from these embedded footprints, so zero fab impact. **Do NOT "Update Footprints from Library"** — it reverts the manual drill/pad fixes. |
| silk_over_copper | 2 | L1, R4 ref-des | Fab auto-clips silkscreen off solder-mask openings. Cosmetic (label slightly clipped). Benign. |
| silk_overlap | 1 | R4 ref-des over its own silk outline | Cosmetic readability only. Benign. |

## Rules set to `ignore` in the project
`footprint_filters_mismatch`, `footprint_type_mismatch` (metadata, benign),
`missing_courtyard`, `npth_inside_courtyard`, `pth_inside_courtyard` (courtyard
checks). Courtyard-ignore is fine on this placement-reviewed board (mounting
holes / connectors sit intentionally close), but re-enable + review for v7.

## v7 backlog (cosmetic, next spin only — NOT the ordered boards)
- Nudge R4 + L1 reference-designator silk off the pads (clears silk_over_copper
  + the R4 silk_overlap).
- Re-enable the ignored courtyard rules and review overlaps.
- The 9 footprint mismatches stay as-is (intentional edits); if a v7 re-import is
  done, re-apply the SW1/SW2 drill + pad/via overrides after, never before DRC.

_Reviewed 2026-07-14. DRC JSON: `kicad-cli pcb drc --format json`._
