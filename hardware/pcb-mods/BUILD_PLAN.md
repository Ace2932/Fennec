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
| `nova_pcb_v6_power_v2` | 61 | 24 | 33 | 4 | U5, U12 *(board flags; **U12 IS populated** — §4)* |
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

Owned (`master-bom.md`): Pinecil V2, flux, wick, sucker, and — **confirmed 2026-08-01** —
solder: **Sn63Pb37, 1 mm, 1.8 % flux core**. Leaded, as §2a recommends, so **the leaded column
in §2a is the live one and nothing shifts +30 °C**. The stage-1 blocker is closed. ⚠️ The
diameter is **1 mm, not the 0.6–0.8 mm** originally specced — see §2a for what that changes
(technique at stages 1/3, not a re-order).

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
      - **Kungber 30 V/10 A** (owned): **prefer this for the plane-tied joints at stages 4, 7 and 8.**
        **24.0 V** into the DC 5525 barrel is 24²/20² ≈ **1.44×** the 20 V PD power, free.
        That headroom is exactly what the 14 A plane pads want. ⚠️ **24 V is the Pinecil V2's
        DC ceiling** (barrel 12–24 V, 24 V/5 A) and this is a 30 V supply — dial it down and
        confirm on the display before plugging in; current limit ≥4 A. Details in §2a.
- [x] **Preheat — SOLVED. Test run 2026-08-01, PASSED, do not buy.** No
      purpose-built preheater is owned and none is needed. `U1.4` (10 A) wet in
      **~2 s with solder through to the far face**; `Q1.3` (**14 A GND inject** —
      the worst THT pad on the board) went easy and came out **shiny on both
      faces**, i.e. the barrel wicked. Setup: **TS-C4, Kungber 24.0 V (~88 W),
      tip 400 °C, Sn63Pb37 1 mm** — heat the pad ~2 s, then feed into the tip/pad
      junction. Full result in §2a. The conditional buy is **closed, not deferred**.
      **Consequence:** if the 14 A GND inject goes in seconds, every XT30/XT60 and
      `SW1.2` is the same problem or easier — the high-current THT is no longer the
      risk item in this plan.
      ⚠️ **The one joint the test did NOT model is `L1` (stage 4)**: SMD, plane-tied
      on *both* sides, so there is no barrel and "solder on the far face" does not
      apply — it is a fillet against a plane sinking heat from underneath as well as
      laterally. If it fights, the answer is the **420 °C boost held a few seconds,
      not a purchase**. The P1S bed (§2a) remains available for stage 4 and is free.
      ⚠️ The Etekcity IR gun **cannot** stand in as the measurement here: 16:1 optics
      (22.6 mm spot at its recommended distance) and a matte-surface emissivity
      assumption make it useless on a 2–3 mm shiny pad. It reads *bulk board*
      temperature only. §2a explains, and uses solder phase-change instead.

  *Kept for the record — the spec that would have applied had it failed.*
  **It would have had to be IR, not a contact hotplate.** Both faces of
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

## 2a. Iron temperature and Pinecil V2 setup

The tip table above says *which* tip. This says *how hot*, and how to actually get
the iron there. Verified against Pine64's Pinecil docs and the IronOS settings
reference on 2026-07-31 — but IronOS menu wording shifts between releases, so
trust the on-device help text over this table if they disagree.

### The alloy — CONFIRMED 2026-08-01: Sn63Pb37, 1 mm, 1.8 % flux core

Leaded, which is what this section recommended. **The leaded column below is the
live one** — the bracketed lead-free setpoints do not apply and nothing in this
document shifts +30 °C.

Why it was the right call anyway:

- It melts at **183 °C** vs SAC305's **217–220 °C**, so every joint happens
  ~35 °C cooler — and the whole difficulty here is getting heat *into* a plane.
- The **logic board is HASL-lead** (§ the JLC order spec), so its pads are already
  tin-lead. Lead-free wire onto lead-plated pads makes a mixed alloy — it works,
  but there is no reason to take it.
- The power board is ENIG, which is happy with either.

**Eutectic, so the inspection criterion is simple: a correct joint is SHINY.**
Sn63Pb37 has **no plastic range** — it goes solid at 183 °C with no mushy interval
to freeze badly in. Dull grey or grainy *after the flux is cleaned off* therefore
means the joint moved while freezing or was heat-starved. It is a defect signature,
not a finish preference — and it is the **opposite** of SAC305, where a correct
joint is legitimately dull. Do not carry that habit over.

⚠️ **"After the flux is cleaned off" is a precondition, not a throwaway clause.**
The owned flux is *no-clean*, whose cured residue is glossy — so an uncleaned board
does not withhold the verdict, it **forges a passing one**. See the next subsection;
it is the reason there is now an explicit clean-and-inspect step at all.

⚠️ **The diameter is 1 mm, not the 0.6–0.8 mm `master-bom.md` originally specced**,
and it cuts both ways along the stage split already in §3. 1 mm carries **~2.8× the
solder per mm of feed**, which:

- **helps** at stages **4/7/8** — the plane-tied pads, where the entire difficulty
  is delivering mass and heat before dwell cooks the laminate;
- **hinders** at stages **1/3** — 0603 pads are ~0.8 mm, so feeding 1 mm wire
  over-delivers and bridges.

Fix is technique, not a second spool: **tin the tip and place** on the 0603s rather
than feeding wire, and keep U7/U8 to flux + drag/wick where the wire barely touches.

**1.8 % rosin core is standard, but it flashes off fast at 380–400 °C.** The
separate flux below is mandatory for stages 4/7/8 and the U7/U8 drag — core flux
alone is gone before the joint wets at those temperatures, and that reads as "the
plane is winning" when it is actually flux starvation.

### The flux — CONFIRMED 2026-08-01: BEEYUIHF, lead-free / no-clean / non-conductive

Label claims, not a datasheet; form, volume and IPC classification are unrecorded.

**"Lead-free" does not mean incompatible with Sn63Pb37.** It describes the *flux* —
formulated to stay active up to SAC305's 217–220 °C. Leaded joints happen ~35 °C
cooler, so the flux is over-specified for this build, never under-. Activation is
~150–200 °C and every stage here runs a 320–400 °C tip, so it is fully spent inside
the joint. No purchase, no substitution.

