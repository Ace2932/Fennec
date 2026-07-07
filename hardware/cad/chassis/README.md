# Chassis — trunk riser bay (+ Jetson tray + L2 mast base)

> Top-level design: [`docs/design-outline.md`](../../../docs/design-outline.md)
> · trunk mate dims: [`../dimensions.md`](../dimensions.md) §11 · reasoning:
> `~/claude-memory/nova-proj/project-chassis-integration.md`

Started 2026-07-06. First chassis-lane part: the printed **riser bay** that
replaces the stock trunk lid — its top IS the Jetson tray and the L2 mast
base (design-outline packaging). OpenSCAD + real-mesh fit gate, per leg_v6
doctrine (the cad/README's "OnShape for chassis" note predates leg_v6; this
lane follows the leg_v6 track).

## What the trunk ACTUALLY is (mesh-measured 2026-07-06, `measure_trunk.py`)

The "~118 × 100 × 40 interior tub" assumption was WRONG. The stock
`SM3_Frame_ChassisTrunk.stl` (127 × 110 × 46.91, floor z0, +x = the printed
"F" arrow) is an open frame:

| Feature | Measured |
|---|---|
| floor slab | top z 3.9; big rear opening + corner cutouts (cable/battery pass) |
| side walls | 6.0 thick, inner y ±48.93, **top z 29.0**, notch x 18.2..31.2 → z 12.5 (both) |
| ends | **OPEN above the floor** — closed at assembly by the v6 shoulder flanges |
| corner wedges | 4× leaning slabs (~35°) rising wall-top→plateau; **plateau tabs z 46.91**, x ±(53.3..63.5), y ±(29.9..36.0) |
| wedge windows | ~9.4 × 6.4 under each plateau tab (stock cover hooks; unused by us) |
| shoulder bolt bores | Ø3.16 along x at (y ±51.75, z 5 & 24), 6.5 deep, both ends — matches `shoulder.scad` |
| interior clear width | 97.86 (stack 90 fits, 3.9/side) |

## Parts

