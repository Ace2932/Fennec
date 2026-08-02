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
| XT60 (J1), XT30 ×17+ | J1/J3-J7/J12/J13 | ✅ |
| JST B3B-XH-A ×10 | J8 (+logic J11) | 📦 |
| IDC BHR-12-VUA ×10 | J20 | 📦 |
| PRPC040 header strip | J2/M1 (+logic J9/J10/JP1) | 📦 |
| TB007-508-02BE ×10 (Same Sky, 16A UL/18A IEC) | SW1 | ✅ ordered 2026-06-22 (MKDS 1,5/2 went OOS 17wk → this sub; needs SW1 drill 1.2→1.5mm — done on board) |
| KF301 kit block (SW2) | SW2 | ✅ |
| MRBF-30 fuse ×2 + Blue Sea 5191 block | inline | ✅ ordered 2026-06-12 (verify 5191 = single-MRBF terminal variant) |
| SMBJ8.5A ×10 (leg) + SMBJ13A ×10 (hip/L2) TVS | off-board | 🛒 |
| Balance buzzer ×5 | — | ✅ |
| UBEC 5V/5A ×2 | — | ✅ |
| E-stop (Mxuteuk) + Blue Sea Contura switch | SW1/SW2 wiring | ✅ |

## Logic board — `nova_pcb_v6_logic` (✅ ORDERED ×5 — JLCPCB 2026-07-01, 4L/1oz/HASL)
| Part | Ref | Status |
|---|---|---|
| **SN74LVC125AD** SOIC-14 ×5 | U7 | 🛒 ⚠️ ORDER LVC NOT HC — 5V-tolerant inputs (servo bus is 5V-TTL; HC at 3.3V isn't 5V-tolerant → servo response over-drives input). Same SOIC-14 pinout, VCC 3.3V (max 3.6V). Sch value was stale "74LS125" (5V TTL, wrong for 3.3V). Changed 2026-06-14. |
| R7 = 10kΩ 0603 | R7 | 🛒 ADD — bus idle pull-up (BUS_SIGNAL→+3V3), keeps half-duplex bus defined in TX/RX turnaround. Added 2026-06-14. |
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
| **Interboard J20↔J20 ribbon** — 2×6 IDC socket-both-ends, 2.54mm ×2 | J20 | 🛒 ⚠️ both J20s are MALE box headers; without this cable the two boards are electrically disconnected (I2C / servo-bus / safety lines). Hard mezzanine blocker. |

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
| **TPU 95A filament** | ✅ **on hand — confirmed 2026-07-31 by having printed with it** (foot shoes ×5, knee_bumper ×5, skid_rail ×2). Was contradicted across three docs: `work-schedule.md` said ✅, `checklists/print-batch.md` §0 had it as an open question, and this table listed only PA6-CF. **~73 g of the ~102 g TPU set is now printed; ~29 g remains** (cable_clip ×24 + grommets) — see `print-batch.md` §1b. External spool only, **AMS will not feed TPU** |
| PETG-CF filament | ⬜ **unknown** — `print-batch.md` §0 still asks "PETG-CF spool on hand?". Needed for `riser_bay` / `floor_plate` / `head_ear`; the fallback is all-PA6 with warp risk on the 127 mm riser lid |

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

## Heat-set inserts — 🛒 ON ORDER 2026-08-02

No insert line existed in this BOM at all until now, and the only count anywhere
(`docs/fastener-schedule.md` purchase summary) covered the chassis and omitted
every leg and shoulder insert — 16 documented against **~68** the design
actually consumes.

| Part | Qty | For | Status |
|---|---|---|---|
| **M3 heat-set, 4.6 mm OD × 5.7** (Ruthex or equivalent) | **100** | femur→knee_arm 16 · shoulder→plate 16 · shoulder→trunk 16 · chassis 12 = ~60 + spares. **`femur_?.stl` is already printed with the Ø4.0 bore this insert wants** | 🛒 order |
| **M3 heat-set, 4.0 mm OD × 6.0** (slim) | **25** | **HFE block retention only** (8 needed). A 4.6 insert cannot travel the 4.4 mm mortise slot to reach its bore — see `fastener-schedule.md`. ⚠️ 4.0 OD in a **6 mm length** is less common than the 4 mm; if unavailable, 4.0 × 4 works at SF ≈ 1.6–2.3 with an M3×14 | 🛒 order |
| **M3×16 SHCS** | **20** | HFE block retention (8 needed). M3×20 **bottoms out** in the blind pocket; M3×14 is the short interim | 🛒 order |
| M3×3.8 short insert | 10 | neck bracket → shoulder deck (front only) | ⬜ verify |
| M2×4 insert | 20 | pod, deck-tie, clamp bar, OLED bracket | ⬜ verify |

⚠️ The owned HANGLIFE 345-pc assortment carries M3 in **D4×L3, D4×L4, D5×L5** —
**no 4.6 OD**, which is what every printed Ø4.0 bore on this robot is sized for.
Its D5×L5 will seat in a Ø4.0 bore (0.5 mm/side, ~1.7× the usual interference);
its D4 will spin freely. Enough to build the first leg, not the robot.

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
| **Cleaner — 99 % IPA + stiff brush + lint-free wipes** | ⬜ **NOT VERIFIED ON SHELF — and nothing else in this build substitutes.** Added 2026-08-01 because `BUILD_PLAN.md` states the shiny criterion three times as valid *"after the flux is cleaned off"*, the plan contained no cleaning step, and no cleaner appeared in this BOM — so the pass criterion was unreachable as written. **99 %, not 70 %**: the 30 % water in rubbing alcohol evaporates slowly and leaves its own residue on exactly the high-Z nets this is meant to protect. Technique matters — IPA *dissolves* rosin, so flooding without wicking it up smears a thin conductive-ish haze over a **wider** area than the original blob, which is worse for the divider. Flood → brush → **blot with lint-free** → repeat until the wipe comes away clean |
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

**🟡 Verify on shelf (buy only if missing):**
- ~~Thin solder 0.6-0.8mm~~ ✅ **closed 2026-08-01 — Sn63Pb37 1 mm 1.8 % flux core in hand** (see
  the soldering table; 1 mm ≠ the 0.6–0.8 mm originally specced, which is a technique change at
  stages 1/3, not a re-order) · XT30 ≥18 genuine-AMASS mating pairs · Blue Sea 5191 = single-MRBF
  terminal variant · re-measure 6000mAh pack dims (task → `dimensions.md §5`).
- 🆕 **99 % IPA + stiff brush + lint-free wipes — check before stage 1, not before power-on.**
  Cheap and probably on the shelf, but it gates the *inspection* criterion rather than any
  joint: with a no-clean flux, an uncleaned board reads shiny whether or not the joints are.
  70 % rubbing alcohol does not substitute (see the soldering table).

**⚪ Phase-4 — do NOT order yet:** D42V55F7 arm buck · 5th INA226 (arm, 0x46) · 6× arm daisy cables.
