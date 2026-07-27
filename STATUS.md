# NOVA — Status Board

Single-pane blockers / in-progress / next-actions. Hand-maintained; the detail
lives in `README.md` (Open Decisions + Build Roadmap), `docs/order-list.md`,
per-board `ROUTING_HANDOFF.md`, and memory. Update when state changes.

_Last updated: 2026-07-26_

## 🔴 2026-07-26 — CAD review: rear hip placement + the posture safety table
Full review: [`docs/cad-review-2026-07-26.md`](docs/cad-review-2026-07-26.md); backlog rows CR26-1..8.
Open items are tracked as issues: **#164** (rear ROM rows + rear hfe sign, sev:high) · **#165** (URDF/MJX hip grid)
· **#166** (CAD gates unrunnable off-laptop / not in CI) · **#167** (rib vs drop-in acceptance) · **#168** (proud wheel heads).
- **FIXED**: the rear hip was placed as a *translation* of the front in `chassis/check_fit.py`
  `coax_to_trunk_bases()` + `preview_assembly.py`. One shoulder part, flange on the trunk end face
  (±63.5 + 77.7 = ±141.2 hip station) ⇒ the rear is that placement **yawed 180°**. Translated put the
  rear flange 155 mm behind its own trunk and the rear hfe axis at −152.8 instead of −129.6 — and bolted
  the leg to a shoulder the *same gate* placed the other way round.
