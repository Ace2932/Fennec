# PCB build plan — v6 power_v2 + logic

Population sequence and the off-board component map, for the two ordered v6
boards. **Not** a validation doc: what to test, and in what order, lives in
`../../docs/pre-power-on-validation.md`. Parts and sourcing live in
`../../docs/order-list.md` and `../../docs/master-bom.md`. This answers "what
do I solder, in what order, and what hangs off the edges".

Inventory below was read out of the two `.kicad_pcb` files on 2026-07-29, not
transcribed from the BOM — where the two disagree, the board files win and the
disagreement is called out.

---

## 1. Inventory

| board | footprints | SMD | THT | mech | DNP |
|---|---|---|---|---|---|
| `nova_pcb_v6_power_v2` | 61 | 24 | 33 | 4 | U5, U12 |
| `nova_pcb_v6_logic` | 22 | 10 | 8 | 4 | — |

**power_v2 SMD (24)** — 16× R 0603, 2× C 0603, 3× SOT-23 (Q2 Q3 Q4),
1× SOD-123F (D1), 1× SOIC-8 (U8), 1× **L\_12x12mm\_H8mm (L1)**
**power_v2 THT (33)** — 8× XT30 (J3–J7, J12–J14), 1× XT60 (J1), 5× buck
stations (U1–U5), 5× CP\_Radial D12.5 (C1–C5), 3× CP\_Radial D10 (C6, C8, C9),
4× INA226 breakout (U9–U12), 2× terminal block (SW1, SW2), 1× IDC 2×06 (J20),
1× JST-XH 3 (J8), 1× 1×03 (J2), 1× 1×02 (M1), 1× TO-220 (Q1)

**logic SMD (10)** — 7× R 0603, 1× C 0603, 1× FB 0603 (FB1), 1× SOIC-14 (U7)
**logic THT (8)** — Teensy 4.1 (U6), Arduino Nano (U12), IDC 2×06 (J20),
1×07 (J10), 2× 1×02 (J9, J21), 1×03 jumper (JP1), JST-XH 3 (J11)

### Board size and which side everything is on

Measured from `Edge.Cuts` and each footprint's own layer field:

| board | outline | F.Cu | B.Cu |
|---|---|---|---|
| power_v2 | **112 × 90 mm** | 35 | **26** |
| logic | **84 × 78 mm** | 19 | 3 (R3, R4, R5) |

**power_v2 B.Cu (26)** — C1–C7, L1, Q2–Q4, R2–R9, R11–R16, U8
**power_v2 F.Cu (35)** — C8, C9, C\_gs1, D1, H1–H4, J1–J8, J12–J14, J20, M1,
Q1, R17, R\_gs1, SW1, SW2, U1–U5, U9–U12

Three consequences that are easy to miss:

- **Most of the SMD is on the BOTTOM** (20 of 24: all the 0603 R except R17/R\_gs1,
  C7, U8, L1, Q2–Q4). Only D1, R17, R\_gs1, C\_gs1 are top-side SMD. Stages 1–4
  therefore all work the bottom face; the first flip is at stage 5.
- **The electrolytics are split** — C1–C6 bottom, C8/C9 top. "Electrolytics last"
  applies to both faces.
- **Top-side THT is soldered from the bottom face**, which by then carries 20 SMD
  parts including L1 at 8 mm tall. This is a second, independent reason the
  bottom-side electrolytics (C1–C6, 12.5 mm cans) must wait: they would block
  iron access to the very pads at stage 8.

### Two corrections to `master-bom.md` (applied there 2026-07-29)

Its reflow-skip line read *"21 SMD parts all 0603/SOT-23/SOIC, hand-solder"*.

1. **The count is 34**, not 21 (24 + 10 across both boards).
2. **They are not all 0603/SOT-23/SOIC.** L1 is `L_12x12mm_H8mm` — a 12×12 mm
   power inductor on the L2 rail (`V12_L2_RAW` → `V12_L2`), and there are two
   SOIC (U8 SOIC-8, U7 SOIC-14).

