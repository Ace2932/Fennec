# NOVA — Status Board

Single-pane blockers / in-progress / next-actions. Hand-maintained; the detail
lives in `README.md` (Open Decisions + Build Roadmap), `docs/order-list.md`,
per-board `ROUTING_HANDOFF.md`, and memory. Update when state changes.

_Last updated: 2026-08-13. **The solder/bench state here is a MIRROR of Notion
(🔧 Soldering / Assembly Steps) and lags it — read Notion before acting.**_

## 🔧 2026-07-31 — BOARDS IN HAND, SOLDERING STARTED

Both boards fabbed, delivered and being populated. **Canonical build sequence:
[`hardware/pcb-mods/BUILD_PLAN.md`](hardware/pcb-mods/BUILD_PLAN.md)** (stages 0–10, tip +
temperature per stage in §2a). Everything below dated 2026-07-26 or earlier is history;
resolutions are marked inline rather than deleted.

**Two things blocked or endangered the current step — neither was on any list. One is now
closed; ~~#1~~ is kept per this file's mark-inline convention.**

1. ~~**Solder is not confirmed to exist.**~~ ✅ **CLOSED 2026-08-01 — Sn63Pb37, 1 mm, 1.8 %
   flux core, in hand.** Leaded as recommended, so the **leaded** column in `BUILD_PLAN.md`
   §2a is the live one and nothing shifts +30 °C. *Original text:* `master-bom.md` read
   `Thin solder 0.6-0.8 mm | ⬜ verify` and no doc recorded the ALLOY, while every
   temperature in §2a depends on it (leaded 183 °C vs SAC305 217–220 °C, and the plane-tied
   pads get materially harder on lead-free). The one surprise was **diameter: 1 mm, not
   0.6–0.8** — helps stages 4/7/8, hinders 1/3, fixed by tin-the-tip-and-place, not a second
   spool.
2. **The Q1 SOA check never happened, and cannot be done with owned gear.** The gate-harden
   spec below is explicitly *"SOA-gated … BENCH-VALIDATE transient (scope) before fab"* —
   **fab happened without it.** Soft-start dumps ½CV² ≈ **0.77 J** into Q1 in its linear
   region; it must sit inside the IRLB3034 10 ms SOA. **No scope is owned** (Rigol DHO804 was
   deferred to Phase 5), and the documented fallback — a 10/22/47 Ω 2–3 W precharge resistor —
   **is not in any ✅ ordered list.** See "Next actions".

**🔴 Mezzanine height — the under-stack constraint (recovered from `9f19770`, 2026-06-17, which
never reached main):** parts on the power board's TOP face sit in the **~20 mm standoff gap**
under the logic board, so the usable height is **≤ ~17 mm**.

- **`C8`/`C9` = 470 µF / 25 V (Ø10×16), NOT 35 V.** The 35 V part (UPW1V471MPD) is ~Ø10×**20 mm**
  and would hit the top board. 25 V still meets 80 % derating on the 16.8 V rail (67 % of rated),
  so this costs nothing electrically. `order-list.md` carried the superseded "use 35 V" text on
  main until 2026-08-15 because the commit that fixed it was only ever on a branch.
- ⬜ **Confirm the INA226 breakout modules on headers clear the 20 mm gap** — they are the
  **tallest under-stack parts**, and they go in at stage 10. Check before fitting, not after.

**Verified clean this pass** (read from the board file, not assumed):

- **Mounting-hole keepouts are real AND effective — proven against the actual fill.** All four
  H1–H4 have 7 mm-dia keepouts on all four copper layers (`copperpour: not_allowed`). That rule
  alone proves nothing, since it still permits tracks. Three checks, all clear:
  **334 track segments + 62 vias** — none within 3.5 mm; **168 component pads** — none within
  3.5 mm; and, the one that actually matters, **the poured copper itself**: 196 sample points
  (centre plus r = 1/2/3/3.4 mm × 12 directions, per hole) tested point-in-polygon against all
  **45 filled polygons** — **zero covered**. Closest pour vertex to any hole centre is
  **3.483 mm**, i.e. the fill boundary tracing the keepout edge exactly.
  (H1 is `BATT_NEG` — a standoff bridging it to logic-side GND would be a dead short across Q1.)
  - ⚠️ **Consequence nobody had written down: do NOT put a flat washer under these standoffs.**
    The clear copper circle is **6.97 mm** diameter. A DIN125 M3 washer is **7.0 mm OD** — it
    overhangs the pour edge, and with the 3.2 mm hole / 3 mm screw play it will definitely sit
    on copper on one side. Solder mask is then the only insulation under a clamped fastener,
    which is not what mask is rated for. **Brass M3×20 standoff directly on the board is fine**
    (hex ~5.5 mm A/F, 6.35 mm across corners → ~0.3 mm radial clearance). If you want a washer,
    use nylon or one with OD ≤ 6.9 mm.