**Stage 1 needs it too — and the reason is technique, not temperature.** The rule
above (mandatory at 4/7/8) is about flux *burning off*. Stage 1 loses it a different
way: §2a prescribes **tin the tip and place** on the 0603s because 1 mm wire
over-delivers on a 0.8 mm pad. But core flux lives *inside the wire* and deploys
where the wire melts — and tip-carry melts it **on the tip**, so the flux flashes off
up there and what reaches the pad is bare solder carrying nothing. The technique that
solves the diameter problem creates a flux-starvation problem. Per 0603:

1. Dab flux on both pads.
2. Tack one end with the tip-carried blob, ~1 s. Part is now anchored, tweezers free.
3. Second end: **feed fresh wire** into the joint — core flux fires right there. This
   is the cleaner of the two joints.
4. Reflow end 1 with a touch of fresh wire so both ends match.

**"Non-conductive + no-clean" closes the R4/R6 leakage question.** `R4` 11.3k and
`R6` 12.1k are the trip-point divider, so residue leakage across a leg would move a
protection threshold rather than fail loudly. Run the number: a 1 % shift needs
~1.1 MΩ in parallel with the 11.3k leg. Cured no-clean residue sits orders of
magnitude above that. Not a concern.

#### ⚠️ What it does open: the residue forges a PASS

Cured no-clean residue is **glossy**. The correctness criterion for eutectic solder
is **shiny**. So a film of clear residue over a dull, grainy, heat-starved joint
**reads as a good joint**.

This is the failure mode worth naming, because it is not "you cannot tell" — it is a
confident wrong answer, biased in the PASS direction, on the one criterion this
document relies on. It defeats exactly the defect (moved while freezing, or
heat-starved) that the shiny rule exists to catch.

**So the verdict is only available after cleaning. Per stage, before moving on:**

Use the **aerosol flux remover** (MG Chemicals 4140, ordered 2026-08-02), not plain IPA.
The chemistry matters here: our flux is **no-clean**, the residue class IPA handles worst,
and IPA only *partially* dissolves it — the resin redeposits as a **white haze**. That is
the mirror of the uncleaned failure above: uncleaned reads glossy → **false PASS**;
half-dissolved reads hazy → **false FAIL**. Plain IPA, used imperfectly, puts errors on
both sides of the one criterion this document relies on. 4140 is rated for no-clean and
states *"safe on plastic components"*, which is what makes it usable at stage 10 alongside
the Teensy/Nano/INA modules and the OLED window.

1. Board **COOL** — it is a flammable aerosol and you have just been at 320–400 °C.
2. Stand the board **angled over paper towel** so runoff carries residue OFF the edge.
   This is the whole mechanical advantage over wiping: it *flushes* rather than
   redistributes.
3. Short bursts through the **extension straw**, working top-down.
4. Brush while wet (acid brush or an old toothbrush).
5. **Final flush with no brushing** — that pass carries the loosened residue away
   instead of spreading it. Do not finish on the brush stroke.
6. Let it flash off and come back to **room temperature** before judging. The propellant
   chills the board, and in coastal air a chilled board fogs — condensation on a good
   joint reads as dull.
7. *Now* judge shiny. Rework anything dull or grainy before the next stage — not at the
   end, when the board no longer sits flat and the pad is behind a tall part.

99 % IPA is still worth having and is **not** a substitute here — it is for general prep,
tool wiping and the printer's PEI plate. If you ever have to fall back to it on a board,
the old rule applies: flood → brush → **blot lint-free** → repeat, because with IPA the
wicking step is the only thing stopping the smear.

Second-order, and specific to this combination: a lead-free-rated flux run at leaded
temps leaves **peripheral** residue — squeezed outside the joint, never hotter than
60–100 °C — less fully spent than the flux inside it. No-clean is only inert once
heat-activated. On a machine that vibrates and collects dust, that is the residue
worth removing even though the joints themselves are fine.

### Temperature by stage

Leaded first, lead-free in brackets. These are *tip setpoints*, not pad temperatures.

| stages | parts | tip | setpoint |
|---|---|---|---|
| 1, 2, 5 | 0603, SOT-23, SOD-123F | TS-ILS | **320 °C** (350) |
| 3 | U8 SOIC-8, U7 SOIC-14 — drag/wick | TS-K | **330 °C** (355) |
| **4, 7, 8** | **L1, SW1.2, Q1.3, U1.4, XT30/XT60, buck stations** | **TS-C4** | **380–400 °C** (400) |
| 6 | headers, JST, IDC | TS-D24 | **330 °C** (355) |
| 9 | electrolytics — **≤3 s per lead** | TS-D24 | **340 °C** (360) |
| 10 | module headers / sockets | TS-D24 | **330 °C** (355) |

**Do not set a WORKING temperature above 400 °C.** Past that the flux flashes off
before it can wet, tip plating degrades quickly, and you get *worse* joints, not
faster ones. **The 420 °C boost below is the deliberate exception** — it is held
for a few seconds on one stubborn pad, not dialled in and left there. Keep the
distinction: 400 °C is the ceiling you *work* at, 420 °C is a momentary reserve.

**The counter-intuitive bit, and the one that matters for stages 4/7/8:** a hotter
tip is *gentler* than a cooler one on these pads. Damage is time-at-temperature at
the laminate, not tip setpoint. 400 °C for 3 s puts far less heat into the board
than 340 °C for 15 s spent waiting for a joint that never quite flows. §7 already
names this failure — *"sitting on a pad waiting is what lifts pads and cooks
laminate"* — and the fix is more tip temperature and less dwell, not less of both.

**Technique for the plane-tied pads** (this is worth as much as the wattage):
tin the tip first so there is a molten thermal bridge, land the **largest flat
face of the tip** against the pad for maximum contact area, and feed solder into
the tip/pad junction — not onto the tip. Contact area is the actual bottleneck
once you have 88 W behind you.

> ⚠️ `master-bom.md` and §2 both describe TS-C4 as a *"≈4 mm bevel"*. In the usual
> TS100 naming a `C`-prefix tip is a **chisel** and `BC` is the bevel/hoof, so the
> kit's actual geometry is worth one look before stage 4. It does not change which
> tip to use — TS-C4 is the fattest one either way — only how you present it:
> chisel → flat face down, bevel → the elliptical face down. Maximise contact.

### Supply — set the Kungber to 24.0 V, not higher

