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

### Two corrections to `master-bom.md`

Its reflow-skip line reads *"21 SMD parts all 0603/SOT-23/SOIC, hand-solder"*.

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
  | TS-ILS (fine long conical) | 0603 R/C, SOT-23, SOD-123 | 1–2 |
  | TS-K (knife) | SOIC drag-solder, bridge wicking | 3 |
  | TS-C4 (≈4 mm bevel) | **every plane-tied / high-current pad** — L1, SW1.2, Q1.3, U1.4, XT60/XT30, buck stations | 4, 6, 7, 8 |
  | TS-D24 (≈2.4 mm chisel) | general THT — headers, JST, terminal blocks, electrolytics | 5, 8 |
  | TS-J02 (bent fine) | tight rework, no straight-on access | any |
  | threaded insert adapter | M3 heat-sets in printed parts (not PCB) | — |
- [ ] **Supply voltage — the half that gets forgotten.** The Pinecil's power
      scales with input voltage; a 9–15 V USB brick delivers a fraction of the
      60–88 W the note above assumes, and no tip compensates for that. The
      bench list already has a **Kungber 30 V/10 A supply** — run the iron's DC
      barrel from it at ~24 V (respect the Pinecil's own max) and it reaches the
      assumed ceiling. Do this before concluding the iron is inadequate.
- [ ] **Preheat — still unsolved.** `master-bom.md` skips the reflow hotplate,
      so nothing on the BOM gets the board to 100–130 °C. The Etekcity IR gun
      can verify the temperature but cannot produce it. May prove unnecessary
      once tip + 24 V are sorted; the 14 A plane pads below are where it would
      bite.

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

| stage | what | why here |
|---|---|---|
| **0** | Bare-board: continuity `VBAT`↔`VBAT_PROTECTED` open (SW1 not fitted), no `VBAT`–`GND` short | Cheapest possible fault-find. A plane short after 33 THT parts is a nightmare. |
| **1** | 0603 R and C, both boards (23 parts) | Smallest, flattest, most numerous. Do them while the board is cold and bare. |
| **2** | D1 (SOD-123F), Q2–Q4 (SOT-23), FB1 | Still small, still cold. Mind D1 polarity. |
| **3** | U8 (SOIC-8), U7 (SOIC-14) | Fine-pitch, wants flux + drag or wick. Before anything tall gets in the way of the iron angle. |
| **4** | **L1** (12×12 SMD inductor) | Last of the SMD. Plane-tied both sides → preheat + fat tip. Doing it before the fine-pitch work would mean preheating the board with SOICs already on. |
| **5** | Low THT: J2, M1, JP1, J9, J10, J21, J8, J11, J20 (both boards) | Headers and JSTs seat flush; do them before the board stops sitting flat. |
| **6** | SW1, SW2 terminal blocks | SW1.2 is a 14 A plane pad — preheat. Still low profile. |
| **7** | XT30 ×8 + XT60 J1, buck stations U1–U4 | The bulk of the high-current THT. All preheat + fat tip. |
| **8** | Q1 (TO-220), electrolytics C1–C9 | Tall. Q1.3 is a 14 A GND pad — preheat. Electrolytics are polarised and heat-sensitive: they go after the pads that need the board hot. |
| **9** | Modules: U9–U11 (INA226), U6 (Teensy 4.1), U12 (Nano) | Heat-sensitive, tallest, and the parts you most want to be able to remove. Socket where possible. |

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

**Off-board modules to have in hand before stage 7:** 4× Pololu buck,
3× INA226 2 mΩ breakout, MRBF fuse block, Contura rocker, E-stop.

Cable routing for these bundles — including the strain-relief and grommet
detail — is in `../wiring/README.md` §"Strain relief + routing notes". The
Jetson −Y bundle is **no longer blocked**; that note was stale until 2026-07-29.

---

## 6. Gates between stages

- After **stage 0** — no `VBAT`–`GND` short.
- After **stage 4** — reflow-quality check on L1 and both SOICs before tall
  parts block the view. Wick any bridge now.
- After **stage 8**, before **stage 9** — this is the last moment the board is
  a bare PCB. Run `pre-power-on-validation.md` §1c **connector mating audit
  (HARD GATE)** and §1e (connector polarity, buck variants, INA addressing)
  here. Fitting Teensy/Nano/INA modules first makes rework much worse.
- Before first power — the whole of `pre-power-on-validation.md`, in its own
  order. Inrush into ~5470 µF and trip-point calibration are not build steps.

---

## 7. Open

- [x] ~~Tip: 4 mm-class chisel~~ **DONE** — TS-C4 owned (§2).
- [ ] **Power the Pinecil from the Kungber supply at ~24 V** (DC barrel, not a
      USB brick). Costs nothing, and TS-C4 on 12 V will still stall on a 14 A
      plane pad — the tip stores heat, the supply replaces it. **Gates stage 6
      onward.**
- [ ] **Then test whether preheat is needed at all**, rather than buying for it:
      TS-C4 at 24 V on `Q1.3` or `SW1.2`, and watch whether the joint wets in a
      couple of seconds or the iron sags. The Etekcity IR gun reads what the pad
      actually reaches. Only buy a hotplate if that test fails.
- [ ] Confirm 0.6–0.8 mm solder actually on the shelf (`master-bom.md` says
      "verify").
- [ ] Fix `master-bom.md`'s "21 SMD parts all 0603/SOT-23/SOIC" (§1).
- [ ] Re-label `pre-power-on-validation.md` §9 — the 🔴 is stale (§4).
- [ ] Decide socket vs direct-solder for U6/U12 on the logic board before
      stage 9.

_Inventory and nets read from the board files 2026-07-29._