| Part | Status | Notes |
|---|---|---|
| `riser_bay.scad` | designed, gated | one print, 126.7 × 110 × 42.9 (z 29.0..71.9). **Reworked 2026-07-07 for the case pivot**: dropped the 96.5×75.4 Jetson standoff grid + all hood pads/inserts; added the COMPACT mast interface (54/59.0, ±14), the case PORT-END cable slot (x −58..−46, y ±18 = also the case bottom-vent breather), 4 cradle deck ties (47.3/−59.0, ±50.35), and relocated the SMA bulkheads to the front strip (57, ±40). L2 cable drop 14×12 @ (53.5,0) |
| `spacer.scad` | **RETIRED** | Jetson standoff washers — unused now the board is in the official case (kept in build_all for reference) |
| `battery_pocket.scad` | designed, gated | rear-loading belly tray, 6× M3 sandwich mount through the floor (**part-5 plate must adopt the (±40/0, ±26.5) pattern**; drill the floor at first assembly), velcro fence at the rear opening |
| `l2_mast.scad` | designed, gated | flange→shaft→plate; **bolt L2 to the plate BEFORE mounting** (plate holes clear the shaft); flange screws driven under the L2 with a ball-end key. **Flange screws = NYLON M3×10 fuses** (backlog #2): mast pops off the deck at ~10 N·m faceplant instead of the shaft/inserts/L2 dying; L2 tethers on its own pigtail. Hand-tight only |
| `d456_head.scad` | designed, gated (**v3 periscope**) | screw-in (user call): camera on its REAR 4×M3 corner pattern (⚠ unverified — tall slots at y ±54, CALIPER before printing) at z 80.5..109.5, above the shoulder deck extension, below the L2; **right-angle USB-C required** (BOM). v1 died on the shoulder webs, v2 under-chin died on the folded front femur (bar through the volume from hfe ~+35). **Row screws = NYLON M3×10 fuses** (backlog #2): bracket pops before the riser-wall inserts rip; camera tethers on the USB-C. Hand-tight only |
| `../leg_v6/shoulder.scad` | **rev'd ×4** | + center notch (x ±26 above z 19.5) + 2× Ø3.4 riser holes (x ±40, z 29.35) + **battery-lead bottom notch** (x ±10 to z −26 = trunk z 12) + **flange floor FEET + deck gussets** (2026-07-06 joint-stiffening, user catch "barely connected": feet bolt the flange bottom to the trunk floor corners at (±59.5, ±42) — M3×14 csk from BELOW, +2 floor holes per end at first assembly, add to the floor_plate drill template; gussets flange→deck-ext at x ±40); leg_v6 + chassis gates re-run (new shoulder-vs-trunk case in check_fit) |
| `floor_plate.scad` | designed, gated | 2.0 plate = mezzanine seat (top 5.9) + battery-sandwich csk pattern + **drill template** for all 10 floor holes; stack pilots at (−40.5/+33.5, ±33) from the power_v2 fab file (74×66); **stack ctr x −3.5** (rear edge 0.5 off the trunk corner posts, front corners clear the front slabs by 0.8) → rear-only slab trim + CoM −3.5; corner clips for the post base flare; front edge x 45 clears the raised stock "F". **5191 slots REMOVED 2026-07-07** — the calipered block is 61.6×20×46.5 and there is NO clean captive spot on the robot for it (below = leg-crouch space, rear-center = shoulder flange, trunk interior = mezzanine stack; all gate-verified conflicts). **5191 = ASSEMBLY-TIME external mount** (bracket/zip-tie to the rear-shoulder exterior or trunk rear, found empirically with real parts; fuse close to the battery-lead entry). Leads: pack rear → up through the rear shoulder flange notch |
| `skid_rail.scad` | designed, gated | TPU 95A belly skids ×2 (backlog #15): keyed+glued under the tray, new lowest z −42.2; E-stop-limp collapse lands HERE, not on the pack. Inboard-haa 15° cap verified intact with rails in the crouch gate |
| ~~tray hood~~ **RETIRED** | — | Jetson heatsink CALIPERED 34.9 (not 21.5) → heatsink top 113.1 collides the L2 plate. **DECISION 2026-07-07 (user): adopt the OFFICIAL JETSON CASE** (110.5×95.2×38.5, `jetson_case_ref.stl`) instead of the bespoke tray+hood. Case on the deck → top 110.4, clears L2 by 4. Drops the hood; E-stop pod + OLED move off the hood (new homes TBD). Repackaging in progress: case cradle mount + L2/D456/SMA refit |
| `jetson_case_mount.scad` | in design | deck cradle + corner hold-downs for the official case (bottom is vented — mount via 4 drilled corners); riser deck reworked (old Jetson standoffs + hood pads removed) |

## Riser design (all trunk-frame numbers)

- **Seat**: side skirts (3.2, outer flush y ±55) rest ON the wall tops
  (z 29.0) — two full-length rails = primary datum. End walls (x ±60.15..63.35)
  stop 0.1 above the wedge plateaus. Lateral register: 4 tabs inside the wall
  inner faces at x ±40 (0.45 clearance, drop-in doctrine).
- **Hold-down (NO stock-shell mods)**: 4× **M3×12** horizontal through the
  shoulder flanges into heat-set pads in the riser end walls at (y ±40,
  z 67.4 — the end-wall pad band z 64.4..70.4 sits above the stack envelope
  and fuses into the deck; a z-65-centered pad protruded into the stack
  corners, gate catch). Inserts press from the pad's INNER face (from
  below, pre-mount) so screw tension seats them deeper — outer-face press
  was extraction-loaded (design-review fix).
  Fore-aft location = these screws (±0.15), leg-doctrine style. The riser is
  NEVER structural.
- **Deck top z 71.9** (= trunk top + 25, outline-locked) and FLAT: every
  fixture is an underslung boss → prints deck-face-down, zero supports.
- **Jetson Orin Nano devkit**: grid 96.5 × 75.4 at bores
  (−58.25/+38.25, −47.4/+28.0); carrier spans x −60..+40, y −49.4..+30,
  **ports face +y**, plugs drop through the deck slot (x −53..−44, y 26..46).
  Rear fin + mast stay clear of the plug row. Board plane z 78.2
  (6.3 spacers, **M3×14** — ×16 grazes the stack envelope, ×12 only bites
  3.2mm).
- **L2 mast base**: 4× M3 heat-sets on a 16 × 28 rectangle at (44/60, ±14) —
  riser↔mast interface is OURS (the 22.5 mm square is L2↔mast, in the mast
  part). Ø11 cable drop at (52, 0). Mast unbolts without touching the Jetson.
- **SMA bulkheads**: 2× Ø6.5 at (−15, +44) and (+25, +44) — 40 apart (MIMO).
  ⚠ verify the U.FL pigtail reach on the real board.
- **D456 head interface (periscope)**: bracket stem rises through the
  shoulder-flange center notch to the riser wall row (4× M3 at y ∓21/∓7,
  z 67.4 — driver passes UNDER the camera, bottom 80.5); cross-plate
  carries the camera's rear pattern at z 80.5..109.5. USB grommet slot
  10×6 at (0, 61.5). **Camera placement is corridor-forced**: the only
  leg-safe, shoulder-safe home for a 124-wide body is above the deck
  extension (79.55) and below the L2 (114.4). Known cost: the camera's
  top-front corner clips the L2's −45° bottom cone ~3.5° in the forward
  sector (ground 150–165 mm ahead — D456's own prime zone). Camera bolts
  to the bracket ON THE BENCH; installed, its rear screws are unreachable.
- **Hood interface**: 4× M3 horizontal heat-sets in the side walls at
  (x −50/+35, z 67) — hood straddles the deck, screws from free air.
- **Vents**: 6× 3 mm slots per side, z 52..66.

## Battery pocket (`battery_pocket.scad`, trunk-frame numbers)

- Open-top tray under the shell (shell floor caps it); rim at z −0.2, tray
  bottom −39.2; cavity 156.6 × 47.6 × 35.8 (pack + 0.8/side, **listing dims
  — caliper the real pack at first article**). Pack overhangs the trunk
  ~14.8/end, 0.25 under the shoulder flange bottoms.
- Rear-loading: pack slides in from −x; velcro strap wraps the pack's REAR
  CORNER (slots at x −77..−61 — direct tension against slide-out, not
  friction; design-review fix; shake-test at first article). Battery swap =
  strap only, 0 tools.
- Mount: 6× M3×12 from inside the trunk through the 3.9 floor into
  full-height boss columns at (x ±40/0, y ±26.5) with side-loaded **M3 nut
  traps** at z −8.2 (review fix: printable columns + a nut beats an insert
  at the pocket's highest-load joint). Floor has no holes there — **drill
  Ø3.4 at first assembly; the part-5 plate adopts the same pattern**
  (screw sandwich: plate + floor + tray).
- Leads: exit the pack rear face behind the trunk end, rise at x ~−70,
  enter through the **shoulder flange bottom notch** (y ±10 to z 12) to the
  MRBF-30 / 5191 block inside (block mount = part-5, ⚠ dims unmeasured).

## L2 mast (`l2_mast.scad`)

- Flange (x 38..63.3, y ±20) on the deck, M3×16 into the riser's underslung
  inserts at (44/60, ±14), head wells through the flare. Shaft outer
  x 44..63.3 × y ±9 (Jetson edge gap 2.3; deck-extension fin gap 0.2), cable
  bore 13×9 — passes the RJ45 plug head. Plate 38×38, L2 seat z 114.4 →
  optical center ≈ trunk top + 100.
- **Assembly order (design-review fix — the reverse deadlocks)**: BARE
  mast bolts to the deck first (**M3×10** — longer punctures the stack
  envelope; Ø7 head wells open to the sky), THEN the L2 bolts on from
  BELOW the plate (M3×8 at (42.25/64.75, ±11.25), 38.5 mm of driver room).
  L2 service = those 4 plate screws; mast + Jetson untouched. Cable bore
  13×11 / deck slot 14×12 — must pass BOTH the RJ45 head and the ~Ø10 DC
  plug (⚠ caliper the real plugs).

## Findings the gate must keep honest

0a. **ROM caps re-verified with the ASSEMBLED state swept** (design review
   2026-07-06): the sweep cloud now carries the coax + tibia straps and
   cable-loop proxies (the leg_v6 "straps never sampled" lesson had
   repeated). Result: caps HOLD — hfe clean through +52, inboard haa clean
   through 15 with contact from ~18. No allowance change needed.
0b. **Inboard haa capped at +15° sw per leg (battery pocket)**: the pack
   hangs 39 below the shell; an inboard roll sweeps the folded leg under
   it — contact from ~18–20° at any hfe fold ≥ 15–30 (hfe ≤ 0 clean at
   full ±40). Outboard splay keeps the full 40 (verified clean — stand-up
   choreography unaffected; FR toe at haa −40 crosses the centerline, so
   >15 inboard had no use case anyway). Gate-derived, feeds URDF/firmware
   together with 0.
0. **hfe toward-trunk fold capped at +50° sw (chassis-safe ROM)**: with the
   tibia folded (kfe −109) and haa −40, the tibia/knee flank (tibia jogs
   30.5 back inboard) grazes the riser side skirt from hfe ≈ +55. Clean
   through +52 at every hip/haa/kfe combination; away-trunk −86 fully
   clean. Crouch itself needs only ~+40 (kfe-109 chord = 138). Feeds the
   URDF joint ranges + firmware clamps; the gate prints beyond-limit poses
   as documented HITs. It's an anti-gravity pose (knee lifted over the
   deck), not a collapse direction — software limit is the artifact fix.
1. **REAR stack corners vs trunk slabs (KNOWN, documented in the gate)**:
   with the stack at ctr x −4 (floor plate), only the two REAR corners
   intersect the leaning slabs → **hand-trim the two rear slab inner ends
   to x ≤ −60.5 when the boards arrive**; front slabs stay stock. Gate
   fails on any hit outside that zone (front hits included). The slabs
   only ever supported the stock covers.
2. **Mezzanine seat = the 2.0 floor plate, top z 5.9; stack top 64.0**
   (deck-boss bottoms 65.3 → 1.3 clear; deck underside 67.9 → 3.9).
3. Shoulder flanges rise to z 79.55 — 7.65 proud of the deck at both ends
   (they close the end gaps; Jetson x −60.. keeps 5.5 clear of the rear fin).
4. Jetson heatsink height 21.5 is ⚠ REVIEW in dimensions.md — caliper before
   designing the hood; L2 gap currently 7.6 above heatsink+hood.
5. Front cable lanes: D456 USB3 runs inside the riser ceiling gap
   (stack-top → deck-underside is 6.0 with max bosses) to the deck slot.
6. **E-stop has no home yet (system gap)**: Ø22 panel + ~50 below-panel
   body fits nowhere at deck/wall level (the stack owns every column).
   Only viable volume = a pod ABOVE the deck rear strip beside the hood —
   design it with the hood part. ⚠ caliper the real HB2-ES544 depth.
7. **CoM sits ~+8 mm forward** of the hip-grid center (L2 + camera + mast
   forward moments vs the centered stack). Cheap trim: shift the mezzanine
   −8 fore-aft when placing the part-5 floor-plate bosses.
8. **Caliper list (one session, before the next prints)**: Jetson heatsink
   height · Blue Sea 5191 block · D456 rear pattern + body · L2 pigtail
   RJ45/DC plug heads · HB2-ES544 depth · pack true dims · stack true
   height incl. Teensy · buck/switch true heights (see 9).

## Thermal + motion review (2026-07-06)

9. **Bucks + switch placement RESOLVED-ON-PAPER**: the outline's "on the
   floor beside the stack" predates the plate — no floor space exists.
   Disposition: power board on ~16 mm standoffs, bucks (13-15 tall) +
   de-cased switch UNDERNEATH on the plate; recomputed stack ≈ 57 ≤ 58
   budget. Constraints: keep bucks off the pack shadow (y ±23 — LiPo
   below the floor) where possible; floor plate gets a mounting rev with
   the boards in hand. The riser now carries a LOW vent row (z 33..45)
   because the buck pocket (z 6..22, ~6-10 W) had zero airflow.
10. **L2 rear-down blindness (quantified, v1-accepted)**: the hood (~z 107)
   will block the rear sector below ~−19° elevation (cone edge −45°) →
   rear ground inside ~0.4 m is invisible to the L2 and NOTHING else looks
   rearward (D456 faces front). Affects reverse maneuvers.
11. **Build order (hard constraint)**: floor plate + battery tray bolt
   BEFORE the mezzanine — all six battery screws sit under the stack.
12. **Leg-vs-leg crossing is in-ROM** (front hfe +50 extended + rear −50
   extended overlap in the same y-plane, x ∓40). Not a chassis-parts
   issue; the URDF/sim lane must enable self-collision checking + the
   gait planner must respect it.
13. Sweep grid densified: kfe now {−109, −55, 0, 55, 109}; link flex
   (~1-2 mm at the foot) is well inside the 4-9 mm contact margins.

## Panel components + small actives (grounding audit 2026-07-06)

Homeless items found by cross-checking the memory docs — all ACTIVE in the
v1 BOM, none had a chassis home:

| Item | Home | Status |
|---|---|---|
| E-stop (Ø22 × ~50 ⚠) | pod above the deck rear strip | design with the hood |
| SW1 lighted rocker (flying lead, ⚠ dims) | riser FRONT-GAP zone (x 52.5..63 interior column is free): through the side skirt ~(x 57, z 45) or the deck front strip | ⚠ caliper, then a riser boolean rev |
| SSD1331 OLED (31×28×11, remote on J10) | hood FRONT face (cable up the deck slot) | hood requirement |
| WS2812B strip (10 mm pitch) | riser skirt perimeter, adhesive; cable enters through a vent slot | assembly-time, no CAD |

BOM additions flagged: right-angle USB-C cable (D456), velcro strap
(battery), TPU grommet insert for the deck slot (printed).

## Service

battery 0 screws · boards/Teensy/JP1 = **4 flange screws + 2 plugs at the
Jetson** — the riser lifts with Jetson/mast/L2/D456 ALL attached, robot
standing · Jetson = hood off · L2 = 4 plate screws under it · D456 bracket
= 4 riser-row screws (camera↔bracket is bench-only) · legs/shoulders per
leg_v6.

## Build + gate

```bash
./build_all.sh          # renders riser + spacer + shoulder rev, runs BOTH gates
```

`check_fit.py` cases: riser↔trunk mesh (seat bands excluded) · stack envelope
vs riser + trunk (known-zone logic) · shoulders both ends · **CROUCH leg
sweep** (haa ±40 × hfe ±86 × kfe ±109 at all four hips, mirror placements —
envelope check) · static fixture asserts.

## First-article checklist (before plate 4 batch)

1. Skirt seats flat on both wall tops, no rock; tabs drop in without force.
2. Riser↔flange screws: M3×10 reaches the inserts across the 0.15 gap; the
   riser doesn't shift fore-aft once torqued.
3. Heat-set purchase at Ø4.0 bores (deck bosses pressed from BELOW, wall
   bores from the outer faces).
4. Jetson on 6.3 spacers: port plugs clear the slot edges; SMA nut clearance.
5. Deck flatness under the mast base (L2 + mast lever arm) — if the deck
   oil-cans, add the two fore-aft ribs deferred from this rev.
6. Stock-shell slab trim done/not-needed per finding 1.
