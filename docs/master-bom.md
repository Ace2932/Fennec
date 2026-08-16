# NOVA — Master BOM (all phases)

Single source for parts status across the whole build. Compiled 2026-06-13 · statuses refreshed 2026-07-01 (post board order + Amazon receipt reconciliation).

**Legend:** ✅ owned · 📦 first DigiKey order (received/placed) · 🛒 2nd DigiKey order (✅ placed 2026-06-22) · ⬜ still needed · 🚫 DNP / deferred-populate

Phases (per `hardware/pcb-mods/README.md`): 0 design (closed) · 1 hardware bring-up (current) ·
2 gait/walk · 3 SLAM/Nav · 4 VLA + arm.

## Core compute
| Part | Status | Note |
|---|---|---|
| Jetson Orin Nano Super 8GB | ✅ | MAXN |
| Teensy 4.1 (U6) | ✅ | owned 'with pins' — male headers for socketing included |
| Arduino Nano ×3 | ✅ | 3-pack |
| 128 GB microSD | ✅ | JetPack 6.2.x; NVMe deferred (NAND prices) |

## Power board — `nova_pcb_v6_power_v2` (✅ ORDERED ×5 — JLCPCB 2026-07-01, 4L/2oz/ENIG, one parcel with logic)
| Part | Ref | Status |
|---|---|---|
| Pololu D42V110F7 / D42V110F12 / D24V22F12 / D42V55F12 | U1–U4 | ✅ |
| Pololu D42V55F7 (arm rail) | U5 | 🚫 Phase 4 populate-and-go |
| INA226 module 20A R002 ×4 | U9–U12 | ✅ off-board (4th = L2 rail @0x45, decided 2026-06-30; arm U12-label = Phase-4. **0 spares — buy 1**) |
| 1000µF 25V (FymuSing) ×5 | C1–C5 | ✅ |
| 470µF 25V UPW1E471MPD ×10 | C6/C8/C9 | 📦 |
| 100nF CC0603 ×10 | C7 (+logic U7 decoupling) | 📦 |
| 0603 R-set (10k/100k/4.7k/22k/11.3k/12.1k/470k/1M) | R2–R16 | 📦 |
| IRLB3034 ×5 | Q1 | ✅ |
| BSS138 ×10 | Q2/Q3/Q4 | 📦 |
| LM393 ×10 | U8 | 📦 |
| SRR1260-220M ×10 | L1 | 📦 |
| XT60 (J1), XT30 **×18** | J1 / J3–J7 / J12–**J14** / U1–U5 (2 each) | ✅ |
| JST B3B-XH-A ×10 | J8 (+logic J11) | 📦 |
| IDC BHR-12-VUA ×10 | J20 | 📦 |
| PRPC040 header strip | J2/M1, **`U9`–`U12` (4× 4-pin, INA226 board side)** (+logic J9/J10/JP1) | 📦 own strip covers all of it — but `U9`–`U12` were not named here until 2026-08-16, and they are 16 of the pins the strip has to supply. Also needed on the **module** side: each INA226 breakout takes its own 4-pin male header before it can be dupont'd to the board |
| TB007-508-02BE ×10 (Same Sky, 16A UL/18A IEC) | SW1 | ✅ ordered 2026-06-22 (MKDS 1,5/2 went OOS 17wk → this sub; needs SW1 drill 1.2→1.5mm — done on board) |
| KF301 kit block (SW2) | SW2 | ✅ |
| MRBF-30 fuse ×2 + Blue Sea 5191 block | inline | ✅ ordered 2026-06-12 (verify 5191 = single-MRBF terminal variant) |
| SMBJ8.5A ×10 (leg) + SMBJ13A ×10 (hip/L2) TVS | off-board | 🛒 |
| Balance buzzer ×5 (FLY RC, pre-set 3.3 V/cell) | balance plug | ✅ purchased 2026-05-16 |
| UBEC 5V/5A ×2 (SoloGood) | `J2` | ✅ purchased 2026-05-03. **Unit A measured 4.98 V @ 16.8 V in, 2026-08-08** (pre-power-on §2). Spare untested. ⚠️ **4 wires into a 3-pin header** — the two blacks common at `J2`.2, see order-list |
| **Panel voltmeter ×8 (diymore, 0.28" 2-wire, DC 2.5–30 V)** | **`M1`** | ✅ **owned, purchased 2026-05-03 — was MISSING from this BOM until 2026-08-08.** Only the header strip was listed; the module that plugs into it was never recorded. 2.5–30 V covers 4S `VBAT_PROTECTED` (12.0–16.8 V). **2-wire = self-powered from the measured rail.** `M1`.1 (square pad) = **+/red**, `M1`.2 = **−/black**. ⚠️ No reverse-polarity protection stated by the vendor — the listing's own Q&A asks and is unanswered. Draws ~10–20 mA continuously whenever SW1 is on |
| E-stop (Mxuteuk) + Blue Sea Contura switch | SW1/SW2 wiring | ✅ |

## Logic board — `nova_pcb_v6_logic` (✅ ORDERED ×5 — JLCPCB 2026-07-01, 4L/1oz/HASL)
| Part | Ref | Status |
|---|---|---|
| **SN74LVC125AD** SOIC-14 ×5 | U7 | 🛒 ⚠️ ORDER LVC NOT HC — 5V-tolerant inputs (servo bus is 5V-TTL; HC at 3.3V isn't 5V-tolerant → servo response over-drives input). Same SOIC-14 pinout, VCC 3.3V (max 3.6V). Sch value was stale "74LS125" (5V TTL, wrong for 3.3V). Changed 2026-06-14. |
| R7 = 10kΩ 0603 | R7 | 🛒 ADD — bus idle pull-up (BUS_SIGNAL→+3V3), keeps half-duplex bus defined in TX/RX turnaround. Added 2026-06-14. |
| **2.54 shorting jumper — SPC02SYAN (S9001-ND) ×10** | **`JP1`** | ✅ ordered 2026-06-22 in the same batch as U7 / R1 / FB1 (all since fitted, so the bag arrived). **Was missing from this BOM until 2026-08-09.** `JP1` is a bus-master selector and is **inert without a shunt** — the 3-pin header alone connects nothing. **2–3 = Pattern B (v1 default, Teensy through the `U7` buffer). 1–2 = Pattern A (bench/debug from the Jetson via `J9`).** ⚠️ **No shunt fitted = the servo bus has NO master and nothing talks** — a safe default, but an easy "why is the bus dead" at bring-up |
| Teensy 4.1 socket — PPTC241LFBN-RC ×2 | U6 | 🛒 |
| Arduino Nano socket — PPTC151LFBN-RC ×2 | U12 | 🛒 (Phase 2) |
| R1 = 22Ω 0603 (RC0603FR-0722RL) | R1 | 🛒 ADD to DigiKey — un-DNP'd 2026-06-13 (was open bus) |
| FB1 = ferrite 0603 600Ω@100MHz | FB1 | 🛒 ADD to DigiKey — un-DNP'd 2026-06-13 |
| R2–R6 = 1kΩ 0603 ×5 | R2–R6 | 🛒 ADD — OLED SPI series protection (5V Nano logic → SSD1331), added 2026-06-14 |
| 100nF decoupling @ U7 (C1) | U7 | ✅ placed + routed 2026-06-14 |
| +3V3 source (Teensy T3V3O→+3V3) | U6 | ✅ fixed 2026-06-13 (was unsourced = dead board) |
| FE-URT-1 USB-TTL adapter | J9 mate | ✅ owned (DIYmall, 2026-05-03) |
| 100nF decoupling @ U7 | — | ✅ part owned; ADD footprint when routing |
| J21 = Conn_01x02 pin header (PinHeader_1x02_P2.54mm_Vertical) | J21 | 🛒 e-stop 2nd-NC-contact sense → Teensy pin 5 (added 2026-06-14). Use PRPC040 strip already in order; mate = dupont/JST to e-stop. |
| **Interboard J20↔J20 ribbon** — **`IDSD-06-D-09.00-T-G`** (Samtec, 2×6 IDC socket both ends, 9" ) | J20 | ✅ **IN HAND 2026-08-09** (ordered 2026-06-22, order-list §80 — this row still said 🛒). ⚠️ Both J20s are MALE box headers; without this cable the boards are electrically disconnected (I2C / servo-bus / safety lines). **It is a finished assembly — nothing to wire or crimp, it plugs on.** Do not confuse with the board-side header below. |
| **`BHR-12-VUA` ×10 — the J20 BOARD header** | J20, **both boards** | 📦 owned. 12-way shrouded IDC **box header**, 2 rows of 6 pins out the bottom, notch in one shroud wall. **This is the part that gets soldered**; the IDSD above is the cable that links the two. All 12 pins are identical metal, so a 180° rotation seats perfectly and reverses every rail — **orientation is carried ONLY by the shroud notch. Match it to the silk; pin 1 is then the rounded-rect pad** (power (151.00, 128.89) · logic (140.00, 124.00)). |

## Phase 2 — gait/walk + status polish
| Part | Status |
|---|---|
| Gait controller / IK / URDF | software |
| WS2812B strip | ✅ owned (ALITOVE 100pc) |
| SSD1331 OLED | ✅ owned (HiLetgo, 7-pin, VCC 2.8-5.5V). Board reworked 2026-06-14 for it: J10.2→V5_AUX (5V), CS/RST swapped to match module pin order, 5× 1k series Rs (R2-R6) on SPI/control. ALT if logic level still flaky: Adafruit 684 (DK 684-ND, has 74LVC245+boost) — 5V VIN, wire 7 of its pins to J10. |

## Phase 3 — SLAM / Nav
| Part | Status |
|---|---|
| RealSense D456, Unitree L2, GbE switch, Cat6 ×2 | ✅ |
| POINT-LIO / Nav2 / robot_localization EKF | software |

## Phase 4 — VLA + arm
| Part | Status |
|---|---|
| Arm STS3215 ×6 | ✅ shelf |
| D42V55F7 arm buck | 🚫 populate-and-go |
| VLA model | software/model |

## Servos / mechanical
| Part | Status |
|---|---|
| Leg STS3215 ×12 active | ⬜ verify count; top-up 2-3 if short |
| LiPo: Ovonic 4S 6000mAh 120C ×2 | ✅ owned (note: 6000mAh/120C, not 4000mAh) |
| PA6-CF filament | ✅ |
| **TPU 95A filament** | ✅ **on hand — confirmed 2026-07-31 by having printed with it** (foot shoes ×5, knee_bumper ×5, skid_rail ×2, cable_clip ×27). Was contradicted across three docs: `work-schedule.md` said ✅, `checklists/print-batch.md` §0 had it as an open question, and this table listed only PA6-CF. **~101 g of the ~106 g TPU set is now printed; ~5 g remains** — grommets only (`grommet_insert` ×6 on hold for LA-25, `case_slot_grommet` ×1, `lead_notch_grommet` ×2). See `print-batch.md` §1b. ⚠️ Updated 2026-08-01: this row previously read *"~73 g printed, ~29 g remains (cable_clip ×24 + grommets)"* — stale on both counts once the clips were printed, and the ×24 was itself superseded (see below). External spool only, **AMS will not feed TPU** |
| PETG-CF filament | ⬜ **unknown** — `print-batch.md` §0 still asks "PETG-CF spool on hand?". Needed for `riser_bay` / `floor_plate` / `head_ear`; the fallback is all-PA6 with warp risk on the 127 mm riser lid |

## Fasteners — screws + sourcing notes (added 2026-08-02)

**Inserts and the M3 screw lengths are in §"Heat-set inserts" above** — that section is
the buy list and is current with #255's two-insert split (OD 4.6×5.7 everywhere, slim
OD 4.0×6.0 for the HFE block only). This section covers what it does not: the **disc-screw
and M2 case-screw** families, the ASINs actually ordered, and the traps that make a wrong
purchase look right — including the two that already caught this build (M2.5-for-M3 discs,
and M2×22 case screws into a 7 mm blind column).

None of this existed before today. `master-bom.md` calls itself *"Single source for parts
status across the whole build"* and carried two fastener rows; everything real lived in
`fastener-schedule.md` + `BOM.md` + `order-list.md`. **The doc you check before ordering
was the one place the fasteners weren't.**

### ✅ ORDERED 2026-08-03 — the leg fastener set is closed

Every length below traces to a measurement, not an assumption. Buttons where a counterbore
wants a low head; socket cap where the seat is a flat-bottomed bore; countersunk where the
seat is a cone.

| item | ASIN | for |
|---|---|---|
| M3×5 button ×100 | `B08H2FN2FP` | horn → HFE (16) — owned kit starts at 6 |
| M3×8 button ×100 | `B08H2HTTRT` | wheel → HFE/KFE (32) — flush in #263's Ø6.0 c'bore |
| M3×14 button ×100 | `B08H2HQ3VZ` | wheel → HAA (16) — owned kit has no 14 |
| M3×16 socket cap ×100 | `B089MDDJMZ` | HFE block retention (8) — ⚠️ M3×20 bottoms |
| M3×20 socket cap ×25 | ⬜ *source it* | `oled_tray` → rear shoulder deck (4) — new 2026-08-10 (#35). Tray is 16.0 mm thick at the bolt (LEG_H 10.5 + PLATE_T 5.5) into the M3×3.8 short insert on line 259 — which is really **4.0 long** (ruthex RX-M3Sx4.0) in a 4.2 pocket. M3×20 protrudes exactly 20−16.0 = **4.0**, i.e. the FULL insert length, tip landing 0.2 above the pocket floor. M3×16 does not reach; M3×22 bottoms. ⚠️ The "M3×20 bottoms" warning on the line above is about the **HFE block**, a different joint — it does not apply here. A Ø6.0×4.0 counterbore would let the M3×16 above serve instead, but it puts ~113 mm² of bridged ceiling into a part that currently measures 0.0 mm² unsupported
| M3×10 CSK ×100 | `B0CQ4Z3DTX` | L2→adapter (4) + battery pocket (6) |
| M3×14 CSK ×100 | `B0CQ4YH87R` | shoulder flange feet → trunk floor (4) |
| Nylon M3 kit 330 pc | `B0DKND2824` | breakaway fuses — ×12 (10) and ×10 (10) |
| M2 CSK self-tap kit ×2 | `B09DB5SMCZ` | 60× M2×8 + 60× M2×12 body-mount |
| uxcell M3 OD 4.0 × **L 6.0** ×50 | **`B07R9SP532`** | slim insert, HFE block (8) — ✅ **RECEIVED 2026-08-08** (ordered 08-03; the table said "arrives Fri 08-07", it landed Sat 08-08). The right part, full 75.4 mm² / SF 2.4–3.4. ⚠️ **Check the thread on arrival** — OD 4.0 is the standard *M2.5* OD, so a substitution at this OD will not take an M3×16 |
| uxcell M3 OD 4.0 × L 4.0 ×50 | `B07LBQS9W3` | ✅ **RECEIVED 2026-08-04.** No longer struck through — it has a real job. 2 mm short → 50.3 mm², SF 1.6–2.3, so **not** the install part, but it IS **the one to burn on the pull test**: if the SHORT insert holds 13.5 kg the L6.0 (1.5× the area) is comfortable. Sacrificial article = the one you don't need |

⚠️ **Two gates before any of it enters a servo.**

1. **Pitch check the M2 self-tappers** — lay one beside a factory screw. Factory is **6 crests
   over 7 mm** (≈1.2 mm pitch). A different pitch cuts a second thread in the plastic column
   and cannot be undone. Compare on the bench; do **not** test by threading one in.
2. **Bag and label the M2×8 and M2×12 separately.** That kit is mostly 14–25 mm in the same
   head and finish, and **anything over 12 bottoms** in the 7 mm blind column.

✅ **M3 nyloc — ORDERED 2026-08-06, arrives Thu 2026-08-07** (shoulder flange feet ×4, CR-8 #2):
Vifmy 230 pc M3-0.5 nylon-insert, 304 SS A2-70, `B0CPJF21KP`, $10.76. Was the last open
fastener line — the owned kit has 140 *plain* M3 nuts, not nylon-insert.

### ✅ Owned M3 inventory — CONTENTS RECORDED 2026-08-03

Recorded because the un-recorded version of this is what produced the false *"M3×14 is
already owned"* claim below, and nearly left the HFE block with no screw.

**M3/M4/M5/M6 stainless hex kit** (`BOM.md`:174, ✅ owned) — all **socket head**:

| | lengths | qty each |
|---|---|---|
| **M3** | **6 · 8 · 10 · 12 mm** | **35** |
| M4 | 8 · 10 · 16 · 20 | 25 |
| M5 | 10 · 16 · 20 · 30 | 6–15 |
| M6 | 16 · 25 · 35 | 6–8 |

Plus 140 M3 nuts, 140 flat washers, 140 spring washers.

**What it closes:** `shoulder_plate`→deck ×16 (M3×6) · `knee_arm`→femur shelf ×16 (M3×8,
and socket head is what that counterbore expects) · riser→shoulder flange ×4 (M3×12) ·
ears→head pad ×4 (M3×10).

⚠️ **The four real gaps: no M3×5, no M3×14, no M3×16, and no countersunk at all.** Those map
exactly onto horn→HFE (needs 5), wheel→HAA (needs 14), HFE-block retention (needs 16, and
M3×20 bottoms), and the chassis CSK positions.

⚠️ Quantity: 35 each of ×6 and ×8 against a total demand of 48 each. Fine if the 32 horn and
32 wheel screws come from bought button-head packs — button is wanted at the wheel positions
anyway, since #263's Ø6.0 counterbores leave a socket head standing 1.4 mm proud.

**Fgruh 1220 pc M3 kit** — also owned, contents NOT recorded. Worth listing the same way
before the next order.

### 🔴 leg servo disc screws — the thread is **M3**, not M2.5 (corrected 2026-08-02, #263)
**The M2.5 set below was ordered AND received, and it does not fit.** The FEETECH STS3215 spec
sheet gives the disc threads as **M3**; M2.5 was this project's own inference, and the note that
"proved" it (`dimensions.md` note 4) misread a ∅2.5 modeled hole as "M2.5 clearance" — but M2.5
clearance is ∅2.9, and ∅2.5 is exactly the M3 tap drill. See that note for the full retraction.

**The lengths were right and carry straight over** — grip is set by printed geometry, not thread
diameter — so the buy is the same 5/6/8/14 in M3. Holes went 2.9 → **3.4** and the disc-facing
head c'bores 5.2 → **6.0** in `leg_v6_common.scad`; `M25_CLEAR` was deleted.

⚠️ **FIRST-ARTICLE, 10 seconds, do it before ordering more:** hand-thread an M3 screw into a
spare disc. The spec sheet and the STEP are both inference; the servo in your hand is not.

**Still all BUTTON head**, and now for a stronger reason: an M3 SHCS head is ∅5.5 × 3.0 tall and
would stand ~1.4 mm proud of the 1.6 mm c'bore, worse than M2.5's 0.9. An M3 button is
∅5.7 × 1.65 → **~0.05 mm, effectively flush**, and ∅5.7 still clears the new 6.0 c'bore. That is
why 6.0 was chosen over the 5.5 an SHCS alone would need.

⚠️ **Do not buy an M3 assortment kit for this.** Same trap as M2.5: kits run 4/6/8/10/12/16/20
— **no ×5, no ×14**, and neither is substitutable (a ×6 drives 3.2 mm into a 3.05 mm horn disc
and bottoms; a ×16 drives 3.4 mm into a 2.1 mm wheel disc and jacks the boss). The owned
M3/M4/M5/M6 stainless kit is 6/8/10/12 only — it covers ×6 and ×8, **not ×5 or ×14.**
Single-length packs for those two.

| Screw | Qty | Joint | Status |
|---|---|---|---|
| **M3×5** button | 16 | horn → HFE (thin LA-7 backing) | ⬜ **ORDER** — no ×5 in the owned kit |
| **M3×6** button | 32 | horn → HAA + KFE (`shoulder_plate` / `knee_arm`) | ✅ owned (kit has ×6) — verify button vs SHCS head height |
| **M3×8** button | 32 | wheel → HFE + KFE (⚠ only ~0.75 mm disc engagement — tightest joint) | ✅ owned (kit has ×8) — ⚠️ **must be button**, an SHCS head stands 1.4 mm proud |
| **M3×14** button | 16 | wheel → HAA (shoulder's long boss reach) | ⬜ **ORDER** — `B08H2HQ3VZ`, no ×14 in the owned kit |

**Superseded M2.5 order** (111-2168015-0136233, $37.26, received 2026-08-02): ×100 M2.5×5,
×105 M2.5×6, ×100 M2.5×8, ×100 M2.5×14 — iexcell `B0DLKG6JK6` · Sutemribor `B0DJKVZ4P2` ·
iexcell `B0DLKC64NP` · iexcell `B0DLKBDMSB`. ✅ **RETURNED 2026-08-03 — the $37 is recovered.** Nothing to keep, nothing to scrap-hunt back into the build.

### M2
| Screw | Qty | For | Status |
|---|---|---|---|
| **M2×9 self-tap, COUNTERSUNK** | 40 | servo BODY-mount — these do NOT hold the case shut; loaded in SHEAR (~30 N/screw at stall), so engagement depth is not critical. HAA + KFE + HFE-near pair. 🔴 **WAS M2×22 — that drives 13 mm into the servo.** Column measured **7.0 mm blind** 2026-08-02 (19.9 was back-solved). Stock is a 7 mm PAN-head PA2.0 self-tapper; buy CSK, the printed floor has a Ø4.6→2.3 cone | ⬜ ORDER |
| **M2×13 self-tap, COUNTERSUNK** | 8 | HFE-far pair only (femur LA-6 ramp, floor 6.525). Body-mount, shear-loaded. 🔴 **WAS M2×25.** Max is floor + 7.0 column = **13.5 mm**; M2×14 bottoms by 0.5 | ⬜ ORDER |
| M2×8 SHCS | 12 | control_pod 4 · deck-tie 4 · clamp bar 4 | ⬜ ORDER — was 14; the 2 "OLED foot" screws went with `oled_mount`, DELETED 2026-08-10 (#35) |
| M2×6 SHCS | 4 | SSD1331 → `oled_tray` | ⬜ ORDER. **×6 is correct and DERIVED, not a guess:** the screw enters at the PCB back and crosses the calipered glass-front→PCB-back depth of **3.4** (dimensions.md:561) before reaching the M2×4 insert, so it engages 6−3.4 = **2.6 mm (1.30×D)**. M2×8 would engage 4.6 into a 4.0 bore and **bottoms out**. ⚠️ The **"+ M2 nut"** this line used to carry was wrong — the mount uses M2×4 heat-set INSERTS (line below), not nuts. |

### ⚠️ Two errors found in `fastener-schedule.md`'s purchase summary (2026-08-02)
Both would have produced a wrong order, and both contradict that document's own detail table.

1. **"×4 M3×16 (bracket→deck)" is wrong — it is M3×8.** `neck_bracket.scad` says M3×8 in two
   places (lines 28, 61) with `BASE_T = 4`, and the schedule's own row 23 also says M3×8.
   4 mm base + 3.8 mm insert = 7.8 mm of usable depth; an M3×16 has nowhere to go and would
   bottom on the 2.3 mm deck floor or split it.
2. **"M3 nyloc ×4 (bracket→deck)" is obsolete.** The NO-DRILL fix of 2026-07-10 replaced
   drill-at-assembly + nyloc with pressed M3×3.8 heat-sets. Only the 4 shoulder-flange-foot
   nylocs remain.

## Harness + assembly consumables (mostly Amazon — NOT yet bought)
The off-board side is 25+ wired connections; this category was unspeced until 2026-06-13.
| Part | For | Status |
|---|---|---|
| Silicone wire 12 AWG (TUOFENG red/black 20ft) | battery / fuse / switch (~15-18 A) | ✅ ordered 2026-06-13 |
| Silicone wire 18 AWG stranded | servo-rail injection (7.5-8 A) | ✅ owned (TUOFENG) — 18AWG OK at 8A |
| Wire 22 AWG solid | I2C / EN / sense | ✅ owned (TUOFENG) — solid, solder don't crimp |
| Ring terminals 12-10 AWG / 5/16" (M8) | MRBF fuse-block wiring | ✅ received (AIRIC 50pc; crimp w/ WGGE yellow station) |
| Heat-shrink assortment | every XT / TVS / fuse joint | ✅ owned (Ginsco 580pc) |
| M3 standoffs ~20 mm | mezzanine board-to-board | ✅ received (PATIKIL brass M3×20 ×50; safe on all 4 holes — 7 mm copper keepout, **verified 2026-07-31 against the actual pour**: 196 sample points inside the keepouts, zero poured copper, closest fill vertex 3.483 mm). ⚠️ **No flat washer under these** — the clear circle is **6.97 mm** and a DIN125 M3 washer is **7.0 mm OD**, so it lands on the pour edge (H1 = `BATT_NEG`) with only solder mask between. Standoff hex is 6.35 mm across corners = ~0.3 mm clearance, fine bare. Nylon or ≤6.9 mm OD if you must |
| M3 screws/nuts/washers | board → chassis | ✅ owned (Fgruh 1220pc) |
| M3 standoffs 20 mm | power board → floor plate (bucks + de-cased switch live underneath — chassis README §9) | ✅ use the M3×20 ×50 already received (line 97). Corrected 16→20mm 2026-07-09: the ordered Ø10×17 C1–C5 caps need the 20mm gap to clear the floor (check_fit case 11). |
| Right-angle USB-C (USB 3.x) cable | D456 → Jetson (straight plug doesn't fit the periscope bracket gap) | 🛒 order |
| Velcro strap ~300 mm | battery pocket rear-corner fence | 🛒 order (or cut from owned roll) |
| JST-XH plug + crimps | board ↔ servo-bus pigtail | ✅ owned (PEBA crimp+connector kit) |
| Servo-bus extension cables | leg runs > stock cable length | 1st Amazon order CANCELLED 2026-07-11 (seller couldn't fulfill — 2nd cable order to fall through) → ✅ **RE-ORDERED 2026-07-11: 2× waveshare 5264-3PIN kit** (each 3× 300mm + 3× 900mm → **6× 300 + 6× 900 total**, ~$20, Prime, arr ~Jul 13). 2 kits because 1 kit's 3× 900 is short of the **4 long runs** (chassis + 3 between-leg links). Make-your-own ruled out — the owned PEBA crimp kit is **JST-XH**, not the servo's **5264** (different housing/latch, won't reliably mate). Still verify the real routed lengths on receipt (#55). Plan (unchanged when they arrive): 900s = chassis run + 3 between-leg links; 300s + the 12 stock in-box servo cables = within-leg links + VCC-pull donors (see wiring README dual-voltage recipe). Top-up trigger: count in-box cables at servo verify — if <12 or pull-mods eat spares, add the mixed 3×300+3×900 pack |

## Heat-set inserts + leg screws — status refreshed 2026-08-02

🔴 **Still to order, and two of them gate the next print's assembly:** the **slim 4.0 OD × 6.0**
insert (8 for the HFE block — did not exist until #255, so it missed the order that went out the
same day) and the **M3×16 / M3×8 / M3×6 SHCS**. ⚠️ **Buy inserts by part code, not brand** —
`B0CDH36ZMX` is "ruthex M3 **VORON** RX-M3x5x4", **OD 5.0**, same price, one row from the right
part in the same search.

No insert line existed in this BOM at all until now, and the only count anywhere
(`docs/fastener-schedule.md` purchase summary) covered the chassis and omitted
every leg and shoulder insert — 16 documented against **~68** the design
actually consumes.

| Part | Qty | For | Status |
|---|---|---|---|
| **M3 heat-set, 4.6 mm OD × 5.7** (Ruthex or equivalent) | **100** | femur→knee_arm 16 · shoulder→plate 16 · shoulder→trunk 16 · chassis 12 = ~60 + spares. **`femur_?.stl` is already printed with the Ø4.0 bore this insert wants** | ✅ **ORDERED 2026-08-02** — ruthex `B08BCRZZS3`, 100 pc |
| **M3 heat-set, 4.0 mm OD × 6.0** (slim) | **25** | **HFE block retention only** (8 needed). A 4.6 insert cannot travel the 4.4 mm mortise slot to reach its bore — see `fastener-schedule.md`. ✅ **THE L6.0 PART EXISTS — found 2026-08-03: uxcell `B07R9SP532`, "M3 x 6mm(L) x 4mm(OD)", M3×0.5, 50 pcs.** The earlier "no L6.0 exists to buy" was a search failure, not a fact. Full 6.0 gives **75.4 mm², SF 2.4–3.4** — the number the design always assumed. | ✅ **RECEIVED 2026-08-08 (`B07R9SP532`).** ⬜ **THREAD-CHECK BEFORE USE — see below.** `B07LBQS9W3` (received 08-04) is the same OD but only **L 4.0** → 50.3 mm², SF 1.6–2.3: a usable fallback, not the right part. ⚠️ 4.0 OD is NON-STANDARD for M3 and IS the standard M2.5 OD — **check the thread on arrival.** |
| **M3×8 SHCS** | **25** | knee_arm → femur shelf (16 needed). ⚠️ NOT M3×10 — that bottoms in the 6.2 mm bore | ✅ **COVERED** — owned kit has 35× M3×8 socket head; the 32 *wheel* screws come from the ordered M3×8 **button** pack `B08H2HTTRT` |
| **M3×6 SHCS** | **25** | shoulder_plate → deck (16 needed). ⚠️ NOT M3×8 — bottoms by 0.42 mm | ✅ **COVERED** — owned kit has 35× M3×6 socket head (deck job needs 16); horn positions have no counterbore so socket head serves |
| **M3×16 SHCS** | **20** | HFE block retention (8 needed). Engages **5.2 mm of the 6.0 insert = 1.73×D**; M3×20 **bottoms out** in the blind pocket | ✅ **ORDERED 2026-08-03** — iexcell `B089MDDJMZ` ×100, socket cap. ⚠️ NOT the flat-head M3×16 (`B0CR6FZBYB`) — the block's seat is a cylindrical Ø6.0 c'bore and needs a flat-bottomed head |
| M3×3.8 short insert | 10 | neck bracket → shoulder deck front (4) · **`oled_tray` → shoulder deck REAR (4), added 2026-08-10 #35** = 8 of 10 | ✅ **ORDERED 2026-08-02** — ruthex `B09ZHSGHXD` (RX-M3Sx4.0; ruthex's short is **4.0**, docs say 3.8, pockets are 4.2 deep so it fits) |
| M2×4 insert | 20 | pod, deck-tie, clamp bar, `oled_tray` (4) | ✅ **ORDERED 2026-08-02** — ruthex `B088QJG676`, 70 pc |

⚠️ **The owned HANGLIFE 345-pc assortment is M3 in D5 ONLY** — confirmed off the box
2026-08-02. This paragraph previously said it carried **D4×L3 and D4×L4**; it does not,
and that mattered because the slim-insert fallback below was written assuming a D4 was
already on the shelf. Its D5 will seat in a Ø4.0 bore (0.5 mm/side, ~1.7× the intended
interference) — enough to build the first leg, not the robot — and it is **useless for the
HFE block**, whose bore is Ø3.5: a D5 there is 1.5 mm diametral against a **1.95 mm mortise
roof** and will split it. Do not try.

⚠️ **The ruthex M3 Short already on order is NOT the slim insert either.** `RX-M3Sx4.0` is
short in *length*; ruthex's own comparison table gives the recommended hole for **every M3
in their range as 4.0 mm**, i.e. OD 4.6. Same OD as the standard, so it has the identical
delivery problem — a 4.6 cannot travel the 4.4 mm mortise slot.

🔴 **BOTH SLIM INSERTS ARE IN HAND (2026-08-04 L4.0, 2026-08-08 L6.0) — AND NEITHER IS CLEARED FOR USE UNTIL THE THREAD IS CHECKED.**

**Why this specific part and not the others.** `check_fit.py:1155` carries the standard
insert ODs: `{"M2": 3.5, "M2.5": 4.0, "M3": 4.6, "M4": 6.0}`. **OD 4.0 IS the standard M2.5
OD** — M3's is 4.6. These are deliberately non-standard slim inserts, chosen because a 4.6
cannot travel the block's 4.4 mm mortise slot. The consequence is that a mislabelled or
substituted part at this OD is *most likely M2.5-threaded*, and it looks completely correct
in the bag. This project has already paid for exactly this confusion once (the Ø2.5 =
M3-tap-drill misread, $37 of M2.5 screws).

- [ ] **Run an M3 screw into one of EACH by hand before pressing any.** Two minutes; it is
      the only check that distinguishes them.

🔴 **DO NOT MIX THESE WITH THE Ø4.0 BORES ELSEWHERE.** `leg_v6/README.md` §4: *"the slim one
is NOT a substitute in a Ø4.0 bore, where it would have zero interference."* Every other
insert site — femur→knee_arm, shoulder→plate, shoulder→trunk, neck bracket, and `oled_tray` —
takes the **4.6 OD × 5.7** ruthex (`B08BCRZZS3`). A 4.0 OD insert dropped into a Ø4.0 bore
has nothing to melt into and pulls straight back out. With ~100 slim inserts now on the
bench and Ø4.0 bores all over the leg, this is a live mixing risk, not a theoretical one.

⚠️ **THE INSERTS ARRIVING DOES NOT UNBLOCK THE HFE BLOCK — the screws are still missing.**
Retention is **M3×16 SHCS ×2 per block** (`fastener-schedule.md`:61). The measured
head-seat-to-pocket-bottom span is **16.8 mm** (`check_fit.py fastener_span_checks()`, the
gate that caught the M3×22-bottoms-out error) — so M3×16 fits, **M3×20 bottoms**. Owned M3 is
**6 · 8 · 10 · 12 only** (§Owned M3 inventory), and M3×16 is listed there as one of the four
real gaps. `B089MDDJMZ` is identified but **not yet ordered**.

✅ **SLIM INSERT SOURCED 2026-08-02 — uxcell `B07LBQS9W3`, $6.69/50.** Its spec line is
unambiguous, which matters here: *"Thread Size: M3; Pitch: 0.5mm; **Length: 4mm**; **Outer
Diameter: 4mm**"*. That is the **4.0 × 4** fallback this table already documents at
SF ≈ 1.6–2.3 — 8 needed, 50 in the pack.

⚠️ **Buy this one by its spelled-out spec, not by an `M3xAxB` code.** The convention is not
stable across vendors: ruthex's `RX-M3x5x4` is **OD 5.0 × L 4.0**, while other listings use
`M3 × length × OD` for the same string. Two of the three candidates found were ambiguous;
only the uxcell listing states which number is which.

**Pair it with M3×14 — or M3×16, which you are buying anyway.** ⚠️ **CORRECTED 2026-08-03: M3×14 is NOT owned.** See §"Owned M3 inventory" — the stainless kit is M3 in 6/8/10/12 only. Either length works here because engagement is capped by the 4.0 mm insert, so M3×16 is the simpler answer; it just runs 1.7 mm into the empty bore below. M3×16 is sized for the 6.0 mm
insert of the design case. Against a 4.0 mm insert the engagement is capped by the insert,
so the longer screw buys nothing and just runs into the 2.5 mm of empty bore below it. The
full-strength **4.0 OD × 6.0** is still worth ordering if it can be found (π·D·L = 75 mm²
vs 50), but the L4 route needs **no other purchase**.

## Soldering / tools — verify on shelf
| Item | Status |
|---|---|
| Pinecil V2 iron | ✅ — **what matters is supply VOLTAGE, not USB vs barrel.** The element is resistive, so power goes as V²: a 9–15 V brick delivers a fraction of the 60–88 W the plane-tied pads need. Two adequate supplies owned, see the two rows below |
| ↳ Anker Nano II 65 W GaN (USB-C) | ✅ owned (May 2026) — negotiates **20 V / 3.25 A = 65 W**, inside the assumed band. Fine for every stage except the plane-tied joints at 4, 7 and 8. Needs a PD-capable C-to-C cable rated ≥3.25 A, not a charge-only lead |
| ↳ Kungber 30 V/10 A bench supply | ✅ owned — **preferred for the plane-tied joints at stages 4, 7 and 8** (L1 and the 14 A pads). Set **exactly 24.0 V** into the DC 5525 barrel: 24² / 20² ≈ **1.44×** the power of the 20 V PD path, for free. ⚠️ **24 V IS the Pinecil V2's DC max** (barrel is 12–24 V, 24 V/5 A) — this is a 30 V supply, so dial it down and confirm on the display before plugging the iron in, and set the current limit **≥4 A** (88 W = 24 V @ 3.66 A) so it cannot fold back into CC mid-joint |
| TS100/Pinecil tip kit (6-pack) | ✅ owned (LUMINZENLUX) — **TS-C4** ≈4 mm bevel + **TS-D24** ≈2.4 mm chisel + TS-K knife + TS-ILS + TS-J02 + **threaded insert adapter**. TS-C4 is the one for the 14 A plane-tied pads; the insert adapter covers the M3 heat-sets in `checklists/print-batch.md`. **Tip AND temperature per stage: `hardware/pcb-mods/BUILD_PLAN.md` §2a** (also has the Pinecil V2 supply/IronOS setup). ⚠️ "≈4 mm bevel" is this doc's own label — in usual TS100 naming a `C` tip is a *chisel* and `BC` is the bevel; confirm by eye before stage 4. Fattest tip either way |
| Preheat — IR station | 🚫 **DO NOT BUY — the conditional is CLOSED, not deferred. Bench test RUN 2026-08-01 and PASSED.** `U1.4` (10 A) wet in ~2 s with solder through to the far face; `Q1.3` (**14 A GND inject — the worst THT pad on the board**) went easy and came out **shiny on both faces**, i.e. the barrel wicked. Setup that achieved it: **TS-C4, Kungber at 24.0 V (~88 W), tip 400 °C, Sn63Pb37 1 mm** — heat the pad ~2 s, then feed into the tip/pad junction. Consequence: if the 14 A GND inject goes in seconds, every XT30/XT60 and `SW1.2` is the same or easier — **stop treating the high-current THT as the risk**. ⚠️ The one joint this did **not** model is **`L1` (stage 4)**: SMD, plane-tied on *both* sides, so there is no barrel and "solder on the far face" does not apply — it is a fillet against a plane sinking heat from underneath as well as laterally. If it fights, the answer is the **420 °C boost held a few seconds, not a purchase**. *(Kept for the record — the spec that would have applied: IR/ceramic, ≥120×120 mm, 50–350 °C closed-loop; candidate YIHUA 853A ~$85–95. Must be IR, never a contact plate — power_v2 is 112×90 mm with both faces populated (35 F.Cu / 26 B.Cu), so a flat plate only serves a face that is still bare: true through stage 4, false at stages 7–8. MHP30/MHP50 far too small regardless.)* |
| Hot air rework station | ⬜ **none owned. Not a preheat substitute** — hot air is localised and fights the same plane conduction that makes those pads hard; it does not replace a bulk soak. Worth owning on its own merits: candidate **YIHUA 8786D** 2-in-1, ~$70. Motivated by **stage 3** (U8 SOIC-8 / U7 SOIC-14 — bridges and lifts, where wick + a THT-only sucker is thin cover) and by **harness dress** (heatshrink over 24 connector ends + TPU strain reliefs). Its bundled ~60 W iron is a downgrade from the Pinecil at 24 V — do not count it as capability |
| Solder — **Sn63Pb37, 1 mm, 1.8 % flux core** | ✅ **CONFIRMED in hand 2026-08-01.** Leaded, as recommended → **melts 183 °C** (SAC305 is 217–220), so **no +30 °C shift**: every *leaded* setpoint in `hardware/pcb-mods/BUILD_PLAN.md` §2a is the live one and the bracketed lead-free numbers do not apply. Logic board is HASL-lead so its pads were already tin-lead; power board is ENIG and takes either. **Eutectic ⇒ no plastic range ⇒ a correct joint is SHINY** — dull/grainy after the flux is cleaned off is a *defect signature* (moved while freezing, or heat-starved), not a finish preference. Do not carry over the SAC305 habit where dull is legitimate. ⚠️ **Diameter is 1 mm, not the 0.6–0.8 mm this row used to specify.** ~2.8× the solder per mm of feed: **helps** at stages 4/7/8 (plane-tied pads — the difficulty there is delivering mass and heat before dwell cooks the laminate), **hinders** at stages 1/3 (0603 pads are ~0.8 mm; feeding 1 mm wire over-delivers and bridges). Fix is technique, not a second spool — **tin the tip and place** on the 0603s instead of feeding wire, and keep U7/U8 to flux + drag/wick. 1.8 % rosin core is standard but **flashes off fast at 380–400 °C**, so the separate flux below is mandatory at stages 4/7/8, not optional — core flux alone is gone before the joint wets and it reads as "the plane is winning" when it is flux starvation |
| Flux — **BEEYUIHF, lead-free / no-clean / non-conductive / "fast climbing"** | ✅ owned. Spec confirmed 2026-08-01 (label claims, not a datasheet — form/volume/IPC classification unrecorded). **"Lead-free" does NOT mean incompatible with Sn63Pb37** — it describes the *flux*, formulated to stay active up to SAC305's 217–220 °C. Leaded joints happen ~35 °C cooler, so it is over-specified, never under-. Activation is ~150–200 °C; every stage here runs a 320–400 °C tip, so it is comfortably spent **in the joint**. **"Non-conductive + no-clean" closes the R4/R6 leakage question**: to shift the 11.3k/12.1k trip divider 1 % you need ~1.1 MΩ across a leg, and cured no-clean residue sits orders above that. ⚠️ **It does NOT close the inspection question — it opens one.** Cured no-clean residue is **glossy**, and the correctness criterion for eutectic solder is **shiny**, so an uncleaned dull/grainy joint reads as a *pass*. Skipping the clean does not make the verdict unavailable, it makes it **wrong in the PASS direction**. See `hardware/pcb-mods/BUILD_PLAN.md` §2a — clean, *then* judge. ⚠️ Second-order: a lead-free-rated flux run at leaded temps leaves **peripheral** residue (squeezed outside the joint, only ever 60–100 °C) less fully spent than the flux inside it. No-clean is only inert once heat-activated. On a machine that vibrates and collects dust, wipe it |
| **Flux remover — MG Chemicals 4140 aerosol, 400 g** | 🛒 **ORDERED 2026-08-02.** The upgrade over plain IPA is chemistry, not purity: our flux is **no-clean**, the class IPA handles worst, and IPA only partially dissolves it — the resin redeposits as a **white haze**, which reads as *dull* and produces a **false FAIL** exactly mirroring the uncleaned **false PASS**. 4140 is rated for *"rosin, non-rosin and no clean"* and is *"safe on plastic components"* (decides it — stage 10 has Teensy/Nano/INA modules and the OLED window). The active co-solvent is **ethyl acetate**; that one ingredient is the whole difference from straight IPA. Aerosol + straw **flushes** residue off the board edge rather than redistributing it, which is what the old blot step existed to work around. Procedure: `hardware/pcb-mods/BUILD_PLAN.md` §2a |
| **99 % IPA (NANOSKIN 99.9 %, 32 oz) + stiff brush + lint-free wipes** | 🛒 **ORDERED 2026-08-02** — kept, but it is **not** the board cleaner any more. General prep, tool wiping, and the printer's PEI plate. 99 %, **not 70 %**: the 30 % water dries slowly and leaves its own residue on the high-Z nets (`R4` 11.3k / `R6` 12.1k trip divider). If it is ever the fallback on a board, wick it — flood → brush → **blot lint-free** → repeat |
| Solder wick (2-3mm braid) | ✅ received (Lesnow) — SMD bridge cleanup (sucker owned, but it's THT-only) |
| Solder sucker | ✅ owned — THT desolder |
| Crimpers | ✅ WGGE WG-015 (12-10 insulated lugs) · iCrimp (23-10 ferrules) · PEBA (dupont/JST) |
| USB micro-B cable | ✅ owned (USC) |
| Reflow hotplate + paste | 🚫 SKIP — **34** SMD parts across both boards (24 power_v2 + 10 logic, counted from the `.kicad_pcb` files 2026-07-29, was written as "21 all 0603/SOT-23/SOIC"). Mostly 0603, but **not all small**: L1 is `L_12x12mm_H8mm`, a 12×12 power inductor plane-tied both sides, plus 2 SOIC (U8-8, U7-14). Skip still correct — hand-solder, no stencil, half-THT board — but L1 is the hardest joint on either board, so it is sequenced last of the SMD (`hardware/pcb-mods/BUILD_PLAN.md` §3 stage 4) |

## Bench / bring-up gear (Amazon — separate from robot BOM)
Kungber 30V/10A supply · FNIRSI LCR-P1 tester · KeeYees logic analyzer · Chanzon 1Ω+4Ω
power resistors · Etekcity 800 IR gun. Scope (Rigol DHO804) deferred to Phase-5 servo testing.

## Remaining gaps — refreshed 2026-07-01 (post board order)
Electronics DONE: both DigiKey orders placed + received (2026-06-22 closed the cart), Amazon batch
received (standoffs, wick, rings, MRBF+5191, 12AWG, bench gear), **both PCBs ordered ×5 at JLCPCB
2026-07-01** (~$203 all-in, one parcel, 3-4d build + 2-4d DDP ship).

**🔴 Order now (blocks v1 bring-up, longest leads):**
1. **Feetech servo daisy/extension cables** — never received; ~15-20 mixed 200/300mm (also the
   VCC-pull donor stock). AliExpress slow boat → order immediately.
2. **STS3215 19kg top-up** — count shelf first (~6 of 8 at last audit → buy 2 + 1 spare, ~$75);
   also confirm 4× 30kg hips in hand (12 active total).
3. **+1 INA226 20A R002 module** — 0 spares (arm U12 ate the 4th; 4th now = L2). Same GODIYMODULES
   listing, ~$13.
4. 🔴 **Leg servo disc screws — the M2.5 order (2026-08-02, ~$18) is SUPERSEDED; the thread is M3**
   (#263; Ø3.0 nominal — ⚠️ tapped-M3 vs PA3.0 self-tap pilot open, see #262 before buying more).
   Lengths 5/6/8/14 unchanged; ×6 and ×8 are covered by the owned M3 kit,
   **×5 and ×14 still need ordering**. See the disc-screw section above. ⬜ **The M2 case-mount
   screws are still open** — now ×40 **M2×9** + ×8 **M2×13**, **countersunk self-tapping** (was
   ×40 M2×22 + ×8 M2×25 — the column is **7 mm blind, measured**, so a ×22 drives ~13 mm into the
   servo). At these lengths the sourcing problem inverts and gets EASIER: self-tap assortments
   stop near 16 mm, which now covers both. ⚠️ Pitch-check against a factory screw (6 crests over
   7 mm) before any goes in — a GB819 **machine** screw cannot grip a coarse formed thread.
   The rule is `L_max = printed floor + measured column`, and the column must be MEASURED —
   back-solving it from an existing screw length makes the length confirm itself.
5. 🔴 **Heat-set inserts — see §"Heat-set inserts" above for the buy list.** The 2026-08-02 order
   covered the **OD 4.6 × 5.7** type (ruthex `B08BCRZZS3`), the short (`B09ZHSGHXD`) and the M2
   (`B088QJG676`) — but **NOT the slim OD 4.0 × 6.0** that #255 introduced for the HFE block
   retention (8 needed, and `coax_R` + `coax_hfe_block` are the next parts to print). A 4.6 insert
   cannot travel the 4.4 mm mortise slot to reach its blind-end bore. Fallback: 4.0 × 4 at
   SF ≈ 1.6–2.3 with an M3×14.
   ⚠️ **Buy inserts by part code, not brand.** `B0CDH36ZMX` is "ruthex M3 **VORON** RX-M3x5x4" —
   **OD 5.0**, same price, same brand, same search page, one row from the right part.

**🟡 Verify on shelf (buy only if missing):**
- ~~Thin solder 0.6-0.8mm~~ ✅ **closed 2026-08-01 — Sn63Pb37 1 mm 1.8 % flux core in hand** (see
  the soldering table; 1 mm ≠ the 0.6–0.8 mm originally specced, which is a technique change at
  stages 1/3, not a re-order) · XT30 ≥18 genuine-AMASS mating pairs · Blue Sea 5191 = single-MRBF
  terminal variant · re-measure 6000mAh pack dims (task → `dimensions.md §5`).
- ~~99 % IPA — verify on shelf~~ ✅ **CLOSED 2026-08-02 — both ordered.** And the primary board cleaner is now
  the **MG Chemicals 4140 aerosol defluxer**, not the IPA: plain IPA on no-clean residue can leave a white
  haze that reads as a dull joint, so it could produce a false FAIL as readily as skipping the clean
  produces a false PASS. See the soldering table.

**⚪ Phase-4 — do NOT order yet:** D42V55F7 arm buck · 5th INA226 (arm, 0x46) · 6× arm daisy cables.
