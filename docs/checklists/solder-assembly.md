# Solder / assembly — see `hardware/pcb-mods/BUILD_PLAN.md`

**This file is a pointer. The canonical build sequence is
[`../../hardware/pcb-mods/BUILD_PLAN.md`](../../hardware/pcb-mods/BUILD_PLAN.md).**

## Why this is a stub

An earlier pass in this session wrote a full parallel populate checklist here
before noticing `BUILD_PLAN.md` (2026-07-29/30) already existed and was better:
11 stages instead of 8, an off-board component map with wire gauges, per-stage
gates, and the tip-per-stage table.

Worse, the two used **the same word "stage" for different steps** — this file's
"Stage 4" was low-profile top-side THT, `BUILD_PLAN`'s stage 4 is L1. Two bench
documents disagreeing on step numbers is the kind of seam that costs a board, so
this one was retired rather than reconciled.

It also had a real sequencing error: it listed **L1 with the ordinary 0603s**.
L1 is a 12×12 mm plane-tied inductor and is the **hardest joint on either
board** — `BUILD_PLAN` correctly gives it its own stage, last of the bottom SMD,
because it is the final point at which a contact preheat plate could still reach
a bare top face.

## What was salvaged into `BUILD_PLAN.md`

Everything of value from the deleted version was folded in, not lost:

- **§2a — iron temperature + Pinecil V2 setup** (new): solder-alloy decision,
  per-stage tip setpoints, the 24.0 V ceiling on the Pinecil V2 barrel, the
  IronOS settings to change, and a pass/fail number for the §7 preheat test.
- **§4 — `U12` must be POPULATED** as the L2 rail monitor at `0x45`, not left DNP
  as an arm part. The firmware already expects it.
- **§3 orientation table** — the `Q1` TO-220 tab sits at `BATT_NEG`, so
  heatsinking it to chassis ground silently bypasses reverse-polarity protection.
- **§3 values note** — `R17` = 10k and `D1` = BZT52C18 (18 V) as built; the older
  "100 Ω / BZT52C15" plan is superseded and would fail the 20 V Vgs limit.
- **§5** — the SMBJ TVS clamps are off-board across the XT30 pigtails, which no
  doc had recorded as a build step.

One fix landed elsewhere: `docs/pre-power-on-validation.md` §1c said "PCB has no
shunt (R13/R14 removed)" without noting that **those designators were later reused**
for the live e-stop pull-up and hardcut hysteresis. Corrected in place.

Notion mirror: **🔧 Soldering / Assembly Steps**, child of the Power Board v6
Build Log.
