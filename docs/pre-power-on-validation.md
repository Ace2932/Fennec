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
- [ ] **Add 100nF decoupling at U7 (74HC125)** — absent; part owned. Small schematic add
      (place C, wire +3V3/GND near U7) — do before/with routing.
- [x] **Routed** (2026-06-14) via Freerouting headless (openjdk + freerouting-2.2.4.jar;
      pcbnew ExportSpecctraDSN → java route → ImportSpecctraSES). 24 nets, 154 tracks, 3 vias.
      Min thermal spokes 2→1 to clear GND starved-thermal. **DRC: 0 errors, 0 unconnected.**
- [x] **J20↔J20 net mapping VERIFIED matched** — both boards' J20 pin→net identical (straight
      ribbon = correct, no bus mirror). Remaining: visual key-orientation at assembly (shrouds enforce).
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

## ⚪ 6. 2oz copper at fab
- [ ] PCBWay checkout: explicitly select **2oz outer copper** for both boards.
      Default is 1oz → halves every thermal margin. Gerbers don't enforce it.

## ⚪ 7. Off-board I2C noise immunity
3 INA226 on dupont near servo switching; FB1/R1 series-R+ferrite are DNP.
- [ ] Start I2C at 100kHz; only raise to 400k after the cal test passes clean
- [ ] If readings glitch under servo load: populate FB1/R1 (footprints reserved)

---
**"100% won't die" = all 🔴 cleared + 🟡 #2/#3/#4 bench-passed.** #5 needs the scope (Phase 5).
Part-quality tests (Q1 Rds, cap ESR, MRBF, fakes) are separate — ROUTING_HANDOFF.md Step 10.