The *conclusion* still holds — hand-solder, no stencil, no hotplate. But L1 is
the hardest joint on either board, not a 0603, and the plan below sequences it
accordingly.

---

## 2. Tooling — the one real gap

Owned (`master-bom.md`): Pinecil V2, flux, 0.6–0.8 mm solder, wick, sucker.

`pre-power-on-validation.md` §1d records the trap: `VBAT_PROTECTED` (PWR.Cu)
and `GND` (GND.Cu) are **solid pad-connected planes**, deliberately — the
high-current pads were thermal-relief throats good for only ~6 A and would
have overheated. The cost is that those pads now **wick heat straight into the
plane**, and that note ends: *"a bare 60–88 W Pinecil will struggle on the big
ones."*

**The only iron on the BOM is exactly the iron that note says will struggle.**

Two things govern whether it actually struggles, and only one of them is the tip.

- [x] **Tip mass — DONE, kit owned** (confirmed 2026-07-29). LUMINZENLUX
      TS100/Pinecil V2 6-pack: **TS-C4** ≈4 mm bevel, **TS-D24** ≈2.4 mm chisel,
      TS-K knife, TS-ILS, TS-J02, plus a **threaded insert adapter**. TS-C4 is
      the tip for the plane-tied pads. The insert adapter also replaces the
      ad-hoc M3 heat-set tip in `../../docs/checklists/print-batch.md`, so the
      same kit covers PCB and printed-part work. Logged in
      `../../docs/master-bom.md`, which previously listed only "Pinecil V2
      iron" — which is why this was an open question at all.

  **Tip per stage** (stages in §3):

  | tip | use | stages |
  |---|---|---|
  | TS-ILS (fine long conical) | 0603 R/C, SOT-23, SOD-123 | 1–2, 5 |
  | TS-K (knife) | SOIC drag-solder, bridge wicking | 3 |
  | TS-C4 (≈4 mm bevel) | **every plane-tied / high-current pad** — L1, SW1.2, Q1.3, U1.4, XT60/XT30, buck stations | 4, 7, 8 |
  | TS-D24 (≈2.4 mm chisel) | general THT — headers, JST, terminal blocks, electrolytics | 6, 9 |
  | TS-J02 (bent fine) | tight rework, no straight-on access | any |
  | threaded insert adapter | M3 heat-sets in printed parts (not PCB) | — |
- [x] **Supply voltage — DONE, two adequate supplies owned.** The half that
      gets forgotten: the element is resistive, so power goes as **V²**. What
      matters is voltage, *not* USB vs barrel — a 65 W PD brick is fine, a
      9–15 V one is not, and no tip compensates for the difference.
      - **Anker Nano II 65 W GaN** (owned): negotiates 20 V / 3.25 A = 65 W,
        inside the 60–88 W band the note above assumes. Fine for every stage
        **except** the plane-tied joints at 4, 7 and 8 — use the bench supply
        for those. Needs a PD C-to-C cable rated ≥3.25 A, not a charge-only lead.
      - **Kungber 30 V/10 A** (owned): **prefer this for the plane-tied joints at stages 4, 7 and 8.** ~24 V
        into the DC 5525 barrel is 24²/20² ≈ **1.44×** the 20 V PD power, free.
        That headroom is exactly what the 14 A plane pads want.
