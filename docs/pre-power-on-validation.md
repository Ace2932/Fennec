# Pre-Power-On Validation Checklist

The gap between "passes DRC" and "verified won't brown out / burn out under gait."
These are DESIGN-validation steps (not part-quality tests — those are in
ROUTING_HANDOFF.md Step 10). Compiled from the 2026-06-13 ultrathink electrical review.

Order: clear 🔴 before any board work, 🟡 during bench bring-up, ⚪ at checkout/assembly.

## 🔴 1. Logic board: schematic fixes + route (BEFORE fab)
Found in 2026-06-13 review. Schematic fixes first (GUI), then re-export netlist → route.
- [x] **R1/FB1 un-DNP** — were DNP in series in the only bus path = open bus. Now R1=22R,
      FB1=ferrite (done 2026-06-13). Need 22Ω 0603 + 0603 ferrite added to DigiKey order.
- [x] **+3V3 source FIXED** (2026-06-13) — Teensy 3.3V pad `T3V3O` added to U6 symbol (Power
      output) + wired to +3V3. Netlist verified: +3V3 = [U6.T3V3O, U7.10/13/14, J20.5].
      74HC125 + 3× INA226 now powered.
- [x] **100nF decoupling at U7 DONE** (2026-06-14) — C1 (CC0603 100nF) across +3V3/GND
      placed next to U7 pin14, routed.
- [x] **Routed** (2026-06-14) via Freerouting headless (openjdk + freerouting-2.2.4.jar;
      pcbnew ExportSpecctraDSN → java route → ImportSpecctraSES). 24 nets, 154 tracks, 3 vias.
      Min thermal spokes 2→1 to clear GND starved-thermal. **DRC: 0 errors, 0 unconnected.**
- [x] **J20↔J20 net mapping VERIFIED matched** — both boards' J20 pin→net identical (straight
      ribbon = correct, no bus mirror). Remaining: visual key-orientation at assembly (shrouds enforce).
- [x] **E-stop sense to Teensy ADDED** (2026-06-14) — was: hardware e-stop (Q3) killed
      bucks but Teensy was blind (no ESTOP on J20, 12 pins full). Added J21 (Conn_01x02)
      → e-stop button's 2nd NC dry contact → Teensy pin 5 (`INPUT_PULLUP`) + GND. Dry
      contact = no level-shift; NC-to-GND = LOW idle, pressed/break/unplug = HIGH = e-stop
      (FAIL-SAFE). Routed F.Cu J21.1→U6.T5 (existing 154 tracks untouched). DRC 0/0,
      gerbers re-cut. Net auto-named `Net-(J21-Pin_1)` (label didn't stick; electrically
      correct). No power-board / J20 change.
- [x] **Firmware pins reconciled to board** (2026-06-14, teensy41_ci green) — board routes
      bus to Serial1 (pins 0/1), OE to 2/3, BATT_LOW to 4, e-stop to 5; firmware was on
      Serial2 7/8 / OE 5,6 / BATT_LOW 3 / ESTOP 2. Updated `main.cpp` defines +
      `feetech_bus.h` (Serial2→Serial1). I2C 18/19 already matched. **E-stop polarity
      flipped LOW→HIGH** (NC fail-safe; SafetyFSM already latches until /safety_clear →
      snap-back on release handled). Reconciliation was mandatory — old defines = dead bus.