Pinecil **V2's DC5525 barrel is rated 12–24 V, 24 V–5 A maximum**, and it reaches
24 V without any PCB modification. Its published range is **18–88 W**, and 88 W is
**24 V at 3.66 A**.

> ⚠️ The Kungber is a **30 V/10 A** supply. **24 V is the Pinecil V2's ceiling, not
> a suggestion** — dial it to 24.0 V and confirm on the display before plugging the
> iron in. Set the current limit to **≥4 A** so the supply does not fold back into
> CC mode mid-joint, which would silently cost you the power you set all this up for.

| supply | gives | use for |
|---|---|---|
| Kungber bench, **24.0 V** into DC5525 | up to 88 W | **stages 4, 7, 8** (L1 + the 14 A pads) |
| Anker Nano II 65 W GaN, USB-C PD | 20 V / 3.25 A = 65 W | every other stage |

The Anker needs a PD C-to-C cable rated ≥3.25 A — a charge-only lead will
quietly negotiate something lower. (V2 also *unofficially* does PD 3.1 EPR at
28 V/140 W with a certified EPR cable; you do not need it, and 24 V from the
bench supply is the known-good path.)

### IronOS settings — what to change

Navigation, with the tip fitted, from the main screen:

- **Button nearest the TIP** → enter soldering mode.
- **Button nearest the USB end** → enter the settings menu.
- **Hold the tip-side button while soldering** → boost.
- **Hold the tip-side button on the main screen** → temperature adjust.

| menu | setting | set to | why |
|---|---|---|---|
| Power | **Power source** | **DC** | On the bench supply. This sets a 10 V cutoff instead of a per-cell battery cutoff — leave it on a cell count and the iron may cut out or clamp power. |
| Power | **Power limit** | **88 W** on the Kungber | The average wattage the iron targets. On USB-PD it is automatically the *lower* of this and the supply's advertised wattage, so 88 W is safe to leave set — the Anker will still cap itself at 65 W. |
| Power | **PD Mode** / **PD timeout** | leave default | Only touch these if a charger misbehaves; PD timeout exists for QC-charger compatibility. |
| Soldering | **Boost temp** | **420 °C** | Your reserve for a 14 A pad that will not wet. Held, not latched — a few seconds, then back off. |
| Soldering | **Temp change long** | 25 °C (optional) | You will be moving between 320 and 400 °C repeatedly across stages; the default 10 °C step makes that tedious. |

### §7's preheat test — RUN 2026-08-01, **PASSED**. Do not buy a preheater.

**Result: both pads wet and filled in ~3–4 s, shiny on both faces.**

| pad | rating | result |
|---|---|---|
| `U1.4` | 10 A — least severe | ✅ ~2 s to wet, solder through to the far face |
| `Q1.3` | **14 A GND inject** — tied straight into the ground plane, the worst THT pad on the board | ✅ easy, **shiny both sides** |

**Why "shiny both sides" is the whole verdict in one observation:** shiny = eutectic
Sn63Pb37 froze undisturbed and not heat-starved; on *both* faces = the solder wicked
the barrel. A plane-starved pad gives the exact opposite — a blob on the iron side
and nothing through the hole.

Setup that achieved it: **TS-C4, Kungber 24.0 V (~88 W), tip 400 °C, Sn63Pb37 1 mm.**
Heat the pad ~2 s, then feed solder into the tip/pad junction.

⚠️ **`L1` (stage 4) is the one joint this did not model** — SMD, plane-tied on *both*
sides, no barrel, so the far-face criterion does not apply. If it fights, use the
420 °C boost, not a purchase.

*The rest of this section is the original criterion, kept because the measurement
reasoning still governs any joint that has to be re-run.* Run as: **TS-C4, Kungber at
24.0 V, tip 400 °C, solder placed ON THE PAD** (not melted off the tip). Start on
`U1.4` (10 A, least severe of the three), then `Q1.3` or `SW1.2` (14 A).

> ⚠️ **Correction to the first version of this section.** It said to fail the test
> if the Etekcity IR gun read the pad below ~185 °C. **Do not point the IR gun at a
> pad** — that criterion was unsound and would have produced false failures:
> - **Spot size.** The Lasergrip 800 is **16:1**, and at its own recommended 36 cm
>   working distance the spot is **22.6 mm across**. A THT pad is 2–3 mm. The
>   reading averages pad, laminate, iron and background — it cannot resolve the
>   thing being measured, at any distance.
> - **Emissivity.** Consumer guns assume a matte surface (~0.95). Shiny solder and
>   ENIG gold sit nearer 0.05–0.2, so the gun largely sees *reflected ambient* and
>   reads far low — it will happily report ~150 °C on a pad genuinely at 250 °C.
>
> The gun stays useful for **bulk board temperature** (FR4 is matte, close to the
> assumed emissivity) — that is how you confirm a preheat plate is working. It is
> not a pad thermometer.

**Use the solder itself as the thermometer.** A phase change at a known temperature
beats any instrument here: if eutectic leaded solder flows, that joint is above
183 °C by definition. No calibration, no emissivity, no spot size.

**And for these THT pads the acceptance is barrel fill, not surface melt.** Solder
has to wick *up through the plated hole* and form a fillet on the **opposite** side
(IPC-A-610 class 2 wants ~75 % vertical fill). That is the unambiguous "the whole
joint reached temperature" signal, and it is exactly what a plane-starved pad fails:
you get a shiny blob on the iron side and nothing on the far side. Surface-melt alone
will lie to you here.

Three outcomes, not two:

| result | what it means | action |
|---|---|---|
| Wets **and fills through** in **≤3–4 s** | the plane is not winning | **No preheat.** Skip the 853A. |
| Only wets after **~8–15 s** | marginal | **Treat as a fail.** It passes on one joint, but there are ~16 XT30/XT60 plus Q1, SW1 and four buck stations to go — cumulative dwell is precisely how pads lift and laminate cooks. |
| Never wets; solder balls and sits | conduction into the plane exceeds what the iron delivers at liquidus | **Preheat mandatory.** |

Two things worth trying before spending anything:

- **Flux is a heat-transfer aid**, not just a cleaner — a fluxed joint conducts into
  the pad noticeably better than a dry one. Be generous on these six pads.