- [ ] **Preheat — unsolved, and CONDITIONAL. Do the bench test before buying.**
      Nothing owned reaches 100–130 °C; the Etekcity IR gun measures it but
      cannot produce it. May prove unnecessary once TS-C4 runs at 24 V.

  **If it is needed, it has to be IR, not a contact hotplate.** Both faces of
  power_v2 are populated (§1), so a flat plate can only heat a face that is
  still bare:

  | stage | needs preheat? | contact plate? |
  |---|---|---|
  | 1–4 (bottom SMD incl. L1) | L1 yes | ✅ top face still bare — lay it top-down |
  | 7–8 (SW1.2, Q1.3, U1.4, XT30s) | yes, most of them | ❌ bottom populated **and** top carries tall connectors — it will not lie flat either way |

  A contact plate therefore covers L1 and **not** the three 14 A pads, which are
  the joints the warning is actually about. Candidate: **YIHUA 853A** IR station,
  ~$85, 130×130 mm heated area (covers 112×90 with margin), 50–350 °C PID.
  MHP30 (30×30) and MHP50 (50×50) are far too small for this board despite
  being the usual hobby recommendations.

  **Hot air is not a substitute.** It is localised and fights the same plane
  conduction that makes these pads hard; preheat works by removing the gradient,
  which needs bulk heating. A hot-air station (e.g. YIHUA 8786D, ~$70) is still
  worth owning for **stage 3** SOIC rework and for harness heatshrink — just do
  not buy it expecting the plane pads to improve.

### Pads that need the fat tip + preheat

| pad | net | current |
|---|---|---|
| SW1.2 | `VBAT_PROTECTED` | 14 A inject |
| Q1.3 | `GND` | 14 A GND inject |
| U1.4 | `V7V5_LEG` | 10 A leg VOUT |
| J1 (XT60) | `VBAT` / `BATT_NEG` | pack feed |
| U2–U4.1/.2/.4 | `VBAT_PROTECTED` / `GND` / rail | buck VIN/VOUT |
| L1 | `V12_L2_RAW` / `V12_L2` | SMD, 12×12, plane-tied |

---

## 3. Population order

Ordering rules, in priority: **low profile before tall** (the board must sit
flat on the bench for every later joint), **small thermal mass before large**
(a preheated board makes small parts harder, not easier), **heat-sensitive and
plug-in modules last**, and **nothing that blocks access to a pad you still
have to reach**.

Side column is which face the **body** sits on. Grouped to keep flips to a
minimum: bottom SMD, then top SMD, then THT.

| stage | side | what | why here |
|---|---|---|---|
| **0** | — | Bare-board: continuity `VBAT`↔`VBAT_PROTECTED` open (SW1 not fitted), no `VBAT`–`GND` short | Cheapest possible fault-find. A plane short after 33 THT parts is a nightmare. |
| **1** | **B** | Bottom 0603: R2–R9, R11–R16, C7 (+ logic R3–R5) | Smallest, flattest, most numerous, and all on one face — do them in one sitting with the top still bare. |
| **2** | **B** | Q2–Q4 (SOT-23) | Same face, still small, still cold. |
| **3** | **B** | U8 (SOIC-8) — and U7 (SOIC-14) on the logic board | Fine-pitch, wants flux + drag or wick. Before anything tall spoils the iron angle. **The stage most likely to want hot air for a bridge.** |
| **4** | **B** | **L1** (12×12 SMD inductor) | Last of the bottom SMD. Plane-tied both sides → fat tip. Last stage where the top face is bare, so the last one a *contact* plate could serve (§2). |
| **5** | **F** | Top SMD: D1 (SOD-123F), R17, R\_gs1, C\_gs1 (+ logic C1, FB1) | Flip once. Only 4 top-side SMD parts — mind D1 polarity. |
| **6** | **F** | Low THT: J2, M1, J8, J20 (+ logic JP1, J9, J10, J21, J11, J20) | Headers and JSTs seat flush; do them before the board stops sitting flat. |
| **7** | **F** | SW1, SW2 terminal blocks | SW1.2 is a 14 A plane pad. Still low profile, so do it before the tall connectors crowd the iron. |
| **8** | **F** | XT30 ×8 + XT60 J1, buck stations U1–U4, **and Q1 (TO-220)** | The bulk of the high-current THT, plus Q1 — pad 3 is a 14 A GND inject. **Last preheat stage; see the note below.** Soldered from the bottom face, which already carries 20 SMD parts — hence C1–C6 must still be off. |
| **9** | B + F | Electrolytics: C1–C6 (bottom), C8–C9 (top) | Tall, polarised, **~105 °C-rated — below the 100–130 °C board preheat.** After every preheat joint, and after stage 8 because the bottom cans would block access to stage 8's solder side. |
| **10** | **F** | Modules: U9–U11 (INA226), U6 (Teensy 4.1), U12 (Nano) | Heat-sensitive, tallest, and the parts you most want to be able to remove. Socket where possible. |

