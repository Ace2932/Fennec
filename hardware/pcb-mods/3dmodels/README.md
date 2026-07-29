# 3dmodels — render-only 3D models

Models referenced by `(model ...)` entries in the v6 board files so
`kicad-cli pcb render` shows populated boards. **No electrical meaning.**

- `Teensy_4.1_Headers.step` — real colored Teensy 4.1 model (GrabCAD
  community, from Aiden's Downloads snapshot). Used on the logic board:
  rotate z 90, offset (0, 0, 3.3) — header plastic bottom (internal z -3.3) seats on the board; uncut pins protrude ~4.6mm below (model z spans -9.5..+9.5, PCB at ±0.8). Supersedes `Teensy_4.1.wrl` (kept as fallback).
- `Arduino_Nano_Classic.step` — real classic Nano (user-supplied GrabCAD,
  MEGA328P). Aux-MCU slot: offset (0, 0, 9.5), rotate (-90, 0, 90) — model
  authored on its side, USB toward -x internally. Paired with 2x KiCad
  `PinSocket_1x15_P2.54mm_Vertical.step` at offsets (0,0,0)/(15.24,0,0)
  so the 8.5mm socket height reads as a socketed module.
- `arduino_nano_r4.step` — step.parts catalog (checksum-verified). Unused
  alternate (modern Nano R4).
- `Arduino_Nano.wrl` — placeholder in the `Module:Arduino_Nano` lib frame
  (pin1 at origin). KiCad 9 ships no Nano STEP.
- `INA226_Module.wrl` — CJMCU-226-style module slab; positioned for the
  `nova_v6:INA226_Module_Breakout` footprint. U12 is DNP (Phase-4 arm rail)
  and correctly renders unpopulated.
- `Teensy_4.1_Assembly.STEP` — XenGi/teensy.pretty original; unused
  (multi-part assembly, off-center bbox). Kept for reference.

XT30s: real XT30-M STEP (`XT30-M.step`, user-supplied GrabCAD model).
Model pins at internal (0,3)/(0,8) along +y -> rotate z 90, offset x -3
(standalone lib footprints) or (-5.5, ±5) (buck stations). Earlier
scaled-XT60 substitution retired.

Patch script (idempotent, re-runnable): `patch_models.py` in this folder;
re-run it to re-add entries if footprints are ever re-imported.
