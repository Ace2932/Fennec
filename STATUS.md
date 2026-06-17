# NOVA — Status Board

Single-pane blockers / in-progress / next-actions. Hand-maintained; the detail
lives in `README.md` (Open Decisions + Build Roadmap), `docs/order-list.md`,
per-board `ROUTING_HANDOFF.md`, and memory. Update when state changes.

_Last updated: 2026-06-15 (B1 cleared — both boards fab-ready, gate GO)_

## ✅ Recently cleared
- **B1 — power board arm placement + routing — DONE** (PR #13). U12 + J14 placed/routed, U5.EN routed on EN_BUCKS, V7V5_ARM/BATT_NEG widened + high-current pads solid, duplicate U12/J14 + dangling chain cleaned, gerbers regenerated. **fab_gate: GO on both boards.**

## 📋 Pre-fab checklist (2026-06-16 board↔order + spec-margin review)
Board parts all match the order; no orphans. Action items from the margin review (detail in `order-list.md`):
- **C8/C9 → 470µF/35V** (not 25V) — they're on the raw 16.8V VBAT rail (25V = 1.49×). ✅ order updated.
- **TVS clamps (SMBJ8.5A) are not optional** — protect the 25V V7V5_LEG bulk caps + servos from ~21V e-stop regen.
- **Hip buck D42V110F12 — tightest rail, the one to PROVE on the bench.** Two compounding tight margins: (1) current ~1.1× (~8A vs ~9A derated @14.8V); (2) **dropout headroom ~1.2V** — it's a 12V output from a 4S rail that sags to 13.2V LVC, so under load+sag it could drop out of 12V regulation → **hip servos brown out mid-gait**. Bench-gate before any gait: 4× 30kg hip stand-in, sweep Vin 16.8→13.2V, confirm (a) thermal IR ok after 10min AND (b) 12V holds (no dropout/>100mV droop) at the low-Vin end. **Plan B is a drop-in:** bucks are off-board, so swap to D24V150F12 or parallel — **no board respin**. Bounded risk.
- 🟠 **TODO (must do pre-fab) — Q1 gate hardening + LVC comparator decoupling (one board edit, bundle).** Board change → reopens the F8/route/gerber cycle once; do both at the same time.
    - **Q1 hardening:** guards Q1's gate vs >20V transients (Vgs 16.8/±20V = 1.19×). Low-value (keyed XT60 + bulk caps), adding for peace of mind.
    - **LVC decoupling (2026-06-17 review):** the LM393 (U8) has **no V+ decoupling and no reference filtering** — V5_AUX (its supply *and* the source of VREF_G/H) is undecoupled, and VREF_G/VREF_H are unfiltered (only VSENSE has C7). → trip-threshold jitter / chatter risk on a safety cutoff.
    - **Best in eeschema, NOT headless** (polarized zener + `Device:R`/`Device:D_Zener` lib_symbols not cached in 01_battery + Q1 mirrored → headless segfault/polarity risk).
    - **eeschema recipe:** *01_battery:* break gate↔VBAT_PROTECTED; add `Device:R` **R17=100Ω** (VBAT_PROTECTED→R17→gate) + `Device:D_Zener` **D1=15V** (BZT52C15, **cathode→gate / anode→GND**). *06_safety_chain (at U8):* add **C10=0.1µF** V5_AUX→GND (decouple V+) + **C11=100nF** VREF_G→GND + **C12=100nF** VREF_H→GND. Annotate → ERC → F8 → place (R17/D1 at battery edge; C10/C11/C12 at U8) → route → save.
    - **Then me:** netlist-verify (R17 VBAT_PROTECTED↔gate; D1 cathode→gate/anode→GND; C10/C11/C12 on the right nets) → re-pour → DRC → regen gerbers → fab_gate.
    - Parts (in cart): **R17 100Ω 0603 · D1 15V zener SOD-123 (BZT52C15) · C10/C11/C12 = 100nF 0603 ×3**.
- **SW1 needs the 15–20A screw block** (kit block is 10A; SW1 ~15A).
- Physical-verify before fab: INA226 module pitch, off-board buck XT30 pin-order, Teensy footprint, L1 (SRR1260) land, 1000µF Ø10×17 fit.
- **🔴 Mezzanine height (≤~17mm under the logic board, ~20mm standoff gap):** C8/C9 = **25V** (Ø10×16) — NOT 35V (Ø10×20 hits the top board; 25V meets 80% derating anyway). Also confirm the **INA226 breakout modules on headers** clear the 20mm gap (tallest under-stack parts). Reverted the earlier 35V call.
- Comfortable margins (no action): Q1 Vds/Id, XT60, INA226 (2.2×), 0603 R power, BSS138, LM393, L1 current (2.8×).
- **Trace current-capacity audit (2026-06-17) — PASS, 1 optional item.** Every high-current rail rides a pour/plane (audit-tool "UNDER" flags were false: thin traces are taps, not bulk path). V7V5_LEG → F.Cu pour + 1.5mm taps (~6A/tap); VBAT_PROTECTED → In2 plane; GND → In1 plane + B.Cu; BATT_NEG → F.Cu pour (1.3mm Q1 pin-escape short, pin-pitch limited); V12_HIP/ARM 3mm (~13A cap); V12_JET/L2/V5_AUX poured. **No vias on any power net** (no via-current risk). 
    - 🟡 **Optional (GUI): VBAT (J1→SW1) is the one no-pour rail** — 3mm trace, ~15A worst-case peak (stall). 3mm/2oz → ~33°C rise @15A, but that's peak-only; nominal walk ~5–8A → ~9°C. Short run (~26mm), heat-sunk into big XT60/SW1 THT pads. **Acceptable as-is.** Tried 4mm headless → hits board edge (edge-clearance); tried parallel B.Cu → B.Cu congested there (clearance/hole collisions). If you want the robustness, **add a parallel B.Cu run + stitch vias in the GUI during the B1 reopen** (you'll see the bottom congestion). Not worth a dedicated cycle.