### All preheat work finishes at stage 8 — this constrains the order

If preheat turns out to be needed (§2), it applies to **L1, SW1.2, Q1.3, U1.4,
the XT30/XT60s and the buck stations** — stages 4, 7 and 8. Every one of those
is done before an electrolytic goes on, because a ~105 °C-rated cap sitting on a
board held at 100–130 °C is being stressed by the very step that is meant to
protect the joint. Same logic for the plug-in modules in stage 10.

So the rule is not "tall parts last" for its own sake: **the board must be free
of anything temperature-limited for as long as it might still need to be hot.**
If a preheat-requiring joint has to be redone later, take the electrolytics off
first rather than preheating around them.

**Do not populate: U5, U12 (power board).** See §4 — the reason changed.

---

## 4. The arm rail (U5 / U12) — status corrected 2026-07-29

`pre-power-on-validation.md` §9 (written 2026-06-14) lists two blockers against
populating U5. **Both are closed on the ordered v2 board.** Verified by reading
pad nets straight out of `nova_pcb_v6_power_v2.kicad_pcb`:

| gap as written | actual on v2 |
|---|---|
| "arm rail has no exit — `V7V5_ARM` = `U5.4` only, single-pad net" | **`J14.2 = V7V5_ARM`.** The rail has an off-board XT30. |
| "🔴 arm buck is UNGATED — `U5.EN` tied to `VBAT_PROTECTED` = always-on" | **`U5.3 = EN_BUCKS`**, byte-for-byte the same net as `U1.3`. Gated by e-stop Q3 **and** hardcut Q2. |

So U5/U12 are **DNP for scope, not for safety** — there is no arm yet. That is
a materially different instruction from "populating this is a crush hazard",
and §9 should be re-labelled rather than left to frighten the next reader.

---

## 5. Off-board component map

Everything that leaves the power board. Gauges per `../wiring/README.md`
§"Wire gauge convention".

| ref | connector | net(s) | goes to | wire |
|---|---|---|---|---|
| J1 | XT60-M | `VBAT` / `BATT_NEG` | 4S LiPo **via the MRBF fuse block** (off-board, floor plate) | 18 AWG silicone |
| SW1 | TB132 screw, 5.08 mm | `VBAT` → `VBAT_PROTECTED` | Contura rocker, ~18 A — **off-board panel/pod**. Drill is 1.5 mm (bumped from lib 1.2) for TB007-508-02BE | 18 AWG |
| SW2 | TB132 screw | `GND` / `EN_SW` | E-stop, signal level only | 22 AWG |
| U1 | 2× XT30 station | `VBAT_PROTECTED`/`GND` in, `V7V5_LEG` out, EN=`EN_BUCKS` | **Pololu buck, off-board module** | 18 AWG |
| U2 | 2× XT30 station | → `V12_HIP` | Pololu buck, off-board | 18 AWG |
| U3 | 2× XT30 station | → `V12_L2_RAW` (then L1 → `V12_L2`) | Pololu buck, off-board | 18 AWG |
| U4 | 2× XT30 station | → `V12_JET`, EN=`EN_JET` | Pololu buck, off-board | 18 AWG |
| U5 | 2× XT30 station | → `V7V5_ARM` | **DNP** — Phase 4 | — |
| J3–J6 | XT30 ×4 | `V7V5_LEG` / `GND` | leg servo **star injection**, one per leg | 18 AWG |
| J7 | XT30 | `V12_HIP` / `GND` | hip rail injection | 18 AWG |
| J12 | XT30 | `V12_JET` / `GND` | Jetson | 18 AWG |
| J13 | XT30 | `V12_L2` / `GND` | L2 LiDAR (post-L1 filter) | 18 AWG |
| J14 | XT30 | `V7V5_ARM` / `GND` | arm rail — fitted, rail DNP | — |
| J8 | JST-XH 3 | `GND` / `V7V5_LEG` / `BUS_SERVO` | servo bus + power pigtail | 28 AWG vendor / 18 AWG |
| J2 | 1×03 header | `VBAT_PROTECTED` / `GND` / `V5_AUX` | aux tap | 22 AWG |
| M1 | 1×02 header | `VBAT_PROTECTED` / `GND` | pack-voltage monitor tap | 22 AWG |
| J20 | IDC 2×06 shrouded | `V5_AUX`, `GND`, `+3V3`, `BUS_SERVO`, `I2C_SDA`, `I2C_SCL`, `BATT_LOW` | **logic board**, 12-way ribbon across the ~20 mm mezzanine gap | ribbon |
| U9–U11 | INA226 breakout | I²C + shunt | plug-in modules, one per active rail | — |
| U12 | INA226 breakout | — | **DNP** — arm rail telemetry | — |

