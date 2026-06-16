# NOVA — Status Board

Single-pane blockers / in-progress / next-actions. Hand-maintained; the detail
lives in `README.md` (Open Decisions + Build Roadmap), `docs/order-list.md`,
per-board `ROUTING_HANDOFF.md`, and memory. Update when state changes.

_Last updated: 2026-06-15 (B1 cleared — both boards fab-ready, gate GO)_

## ✅ Recently cleared
- **B1 — power board arm placement + routing — DONE** (PR #13). U12 + J14 placed/routed, U5.EN routed on EN_BUCKS, V7V5_ARM/BATT_NEG widened + high-current pads solid, duplicate U12/J14 + dangling chain cleaned, gerbers regenerated. **fab_gate: GO on both boards.**

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
