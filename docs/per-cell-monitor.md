# Per-cell battery monitor (backlog #9)

Status: **design, not built.** This is a v6 add-on board plus bodge wires. No KiCad file changes (v6 copper is frozen).
All numbers are derived in the tables below. `est` means the value was not checked against a datasheet or a vendor page.

## 1. Requirement

**Failure caught.** The existing safety chain only sees the whole pack. The LM393 (`U8`) compares `VSENSE` = VBAT × 22k/122k. `BATT_LOW` trips at an as-built 13.03 V and `HARDCUT` at 12.56 V (`power-budget.md:209-212`).
If three cells sit at 3.60 V and one at 2.60 V, the pack reads 13.40 V and **neither trip fires**. `HARDCUT` only fires once the weak cell is around 2.2 V (3 × 3.45 + 2.2 = 12.55), and that is already inside the damage region (< 2.5 V).
The only per-cell protection today is the FLY-RC balance buzzer (3.3 V/cell). It makes a sound and cuts nothing.

| Item | Value | Why |
|---|---|---|
| WARN | min cell < **3.40 V** for 2 s | Software only: stop starting new tasks and head home. This is about 10 % capacity left under a 14 A walk (est). |
| SHUTDOWN | min cell < **3.25 V** for 2 s | Takes the **same graceful path as `BATT_LOW`** (limp, `/battery_low`, `ShutdownDecider`, poweroff). 3.25 V is the per-cell equivalent of the as-built 13.03 V trip (13.03 / 4 = 3.26 V). |
| CUT | min cell < **3.00 V** for 2 s | Asserts the hardware cut (§4). This is the conventional loaded floor for LiPo, with 0.5 V margin above the 2.5 V damage floor. |
| Accuracy | **±75 mV per cell worst-case after calibration** (cell 4 is the worst case) | CUT has to fire before the true cell voltage falls below 2.90 V. That leaves 100 mV between 3.00 and 2.90, and 75 mV keeps SHUTDOWN (3.25) from ever landing below CUT. |
| Load sag, not error | about 30–40 mV per cell at 14 A | Pack IR is about 2–3 mΩ/cell (est, 120C 6 Ah). The 2 s sustain window rides out servo transients and does not rely on accuracy. |
| Sample rate | 200 Hz per channel raw, 0.5 s EMA, evaluated at 10 Hz | From 3.25 V to 3.00 V loaded is about 3–5 % of capacity (est). At the 14 A sustained walk (`power-budget.md:192`) that is **13–21 s**, and less for a weak cell. Detection latency is ≤ 2.1 s, which is ≪ 13 s. |

## 2. Options

Cell-4 error is the worst case, evaluated at 3.25 V/cell. It covers resistor ratio error, 25 °C drift, and Teensy ADC TUE (max 4.28 LSB, from the i.MX RT1060 datasheet Table 55), plus the reference error.

| | (a) Dividers → Teensy ADC | (b) AFE (BQ76920 / LTC6811 / MAX14920) | (c) Difference amps |
|---|---|---|---|
| Cost | ~$12 (est) | BQ76920 ~$3 + isolator ~$4 + passives ≈ $12. LTC6811 + LTC6820 ≈ $25+ (est) | 3× high-CM diff amp (INA149-class) ≈ $20 (est) |
| Parts | ~30 passives/small parts, 0 new ICs on buses | IC + ~15 passives + isolator + LDO | 3–4 amps + protection |
| Cell-4 error | 1 % R, no ref: **±536 mV** · 0.1 % R, no ref: ±142 mV · 0.1 % R + LM4040: ±109 mV (±188 mV at 1 µA pin leak) · **after 2-point cal: ±60 mV** | ±10 mV class (est), factory-trimmed | ±5 mV class (est). No stacking because each cell is measured directly. |
| Drain on pack | ~0.3 mA per divider. Cell 1 carries 1.19 mA and cell 4 carries 0.30 mA. **Must be gated** (below). | Always powered from the pack: ~40 µA NORMAL, 0.1 µA SHIP (est) | Input networks draw the same kind of current, and the amps need a supply of at least the tap voltage |
| Isolation / ground | Referenced to board GND. **Pack − is left unconnected.** | VSS must be **pack −**, and `BATT_NEG ≠ GND` (Q1 sits in the low side). The I²C to the Teensy therefore needs a digital isolator. | A 5 V difference amp cannot take 16.8 V CM, so it needs a high-CM part |
| Fits v6? | Yes: 4 free ADC pins and a flying lead | v7 (needs the isolator and a new bus device) | Possible, but costs more than (a) and is no better in practice |