- **The Bambu P1S bed is an owned 100 °C contact plate.** Per §2 a contact plate only
  serves a face that is still bare — **stages 1–4**, which is exactly where **L1**
  lives, the hardest SMD joint on either board. Lay the board top-face-down on the
  bed with **kapton or foil between it and the PEI** so flux and solder never touch
  the sheet. 100 °C is the low end of the 100–130 °C target, but it removes ~80 °C
  of gradient for free. It does **nothing** for stages 7–8 (both faces populated by
  then), which is where the three 14 A pads are — so it does not replace the IR
  decision, it may just make stage 4 a non-event.

---

## 3. Population order

Ordering rules, in priority: **low profile before tall** (the board must sit
flat on the bench for every later joint), **small thermal mass before large**
(a preheated board makes small parts harder, not easier), **heat-sensitive and
plug-in modules last**, and **nothing that blocks access to a pad you still
have to reach**.

**Every stage ends with clean → inspect → rework, before the next one starts** (§2a).
Not a tidiness step: the flux is no-clean and its residue is glossy, so shiny — the
whole correctness criterion — cannot be read until the board is cleaned. Deferring it
to the end also defeats the ordering rules above, because by then the pad you need to
redo is behind a tall part on a board that no longer sits flat.

Side column is which face the **body** sits on. Grouped to keep flips to a
minimum: bottom SMD, then top SMD, then THT.

| stage | side | what | why here |
|---|---|---|---|
| **0** | — | ✅ **DONE 2026-08-01** — bare-board: continuity `VBAT`↔`VBAT_PROTECTED` open (SW1 not fitted), no `VBAT`–`GND` short | Cheapest possible fault-find. A plane short after 33 THT parts is a nightmare. ⚠️ Applies to **the board it was run on** — five of each were ordered, so if the meter went on a spare rather than the build board, this is not carried over. Re-run on the actual build board before stage 1 if in doubt; it costs one minute. |
| **1** ✅ **DONE 2026-08-02** (15 power 0603 + 3 logic 1k) | **B** | Bottom 0603: R2–R9, R11–R16, C7 (+ logic R3–R5) | Smallest, flattest, most numerous, and all on one face — do them in one sitting with the top still bare. |
| **2** | **B** | Q2–Q4 (SOT-23) | Same face, still small, still cold. |
| **3** | **B** | U8 (SOIC-8) — and U7 (SOIC-14) on the logic board | Fine-pitch, wants flux + drag or wick. Before anything tall spoils the iron angle. **The stage most likely to want hot air for a bridge.** **Includes the `U8` 8↔4 bypass tack — see below.** |
| **4** | **B** | **L1** (12×12 SMD inductor) | Last of the bottom SMD. Plane-tied both sides → fat tip. Last stage where the top face is bare, so the last one a *contact* plate could serve (§2). |
| **5** | **F** | Top SMD: D1 (SOD-123F), R17, R\_gs1, C\_gs1 (+ logic C1, FB1) | Flip once. Only 4 top-side SMD parts — mind D1 polarity. |
| **6** | **F** | Low THT: J2, M1, J8, J20 (+ logic JP1, J9, J10, J21, J11, J20) | Headers and JSTs seat flush; do them before the board stops sitting flat. |
| **7** | **F** | SW1, SW2 terminal blocks | SW1.2 is a 14 A plane pad. Still low profile, so do it before the tall connectors crowd the iron. |
| **8** | **F** | XT30 ×8 + XT60 J1, buck stations U1–U4, **and Q1 (TO-220)** | The bulk of the high-current THT, plus Q1 — pad 3 is a 14 A GND inject. **Last preheat stage; see the note below.** Soldered from the bottom face, which already carries 20 SMD parts — hence C1–C6 must still be off. |
| **9** | B + F | Electrolytics: C1–C6 (bottom), C8–C9 (top) | Tall, polarised, **~105 °C-rated — below the 100–130 °C board preheat.** After every preheat joint, and after stage 8 because the bottom cans would block access to stage 8's solder side. |
| **10** | **F** | Modules: **U9–U12** (INA226 ×4 — see §4, U12 is the L2 monitor), U6 (Teensy 4.1), U12-logic (Nano) | Heat-sensitive, tallest, and the parts you most want to be able to remove. Socket where possible. Note `U12` names *different* parts on the two boards: INA226 on power, Arduino Nano on logic. |

### 🔴 Stage 3 also carries a bodge: `U8` has NO supply decoupling on the board

Verified from `nova_pcb_v6_power_v2.kicad_pcb` 2026-08-06 by full capacitor census, with
a negative control: **C1–C5** sit on `V7V5_LEG`/`V12_HIP`, **C6** on `V12_L2`, **C8/C9**
on `VBAT_PROTECTED`, and **C7 100nF is `VSENSE`↔GND — the sense filter, not a bypass.**
Scanning every footprint for one touching both `V5_AUX` and GND returns only `J2`, `J20`
and `U8` itself. **No two-pad part decouples `V5_AUX` anywhere on the board.** `U8`'s
supply pin is fed from `J2`'s UBEC down a wire with nothing local to it.

So a **100nF hand-tack across `U8` pins 8 (`V5_AUX`) and 4 (GND)** is a required build
step, not a nicety — without it the comparator trips are liable to chatter.

**It cannot be a plain 0603 bridge.** Pins 8 and 4 are **6.25 mm apart** (pin 8 at
x 91.905/y 130.525, pin 4 at 88.095/135.475) and an 0603 spans 1.6 mm. There is no GND
via nearby — the board has only **four** GND vias and none are close — and the nearest
GND pad is `Q2`.2 at 4.8 mm, still too far. So it needs a link: tack the 0603 to pin 8
and run a fine wire to pin 4. **Pull two or three strands out of the solder wick** for
that link — pre-tinned, ~0.1 mm, and far less likely to lever the 0603 off its joint
than the 22 AWG solid. Keep the loop short and flat, then confirm **4→8 ≈ 9.83 k**
(§6) — ~0 Ω means the tack shorted the rail.

⚠️ **Do not carry this bodge to `U7`.** The logic board's `C1` 100nF is a real routed
part on `GND`↔`+3V3` (stage 5). U7 is decoupled by design; U8 is not.

### Per-stage parts, with VALUES

Read out of the board files 2026-07-30. **The side column in the table above is
power_v2**; the logic board is 19 top / 3 bottom (R3, R4, R5), so its parts are
listed per stage below rather than by that column.