- [x] **OLED (J10) integration fixed** (2026-06-14) — owned HiLetgo SSD1331 (7-pin, VCC
      2.8-5.5V = has onboard reg). Found 3 issues vs the board: (1) J10 pin order had CS/RST
      crossed vs the module → swapped on board (J10.5=OLED_RST, J10.7=OLED_CS); (2) Vcc was
      on NANO_3V3 (Nano's ≤50mA reg, often absent off-USB) → moved to **V5_AUX (5V)**;
      (3) Nano is 5V → its SPI logic over-drives the 3.3V-reg'd SSD1331 → added **5× 1k
      series R (R2-R6)** on SCK/MOSI/RST/DC/CS. Schematic + full re-route, DRC 0/0, gerbers
      re-cut. BENCH-VERIFY: if display still glitches, swap to Adafruit 684 (74LVC245+boost,
      5V VIN, DK 684-ND) — wire 7 pins to J10.
- [x] **U7 → SN74LVC125A (5V-tolerant)** (2026-06-14) — servo bus is 5V-TTL; the 74HC125 at
      +3V3 is NOT 5V-tolerant (input abs-max VCC+0.5=3.8V) → servo's 5V response over-drives
      gate2 input, clamp current ~54mA through R1's 22Ω = stress/damage. SN74LVC125A: same
      SOIC-14 pinout (drop-in), VCC 3.3V (max 3.6V — keep on +3V3, never 5V), inputs 5V-tolerant,
      outputs swing 3.3V (Teensy-safe). Correct whether bus is 3.3V or 5V. (Sch value was stale
      "74LS125" = 5V TTL, also wrong for 3.3V.) Value-only change, no reroute.
- [x] **Bus idle pull-up R7 (10k BUS_SIGNAL→+3V3)** (2026-06-14) — half-duplex push-pull bus
      floats during TX↔RX turnaround → gate2 input indeterminate / false RX bytes. R7 holds idle
      HIGH at 3.3V; 10k = idle bias only (drivers do edges), no speed penalty.
- [ ] (tidy) Add `no_connect` flags to 16 unused Nano GPIO pins — clears ERC noise
- [ ] 2oz outer copper selected for BOTH boards at PCBWay

## 🔴 1b. USB back-feed isolation (Teensy + Nano externally powered)
V5_AUX (UBEC 5V) feeds Teensy VIN + Nano +5V. Plugging USB to flash/debug WHILE battery
live = USB 5V vs UBEC 5V fighting on V5_AUX. (This is the ERC "two power outputs" conflict.)
- [ ] **Teensy 4.1: cut the VUSB↔VIN pad** (bottom of board, PJRC-documented) so USB does
      data-only when powered from VIN. Do this before first battery+USB session.
- [ ] **Nano:** never plug USB while battery-powered, OR add a series Schottky on the +5V
      feed. Confirm whichever before bring-up.

## 🔴 1c. Connector mating audit (BEFORE assembly — HARD GATE)
The board files only define what net lands on each connector pin; they CANNOT verify the
**physical part's** pinout/polarity. Every off-board connector below is correct on the BOARD
side (verified from the .kicad_pcb) — the open item is confirming the MATING part agrees.
Only rigid direct-plug modules force a board re-route; the rest are hand-wired, so the board
pin is the reference and you wire the cable/leads to match it. (Compiled 2026-06-14 after the
OLED pinout miss — that was a rigid direct-plug module, now fixed; this is the rest of the set.)

**🔴 High — a mismatch damages a part or shorts power:**
- [ ] **J11 WS2812B** — board: `1=+5V, 2=GND, 3=DATA`. WS2812B strip wire order varies; reverse
      5V/GND = fried strip. Crimp the JST-XH pigtail to match J11, and connect to the strip's
      **DIN** end (not DOUT). Verify with a meter before plugging in.
- [ ] **J8 servo bus** — board: `1=GND, 2=V7V5_LEG, 3=BUS_SERVO`. ✅ Matches Feetech STS3215
      standard (GND/VCC/Signal). NOTE: servo uses a 5264 connector, board is JST-XH — crimp
      your own JST-XH pigtail in GND/V+/Signal order (don't assume a pre-made cable's housing mates).
- [ ] **J20 interboard ribbon** — both boards' pinouts identical (verified). A 2×6 IDC ribbon
      can be built/plugged mirrored → 5V meets GND. **Meter-check pin1↔pin1 continuity** on the
      assembled cable before first power; confirm shroud keys are consistent.
- [ ] **U1–U5 Pololu bucks** (off-board, XT30 + EN wire) — board: `VIN=VBAT_PROTECTED, GND,
      EN=EN_BUCKS/EN_JET, VOUT`. Reverse VIN into a Pololu = dead module. Match each buck's
      VIN/GND/VOUT/EN silk to the wiring.

**🟡 Medium — silent failure / safety-logic inversion:**
- [ ] **U9–U11 INA226 modules** — board connects I2C+power only (`4=SDA, 5=SCL, 6=VCC, 7=GND`).
      Confirm (a) module header order matches your dupont wiring, (b) the inline shunt terminals
      are on the intended rail for each, (c) **3 distinct I2C addresses** (A0/A1 straps).
- [ ] **SW2 + J21 e-stop contacts** — board expects **NC** (`SW2: GND↔EN_SW`; `J21: sense↔GND`).
      Fail-safe depends on NC, not NO. Identify the NC pairs on the Mxuteuk button; confirm it has
      a *second* NC block for J21. NO wiring → reads always-pressed or never trips.
- [ ] **JP1 (JP_BUS_MASTER) reachable after stack-up** — single config jumper, logic board
      TOP face at (160, 86), **same face as the socketed Teensy U6 + USB** (verified from
      .kicad_pcb). That face must mount outward for USB access → JP1 should be reachable; just
      confirm final stack orientation puts the Teensy face out, not into the gap. Flip to **A**
      once for servo-ID assignment, then back to **B** (default).
- [ ] **In-gap component heights** — confirm tallest parts facing the ~20 mm mezzanine gap
      (bulk caps Ø10×17 mm, INA226 modules) clear the M3×20 standoff gap (≤~17 mm target).

**🟢 Low — protected or bench-only:**
- [ ] **J1 XT60** — `1=VBAT(+), 2=BATT_NEG(−)`. Q1 reverse-prot covers a slip, but confirm.
- [ ] **SW1** — confirm the physical switch is rated for full pack current (~15–18 A).
- [ ] **J9 FE-URT-1** — Pattern-A bench adapter only; confirm its data pin = MASTER_A if used.
- [ ] **Q1 IRLB3034** — TO-220 G/D/S = pin 1/2/3 (matches footprint); confirm tab = Drain.

## 🟡 2. Trip-point calibration (ratiometric to V5_AUX)
VREF tracks the UBEC, VSENSE tracks the battery. UBEC sag shifts trips LOWER (later).
Verified-on-paper trips: BATT_LOW 13.0V, HARDCUT 12.4V (resistor math confirmed 2026-06-13).
- [ ] Measure UBEC output — must hold **5.0V ±2%** (4.9–5.1V). If under 4.7V, trips shift
      ~1.3V late; swap divider or fix UBEC.
- [ ] Bench-sweep supply 13.5→12.0V, confirm BATT_LOW asserts ~13.0V, HARDCUT ~12.4V
- [ ] Confirm hysteresis (R14 470k / R15 1M) prevents chatter at threshold

## 🟡 3. Inrush into bulk capacitance (~5470µF: 5×1000µF + 3×470µF)
Charged 16.8V pack → XT60 → ~5470µF = hard inrush spike + connector arc. No precharge.
- [ ] First connect at CURRENT-LIMITED bench supply (0.5A) — watch for sustained inrush
- [ ] Inspect XT60 contacts after several connect cycles (pitting = consider precharge resistor)
- [ ] Confirm Q1 doesn't overheat on repeated inrush (IR check)

## 🟡 4. All-stall rail collapse
Leg buck derates ~7-8A @ 14.8V Vin; 8× STS3215 stall ≈ 21A. Multi-stall (robot falls,
legs jam) exceeds buck → foldback/brownout. Electrically safe (robot goes limp), but:
- [ ] Confirm firmware load-monitor / safety envelope trips BEFORE the buck folds back
- [ ] Bench: stall 2-3 leg servos simultaneously, watch rail voltage on INA telemetry
- [ ] Confirm Jetson rail (separate buck) does NOT brown out when leg rail collapses

## 🟡 5. Buck stability with remote bulk caps on star wires
Output-wire inductance + 1000µF bulk = LC tank the buck loop may ring against (Pololu warns).
- [ ] SCOPE each rail output during a servo transient — look for ringing/overshoot at the
      injection point. If ringing: add small series damping or move bulk closer.
- [ ] (Phase-5 task — needs scope; deferred with the scope purchase)


## 🟡 8. WS2812B status-LED current budget (J20 ribbon limit)
V5_AUX reaches the logic board ONLY via 2× J20 ribbon conductors (~2A, 28AWG). Feeds
Teensy(~0.1A)+Nano(~0.05A)+WS2812B strip (J11). WS2812B = 60mA each @ full white.
- [ ] Keep status LEDs **≤16-20** (≤1A) — fine on the ribbon. (§8 intent = a few status LEDs.)
- [ ] If a larger strip is ever wanted: feed it DIRECTLY from power-board V5_AUX, not J20.
- NOTE (verified 2026-06-14): I2C pullups R11/R12 → +3V3 (NOT 5V) ✓ — Teensy 4.1 I2C pins
  are not 5V-tolerant; whole logic domain is consistently 3.3V. No level-shift hazard.

## ⚪ 6. 2oz copper at fab
- [ ] PCBWay checkout: explicitly select **2oz outer copper** for both boards.
      Default is 1oz → halves every thermal margin. Gerbers don't enforce it.

## ⚪ 7. Off-board I2C noise immunity
3 INA226 on dupont near servo switching. (Bus-integrity R1=22Ω + FB1 ferrite now POPULATED,
not DNP — 2026-06-13 fix; tune values up only if needed.)
- [ ] Start I2C at 100kHz; only raise to 400k after the cal test passes clean
- [ ] If readings glitch under servo load: raise R1 toward 100Ω / swap ferrite

## 🟡 10. Servo-bus half-duplex timing (firmware bring-up, servos on bus)
Single-wire half-duplex: Teensy Serial1 (pins 0/1) drives the bus through SN74LVC125A
gates, direction switched by OE̅_TX (pin 2) / OE̅_RX (pin 3), active-LOW, with a 2µs
TX↔RX settle in `feetech_bus.h transmit_blocking`. At 1Mbaud one byte ≈ 10µs — a short
or wrong turnaround corrupts frames or causes driver contention. (Pin choice is correct;
this validates the *timing*, the real half-duplex risk.)
- [ ] SCOPE bus line + both OE̅ pins during a PING/READ round-trip: TX gate must disable
      BEFORE the servo replies (no driver fight), RX gate enable in time for the first reply byte.
- [ ] Confirm `flush()` finishes (last byte fully shifted out) before OE̅_TX releases —
      a clipped last byte = checksum fail.
- [ ] Confirm 2µs settle is enough at 1Mbaud; widen if the first reply byte is clipped.
- [ ] Bus integrity at far servo (R1=22Ω + FB1 ferrite populated): check rise/fall + reflections.
      On errors the firmware auto-drops 1M→500k→250k — confirm that fallback triggers and recovers.
- [ ] Single servo (ID ping) first, then full 12-servo chain — watch SYNC_WRITE (no-ACK broadcast)
      vs individual READs for collisions.

## 🔵 9. Phase-4 arm rail (when populating U5 — NOT for current fab)
Found 2026-06-14 by `tools/board_health.py` + EN-gating audit. The arm buck U5
(D42V55F7) is DNP. "Populate-and-go" is INACCURATE — it needs the fixes below.
The current board (no arm) is unaffected: U5 empty = zero effect, DRC 0/0.

**Gap 1 — arm rail has no exit.** `V7V5_ARM` = `U5.4` only (single-pad net).
Populate U5 → 7.5V goes nowhere; arm servos can't be powered.
- [ ] Add an off-board injection connector (XT30) for `V7V5_ARM` before populating U5.

**Gap 2 — 🔴 arm buck is UNGATED by the safety chain (safety hazard).** U5.EN
(pin3) is tied to **VBAT_PROTECTED = always-on**. Contrast: U1/U2/U3 legs+hips
EN=EN_BUCKS (killed by e-stop Q3 AND hardcut Q2); U4 jetson EN=EN_JET (killed by
hardcut Q4). U5 arm is killed by **NEITHER e-stop NOR hardcut** → when populated,
hitting e-stop leaves the arm powered + holding torque (pinch/crush hazard), and
critical-low battery kills everything except the arm.
- [ ] Re-route U5.EN from VBAT_PROTECTED → **EN_BUCKS** (gates the arm on both
      e-stop and hardcut, same as legs/hips). Do this with Gap-1 connector add.

**Phase-4 must-checks (for the arm to function — not board-fab blockers):**
- [ ] Bus: 6 arm STS3215 daisy-chain off J8 → firmware servo count 12→18;
      re-check SYNC_WRITE frame size vs `MAX_PARAM_BYTES` (was bumped for 12).
- [ ] Power budget: arm buck (D42V55F7) rating vs 6-servo stall, and
      battery / MRBF fuse / Q1 headroom for legs+hips+jetson+arm simultaneously.

---
**"100% won't die" = all 🔴 cleared + 🟡 #2/#3/#4 bench-passed.** #5 needs the scope (Phase 5).
Part-quality tests (Q1 Rds, cap ESR, MRBF, fakes) are separate — ROUTING_HANDOFF.md Step 10.