**Off-board modules to have in hand before stage 8:** 4× Pololu buck,
3× INA226 2 mΩ breakout, MRBF fuse block, Contura rocker, E-stop.

Cable routing for these bundles — including the strain-relief and grommet
detail — is in `../wiring/README.md` §"Strain relief + routing notes". The
Jetson −Y bundle is **no longer blocked**; that note was stale until 2026-07-29.

---

## 6. Gates between stages

- After **stage 0** — no `VBAT`–`GND` short.
- After **stage 4** — reflow-quality check on L1 and both SOICs before tall
  parts block the view. Wick any bridge now.
- After **stage 9**, before **stage 10** — this is the last moment the board is
  a bare PCB. Run `pre-power-on-validation.md` §1c **connector mating audit
  (HARD GATE)** and §1e (connector polarity, buck variants, INA addressing)
  here. Fitting Teensy/Nano/INA modules first makes rework much worse.
- Before first power — the whole of `pre-power-on-validation.md`, in its own
  order. Inrush into ~5470 µF and trip-point calibration are not build steps.

---

## 7. Open

- [x] ~~Tip: 4 mm-class chisel~~ **DONE** — TS-C4 owned (§2).
- [x] ~~Adequate supply~~ **DONE** — Anker 65 W PD (20 V) and Kungber bench
      (~24 V) both owned. Use the Kungber for stages 4, 7 and 8 (§2).
- [ ] **Test whether preheat is needed at all** — do not buy for it first.
      TS-C4 on the Kungber at ~24 V. Start on `U1.4` (10 A, least severe of the
      three), then `Q1.3` or `SW1.2` (14 A). Does the joint wet in ~3 s, or does
      the tip temperature crater while you sit there at 10 s? The Etekcity IR gun
      reads what the pad actually reaches. Sitting on a pad waiting is what lifts
      pads and cooks laminate — that is the failure this is screening for.
      **Only if it fails: the 853A IR preheater (§2), not a contact hotplate and
      not hot air.** This is the only thing between here and stage 4, and it
      costs nothing but a few minutes at the bench.
- [ ] Hot-air station (§2) — independent of preheat. Buy when stage 3 (SOIC) or
      harness heatshrink actually calls for it, not as a preheat substitute.
- [ ] Confirm 0.6–0.8 mm solder actually on the shelf (`master-bom.md` says
      "verify").
- [x] ~~Fix `master-bom.md`'s "21 SMD parts all 0603/SOT-23/SOIC"~~ **DONE**
      2026-07-29 — corrected to 34 there, with the L1 caveat (§1).
- [ ] Re-label `pre-power-on-validation.md` §9 — the 🔴 is stale (§4).
- [ ] Decide socket vs direct-solder for U6/U12 on the logic board before
      stage 10.

_Inventory and nets read from the board files 2026-07-29._
