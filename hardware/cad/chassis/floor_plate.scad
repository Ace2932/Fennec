// =============================================================================
// NOVA chassis — FLOOR PLATE (part 5): drill template + load spreader
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (+x FRONT).
// Sits ON the stock trunk floor (top z 3.9), 2.0 thick -> top plane 5.9 =
// the mezzanine seat (the riser's headroom math budgeted exactly this).
//
// Three jobs:
//   1. BATTERY SANDWICH: 6x M3x12 countersunk here, through the (drilled)
//      floor, into the pocket's nut-trap columns at (x +/-40/0, y +/-26.5).
//      The plate spreads the 510g pack's load across the floor slab.
//   2. MEZZANINE SEAT: 4x O2.5 pilots at (-41/+33, +/-33) — the power_v2
//      board's MEASURED mount pattern (74 x 66, from the fab .kicad_pcb;
//      hole XY unchanged by the standoff-height fix below — do not touch).
//      stack center at x = -3.5 (STACK_CTR below): shifted 3.5 rearward so
//      the FRONT stack corners clear the trunk's corner slabs entirely
//      (front trim no longer needed; rear slabs still get trimmed to
//      x <= -60.5) and the CoM pulls ~3.5 of the wanted 8 rearward. (An
//      earlier draft of this note said -4; -3.5 is the built value.)
//      M3x10 SELF-TAP through the
//      board standoff bases into plate+floor (5.9 of bite; the belly pack
//      sits under the floor center, so under-floor nuts are impossible).
//      STANDOFF LENGTH (floor top z5.9 -> power board bottom): 20mm, the
//      M3x20 brass standoffs already ON HAND (order note, memory
//      project-power-board-arm-phase4 2026-06-14). Corrected 2026-07-09
//      from a stale ~16mm spec: the ordered 1000uF caps (C1-C5) are the
//      Ø10x17mm cans, so 16mm left them 1mm proud of the floor (the order
//      note flagged "1mm over the 16mm spec"). At 20mm the caps bottom at
//      z9 -> 3.0mm clear of the floor plate/stock trunk floor. The board +
//      caps are ALREADY ORDERED/FIXED, so the chassis standoff is the free
//      dimension. Fit window S in [~18, 24.7mm]: floor min ~18 clears the
//      17mm cans, ceiling 24.7 is the riser-deck headroom for the FULL
//      stack (power board + pb->lb standoff + logic board, component-side
//      up). 20mm gives 3.0mm floor / 5.68mm deck margins — see
//      power_board_model.py (STANDOFF_FLOOR_MM) + check_fit.py case 11 for
//      live numbers. The logic board's stack height is no longer an
//      estimate: power_board_model.logic_board_mesh() parses
//      nova_pcb_v6_logic.kicad_pcb directly, tallest deck-facing part is
//      the Teensy 4.1 / Arduino Nano socket footprint (catalog part,
//      13.0mm) -> stack top z62.22, 5.68mm clear of the deck (z67.9). No
//      Teensy calipering needed.
//   3. DRILL TEMPLATE: clamp the plate, drill O3.4 (battery) + O2.5
//      (stack) through the stock floor using these holes as guides.
//
// MRBF / Blue Sea 5191 block: 2x M5 slots on the starboard-rear solid
// floor (clear of the big rear opening) — ⚠ block dims UNMEASURED
// (dimensions.md ❌); finalize slot spacing at caliper. Battery leads
// arrive beside it through the rear flange notch.
//
// Rear cutout mirrors the trunk's rear floor opening (weight, airflow
// from the belly gap, inspection). Print: flat, zero supports, PETG-CF
// fine (non-structural spreader).
// Fit gate: check_fit.py case 9.

$fn = 48;
EPS = 0.05;

T = 2.0;                        // plate thickness (z 3.9..5.9)
X0 = -62; X1 = 45;              // rear 1.5 off the open end; front clear of
                                // the raised stock "F" arrow (x ~46..53)
HW = 48;                        // halfwidth (walls inner +/-48.93)
// rear corner clips: the trunk's corner POSTS flare to (x -55.3..-63.3,
// y +/-35.2..48.8) at floor level — gate catch 2026-07-06
BAT_X = [-40, 0, 40];  BAT_Y = 26.5;
STACK_CTR = -3.5;   // rear board edge -59.5: 0.5 off the corner posts
                    // (x -60..-63.3); front corners 52.5 clear the front
                    // slabs (53.3) by 0.8 -> rear-only trim + CoM -3.5
STK_X = [-40.5, 33.5];  STK_Y = 33;  // power_v2 fab pattern 74 x 66
MRBF = [[-38, -22], [-26, -22]];  // 2x M5 slot centers (⚠ caliper 5191)

module floor_plate() {
    difference() {
        translate([X0, -HW, 3.9]) cube([X1 - X0, 2 * HW, T]);
        // battery sandwich: O3.4 + 90-deg csk (heads flush, stack above)
        for (bx = BAT_X, sy = [-1, 1]) {
            translate([bx, sy * BAT_Y, 3.9 - EPS])
                cylinder(d = 3.4, h = T + 2 * EPS);
            translate([bx, sy * BAT_Y, 5.9 - 1.7])
                cylinder(d1 = 3.4, d2 = 6.8, h = 1.7 + EPS);
        }
        // mezzanine pilots (drill guides too)
        for (sx = STK_X, sy = [-1, 1])
            translate([sx, sy * STK_Y, 3.9 - EPS])
                cylinder(d = 2.5, h = T + 2 * EPS);
        // (MRBF/5191 slots REMOVED 2026-07-07: the calipered block is
        //  61.6×20×46.5 — 46.5 tall — and the mezzanine stack fills the
        //  whole plate footprint to z64. No room here. The block mounts
        //  in the BELLY at the pack instead, per the design intent
        //  "MRBF-30 at the pack" — see battery_pocket.scad tail mount.)
        // rear cutout over the trunk's rear floor opening
        hull() for (px = [-58, -48], py = [-22, 22])
            translate([px, py, 3.9 - EPS]) cylinder(r = 4, h = T + 2 * EPS);
        // rear corner clips (trunk corner posts, base flare included)
        for (sy = [-1, 1])
            translate([-62 - EPS, min(sy * (HW + EPS), sy * 34.7), 3.9 - EPS])
                cube([62 - 54.8 + EPS, HW - 34.7 + 2 * EPS, T + 2 * EPS]);
    }
}

floor_plate();
