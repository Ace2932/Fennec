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
- 🟠 **TODO (must do pre-fab) — Q1 gate-protection hardening.** DECIDED: add it (peace-of-mind, despite low value — reverse-plug is already impossible via keyed XT60 + bulk caps damp the rail; this guards Q1's gate vs >20V transients, Vgs is 16.8V/±20V = 1.19×). **Board change → reopens the F8/route/gerber cycle.**
    - **Best done in eeschema, NOT headless** (polarized zener + the `Device:R`/`Device:D_Zener` lib_symbols aren't cached in 01_battery + Q1 is mirrored → headless = segfault/polarity risk; a backwards zener is worse than nothing).
    - **eeschema recipe (01_battery, at Q1):** break gate↔VBAT_PROTECTED; add `Device:R` **R17=100Ω** wired VBAT_PROTECTED→R17→gate; add `Device:D_Zener` **D1=15V** (BZT52C15) **cathode→gate / anode→GND**; annotate → ERC → F8 → place R17+D1 near Q1 (battery edge) → route → save.
    - **Then me:** netlist-verify (R17 spans VBAT_PROTECTED↔gate; D1 cathode→gate, anode→GND — catches a backwards zener) → re-pour → DRC → regen gerbers → fab_gate.
    - Parts (in cart): **R17 100Ω 0603 · D1 15V zener SOD-123 (BZT52C15)**.
- **SW1 needs the 15–20A screw block** (kit block is 10A; SW1 ~15A).
- Physical-verify before fab: INA226 module pitch, off-board buck XT30 pin-order, Teensy footprint, L1 (SRR1260) land, 1000µF Ø10×17 fit.
- Comfortable margins (no action): Q1 Vds/Id, XT60, INA226 (2.2×), 0603 R power, BSS138, LM393, L1 current (2.8×).

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
