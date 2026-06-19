# NOVA — Status Board

Single-pane blockers / in-progress / next-actions. Hand-maintained; the detail
lives in `README.md` (Open Decisions + Build Roadmap), `docs/order-list.md`,
per-board `ROUTING_HANDOFF.md`, and memory. Update when state changes.

_Last updated: 2026-06-18_

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
- 74HC125→SN74LVC125A stale across ~15 secondary docs (primary BOM/README/setup-servos fixed). Sweep deferred.
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

**❓ Questions for you (gate fixes):**
1. Which joint-ID map is canonical?
2. Does E-stop de-energize servo rails (limp) or just stop commands (servos hold)?
3. Do STS3215 default torque-on at power-up, or must FW enable?
4. Is the all-stall load-monitor implemented anywhere?
5. Intended Jetson liveness watchdog, or lean on FW watchdog + hardcut only?

Full audit detail in memory: [[project-system-audit-2026-06]].

## 🟠 Pending board edit (pre-fab, reopens power board once)
- **Q1 gate hardening — ⚠️ MARGINAL, backstop only.** Q1 gate=VBAT (≤16.8V), Vgs(max)=20V → 3.2V
  headroom. Mechanism = **R17 (~1kΩ, NOT 100Ω) + D1 18V gate-source zener (BZT52C18)** — zener
  clamp = Vz+Iz·Zz, so R17 must be ~1k to keep clamp <20V (100Ω → ~21V, fails). NOT 15V (conducts
  at 16.8V), NOT a TVS (clamps ~29V > 20V). **Primary fix = inrush-limit VBAT** (precharge/NTC,
  pre-power §3) to prevent the ring; zener = backstop. Cleaner: gate divider (Vgs→12V) or ±25V-Vgs
  FET. **BENCH-VALIDATE the VBAT transient (scope) before trusting it — don't fab assuming solved.**
  Sequence: eeschema place → F8 → route → DRC 0 → **regen gerbers** → fab_gate GO.

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
- **Phase 0** (pre-build): ~closing — logic board fab-ready; power board pending B1.
- **Phase 1** (HW bring-up): firmware skeleton green (p99 1 µs, isolation), bench bring-up not started.
- **Phase 2+** (locomotion/autonomy/arm): groundwork only (URDF + IK/gait scaffolded).
