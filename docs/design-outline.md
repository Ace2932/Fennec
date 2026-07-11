# NOVA — Full Design Outline

**The canonical top-level design document.** Promoted from the 2026-07-05
packaging review (user call: "this plan should be the outline for the full
design"). Every CAD/build decision traces here; per-domain detail lives in
the linked docs. Sibling memories: `~/claude-memory/nova-proj/`
(`project-chassis-integration`, `project-leg-v6-design`).

## Architecture at a glance

```
        FRONT                                        REAR
      ┌─D456+L2 head┐┌──────── riser-bay top ───────┐
      │ L2 on crown ││            Jetson            │   ← +25mm printed riser
      │ (flared 124)││        100×79 fan-up         │     (replaces stock lid)
   ┌──┴─────────────┴┴───────────────────────────────┴──┐
   │ shoulder │  STOCK TRUNK BOTTOM 127×110             │ shoulder │
   │ v6 (new) │  mezzanine stack 112×90×58, Teensy up   │ v6 (new) │
   │          │  bucks + de-cased switch UNDER the stack │          │
   └──────────┴──────────┬───────────────┬───────────────┴─────────┘
        legs: leg_v6     │ BELLY BATTERY │   155×46×35, 510g
        (coax/femur/     │ + MRBF block  │   ~104mm off ground
         tibia+knee_arm) └───────────────┘   un-strikeable at full crouch
```

- **Legs**: `hardware/cad/leg_v6/` — designed, gated, ROM-verified. d=64.3
  stock stance; kfe ±109° sw (118 mech), hfe −86..**+50°** (toward-trunk
  fold capped by the riser skirt — chassis gate 2026-07-06; contact from
  ~+55 at kfe-folded; crouch needs only ~+40), haa **inboard +15° sw** /
  outboard 40 (belly pack — contact from ~18-20° inboard when folded;
  splay direction fully clean; chassis gate).
- **Trunk**: stock bottom shell KEPT (leg/shoulder interfaces intact); lid
  replaced by the riser bay (stack is 58 tall vs the open frame's 29-tall
  walls — the trunk is NOT a tub, dimensions.md §11).
- **Electronics**: mezzanine power+logic stack inside on the part-5 floor
  plate (stack ctr x −3.5); Teensy USB + JP1 face up; **4 off-board bucks +
  de-cased switch UNDER the power board** (~16mm standoffs — the "beside
  the stack" floor space never existed, 2026-07-06 thermal review; riser
  low-vent row cools the pocket); leg wiring exits through the shoulder
  flange grommets (front bays face the trunk; rear bays face rearward —
  all-forward horn config).
- **Power**: belly battery (lowest CoM, swap without tools) → MRBF-30 at the
  pack → SW1 → boards. Dual-voltage servo harness per
  `hardware/wiring/README.md` (VCC-pulled daisy links + local XT30 spurs).
- **Perception**: L2 on the head crown via `l2_adapter` (front-top, sees over
  the Jetson case + legs), Ethernet routes down through the head/neck; D456
  in the same flared front head shell (tilted face), USB3 side channel to
  the rear riser.
- **Compute**: Jetson official case on the riser top, rear, cradle-mounted
  (hood retired — see #33/#34), fan up; SMA WiFi bulkheads on the head EARS
  (tray retired — #32); barrel V12_JET + RJ45 + USB rise through the rear
  grommet.
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
| Chassis | ✅ riser bay designed + gated (`hardware/cad/chassis/`) | hand-trim of 4 trunk slab ends when boards arrive |
| Chassis | ✅ belly battery pocket + L2 crown mount designed + gated | battery leads route through the shoulder-flange bottom notch; assembly: the L2 mounts on the head crown via `l2_adapter` (bench: L2→adapter M3×10 CSK, then adapter→crown M3×8 SHCS); head+L2 ride the neck on the 4 nylon M3 breakaway (#42) |
| Chassis | ✅ D456 head designed + gated (forward 27° down-tilt face + L2 crown, ONE part — user call) | camera forward of the chassis (body x136–173, back-face ctr 143,0,111.5, tilted 27° down) so near-ground is in frame; head_study = 0 leg-sweep hits at front hfe −50. Rear **2× M3 @94.4 centerline** mount, CALIPER 07-07 (periscope retired 07-07) |
| Chassis | ✅ floor plate designed + gated | mezzanine seat + battery sandwich + drill template; stack ctr x −3.5 (power_v2 fab-file holes); rear-only slab trim; 5191 slots ⚠ caliper |
| Chassis | ✅ E-stop + OLED re-homed (`control_pod.scad`, rear-top, bolts to the riser rear wall — hood retired) | wire the E-stop NC pair + OLED SPI down the pod grommet at assembly |
| Kinematics | ✅ measured (B2) | masses from prints → URDF; joint ranges = sweep gate values |
| Gait | pure-math trot + IK green | gait node (`foot_target` → `solve_side` → `/joint_commands`) |

## Interface chain (leg → shoulder → body) + fastener map
**Leg ↔ shoulder (haa joint).** Horns ALL face FORWARD (the stock
configuration, VERIFIED in the A360 assembly: front horn planes ≈171mm
fwd of grid center, rear ≈111 — translation symmetry). This matches the
URDF (four identical translated legs) and `solve_side` (L/R mirror only),
keeps one coax chirality per SIDE at all corners, and all knees bend the
same way. (An "outward" variant was rejected 2026-07-06: it silently
chirality-swaps the rear legs vs the URDF/IK.) Trunk-end→hip-station is
77.7mm at BOTH ends → front/rear shoulders are THE SAME PART, translated.
Per side the shoulder carries:
- REARWARD arm: Ø19 boss through the coax floor window, bolts the haa
  WHEEL (4× M2.5 + ctr, counterbored) — assembled once.
- FORWARD arm = **BOLT-ON PLATE** (knee_arm pattern: prints seat-face-down,
  4× M3 into crossmember heat-sets, diagonal pair close-fit): bolts the haa
  HORN. **A whole leg detaches in 4 M3 + one cable unplug** — horn stays on
  its plate, wheel stays bolted; no re-calibration on refit. (Front plates
  sit outboard of the trunk; rear plates sit in the 78mm trunk-to-hip gap —
  driver access verified by the gap size.)
- Cables: FRONT coax bays face the trunk; REAR bays face rearward — both
  reachable; rear leg bundles enter through rear-shoulder grommets.
**Shoulder ↔ trunk.** Shoulder foot-plate bolts to the STOCK bottom shell's
end wall + a 20mm under-floor lip (4-6× M3 into shoulder-side heat-sets,
screws through the shell — measure the stock end-face hole pattern from the
ChassisTrunk mesh at design time). Legs load the bottom shell ONLY — the
riser is never structural, so it lifts off with the robot standing.
**Body stack (bottom-up).** belly battery pocket (bolts under the shell) →
STOCK bottom shell (kept; reprint in PA6-CF later if the stock print proves soft) → shoulders ×2 (same part) → riser bay (seats on the wall-top rails
z 29 + corner plateau tabs; **4× M3×12 horizontal through the shoulder
flanges into riser heat-sets** — the imagined "shell bosses" don't exist,
mesh-measured 2026-07-06, `hardware/cad/chassis/README.md`) → the Jetson
rides the case cradle on the riser top; the single head unit (D456 face + L2
crown + ears) bolts to the neck_bracket via 4 nylon M3 breakaway (#42) —
head shell ceiling trunk z 72.8 — the shoulder deck extension is above.
(Jetson tray hood + standalone L2 mast RETIRED 2026-07-07, folded into
head.scad + the case cradle.)

## P1S print plan (bed 256×256×256 — everything fits flat)
| Plate | Parts | Note |
|---|---|---|
| 1 | coax R+L, femur R+L | flat, zero supports (femur), tree under coax bridge |
| 2 | tibia R+L, 4× knee_arm, 8× strap | supports under tibia blades |
| 3 | shoulder ×2 + 4× outer horn plates | plates seat-face-down |
| 4 | riser bay | largest part 126.7×110×42.9 (8× Jetson spacer RETIRED — Jetson now rides the official-case cradle) |
| 5 | battery pocket, head + neck_bracket + l2_adapter + ears, control_pod + oled_mount, jetson_case_mount + clamp_bars | (L2 mast + D456 head + tray hood RETIRED 2026-07-07 → geometry folded into head.scad + the case cradle; jetson_cowl RETIRED 2026-07-10 → right-angle plug adapters, backlog #41) |
PA6-CF dried + annealed, 0.2mm, ≥4 walls, ≥40% infill (doctrine).

## Service paths (design requirement: reach anything without teardown)
| To service | Remove | Screws |
|---|---|---|
| Battery swap | strap only | 0 |
| Teensy USB / JP1 / SD / boards | riser lifts — Jetson/L2/D456 ride along (L2+D456 on the head, Jetson on the cradle) (4 flange screws + unplug 2 cables at the Jetson) | 4 |
| Jetson | unbolt 2 clamp bars (4× M2 from above); case lifts out — tray hood RETIRED | 4 |
| L2 | `l2_adapter` off the crown: 2 rear bolts (up from below the crown, into the adapter heat-sets) + 1 front tongue/hook (slides under the crown front lip, no bolt) — head + Jetson stay. Needs a stubby/right-angle driver (2 rear bolts up a tight ~18mm pocket shared with neck_bracket access) | 2 |
| One whole leg | shoulder outer plate + unplug at coax bay | 4 |
| One servo | its leg off → that joint's yoke discs → strap/columns | ~15-20 |
| Shoulder | its 2 legs off → trunk screws | 4-6 |
| D456 | camera is part of the forward neck-mounted head unit (D456 face + L2 crown, ONE part) — bolts to `neck_bracket` via 4 nylon M3 breakaway; camera↔head is not separately serviceable in the field (bench-only rework) | 4 |

## Doc graph (start → detail)
`docs/design-outline.md` (this) → `hardware/cad/leg_v6/README.md` (legs) ·
`hardware/cad/dimensions.md` (every mating dim) · `hardware/wiring/README.md`
(harness + dual-voltage) · `docs/pre-power-on-validation.md` (hard gates) ·
`hardware/cad/README.md` (CAD tracks) · memories `~/claude-memory/nova-proj/`
(design reasoning). Each detail doc back-links here.

## Print + assembly gates
- PA6-CF dried + annealed, 0.2mm layers, ≥4 walls, ≥40% infill.
- First-article checklists in `hardware/cad/leg_v6/README.md`.
- Pre-power-on: `docs/pre-power-on-validation.md` (hard gates §1b-§1e).
- Pre-walk: torque limits armed (done), boot-settle, feet-under-knees
  stand-up, servo centering done at assembly.