**Why the error stacks in (a).** Cell *k* = tap*k* − tap*(k−1)*, and each tap is ADC / G. A resistor ratio error gives dG/G = (1 − G)(ε_b − ε_t), so the worst case is 2ε(1 − G).
For tap 4, G = 0.177, so 1 % resistors give 1.65 % × 13.0 V = 214 mV. Tap 3 (G = 0.236) gives 1.53 % × 9.75 V = 149 mV. The per-cell errors add: **cell 4 ≈ 363 mV from the resistors alone.**
At 0.1 %, both terms shrink by 10×. What remains is the Teensy's reference, VREFH = VDDA = its 3.3 V rail. A 1.5 % (est) rail error is 1.5 % of *every cell*, so 49 mV. The fix is the **LM4040 reference channel**.

**Drain arithmetic.** Suppose the dividers stayed across the pack with `SW1` off. The pack stays plugged into the balance port, and current returns to pack − through Q1's body diode (GND→`BATT_NEG` is its forward direction; see `BUILD_PLAN.md:1062`).
Cell 1 then loses 0.89 mA more than cell 4. That is **1 % imbalance (60 mAh) every 2.8 days**, and cell 1 goes from storage charge (~3000 mAh, est) to empty in **105 days**.
With the gate described below, the off-state leakage is ≤ 1 µA per CPC1017N (datasheet). Cell 1 then sees ≤ 4 µA, which is about **86 years**.

## 3. Recommended design: (a), gated, with a reference channel and calibration

**Balance-lead ground rule: `J_BAL` pin 1 (pack −) stays unconnected.** Tying it to GND would put 26 AWG balance wire in parallel with Q1 and the 12 AWG return. If the main negative connection goes high-resistance, up to 14 A would flow through the balance wire. It would also bypass the reverse-polarity FET (this is the same trap as `BUILD_PLAN.md:798` and `STATUS.md:91`).
The cost of leaving it floating: cell 1 reads **low** by I·R_neg ≈ 14 A × 3.5 mΩ (est) ≈ 49 mV. That errs toward an early trip, which is the safe direction. If it causes nuisance trips, compensate in firmware using the summed INA226 rail power.

```
J_BAL  JST-XH 5p (B5B-XH-A), pin1 = pack−: NC.  J_BAL_THRU B5B-XH-A in parallel → FLY-RC buzzer still plugs in.
per tap k = 1..4 (pin k+1):
  TAPk ─R_PROTk 2.2k 0.1% 1206─┬─ K1..K4 CPC1017N (SSR, 60 V, 16 Ω max) ─ RTk ─┬─ ADCk ──► Teensy pin
                               │                                              ├─ RBk 10.0k 0.1% ─ GND
                               │                                              └─ Ck 1 µF X7R ─ GND
  RT1 1.96k · RT2 16.2k · RT3 30.1k · RT4 44.2k   (0805, 0.1 %, 25 ppm)
SSR LEDs: V5_AUX ─ 1.0k ─ K1.LED ─ K2.LED ─ GND ;  V5_AUX ─ 1.0k ─ K3.LED ─ K4.LED ─ GND
          (5.0 − 2×1.2)/1k = 2.6 mA ≥ 1 mA I_F(on). V5_AUX (UBEC, J2) exists only while SW1 is on → dividers off when robot off.
REF:   +3V3 ─ 1.5k ─┬─ Uref LM4040AIM3-2.5 (0.1 %) ─ GND ; ─ 100 nF ; ──► Teensy pin 20
CUT:   Teensy pin 21 ─ 1k ─ Qc BSS138 gate (100k gate→GND) ; drain ─► power-board VSENSE (C7 pad 1) ; source ─ GND
```