- **🔴 OPEN, owner + real `servo.stl`**: `rom_envelope_table.py`'s **REAR rows are therefore invalid**, and
  since `limits.py` loosened the hfe scalar to mechanical ±86 (2026-07-25) that table is the **sole**
  chassis protection. Re-measured rear = front ([−94,+66] @ haa 0/kfe −109) vs the shipped flat
  [−77.2,+95] at every kfe. **Re-run `hfe_envelope.py`, copy to `nova_ops/`, and pin the leg-local→canonical
  hfe SIGN for the yawed rear hips** (same class as #153/#155). No LiPo-powered ROM extremes on the rear
  legs until then.
- **FIXED (docs)**: leg chirality pairs **diagonally** (front +y = R, rear +y = **L**) — `leg_v6/README.md`.
- **🟠 DECISION (gait/sim)**: URDF `body_half_x`/MJX `MOUNT.x` 0.1412 is the *stock* hfe station; v6 puts the
  pitch axes at ±129.6 ⇒ the modeled stance is 23.2 mm longer fore-aft than the robot. Folds into B2.

## 🟢 2026-06-27 — Boards FAB-READY (supersedes the "Pending board edit" + B1 items below)
Both boards **fab_gate GO**, branch `feat/power-board-arm-routed` (HEAD 475cdc5). The two "Pending board edit"
sections + **B1 (U12+J14 place)** below are all **DONE**.
- ✅ **Q1 gate-harden** placed + routed (R17/C_gs1/D1/R_gs1). Q1 = **drain BATT_NEG / source GND** (reverse-prot correct; the "source=BATT_NEG" doc label was wrong — fixed in order-list).
- ✅ **Mounting-hole keepouts** H1–H4 (brass-safe). ✅ **SW1 drill 1.2→1.5mm** for **TB007-508-02BE** (MKDS OOS → sub ordered ×10); SW1 value → Contura_SPST_18A.
- ✅ **VBAT_PROTECTED reroute-gap closed** · **VBAT + V12_HIP B.Cu pours** · **via annular 0.5→0.55mm** (39 vias, 2oz).
- ✅ **Thermal-relief current-throat fix** — SW1.2/U1.4/Q1.3 (14/10/14A) were plane-only 0.5mm spokes (~6A); VBAT_PROTECTED + GND inner planes → **SOLID**, leg spokes 2.0mm.
- ✅ **Fuse = MRBF-30** (Blue Sea 5191); Class T superseded. **Fab = PCBWay 2oz + stencils (NOT DKRed — 1oz/no-stencil).**
- **Open before PCBWay (assembly-time, not board-file):** physical footprint verify (Teensy U6 + bucks U1–U5) · hand-tack 100nF on U8 LM393 Vcc · INA IN± inline harness (leg total-current deferred v7) · **dual-voltage servo harness (FRY-critical)**. Detail: `docs/pre-power-on-validation.md` §1c/§1d.

## 🔬 System audit 2026-06-18 (cross-domain: FW / PCB / SW / docs)

Multi-agent alignment pass. Core electrical contracts (INA226 addrs/shunt, bus
1Mbaud, 13.0/12.4 V thresholds, Teensy↔PCB pin map) **align**. Open items below.

**Fixed this pass (commits 2026-06-18):**
- `/rostest` skill + local test cmd was `PYTHONPATH=.` → collected **0 tests** (green-on-nothing). Fixed to package-root PYTHONPATH; preflight run only when `rclpy` present. (CI `ros-pytest.yml` verified FINE — it `cd`s into each package so its `PYTHONPATH=.` resolves correctly + already ignores `test_preflight.py`.)
- Teensy `firmware/README.md` pinout table contradicted `main.cpp` (Serial2 7/8 vs real Serial1 0/1, E-stop 2 vs 5, batt 3 vs 4, OE polarity) → corrected to match code/PCB.
- `main.cpp` NaN-in-commanded-position → `(uint16_t)NaN`=0 far-end slam. Added NaN guard at goal clamp.
- Battery capacity 4000→6000 mAh + runtime in `power-budget.md`, `BOM.md` (primary docs).

**🔴 Open misalignments (NOT yet fixed — need decision/bench):**
- **Joint-ID→joint map disagrees across 3 files**: `safety_envelope/limits.py` (type-grouped 1-4/5-8/9-12) vs `nova_description/joint_id_map.yaml` (per-leg interleaved) vs `servo_homing/config.py` (per-leg coxa/femur/tibia). Wrong limits → wrong joints, silent. **BLOCKS safe envelope. Pick canonical map (folds into B2).**
- 74HC125→SN74LVC125A + "star ground"→GND-plane + Serial2→Serial1 SWEPT across active docs 2026-06-27 (historical changelog/research/weekly-checklists/deprecated-board left as-dated).
- `dimensions.md` LiPo pocket still sized for 4000 mAh pack — needs real 6000 mAh pack dims (CAD input, B2).

**🔴 Weak points / breaks (ranked, NOT fixed):**
1. **No torque/current/velocity limit ever written to servos; no thermal cutoff.** FW clamps position only; overload/overheat bits read+counted, never acted on. Stalled joint → full stall current indefinitely. Also FW never writes `REG_TORQUE_ENABLE` (servos may ignore goals if EEPROM default off).
2. **E-stop torque-cut path unconfirmed** — FW only stops bus writes; does hardware EN_BUCKS kill (Q2/Q3) actually de-energize leg/hip so robot goes limp? (Q1 looks reverse-prot only.) Verify on bench (B3).
3. **Arm buck U5.EN tied always-on** (VBAT_PROTECTED) → E-stop+hardcut leave arm energized w/ torque = crush hazard. DNP now; Phase-4 blocker. `V7V5_ARM` also a dead net. See [[project-power-board-arm-phase4]].
4. **`safety_envelope/wrapper.py` load-refusal inverted** — refuses load-*reducing* motion too (vs docstring). Can keep joint pushing into stall.
5. **No Jetson-side liveness watchdog** — nothing consumes `/heartbeat`/`/command_stale`; FW reset or agent death mid-motion goes unnoticed (leans on FW 500 ms freeze + 12.4 V hardcut).
6. **Hip rail D42V110F12 ~1.0× headroom** — brownout under 4× hip walk; all-stall (20 A) exceeds buck → relies on a load-monitor that **isn't confirmed written**. Bench (B3).
7. Blocking bus reads in 200 Hz RT loop (missing servo burns full 2500 µs/tick).
8. micro-ROS `RCCHECK` still hard-bricks on transient agent hiccup during ~30 init calls (only support-init made retry-safe).
9. Zero first-article prints; femur Y=±24 reach + tibia placement eyeballed (B2). 6→8 mm bearing sleeve unsourced.

**✅ DECIDED 2026-06-27 (gate fixes — unblocks the firmware sprint):**
1. **Joint-ID map = PER-LEG SEQUENTIAL** — leg1 coxa/femur/tibia = IDs 1-3, leg2 = 4-6, leg3 = 7-9, leg4 = 10-12. Conform `limits.py` (type-grouped) + `joint_id_map.yaml` (interleaved) to `servo_homing/config.py`'s per-leg scheme.
2. **E-stop = LIMP** — hardware Q3 kills buck power → servos unpowered/collapse (gear-damped, not free-fall). **PLUS add a firmware graceful soft-stop** (ramp to stable crouch) for non-emergency stops.
3. **FW always writes `REG_TORQUE_ENABLE=1` on init** — defensive, no dependence on EEPROM default.
4. **Implement the all-stall load-monitor** — per-servo `effort[]` → back off before 4× hip stall (~20A) browns the hip rail (weak-point #6).
5. **Implement a Jetson liveness watchdog** — consume `/heartbeat` → catch agent/Jetson death mid-motion.

Full audit detail in memory: [[project-system-audit-2026-06]].

## ✅ DONE 2026-06-27 — Q1 gate hardening (was: Pending board edit; spec kept for reference)
- **Q1 gate hardening — gate soft-start + zener backstop (⚠️ SOA-gated).** Q1 gate=VBAT (≤16.8V),
  Vgs(max)=20V → 3.2V headroom. **Primary = soft-start: R17 10k + C_gs 470nF** (τ=4.7ms ≫ 0.5ms LC
  ring → Q1 ramps on, bulk charges gently, no overshoot). **D1 18V zener (BZT52C18) = backstop**
  (R17=10k → clamp ~18V; 100Ω→21V fails). NOT 15V, NOT a TVS (~29V>20V). +R_gs 100k bleed (opt).
  **⚠️ SOA check:** soft-start dumps ½CV²≈0.77J in Q1 (linear) over the ramp — must stay in IRLB3034
  10ms SOA, else use a precharge resistor (energy in R not FET). **BENCH-VALIDATE transient (scope)
  before fab.** New parts to order: **C_gs 0.47µF 0603 X7R 25V — DK 1276-2082-1-ND (CL10B474KA8NFNC) ✅** + **D1 BZT52C18 zener — DK 4878-BZT52C18CT-ND, SOD-123F ✅** (rest owned). **Reminders when placing the edit:** use **SOD-123F** footprint for D1; soft-start (R17+C_gs) is PRIMARY, zener is BACKSTOP; SOA-check Q1; bench-validate transient before fab. 
  Sequence: eeschema place → F8 → route → DRC 0 → **regen gerbers** → fab_gate GO.

  **EXACT eeschema edit — sheet `01 Battery Input + Reverse Protection`** (Q1 gate pad1 is currently
  tied DIRECTLY to `VBAT_PROTECTED`; break that and insert the network):
  ```
  VBAT_PROTECTED ──[R17 10k]──┬── Q1_GATE (new net) ── Q1.pad1 (gate)
                              ├──[C_gs 0.47µF]── BATT_NEG
                              ├──[D1 zener ▷|]── BATT_NEG   (cathode/band → Q1_GATE)
                              └──[R_gs 100k]── BATT_NEG
  ```
  - **R17** 10k 0603 (R_0603): `VBAT_PROTECTED` → `Q1_GATE`
  - **C_gs** 0.47µF 0603 (C_0603): `Q1_GATE` → `BATT_NEG`
  - **D1** BZT52C18 **SOD-123F**: **cathode→`Q1_GATE`**, anode→`BATT_NEG` (gate is +, band toward gate)
  - **R_gs** 100k 0603 (R_0603): `Q1_GATE` → `BATT_NEG`
  - **Reassign Q1 pad1 net** `VBAT_PROTECTED` → `Q1_GATE`.
  Place all four near Q1's gate pin (Q1 TO-220 ≈ 98.5,−56.5 on board top). Then **F8** → I route the
  4 parts + `Q1_GATE` net headless (incremental), re-pour, DRC, regen gerbers.
  **Precharge resistor:** buy 10/22/47Ω 2–3W as insurance, but do NOT add to the board unless the SOA
  check fails soft-start — it's an *alternative* (goes across SW1 + needs a 2-stage connect procedure),
  not additive. Decide at bench.

## ✅ DONE 2026-06-27 — mounting-hole keepouts (was: Pending board edit)
- **All 4 mounting holes (H1–H4) sit in power/GND zones** (H1=BATT_NEG, H2=V7V5_LEG, H3/H4 GND/VBAT). Zone clearance ~0.25mm → copper under the ~3mm standoff flange → **metal standoff shorts the net to the standoff/logic board.** H1 (BATT_NEG) → GND on logic side = dead short across Q1.
  - **Fix:** add Rule Area keepout (**~7mm dia, keep-out copper fill, all copper layers**) on each of H1/H2/H3/H4 → re-pour. No copper under any standoff.
  - **Standoffs:** brass M3×20 (PATIKIL 50pc, owned) work on ALL 4 holes **once the keepout is in** (no copper under flange/barrel). Nylon at H1 = optional extra; not required. 20mm body = the mezzanine gap ✓.

## ⚠️ Servo harness — dual-voltage bus (FRY-CRITICAL, pre-bringup)
- Bus = 1 shared signal, 2 voltages, boundary **inside each leg** (hip 12V / femur+tibia 7.5V). Stock 3-wire daisy across a 12V↔7.5V transition shorts VCC → fried servo.
  - **Need:** power per voltage segment + **VCC-isolated (signal+GND-only) links at every hip→femur transition** + **extension daisy cables for long leg runs** (Feetech/AliExpress — never received). Meter every servo VCC=correct rail before power. Spec in `hardware/wiring/README.md`. Confirm 12 servos in hand.

## 🔴 Hard blockers (gate everything downstream)
| # | Blocker | Owner | Gates | Notes |
|---|---|---|---|---|
| B1 | **Place U12 + J14 on power board** (GUI) | you | power routing → DRC → gerbers → fab | board too dense for headless placement; F8 already done. Then I route V7V5_ARM/GND/EN/U12-I2C headless. |
| B2 | **CAD measurement pass** — replace `TODO-CAD` link lengths | you (CAD) | real gait / sim / MoveIt | femur/tibia/hip offsets + joint ranges, in `nova_description` xacro **and** `nova_locomotion` (keep synced). Math/structure already correct + tested. |
| B3 | **Safety-chain bench validation + MRBF fuse install** | you (bench) | ANY LiPo power-on | LVC 13.0/12.4 V, E-stop, hard-cutoff, INA cal unvalidated; battery lead unfused until MRBF in. Checklist in `order-list.md` "After things arrive". |

## 🚧 In progress / open PRs
| PR | What | State |
|---|---|---|
| #10 | nova_locomotion (leg IK + trot) + ros-pytest CI | open |
| #9 | nova_description URDF (sim keystone) | open |
| #8 | fab_gate.py two-board readiness gate | open |
| #7 | logic board ERC → 0 | open |
| #6 | order-list FINAL pre-build order | open |
| #3 | "LE_NOVA ECC bundle" | open — **predates current work, triage/close?** |

## ⏭️ Next actions (rough order)
1. Merge PRs #6–#10 (triage #3).
2. **B1:** place U12+J14 → save → I route → `fab_gate` GO on both boards.
3. Fab: both boards ×5 + stencils → PCBWay. Place FINAL order (DigiKey cart + Pololu arm buck + Amazon INA + Feetech cables).
4. **B2:** CAD pass → refine `TODO-CAD` across URDF + locomotion.
5. Assemble + **B3** (MRBF + safety bench validation) before any LiPo.
6. Firmware bench bring-up (real SN74LVC125A + INA226 + STS3215) + servo ID assignment (`docs/setup-servos.md`). Run bus half-duplex timing checks — `pre-power-on-validation.md` §10.
7. Leg first-article print (PA6-CF).

## 🟡 Not started (deeper backlog)
- `gait_node` — cmd_vel → trot → IK → `/joint_commands` (Phase-2 glue over the tested core).
- `nova_calibration` per-joint `config.py` fill (FROM CAD) → servo home auto-detect.
- Phase 2 sim: MJX gait training (now unblocked by URDF, pending B2).
- Phase 3: Nav2 / autonomy. Phase 4: arm install + MoveIt + VLA.

## Phase snapshot
- **Phase 0** (pre-build): ~closing — **both boards fab-ready GO** (B1 done); open items are assembly-time only.
- **Phase 1** (HW bring-up): firmware skeleton green (p99 1 µs, isolation), bench bring-up not started.
- **Phase 2+** (locomotion/autonomy/arm): groundwork only (URDF + IK/gait scaffolded).
