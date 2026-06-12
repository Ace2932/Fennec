# DEPRECATED — 2026-06-05

This single-board project (`nova_pcb_v6/`) is **superseded by the 2-board mezzanine**:

- `../nova_pcb_v6_power/` — battery / rails / servo-bus / safety
- `../nova_pcb_v6_logic/` — Teensy / 74HC125 / Nano

joined by inter-board connector **J20**. Do new work on the mezzanine projects;
this board is kept for reference/history only.

**Known unfixed bug here:** Teensy 4.1 powered via its 3.3V *output* pin with VIN
floating (a Teensy 4.x cannot be back-powered through 3.3V), and the Nano `+5V`/`VIN`
both float. Fixed **only** on the mezzanine logic board (`V5_AUX` → Teensy VIN +
Nano `+5V`); not back-ported here.