Fault current with a short downstream of R_PROT is tap/2.2k, which is at most **7.6 mA / 0.13 W** (1206 is rated 0.25 W).
If an RB opens, the pin sees the tap through ≥ 4.2k, so injection is ≤ 0.35 mA. If the i.MX injection limit turns out lower, add a BAT54S (open question).
C = 1 µF is the charge reservoir for the SAR sample capacitor. The datasheet wants R_AS ≤ 1 kΩ at a 150 ns sample, and our Thevenin impedance is 3–8 kΩ. With 2 pF charge-sharing into 1 µF the droop is 2 ppm, so the cap is not optional.

| Tap | G = RB/(R_top+RB) | V_pin @ 4.25 V/cell | mV per LSB at tap | Thevenin |
|---|---|---|---|---|
| 1 | 0.70542 | 2.998 | 1.14 | 2.95k |
| 2 | 0.35191 | 2.991 | 2.29 | 6.48k |
| 3 | 0.23632 | 3.013 | 3.41 | 7.64k |
| 4 | 0.17725 | 3.013 | 4.55 | 8.23k |

**Trip points, from counts to volts.** V_tap = N · (VREF/4095) / G. VREF = 2.500 × 4095 / N_ref, and nominally N_ref = 3102.
Take a weak cell 4 with cells 1–3 at 3.70 V: N3 = 3255 → 11.100 V.

| Threshold | N4 | V4 = N4·LSB/G4 | Cell 4 = V4 − V3 | Weak cell 1 instead: N1 |
|---|---|---|---|---|
| WARN 3.40 | 3189 | 14.499 | 3.399 | 2976 |
| SHUTDOWN 3.25 | 3156 | 14.349 | 3.249 | 2845 |
| CUT 3.00 | 3101 | 14.099 | 2.998 | 2626 |

A 250 mV step on cell 4 is 55 counts, so quantization (±4.55 mV) is not the limit.

**Worst-case error budget at 3.25 V/cell, in mV, linear sum**

| Term | Cell 1 | Cell 2 | Cell 3 | Cell 4 |
|---|---|---|---|---|
| Uncalibrated: 0.1 % R + 25 ppm × 25 °C + TUE 4.28 LSB + LM4040 (0.1 % + 100 ppm × 25 °C + ref TUE = 0.49 %) | 23.9 | 47.4 | 78.1 | 108.9 |
| … plus datasheet-max 1 µA pin leakage (I_IN ±1 µA) | 28.0 | 69.9 | 128.9 | 187.6 |
| **After 2-point cal** (residual: 25 ppm × 25 °C, 1 LSB INL, 0.25 µA leak drift (est), ref tempco) | **12.6** | **24.7** | **42.1** | **59.5** |
| Cell 1 only: ground offset I·R_neg (reads low) | −49 @14 A | — | — | — |

The conclusion: **calibration is part of the design, not an option.** Uncalibrated, the error misses the ±75 mV spec. Calibrated, it meets it with 15 mV to spare, and that margin assumes a DMM good to ≤ ±10 mV on each cell (open question).

## 4. Integration

**Pins (both checked).** `main.cpp:105-117` uses 0, 1, 2, 3, 4, 5, 13 (LED), 18 and 19. There is no `analogRead` anywhere in the firmware.
On the logic board, the U6 footprint `nova_v6:Teensy_4.1` only connects pads 0–5, 18, 19, VIN and 3V3, and **pads T14–T17, T20 and T21 are NC** (checked in the exported netlist).
The assignments: **14 (A0) = TAP1, 15 (A1) = TAP2, 16 (A2) = TAP3, 17 (A3) = TAP4, 20 (A6) = VREF_CHK, 21 = CELL_CUT.**
All six are soldered as flying leads to the underside of the Teensy socket pins. `J20` has no spare pins (all 12 are used), so `CELL_CUT` is a separate wire to `C7`.1 on the power board.