- **All 9 AMASS XT connectors** still pad1 = − / pad2 = +. The 2026-06-29 fix held.
- **XT30 mating halves needed = 16** (8 board connectors J3–J7/J12–J14, plus 8 across the four
  populated buck stations U1–U4 at 2 each); 18 if U5 is ever fitted. This closes the
  "confirm ~18 mating pairs" item on the Notion board.
- **U12 (power board) must be POPULATED** as the L2 monitor at 0x45 — it stopped being an arm
  part on 2026-06-30 and `-D NOVA_INA226_L2` is enabled. See `BUILD_PLAN.md` §4.

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
  hfe SIGN for the yawed rear hips** (same class as #153/#155) — the rear rows must be **NEGATED**
  (`canonical_rear = (−hi_local, −lo_local)`; the URDF hfe axis is uniform in world, so canonical +hfe folds
  toward the trunk at the front and away at the rear). Under the old translated placement that negation was a
  no-op, so an un-negated regeneration silently puts the rear bound on the WRONG SIDE. No LiPo-powered ROM
  extremes on the rear legs until then.
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
- ✅ **Fuse = MRBF-30** (Blue Sea 5191); Class T superseded. ~~**Fab = PCBWay 2oz + stencils (NOT DKRed — 1oz/no-stencil).**~~ → **SUPERSEDED 2026-06-29: fab = JLCPCB, and NO stencils.** Switched on cost (PCBWay $277 vs JLC $121 for the power board); PCBWay's 0.125 mm-annular flag was a non-issue at JLC. **Ordered 2026-07-01**, both boards in one parcel, ~$203 all-in. Power = 4L 90×112, 2 oz outer / 0.5 oz inner, ENIG, TG155. Logic = 4L 84×78, 1 oz, HASL-lead, TG135. No stencil — zero fine-pitch, hand-soldered by design.
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
| ~~B1~~ | ~~**Place U12 + J14 on power board** (GUI)~~ **✅ DONE 2026-06-27** — placed, routed, DRC 0/0, gerbers regenerated, boards ordered 2026-07-01 and delivered. Verified on the ordered board: `J14.2` = `V7V5_ARM`, `U5.3` = `EN_BUCKS`. | — | — | Kept for the record; no longer a blocker. |
| B2 | **CAD measurement pass** — replace `TODO-CAD` link lengths | you (CAD) | real gait / sim / MoveIt | femur/tibia/hip offsets + joint ranges, in `nova_description` xacro **and** `nova_locomotion` (keep synced). Math/structure already correct + tested. |
| B3 | **Safety-chain bench validation + MRBF fuse install** | you (bench) | ANY LiPo power-on | LVC 13.0/12.4 V, E-stop, hard-cutoff, INA cal unvalidated; battery lead unfused until MRBF in. Checklist in `order-list.md` "After things arrive". |

## ✅ PRs — all closed out (verified via `gh` 2026-07-31)
| PR | What | State |
|---|---|---|
| #10 | nova_locomotion (leg IK + trot) + ros-pytest CI | **MERGED** |
| #9 | nova_description URDF (sim keystone) | **MERGED** |
| #8 | fab_gate.py two-board readiness gate | **MERGED** |
| #7 | logic board ERC → 0 | **MERGED** |
| #6 | order-list FINAL pre-build order | **MERGED** |
| #3 | "LE_NOVA ECC bundle" | **CLOSED** (not merged — triaged away) |
| #13 · #14 · #17 | power board routed · docs/review hub · firmware boot-settle | **MERGED** |

~~Currently open PRs are the leg_v6 HFE-joint set (#232 / #233 / #234)~~ — stale. As of 2026-08-02:
**#256** (aerosol defluxer) · **#254** (fasteners into the BOM) · **#253** (shoulder_plate handedness
+ print orientation) · **#250** (cable_clip count) — all docs-only; plus **#233** (CAD), **#189**
(firmware CI), **#123** (sim). #232 and #234 are closed.

## ⏭️ Next actions (rewritten 2026-08-02 — items 1–3 were stale, all three are done)

1. ~~Check the solder drawer~~ ✅ **DONE 2026-08-01 — Sn63Pb37, 1 mm, 1.8 % flux core.** Leaded, so
   every *leaded* setpoint in `BUILD_PLAN.md` §2a is the live one and nothing shifts +30 °C.
   Eutectic ⇒ **shiny is the correctness criterion.**
2. **Solder, per `BUILD_PLAN.md` stages 0–10.** ✅ **STAGES 0–6 COMPLETE AND VERIFIED ON BOTH
   BOARDS (2026-08-09).** Every SMD part on both boards is placed *and* measured.
   ⏭️ **Next: stage 7 — `SW1` + `SW2` screw terminal blocks.** `SW1` is `TB007-508-02BE` (not
   the 10 A kit block; drill was widened 1.2 → 1.5 mm for it). Three of the four pads are
   plane-tied → **TS-C4 at 380–400 °C off the Kungber at 24.0 V**, TS-D24 330 °C for `SW2`.2
   (`EN_SW`) only. Per-pad plan in `BUILD_PLAN.md` §2a; the Contura III rocker is off-board and
   wires into `SW1` later. Then 8 high-current · 9 electrolytics · 10 INA modules.
   ⚠️ **This list has gone stale twice now.** The bench record is Notion (*🔧 Soldering /
   Assembly Steps*); this file is a mirror and lags it. **Read Notion before acting on
   anything here.** On 2026-08-13 items 2 and 3 below were four stages behind, and this item
   was sending the next bench action at a gate that had already passed, against an expectation
   that would have failed a good board.
3. ~~Run the preheat bench test~~ ✅ **RUN 2026-08-01, PASSED — do NOT buy a preheater.** `U1.4` wet
   in ~2 s with solder through to the far face; `Q1.3` (14 A GND inject, the worst THT pad on the
   board) easy and **shiny on both faces**. TS-C4, Kungber 24.0 V (~88 W), tip 400 °C. Consequence:
   every XT30/XT60 and `SW1.2` is the same or easier — stop treating high-current THT as the risk.
   The one joint it did **not** model is `L1` (SMD, plane-tied both sides, no barrel); if it
   fights, the answer is the **420 °C boost, not a purchase**.
4. **Decide the Q1 SOA question before the first pack hot-plug** (§ the 🔴 block at top). Three
   options, no scope required for the first two:
   - First power-on is already from the **current-limited bench supply at 0.5 A**
     (`pre-power-on-validation.md` §3), which never creates the inrush the SOA concern is about.
     That defers the risk rather than clearing it.
   - **Precharge through an owned resistor.** The Chanzon **1 Ω + 4 Ω** power resistors are on the
     bench-gear list — a 2-stage connect through the 4 Ω limits peak inrush to ~4.2 A at 16.8 V and
     puts the 0.77 J in the resistor instead of the FET. ⚠️ **Confirm their wattage rating first** —
     it is not recorded in `master-bom.md`.
   - Buy the scope and actually measure it. This is the only option that *clears* the gate.
5. **B3** — MRBF install + safety-chain bench validation before any LiPo. Includes the two audit
   items still genuinely open: **E-stop torque-cut path** (does `EN_BUCKS` really limp the robot)
   and **micro-ROS `RCCHECK`** still hard-bricking on a transient agent hiccup at any init call
   after `rclc_support_init`.
6. Firmware bench bring-up (real SN74LVC125A + INA226 + STS3215) + servo ID assignment
   (`docs/setup-servos.md`). Bus half-duplex timing — `pre-power-on-validation.md` §10.
7. **B2** — remaining CAD: joint ranges, masses/inertias, the `body_half_x` 0.1412-vs-±129.6 hfe
   station decision, and `nova_description/README.md` still warns "do NOT train a gait until the
   TODO-CAD values are…" which is now stale against its own xacro.
8. Leg first-article print (PA6-CF).

## 🟡 Not started (deeper backlog)
- `gait_node` — cmd_vel → trot → IK → `/joint_commands` (Phase-2 glue over the tested core).
- `nova_calibration` per-joint `config.py` fill (FROM CAD) → servo home auto-detect.
- Phase 2 sim: MJX gait training (now unblocked by URDF, pending B2).
- Phase 3: Nav2 / autonomy. Phase 4: arm install + MoveIt + VLA.

## Phase snapshot (2026-07-31)
- **Phase 0** (pre-build): **CLOSED.** Both boards designed, fabbed, delivered.
- **Phase 1** (HW bring-up): **STARTED — this is where we are.** Soldering in progress
  (`BUILD_PLAN.md` stages 0–10). Firmware skeleton green (p99 1 µs, isolation); nothing on these
  boards has been powered or bench-proven yet. B3 is the gate out of this phase.
- **Phase 2+** (locomotion/autonomy/arm): groundwork only (URDF + IK/gait scaffolded, walks in sim
  on flat). Gated on the remainder of B2.