Values matter more than references here: R2..R17 are eight different values in
one 0603 reel family, and a swapped divider resistor moves a trip point rather
than failing loudly.

| stage | power_v2 | logic |
|---|---|---|
| **1** B 0603 | R2 100k · R3 22k · R4 11.3k · R5 10k · R6 12.1k · R7 10k · R8 10k · R9 10k · R11 4.7k · R12 4.7k · R13 10k · R14 470k · R15 1M · R16 100k · C7 100nF | R3 1k · R4 1k · R5 1k |
| **2** B SOT-23 | Q2 · Q3 · Q4 — all BSS138 (`_cutoff` / `_estop` / `_jetcut`) | — |
| **3** SOIC | U8 LM393 (**B**) | U7 74LVC125 (**F** — top side, not bottom) |
| **4** B | L1 22 µH (SRR1260-220M) | — |
| **5** F SMD | D1 BZT52C18 18 V zener · R17 10k · R_gs1 100k · C_gs1 0.47 µF | C1 100nF · FB1 600R ferrite · R1 22R · R2 1k · R6 1k · R7 10k |
| **6** F low THT | J2 (UBEC 5V aux) · M1 (voltmeter tap) · J8 (servo-bus JST) · J20 (interboard) | J9 · J10 · J11 · J20 · J21 · JP1 |
| **7** F | SW1 rocker · SW2 e-stop (screw terminals) | — |
| **8** F high-current | J1 XT60 · J3–J7, J12, J13, J14 XT30 · U1–U4 buck stations · Q1 IRLB3034PBF | — |
| **9** electrolytics | C1–C5 1000 µF 25 V (**B**) · C6 470 µF (**B**) · C8, C9 470 µF (**F**) | — |
| **10** modules | U9 INA226 leg 0x40 · U10 hip 0x41 · U11 Jetson 0x44 · **U12 L2 0x45** | U6 Teensy 4.1 · U12 Arduino Nano |

`C_gs1` 0.47 µF and `D1` are the Q1 gate-harden network (`order-list.md` §97-102,
ordered 2026-06-22). Note that list still says "board edit still pending" — the
edit is done; the parts are on the board.