**Chain tie-in.**

| Stage | Pack-level (exists) | Per-cell (new) | Executed by |
|---|---|---|---|
| Warn | — | 3.40 V → `/cell_voltages` flag | software |
| Graceful | `BATT_LOW` pin 4 (13.03 V) | 3.25 V is **OR'd into `batt_low_now`**, so the same FSM latch, limp and `ShutdownDecider` run | software |
| Cut | `HARDCUT` (12.56 V) → Q2/Q4 disable `EN_BUCKS`/`EN_JET` | 3.00 V → pin 21 → BSS138 pulls `VSENSE` to 0 → **both** comparators trip | software decides, hardware executes |

The pack-level `HARDCUT` is left untouched and stays independent of firmware. The per-cell cut depends on firmware: if the Teensy is dead, it does not fire. A true hardware per-cell cut (a latch, or the AFE's own UV FET drive) is v7 work.

```cpp
// ~1 analogRead per 1 kHz tick keeps the loop p99 budget; round-robin 5 ch → 200 Hz each
static const uint8_t CH[5] = {14,15,16,17,20};
ema[i] += (analogRead(CH[i]) - ema[i]) * (1.0f/100);        // τ ≈ 0.5 s at 200 Hz
i = (i+1) % 5;
if (tick % 100 == 0) {                                        // 10 Hz evaluate
  float vref = 2.500f * 4095 / ema[4];
  for k: tap[k] = (ema[k]*vref/4095 - cal_off[k]) * cal_gain[k];   // per-channel 2-pt cal (EEPROM)
  cell[k] = tap[k] - (k ? tap[k-1] : 0);  vmin = min(cell);
  sensor_fault = any(cell<2.0 || cell>4.45) || vref out of 3.2..3.4;  // open RB / unplugged lead is loud, not silent
  warn = sustain(vmin<3.40 || sensor_fault, 2s);  shut = sustain(vmin<3.25, 2s);  cut = latch(sustain(vmin<3.00, 2s));
  publish /cell_voltages (Float32MultiArray[4] + vmin + flags)
}
bool batt_low_now = digitalRead(BATTERY_LOW_PIN) == HIGH || shut;   // main.cpp:1260
digitalWrite(21, cut);   // re-asserted within ~2 s after any reboot while the cell is still low
```

A known limitation that this design does not fix: `HARDCUT` only disables the bucks. The UBEC (`J2` → `V5_AUX`), the Teensy and `U8` stay on the pack until `SW1` is opened, so the pack keeps draining after a cut.

## 5. Bench validation

Rig: bench PSU into `J1` (as in `pre-power-on-validation.md` §2), plus a cell simulator. The simulator is PSU+ → 4× 100 Ω 1 W → PSU−, with the ladder nodes wired to a spare XH-5 plug, and a 500 Ω 10-turn pot across the "weak" position.
The DMM on each node is the source of truth. It reads the loaded node, so the ladder's stiffness does not matter.

| # | Test | Pass |
|---|---|---|
| 1 | Calibrate: PSU at 13.20 V and 16.80 V; record N and the DMM value for each tap; store gain/offset | Fit residual ≤ 1 LSB |
| 2 | Accuracy: 12.0, 13.2, 14.8, 16.0, 16.8 V | \|Teensy − DMM\| ≤ 25 mV for every cell (room temp; the ±75 budget includes temperature) |
| 3 | Trips: pot on cell k (k = 1..4), sweep down at ≤ 10 mV/s | WARN 3.40, SHUTDOWN 3.25, CUT 3.00, each **±50 mV** by DMM, for all 4 positions |
| 4 | SHUTDOWN effect | FSM latches BATTERY_LOW, `/battery_low` = true, `battery_shutdown` begins poweroff |
| 5 | CUT effect | `V7V5_LEG` and `V12_JET` go to 0 V, the Teensy stays alive, and the cut is held again after a Teensy reset |
| 6 | Debounce: 0.5 s dip to 2.9 V, then 3 s dip | 0.5 s: no trip. 3 s: trip. |
| 7 | Sabotage: lift RB3; then unplug the balance lead | `sensor_fault` → WARN within 3 s. **Reading "fine" counts as a fail.** |
| 8 | Drain: µA meter in the TAP4 wire; SW1 off, then on | Off: ≤ 5 µA. On: 0.30 ± 0.03 mA. |
| 9 | Fault: short the TAP4 node (after R_PROT) to GND for 10 s | ≤ 8 mA, R_PROT < 60 °C, nothing else changes |
| 10 | Regression | The existing 13.03 / 12.56 V trips still fire at their as-built values |

## 6. BOM

| Qty | Part | P/N (Digikey/LCSC style) | Unit | Ext |
|---|---|---|---|---|
| 2 | JST-XH 5p header (in + buzzer pass-through) | JST B5B-XH-A | $0.20 est | 0.40 |
| 4 | 2.2k 0.1 % 25 ppm 1206 0.25 W | Panasonic ERA-8AEB222V | $0.45 est | 1.80 |
| 4 | 10.0k 0.1 % 25 ppm 0805 | ERA-6AEB103V | $0.35 est | 1.40 |
| 1 each | 1.96k / 16.2k / 30.1k / 44.2k 0.1 % 0805 | ERA-6AEB1961V / 1622V / 3012V / 4422V | $0.35 est | 1.40 |
| 4 | 1 µF 16 V X7R 0805 | Murata GRM21BR71C105KA01L | $0.05 est | 0.20 |
| 4 | PhotoMOS SSR 60 V 100 mA 16 Ω, I_F 1 mA | IXYS CPC1017NTR | $1.20 est | 4.80 |
| 2 | 1.0k 0603 (SSR LEDs) | generic | $0.01 | 0.02 |
| 1 | 2.5 V 0.1 % shunt reference + 1.5k + 100 nF | TI LM4040AIM3-2.5 | $0.70 est | 0.80 |
| 1 | BSS138 + 100k + 1k (CUT) | onsemi BSS138 | $0.15 est | 0.20 |
| — | proto board, 26 AWG leads | — | — | 2.00 est |
| | **Total** | | | **≈ $13 est** |

Only these specs were checked against a datasheet: CPC1017N (60 V, 100 mA, 16 Ω max, 1 mA I_F, 1 µA off-leakage) and the i.MX RT1060 ADC (TUE, I_IN, R_AS).

## Open questions for Aiden

1. **Pack model:** `BOM.md:58` says Ovonic 4S 6000 mAh 120C ×2, with an XH-5 balance lead (`BOM.md:81`). Please meter which pin is pack − before building the harness.
2. **DMM accuracy** on the 4 V and 20 V ranges. It sets the calibration floor: the ±75 mV budget assumes ≤ ±10 mV per cell.
3. **The Teensy footprint says "Pin order … VERIFY vs board"** (`Teensy_4.1.kicad_mod` descr). Please ring out pads 14–17, 20 and 21 before soldering leads.
4. For v6, do you want the CUT bodge to `VSENSE`, or software WARN/SHUTDOWN only, with the pack-level `HARDCUT` as the only cut?
5. Where does the board sit? Next to the pack (short balance lead, long 3 V analog leads) or next to the logic board (the opposite). I'd default to next to the logic board, with the 1 µF caps at the Teensy end.
6. Do you want v7 to move to the BQ76920 with an ISO1540, which gives a hardware UV cut and removes the calibration step?
