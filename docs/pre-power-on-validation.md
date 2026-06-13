# Pre-Power-On Validation Checklist

The gap between "passes DRC" and "verified won't brown out / burn out under gait."
These are DESIGN-validation steps (not part-quality tests — those are in
ROUTING_HANDOFF.md Step 10). Compiled from the 2026-06-13 ultrathink electrical review.

Order: clear 🔴 before any board work, 🟡 during bench bring-up, ⚪ at checkout/assembly.

## 🔴 1. Logic board routed + reviewed
- [ ] Route `nova_pcb_v6_logic` (0 traces today) → DRC 0 errors
- [ ] **Add 100nF decoupling at U7 (74HC125)** — currently absent; part owned
- [ ] **Verify J20↔J20 pin-1 orientation** — both J20s are male box headers joined by a
      socket-to-socket ribbon. If pin-1 doesn't map pin-1, the ribbon MIRRORS the whole
      interboard bus (I2C swapped, EN/safety lines crossed). Check the two footprints'
      pin-1 positions + the ribbon's straight-through mapping before fab.
- [ ] 2oz outer copper selected for BOTH boards at PCBWay

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
