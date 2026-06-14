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
- [ ] (tidy) Add `no_connect` flags to 16 unused Nano GPIO pins — clears ERC noise
- [ ] 2oz outer copper selected for BOTH boards at PCBWay

## 🔴 1b. USB back-feed isolation (Teensy + Nano externally powered)
V5_AUX (UBEC 5V) feeds Teensy VIN + Nano +5V. Plugging USB to flash/debug WHILE battery
live = USB 5V vs UBEC 5V fighting on V5_AUX. (This is the ERC "two power outputs" conflict.)
- [ ] **Teensy 4.1: cut the VUSB↔VIN pad** (bottom of board, PJRC-documented) so USB does
      data-only when powered from VIN. Do this before first battery+USB session.
- [ ] **Nano:** never plug USB while battery-powered, OR add a series Schottky on the +5V
      feed. Confirm whichever before bring-up.

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

---
**"100% won't die" = all 🔴 cleared + 🟡 #2/#3/#4 bench-passed.** #5 needs the scope (Phase 5).
Part-quality tests (Q1 Rds, cap ESR, MRBF, fakes) are separate — ROUTING_HANDOFF.md Step 10.