## 🧪 Safety-chain findings (2026-06-17 circuit-logic review) — feed into B3 bench validation
Logic + divider math **verified correct** (graceful 13.02V, hard ~12.4V w/ hysteresis, fail-safe E-stop open=off, BATT_LOW at Teensy-safe 3.3V). No wiring bugs. Bench-validation worries to prove:
- **LVC trip accuracy is referenced to V5_AUX (the 5V UBEC), not a precision ref** → all trips scale with the UBEC's actual output (4.85V → graceful ~12.6 / hard ~12.0 = over-discharge). **Bench-trim trip points against MEASURED V5_AUX.** Design-improvement option (not now): TL431 precision ref feeding the dividers decouples it.
- **Graceful→hard timing window (13.0→12.4V) may be shorter than the Jetson's clean shutdown (~15-30s)** → if pack crosses 12.4V mid-shutdown, hard-cut yanks power → SD-corruption risk. **Bench-measure that 13.0→12.4 takes longer than `systemctl poweroff`** (likely self-extends — load drops during shutdown → VBAT rebounds → may un-trip hard cut; confirm).
- **Power-on false battery-low latch — ✅ FIXED in firmware (PR #17):** boot read of BATTERY_LOW was instantaneous off a V5_AUX-ramping comparator → nondeterministic false latch. Now settle-confirmed (250ms + every-sample-HIGH). Bench: power-cycle 10× cold, confirm no spurious latch.
- **V5_AUX death = no LVC cutoff** (comparators + pull-ups die) → over-discharge. Known SPOF, mitigated by the independent balance-plug buzzer (owned). Keep buzzer on the pack whenever SW1 is on.

## 🔌 Logic-board / bus findings (2026-06-17 review) — feed into firmware bench bring-up
74LVC125 half-duplex bus logic + JP_BUS_MASTER + R1(22Ω)/FB1(ferrite) integrity **verified correct**. Checks to do at bring-up:
- **🔴 BRING-UP-CRITICAL: bus is driven at 3.3V** (U7 74LVC125 VCC=+3V3, idle pull-up R7→+3V3). LVC is 5V-tolerant on *inputs* (reads 5V servo replies fine) but only *drives* 3.3V. **Confirm STS3215 VIH ≤ ~2.3V so 3.3V is a solid high** — *probably OK* (STS3215 commonly driven at 3.3V in LeRobot/SO-ARM) but **bench-test a single servo on the real bus FIRST.** If it needs 5V: power U7 from V5_AUX + R7 to 5V, or level-shift. Fail-early on the bench before assuming the bus works.
- **WS2812B (J11) on V5_AUX via JST-XH (3A) + J20:** keep LEDs **status-only (few)** — a full strip exceeds the JST pin / J20 / 5A UBEC budget. (5V Nano drives the data → WS2812B VIH ok ✓.)
- **OLED (J10) SPI driven at 5V** by the 5V Nano → verify the SSD1331 module is 5V-logic-tolerant (likely ok — PR #2 OLED level fix).
- **LVC sense/comparator GND vs 15A power-GND bounce:** mitigated by the C7 RC filter + comparator hysteresis (mV bounce ≪ 0.16V band), but confirm the divider/comparator GND taps a *quiet* point, not the 15A return path.
- No 5V↔3.3V cross-domain clash: Nano's 5V signals stay logic-board-local; all J20 cross-board nets (I2C, BUS_SERVO, BATT_LOW) are 3.3V ✓.
- **I2C @ 400kHz with 4 INA226 modules + the mezzanine ribbon:** bus C (~150-250pF from 4 modules + ribbon + traces) vs the 4.7k pull-ups — verify rise time at bring-up; if marginal → 2.2k pull-ups or drop to 100kHz.
- **Inrush at SW1 close:** C8/C9 (940µF on VBAT) + buck input caps → tens of A brief inrush through the 20A switch contacts. RC-build-acceptable; watch for contact wear → NTC inrush limiter if it becomes an issue.

## 🔴 Hard blockers (gate everything downstream)
| # | Blocker | Owner | Gates | Notes |
|---|---|---|---|---|
| B2 | **CAD measurement pass** — replace `TODO-CAD` link lengths | you (CAD) | real gait / sim / MoveIt | femur/tibia/hip offsets + joint ranges, in `nova_description` xacro **and** `nova_locomotion` (keep synced). Math/structure already correct + tested. |
| B3 | **Safety-chain bench validation + MRBF fuse install** | you (bench) | ANY LiPo power-on | LVC 13.0/12.4 V, E-stop, hard-cutoff, INA cal unvalidated; battery lead unfused until MRBF in. Checklist in `order-list.md` "After things arrive". |

## 🚧 In progress / open PRs
| PR | What | State |
|---|---|---|
| #13 | power board arm routed + cleaned + gerbers | open |
| #10 | nova_locomotion (leg IK + trot) + ros-pytest CI | open |
| #3 | "LE_NOVA ECC bundle" | open — **predates current work, triage/close?** |
| — | #6–#9, #11 (order-list, URDF, fab_gate, logic ERC, STATUS) | ✅ merged |

## ⏭️ Next actions (rough order)
1. Merge PRs #13 + #10 (triage #3).
2. **Fab:** both boards ×5 + stencils → PCBWay (both pass `fab_gate` GO).
3. Place **FINAL order** (DigiKey cart per `order-list.md` + Pololu D42V55F7 arm buck + Amazon +1 INA226 + Feetech cables).
4. **B2:** CAD pass → refine `TODO-CAD` across URDF + locomotion.
5. Assemble + **B3** (MRBF fuse + safety bench validation) before any LiPo.
6. Firmware bench bring-up (real 74LVC125 + INA226 + STS3215) + servo ID assignment (`docs/setup-servos.md`).
7. Leg first-article print (PA6-CF).

## 🟡 Not started (deeper backlog)
- `gait_node` — cmd_vel → trot → IK → `/joint_commands` (Phase-2 glue over the tested core).
- `nova_calibration` per-joint `config.py` fill (FROM CAD) → servo home auto-detect.
- Phase 2 sim: MJX gait training (now unblocked by URDF, pending B2).
- Phase 3: Nav2 / autonomy. Phase 4: arm install + MoveIt + VLA.

## Phase snapshot
- **Phase 0** (pre-build): **both boards fab-ready (fab_gate GO)** — submit to PCBWay + place FINAL order to close it out.
- **Phase 1** (HW bring-up): firmware skeleton green (p99 1 µs, isolation), bench bring-up not started.
- **Phase 2+** (locomotion/autonomy/arm): groundwork only (URDF + IK/gait scaffolded; pending B2 CAD).
