# NOVA — Full Design Outline

**The canonical top-level design document.** Promoted from the 2026-07-05
packaging review (user call: "this plan should be the outline for the full
design"). Every CAD/build decision traces here; per-domain detail lives in
the linked docs. Sibling memories: `~/claude-memory/nova-proj/`
(`project-chassis-integration`, `project-leg-v6-design`).

## Architecture at a glance

```
        FRONT                                        REAR
      ┌─ D456 head ─┐┌────── riser-bay top ─────────┐
      │ (flared,    ││  L2 mast          Jetson     │   ← +25mm printed riser
      │  124 wide)  ││  75×75×65      100×79 fan-up │     (replaces stock lid)
   ┌──┴─────────────┴┴───────────────────────────────┴──┐
   │ shoulder │  STOCK TRUNK BOTTOM 127×110             │ shoulder │
   │ v6 (new) │  mezzanine stack 112×90×58, Teensy up   │ v6 (new) │
   │          │  bucks + de-cased switch beside          │          │
   └──────────┴──────────┬───────────────┬───────────────┴─────────┘
        legs: leg_v6     │ BELLY BATTERY │   155×46×35, 510g
        (coax/femur/     │ + MRBF block  │   ~104mm off ground
         tibia+knee_arm) └───────────────┘   un-strikeable at full crouch
```

- **Legs**: `hardware/cad/leg_v6/` — designed, gated, ROM-verified. d=64.3
  stock stance; kfe ±109° sw (118 mech), hfe ±86°.
- **Trunk**: stock bottom shell KEPT (leg/shoulder interfaces intact); lid
  replaced by the riser bay (stack is 58 tall vs 40 interior).
- **Electronics**: mezzanine power+logic stack inside; Teensy USB + JP1 face
  up; 4 off-board bucks + switch on the floor; wiring drops through 4
  leg-corner grommets to the coax bays (which face the trunk).
- **Power**: belly battery (lowest CoM, swap without tools) → MRBF-30 at the
  pack → SW1 → boards. Dual-voltage servo harness per
  `hardware/wiring/README.md` (VCC-pulled daisy links + local XT30 spurs).
- **Perception**: L2 on a center-front mast (~100 above trunk top, sees over
  the Jetson hood + legs), Ethernet down the mast; D456 in a flared front
  head shell, USB3 side channel to the rear riser.
- **Compute**: Jetson on the riser top, rear, hooded, fan up; SMA bulkheads
  on the tray; barrel V12_JET + RJ45 + USB rise through the rear grommet.
- **CoM**: battery centered under the hip grid; Jetson-rear balances
  L2+head-front; ~4.15kg total.

## Design doctrines (non-negotiable, learned the hard way)
1. **Measure, never assume** — every mating dim from mesh/STEP/caliper,
   recorded in `hardware/cad/dimensions.md` with status flags.
2. **Fit-gate everything** — real counterpart meshes, sampled containment,
   wired into the build (`leg_v6/check_fit.py` pattern). Pose SWEEPS for
   anything that moves; crouch-pose gate for anything near the belly.
3. **One mirroring boundary** — `leg_ik.solve_side()`. Canonical left
   frames everywhere else. Parts carry side dots (1=R, 2=L).
4. **Assembly is part of the design** — insertion paths, screw access,
   service order, cable strain relief at every exit, centering servos at
   nominal pose (`set-servo-ids.py --center`) before yokes bolt on.
5. **Foreseeable problems get fixed in the artifact, not warned about.**

## Lanes + status

| Lane | Status | Next artifact |
|---|---|---|
| PCBs | ✅ fabbed (JLCPCB, arriving) | assembly hand-mods (U8 100nF, INA harness) |
| Legs (leg_v6) | ✅ designed + gated | **v6 shoulder** (haa yoke ↔ trunk, sweeps haa×hfe, keeps coax bay reachable) |
| Firmware safety | ✅ torque limits, limp, LVC | boot-settle PR #17 · stand-up choreography |
| Chassis | outline locked | riser bay + Jetson tray + mast base (fit-gate vs stack, Jetson, CROUCH legs) |
| Chassis | — | belly battery pocket (155×46×35; gate at crouch) |
| Chassis | — | L2 mast (4×M3 @22.5 sq) + D456 head (pick mount face) |
| Kinematics | ✅ measured (B2) | masses from prints → URDF; joint ranges = sweep gate values |
| Gait | pure-math trot + IK green | gait node (`foot_target` → `solve_side` → `/joint_commands`) |

## Print + assembly gates
- PA6-CF dried + annealed, 0.2mm layers, ≥4 walls, ≥40% infill.
- First-article checklists in `hardware/cad/leg_v6/README.md`.
- Pre-power-on: `docs/pre-power-on-validation.md` (hard gates §1b-§1e).
- Pre-walk: torque limits armed (done), boot-settle, feet-under-knees
  stand-up, servo centering done at assembly.