⚠️ **Fit the values in the table, not the ones in the older notes.** Several
places (the Notion build log's "Pending board edit", early review text) still say
*R17 = 100 Ω, D1 = BZT52C15 (15 V)*. **As built and as ordered: `R17` = 10k,
`D1` = BZT52C18 (18 V).** The 2026-06-18 analysis rejected 100 Ω outright — clamp
= Vz + Iz·Zz, so a 33 V spike gives 100 Ω → ~21 V, **over the IRLB3034's 20 V
Vgs limit**; 10 k → 18.04 V. Also note `C_gs1` is marked **"474" = 470 nF**;
a part marked "470" is 47 pF and gives you no soft-start at all.

### Polarity and orientation — getting these wrong is destructive

| part | the trap |
|---|---|
| **J1 XT60, J3–J7 / J12–J14 XT30** | **pad 1 = NEGATIVE, pad 2 = POSITIVE.** Verified from the nets: `J1.1 = BATT_NEG`, `J1.2 = VBAT`. Do **not** assume pad 1 is +. Match against the connector's flat side, not the pad number — this exact reversal has been caught before on this board. |
| **C1–C9 electrolytics** | Polarised, and split across both faces (C1–C6 bottom, C8/C9 top), so "the stripe faces the same way" is not a single rule — check each against its own silk. |
| **D1 BZT52C18** | Zener, SOD-123F. Cathode band. Backwards it clamps nothing and conducts the wrong way. |
| **Q1 IRLB3034PBF** | TO-220-3. Its pad 3 is the 14 A GND inject; pad 1 is `Net-(D1-K)`, pad 2 is `BATT_NEG`. **⚠️ The TO-220 TAB is bonded to the drain = `BATT_NEG`, not GND** — and `SW1` switches only the positive rail, so the tab is live whenever the pack is plugged in, switch off included. Bolting it to a grounded chassis or a shared heatsink shorts drain→source and **silently, permanently bypasses reverse-polarity protection**. Mount isolated or free-standing; if it is ever heatsinked, mica/silpad + shoulder bush and **meter tab-to-GND for an open** first. |
| **U8 LM393 / U7 74LVC125** | SOIC pin-1 dot. **U7 is on the logic board TOP face**, U8 on the power board bottom — do not carry one assumption to the other. |
| **U9–U12 INA226** | Off-board modules on a 4-pin header: `+3V3 / GND / SCL / SDA` at −5.08 / −2.54 / 0 / +2.54 mm. Rail current does NOT pass through the board. |
| **U6 Teensy / U12 Nano** | Orientation set by the USB end. Socket if undecided — see §7. |

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

**Do not populate: U5 (power board).** See §4 — the reason changed.
**U12 DOES get populated** as the L2 rail monitor at 0x45 — also §4.

---

## 4. The arm rail (U5 / U12) — status corrected 2026-07-29

`pre-power-on-validation.md` §9 (written 2026-06-14) lists two blockers against
populating U5. **Both are closed on the ordered v2 board.** Verified by reading
pad nets straight out of `nova_pcb_v6_power_v2.kicad_pcb`:

| gap as written | actual on v2 |
|---|---|
| "arm rail has no exit — `V7V5_ARM` = `U5.4` only, single-pad net" | **`J14.2 = V7V5_ARM`.** The rail has an off-board XT30. |
| "🔴 arm buck is UNGATED — `U5.EN` tied to `VBAT_PROTECTED` = always-on" | **`U5.3 = EN_BUCKS`**, byte-for-byte the same net as `U1.3`. Gated by e-stop Q3 **and** hardcut Q2. |

So U5 is **DNP for scope, not for safety** — there is no arm yet. That is
a materially different instruction from "populating this is a crush hazard",
and §9 should be re-labelled rather than left to frighten the next reader.

### ⚠️ But U12 is a different case — POPULATE IT (corrected 2026-07-31)

**U12 is not an arm part any more.** Grouping it with U5 above is stale, and
following it would leave a rail unmonitored:

- All four INA226 slots are **electrically identical** — pads 4/5/6/7 =
  `I2C_SDA` / `I2C_SCL` / `+3V3` / `GND`. Nothing about the U12 footprint is
  arm-specific; current sense is off-board through the module's own terminals
  either way.
- The 4th INA was **reassigned to the L2 LiDAR rail on 2026-06-30** (commit
  `5fc5eba`) — L2 is live, nav-critical and brownout-sensitive, whereas an INA on
  the DNP arm rail would read nothing.
- **The firmware already expects it.** `platformio.ini:41` has
  `-D NOVA_INA226_L2` **enabled**, `ina226_telemetry.h:26` declares
  `INA226_ADDR_L2 = 0x45`, and `/power_rails` was widened 9 → 12 floats with
  L2 v/a/w at `[9..11]`. Leave U12 empty and those three publish nothing.
- You own **4 modules and no spares** — the 4th is not a shelf spare, it is this.

**Action:** fit U12 at stage 10, bead it to **0x45 (A0 + A1 → VS)**, and wire its
`IN+`/`IN−` inline in the **L2 12 V** harness. The arm, when it exists, gets a
**5th** module at 0x46 on the same bus — no board change.

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
| U9–U11 | INA226 breakout | I²C + shunt | plug-in modules — leg 0x40 / hip 0x41 / Jetson 0x44 | — |
| — | **TVS clamps, no footprint** | across `V7V5_LEG`, `V12_HIP`, `V12_L2` | **Off-board by design** — a sweep of every power schematic and the `.kicad_pcb` finds **zero** `SMBJ` parts; `D1` is the only diode on the board. Solder **2× SMBJ8.5A** across the `V7V5_LEG` injection pigtails, **1× SMBJ13A** on `V12_HIP`, optional **1× SMBJ13A** on `V12_L2`. **Cathode band → +.** Not optional: e-stop regen can drive `V7V5_LEG` to ~21 V against 25 V bulk caps. Heat-shrink each. | inline |
| U12 | INA226 breakout | I²C + shunt | **POPULATE — L2 12 V rail monitor @ 0x45** (§4). `IN±` inline in the L2 harness, same as U9–U11. Silk still says "arm"; the firmware says L2. | — |

### Logic board — what connects where

Same source: nets read from `nova_pcb_v6_logic.kicad_pcb`.

| ref | connector | pins → net | goes to |
|---|---|---|---|
| J20 | IDC 2×06 shrouded | 1,2=`V5_AUX` · 3,4,10,11,12=`GND` · 5=`+3V3` · 6=`BUS_SERVO` · 7=`I2C_SDA` · 8=`I2C_SCL` · 9=`BATT_LOW` | **power board J20**, 12-way ribbon across the ~20 mm mezzanine gap. Both ends are MALE box headers — without the cable the two boards are electrically disconnected. |
| JP1 | 1×03 header | 1=`MASTER_A` · 2=`BUS_SIGNAL` · 3=`MASTER_B` | **bus-master select — verified by net, not by label.** `MASTER_A` → `J9.2` (FE-URT-1). `MASTER_B` → **`U7.3`, the 74LVC125 output** — i.e. Pattern B is Teensy *through the buffer*, not the Teensy pin directly. `BUS_SIGNAL` → `R1.1` (22 R series), `R7.2` (10k idle pull-up to +3V3), `U7.5`. **Jumper 2–3 = Pattern B (default). Jumper 1–2 = Pattern A** (bench/debug from the Jetson). |
| J9 | 1×02 | 1=`GND` · 2=`MASTER_A` | FE-URT-1 USB-TTL adapter (Pattern A path) |
| J10 | 1×07 | 1=`GND` · 2=`V5_AUX` · 3=`SPI_SCK_F` · 4=`SPI_MOSI_F` · 5=`OLED_RST_F` · 6=`OLED_DC_F` · 7=`OLED_CS_F` | SSD1331 OLED. Pin order matches the module (board reworked 2026-06-14 for it); R2–R6 are the 1k series protection on these lines. |
| J11 | JST-XH 3 | 1=`V5_AUX` · 2=`GND` · 3=`LED_DATA` | WS2812B status strip |
| J21 | 1×02 | 1→ **U6 pad T5 (Teensy pin 5)** · 2=`GND` | e-stop 2nd NC contact sense. Verified connected — not a dangling header. |

### Assembly configuration — decide these before stage 10

Three choices are made by how you populate, not by firmware. `pre-power-on-validation.md`
§1e is the authority; this is the physical summary.

1. **JP1 bus master.** 2–3 = Pattern B (default, Teensy drives). 2–1 = Pattern A.
2. **INA226 I²C addresses.** U9–U12 are **four** identical modules — address
   straps are the only thing distinguishing the rails. Set them before fitting;
   they are not distinguishable once installed.
   **leg `0x40`** (default, no bead moved) · **hip `0x41`** (A0→VS) ·
   **Jetson `0x44`** (A1→VS) · **L2 `0x45`** (A0+A1→VS). Map to your module's own
   silk legend — do not assume pad order.
3. **Buck variants.** U1 = D42V110F7 (leg 7.5 V), U2 = D42V110F12 (hip 12 V),
   U3 = D24V22F12 (L2 12 V), U4 = D42V55F12 (Jetson 12 V). Four different
   modules in identical 2×XT30 stations — the silk is the only thing telling
   them apart, and a swap puts 12 V on the 7.5 V servo rail.

**Off-board modules to have in hand before stage 8:** 4× Pololu buck,
**4× INA226 2 mΩ breakout** (leg/hip/Jetson/**L2** — §4; you own exactly 4 and no
spares), MRBF fuse block, Contura rocker, E-stop.

Cable routing for these bundles — including the strain-relief and grommet
detail — is in `../wiring/README.md` §"Strain relief + routing notes". The
Jetson −Y bundle is **no longer blocked**; that note was stale until 2026-07-29.

---

## 6. Gates between stages

- After **stage 0** — no `VBAT`–`GND` short. ✅ **PASSED 2026-08-01** (run in a
  separate session; result reported, not observed here). Per-board, not per-design
  — see the stage 0 row in §3.
- 🔴 **BEFORE stage 2 — meter the trip network from the EMPTY `U8` land.** This is the
  only moment it is easy: `U8`, `Q2`–`Q4` and the UBEC are all unpopulated, so the
  divider is isolated and every node is exposed on a bare SOIC-8 footprint. Stage 3
  covers all eight probe points permanently.

  Pads, read out of `nova_pcb_v6_power_v2.kicad_pcb` (not copied from a note):
  `1=BATT_LOW 2=VSENSE 3=VREF_G 4=GND 5=VREF_H 6=VSENSE 7=HARDCUT 8=V5_AUX`.
  `R4` 11.3k sits `V5_AUX`↔`VREF_G`; `R6` 12.1k sits `V5_AUX`↔`VREF_H`. So:

  | probe | expect |
  |---|---|
  | `8 → 3` | **11.3k** (`R4`) |
  | `8 → 5` | **12.1k** (`R6`) |

  **The decisive check is that `8→3` reads LOWER than `8→5`** — do not rely on the
  absolute values alone. Both nets carry a lower leg to GND (`R5` 10k on `VREF_G`,
  `R7` 10k on `VREF_H`) plus `R15` 1M / `R14` 470k, so each reading can sit a little
  under its nominal and *both* will still look plausible if the parts are swapped. The
  ordering will not. If it is ambiguous, meter `R4` and `R6` across their own pads —
  that is immune to the topology.

  **Why it matters:** `R4`/`R6` set the two comparator references. Swapped, the board
  **hard-cuts at 13.0 V *before* the 12.5 V warning ever fires** — it just shuts down
  early, forever, and never announces why. They are the only 1 % parts in the stage-1
  reel and they are adjacent values.
- 🔴 **AFTER stage 3 — the SOIC probe tables.** Computed from the two `.kicad_pcb`
  netlists (resistors only; caps open, semiconductors off), 2026-08-06. **Clean before
  probing** — wet flux shunts the 1M-range readings.

  **`U8` LM393 (power_v2, B.Cu).** Drag bridges only occur within a row, so these six
  adjacent pairs are the hunt. Every one is distinctly non-zero:

  | pins | expect | ~0 Ω means |
  |---|---|---|
  | 1–2 | 1029 k (2M range) | `BATT_LOW` shorted to `VSENSE` |
  | 2–3 | 29.5 k | `VSENSE` into `VREF_G` |
  | 3–4 | 7.47 k | `VREF_G` to GND — reference dead, board trips forever |
  | 5–6 | 29.5 k | `VREF_H` into `VSENSE` |
  | 6–7 | 38.9 k | `VSENSE` into `HARDCUT` |
  | 7–8 | 9.02 k | `HARDCUT` tied to rail — hardcut never fires |

  Supply and baselines: **4→8 = 9.83 k** (V5_AUX↔GND via R4+R5 ∥ R6+R7 ∥ R9+R16 — this
  is also the check on the 8↔4 bypass tack; **~0 Ω = shorted, OL = something open**.
  ⚠️ It is *not* OL). **4→7 = 16.89 k** and **1→3 = 1000 k** are the pre-`U8` baselines
  already measured as 16.87 k / 1M (`J20`.3 = GND, `J20`.9 = `BATT_LOW`).

  ⚠️ **`U8` pins 2 and 6 are the same net (`VSENSE`) — 0 Ω between them is CORRECT.**
  ⚠️ Pins 1 and 4 are the **same row, opposite ends**; pin 1 is directly across from
  pin 8. Not diagonal.

  **`U7` 74LVC125 (logic, F.Cu).** R1/R2/R6/R7 are stage 5, so with only `U7` fitted
  **every adjacent pair reads OL** — with one exception:

  ⚠️ **pins 13 and 14 are the same net (`+3V3`) — 0 Ω there is CORRECT.** Anything else
  adjacent reading below OL is a bridge. Pins 9/12 are GND, 10/13/14 are `+3V3`,
  **8 and 11 are unconnected**.

  **Diode mode is the only test that proves the CHIP rather than the network.** The
  meter sources ~1 mA, so a 7–39 kΩ path exceeds its compliance and displays OL, while
  a junction displays 0.4–0.8 V — resistors read OL, silicon reads a number. Reference
  the GND pin (`U8`.4 / `U7`.7) and **judge by matched pairs, not absolutes** (same
  doctrine that saved the R4/R6 check):

  - `U8` — **2 and 6** (both IN−, *same net*, must read identically), **3 and 5**
    (both IN+), **1 and 7** (both open-collector outputs). Skip pin 8; the 9.83 k
    network makes it ambiguous, and the 4→8 resistance already covers it.
  - `U7` — **8 and 11 connect to nothing on the board**, so any reading there is purely
    the die: the cleanest proof those leads actually bonded. Then **9/12** (same net),
    **10/13** (same net), and function twins **1/4**, **2/5**, **3/6**.

  A pin at OL both directions is a lead that looks wetted and is not bonded — the one
  defect a resistance sweep cannot see, because the network around the pad measures
  correct with no chip attached to it.

  **WHERE TO PUT THE TIPS — you do not need to touch a 1.27 mm SOIC lead.** A bridge
  shorts the two *nets*, so measure at any pad on them. Pads read out of the board files
  2026-08-08; `J20`/`J13`/`JP1`/`U6` are **bare** (their connectors are stages 6/8/10).

  `U8` — GND reference **`J13`.1** (191.00, 128.00), a bare 14.4 mm² XT30 pad:

  | checks | probe | expect |
  |---|---|---|
  | 1–2 | `J20`.9 ↔ `C7`.1 | 1029 k (2M range) |
  | 2–3 | `C7`.1 ↔ `R5`.1 | 29.5 k |
  | 3–4 | `R5`.1 ↔ `J13`.1 | 7.47 k |
  | 5–6 | `R7`.1 ↔ `C7`.1 | 29.5 k |
  | 6–7 | `C7`.1 ↔ `Q2`.1 | 38.9 k |
  | 7–8 | `Q2`.1 ↔ `J20`.1 | 9.02 k |
  | **4–8 (bypass tack)** | `J13`.1 ↔ `J20`.1 | **9.83 k** |
  | 4–7 baseline | `J13`.1 ↔ `Q2`.1 | 16.89 k |
  | 1–3 baseline | `J20`.9 ↔ `R5`.1 | 1000 k |

  `U7` — GND **`J20`.3** (142.54, 124.00), +3V3 **`J20`.5** (145.08, 124.00):

  | checks | probe | expect |
  |---|---|---|
  | 1–2 · 2–3 · 3–4 | `U6`.5↔`U6`.3 · `U6`.3↔`JP1`.3 · `JP1`.3↔`U6`.6 | OL |
  | 4–5 · 5–6 · 6–7 | `U6`.6↔`JP1`.2 · `JP1`.2↔`U6`.4 · `U6`.4↔`J20`.3 | OL |
  | 9–10 **and** 12–13 | `J20`.3 ↔ `J20`.5 | OL |
  | **8, 11 — lead only** | each lead ↔ `J20`.3 | **OL** |

  ⚠️ `U7` pins **8 and 11 connect to nothing on the board**, so no substitute pad exists
  and they must be probed at the lead. That is also why they are the cleanest diode-mode
  bonding test on either chip — any reading there is purely the die.

  Two limits of net-level probing, so it does not mislead: it proves a bridge **exists**
  but not **where** (on a bad reading, go back in at the pins with a fine tip), and a
  bridge between two pins on the **same** net (`U8` 2–6, `U7` 13–14) is invisible to it —
  which is fine, because it is also harmless.
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
- [x] ✅ **Can the joint reach temperature with no heater under the pad? — TESTED
      2026-08-01, YES.** `U1.4` wet in ~2 s with solder through to the far face;
      `Q1.3` (14 A GND inject) was easy and **shiny on both faces**. Setup: TS-C4,
      Kungber 24.0 V (~88 W), tip 400 °C, Sn63Pb37 1 mm. **No preheater — the buy is
      closed, not deferred.** Details in §2a. Remaining unknown is `L1` only (stage 4,
      SMD, plane-tied both sides, no barrel) → 420 °C boost if it fights, and the P1S
      bed (§2a) is still free cover for that one stage.
- [ ] Hot-air station (§2) — independent of preheat. Buy when stage 3 (SOIC) or
      harness heatshrink actually calls for it, not as a preheat substitute.
- [x] ✅ **Solder confirmed in hand 2026-08-01 — Sn63Pb37, 1 mm, 1.8 % flux core.**
      Leaded as recommended, so the leaded column in §2a is live and nothing shifts
      +30 °C. Stage 1 is unblocked. Diameter is **1 mm, not the 0.6–0.8 mm** the BOM
      specced — helps stages 4/7/8, hinders 1/3, and the fix is tin-the-tip-and-place
      rather than a second spool (§2a). Eutectic ⇒ **shiny is the correctness
      criterion**; dull/grainy after cleaning is a defect signature.
- [x] ✅ **Flux confirmed 2026-08-01 — BEEYUIHF, lead-free / no-clean / non-conductive.**
      "Lead-free" is about the flux, not compatibility: it stays active to 217–220 °C
      and every joint here is cooler, so it is over-specified, never under-. No buy.
      Two things it changed (§2a): separate flux is now mandatory at **stage 1** as
      well as 4/7/8 — tin-the-tip-and-place strands the core flux on the tip, so the
      pad gets bare solder — and non-conductive residue closes the R4/R6 divider
      leakage question (a 1 % trip shift needs ~1.1 MΩ across the 11.3k leg).
- [ ] 🟡 **99 % IPA + brush + lint-free wipes — verify on shelf BEFORE stage 1.**
      Found missing 2026-08-01: this plan asserted the shiny criterion three times as
      valid *"after the flux is cleaned off"*, but contained **no cleaning step**, had
      **no inspection step at any stage**, and `master-bom.md` listed **no cleaner**.
      The criterion was unreachable as written. Worse with a *no-clean* flux, whose
      cured residue is glossy — so an uncleaned board does not withhold the verdict,
      it returns a **false PASS** over a dull joint. Clean-then-inspect is now an
      explicit per-stage step in §2a. 70 % rubbing alcohol does not substitute.
- [ ] 🔴 **Q1 SOA check — was written as a pre-fab gate, and fab happened without it.**
      `STATUS.md` and `order-list.md` §131-135 both mark the gate-harden design
      *"SOA-gated … BENCH-VALIDATE transient (scope) before fab"*. Soft-start puts
      ½CV² ≈ **0.77 J** through Q1 in its linear region during the ~5–15 ms ramp,
      which must sit inside the IRLB3034's 10 ms SOA. **No scope is owned** (Rigol
      DHO804 deferred to Phase 5) and the documented fallback — a 10/22/47 Ω 2–3 W
      **precharge resistor — does not appear in any ✅ ordered list.**
      Not a soldering blocker; it is a **first-pack-hot-plug** blocker.
      - First power-on is from a current-limited 0.5 A bench supply
        (`pre-power-on-validation.md` §3), which never creates that inrush — this
        defers the risk, it does not clear it.
      - **Owned mitigation:** the Chanzon **1 Ω + 4 Ω** power resistors on the
        bench-gear list. A 2-stage connect through the 4 Ω caps peak inrush near
        4.2 A at 16.8 V and dissipates the 0.77 J in the resistor, not the FET.
        ⚠️ Their wattage rating is **not recorded** — confirm before relying on it.
      - Only a scope measurement actually clears the gate.
- [ ] Confirm the TS-C4's real tip geometry (chisel vs bevel — see §2a). Cosmetic;
      affects presentation angle only.
- [x] ~~Fix `master-bom.md`'s "21 SMD parts all 0603/SOT-23/SOIC"~~ **DONE**
      2026-07-29 — corrected to 34 there, with the L1 caveat (§1).
- [x] ~~Re-label `pre-power-on-validation.md` §9 — the 🔴 is stale.~~ **DONE** — §9 now
      reads "✅ BOTH GAPS CLOSED ON v2 (verified 2026-07-30)" with the original text
      kept beneath it as the record. Verified 2026-07-31.
- [x] ~~Decide socket vs direct-solder for U6/U12 on the logic board.~~ **DECIDED —
      SOCKET.** `order-list.md:80` records **Teensy/Nano sockets (PPTC241 / PPTC151)
      ✅ ORDERED 2026-06-22**. Both modules are debug-swappable; do not solder them
      down. Cut the Teensy's `VUSB`↔`VIN` pad *before* seating it.
- [x] ~~Confirm XT30 quantity (~18 mating pairs).~~ **COUNTED from the board file
      2026-07-31: 16 mating halves needed** — 8 board connectors (J3–J7, J12–J14)
      plus 8 across the four populated buck stations (U1–U4, 2× XT30 each). 18 only
      if U5 is ever fitted. Board side is XT30U-**M**, so the cables carry females.

_Inventory and nets read from the board files 2026-07-29._
