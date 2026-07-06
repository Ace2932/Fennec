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
| `riser_bay.scad` | designed, gated | one print, 126.7 × 110 × 42.9 (z 29.0..71.9) |
| `spacer.scad` | designed | Jetson standoff washers Ø8 × 6.3, print 8 |
| `../leg_v6/shoulder.scad` | **rev'd** | + center notch (x ±26 above z 19.5) + 2× Ø3.4 riser holes (x ±40, z 26.95); leg_v6 gate re-run |
| tray hood / L2 mast / D456 head shell | next (plate 5) | interfaces reserved below |

## Riser design (all trunk-frame numbers)

- **Seat**: side skirts (3.2, outer flush y ±55) rest ON the wall tops
  (z 29.0) — two full-length rails = primary datum. End walls (x ±60.15..63.35)
  stop 0.1 above the wedge plateaus. Lateral register: 4 tabs inside the wall
  inner faces at x ±40 (0.45 clearance, drop-in doctrine).
- **Hold-down (NO stock-shell mods)**: 4× M3×10 horizontal through the
  shoulder flanges into heat-set pads in the riser end walls at (y ±40,
  z 67.4 — the end-wall pad band z 64.4..70.4 sits above the stack envelope
  and fuses into the deck; a z-65-centered pad protruded into the stack
  corners, gate catch).
  Fore-aft location = these screws (±0.15), leg-doctrine style. The riser is
  NEVER structural.
- **Deck top z 71.9** (= trunk top + 25, outline-locked) and FLAT: every
  fixture is an underslung boss → prints deck-face-down, zero supports.
- **Jetson Orin Nano devkit**: grid 96.5 × 75.4 at bores
  (−58.25/+38.25, −47.4/+28.0); carrier spans x −60..+40, y −49.4..+30,
  **ports face +y**, plugs drop through the deck slot (x −53..−44, y 26..46).
  Rear fin + mast stay clear of the plug row. Board plane z 78.2 (6.3 spacers).
- **L2 mast base**: 4× M3 heat-sets on a 16 × 28 rectangle at (44/60, ±14) —
  riser↔mast interface is OURS (the 22.5 mm square is L2↔mast, in the mast
  part). Ø11 cable drop at (52, 0). Mast unbolts without touching the Jetson.
- **SMA bulkheads**: 2× Ø6.5 at (−15, +44) and (+25, +44) — 40 apart (MIMO).
  ⚠ verify the U.FL pigtail reach on the real board.
- **D456 head interface**: 4× M3 heat-set ROW in the front wall at
  y −21/−7/+7/+21, z 67.4 (screws clamp; the shell bears on the wall face
  for moment) + Ø9 USB3 grommet at (0, 65), reached through the
  shoulder-flange center notch. **Head-shell ceiling: trunk z 72.8** — the
  shoulder deck extension plate spans z 73.05..79.55 over x 63.5..109 at
  both ends.
- **Hood interface**: 4× M3 horizontal heat-sets in the side walls at
  (x −50/+35, z 67) — hood straddles the deck, screws from free air.
- **Vents**: 6× 3 mm slots per side, z 52..66.

## Findings the gate must keep honest

0. **hfe toward-trunk fold capped at +50° sw (chassis-safe ROM)**: with the
   tibia folded (kfe −109) and haa −40, the tibia/knee flank (tibia jogs
   30.5 back inboard) grazes the riser side skirt from hfe ≈ +55. Clean
   through +52 at every hip/haa/kfe combination; away-trunk −86 fully
   clean. Crouch itself needs only ~+40 (kfe-109 chord = 138). Feeds the
   URDF joint ranges + firmware clamps; the gate prints beyond-limit poses
   as documented HITs. It's an anti-gravity pose (knee lifted over the
   deck), not a collapse direction — software limit is the artifact fix.
1. **Stack corners vs trunk corner slabs (KNOWN, documented in the gate)**:
   the 112×90 mezzanine's four corners intersect the leaning slabs at
   x ±(53.3..56), y ±(42..47), z 29..33. The slabs only ever supported the
   stock covers (riser seats on wall tops + plateaus instead) → **hand-trim
   the four slab lower ends below z 34 when the fabbed boards arrive**, or
   confirm the real logic-board corners are bare and clear. Gate fails on
   any stack hit OUTSIDE that zone.
2. **Mezzanine floor-boss budget ≤ 4.0** (stack top 61.9 + boss ≤ deck
   underside 67.9 − 2.0). Constrains part 5 (floor boss plate).
3. Shoulder flanges rise to z 79.55 — 7.65 proud of the deck at both ends
   (they close the end gaps; Jetson x −60.. keeps 5.5 clear of the rear fin).
4. Jetson heatsink height 21.5 is ⚠ REVIEW in dimensions.md — caliper before
   designing the hood; L2 gap currently 7.6 above heatsink+hood.
5. Front cable lanes: D456 USB3 runs inside the riser ceiling gap
   (stack-top → deck-underside is 6.0 with max bosses) to the deck slot.

## Service (unchanged from the outline table)

battery 0 screws · boards/Teensy/JP1 = D456 head off (2) + 4 flange screws,
riser lifts with Jetson/mast/L2 attached, robot standing · Jetson = hood off
· L2 = 4 mast-base screws · legs/shoulders per leg_v6.

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
