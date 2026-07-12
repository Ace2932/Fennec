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

## Harness + assembly consumables (mostly Amazon — NOT yet bought)
The off-board side is 25+ wired connections; this category was unspeced until 2026-06-13.
| Part | For | Status |
|---|---|---|
| Silicone wire 12 AWG (TUOFENG red/black 20ft) | battery / fuse / switch (~15-18 A) | ✅ ordered 2026-06-13 |
| Silicone wire 18 AWG stranded | servo-rail injection (7.5-8 A) | ✅ owned (TUOFENG) — 18AWG OK at 8A |
| Wire 22 AWG solid | I2C / EN / sense | ✅ owned (TUOFENG) — solid, solder don't crimp |
| Ring terminals 12-10 AWG / 5/16" (M8) | MRBF fuse-block wiring | ✅ received (AIRIC 50pc; crimp w/ WGGE yellow station) |
| Heat-shrink assortment | every XT / TVS / fuse joint | ✅ owned (Ginsco 580pc) |
| M3 standoffs ~20 mm | mezzanine board-to-board | ✅ received (PATIKIL brass M3×20 ×50; safe on all 4 holes — 7mm copper keepout) |
| M3 screws/nuts/washers | board → chassis | ✅ owned (Fgruh 1220pc) |
| M3 standoffs 20 mm | power board → floor plate (bucks + de-cased switch live underneath — chassis README §9) | ✅ use the M3×20 ×50 already received (line 97). Corrected 16→20mm 2026-07-09: the ordered Ø10×17 C1–C5 caps need the 20mm gap to clear the floor (check_fit case 11). |
| Right-angle USB-C (USB 3.x) cable | D456 → Jetson (straight plug doesn't fit the periscope bracket gap) | 🛒 order |
| Velcro strap ~300 mm | battery pocket rear-corner fence | 🛒 order (or cut from owned roll) |
| JST-XH plug + crimps | board ↔ servo-bus pigtail | ✅ owned (PEBA crimp+connector kit) |
| Servo-bus extension cables | leg runs > stock cable length | 1st Amazon order CANCELLED 2026-07-11 (seller couldn't fulfill — 2nd cable order to fall through) → ✅ **RE-ORDERED 2026-07-11: 2× waveshare 5264-3PIN kit** (each 3× 300mm + 3× 900mm → **6× 300 + 6× 900 total**, ~$20, Prime, arr ~Jul 13). 2 kits because 1 kit's 3× 900 is short of the **4 long runs** (chassis + 3 between-leg links). Make-your-own ruled out — the owned PEBA crimp kit is **JST-XH**, not the servo's **5264** (different housing/latch, won't reliably mate). Still verify the real routed lengths on receipt (#55). Plan (unchanged when they arrive): 900s = chassis run + 3 between-leg links; 300s + the 12 stock in-box servo cables = within-leg links + VCC-pull donors (see wiring README dual-voltage recipe). Top-up trigger: count in-box cables at servo verify — if <12 or pull-mods eat spares, add the mixed 3×300+3×900 pack |

## Soldering / tools — verify on shelf
| Item | Status |
|---|---|
| Pinecil V2 iron | ✅ |
| Thin solder 0.6-0.8 mm | ⬜ verify |
| Flux | ✅ owned (BEEYUIHF) |
| Solder wick (2-3mm braid) | ✅ received (Lesnow) — SMD bridge cleanup (sucker owned, but it's THT-only) |
| Solder sucker | ✅ owned — THT desolder |
| Crimpers | ✅ WGGE WG-015 (12-10 insulated lugs) · iCrimp (23-10 ferrules) · PEBA (dupont/JST) |
| USB micro-B cable | ✅ owned (USC) |
| Reflow hotplate + paste | 🚫 SKIP — 21 SMD parts all 0603/SOT-23/SOIC, hand-solder; no stencil; half-THT board anyway |

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
- Thin solder 0.6-0.8mm · XT30 ≥18 genuine-AMASS mating pairs · Blue Sea 5191 = single-MRBF
  terminal variant · re-measure 6000mAh pack dims (task → `dimensions.md §5`).

**⚪ Phase-4 — do NOT order yet:** D42V55F7 arm buck · 5th INA226 (arm, 0x46) · 6× arm daisy cables.
