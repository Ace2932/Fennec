// =============================================================================
// NOVA chassis — L2 LiDAR MAST (riser deck -> Unitree L2, optical ctr ~+100)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame. L2: 75 x 75 x 65,
// 230g, bottom mount 4x M3 on 22.5 square, thread depth 6 (dimensions.md).
//
// Stack: base flange on the riser deck (bolts the underslung deck inserts
// at (44/60, +/-14), **M3x10** from ABOVE, counterbored — LONGER SCREWS
// PUNCTURE THE STACK ENVELOPE: an M3x16 tip lands at z 59.9, 4mm into the
// mezzanine's headroom; M3x10 tip = 65.9 with 5.1 of insert engagement)
// -> hollow shaft -> top plate at z 110.4..114.4. L2 bottom seats at
// 114.4 -> optical center ~146.9 = trunk top + 100.
//
// Cable: the L2 pigtail (RJ45 + power barrel) feeds DOWN through the plate
// slot (15 x 12) -> shaft bore (13 x 11 — passes the 11.7 x 8 RJ45 plug
// head flat AND the ~O10 DC barrel plug; ⚠ caliper the real plugs) ->
// the riser deck's 14 x 12 slot at (53.5, 0) -> trunk interior.
//
// Assembly ORDER (design-review fix — the reverse order deadlocks): bolt
// the BARE MAST to the deck first (the O7 head wells are open to the sky),
// THEN bolt the L2 on from BELOW the plate: its holes at (42.25/64.75,
// +/-11.25) clear the shaft, with 38.5mm of under-plate driver room
// (ball-end L-key, M3x8 up into the L2 base threads). L2 off = those same
// 4 plate screws — mast and Jetson stay untouched.
//
// Clearances (gate-enforced): shaft front wall x 44 vs Jetson carrier edge
// x 41.7 (2.3); flange rear edge x 63.3 vs the shoulder deck-extension fin
// at x 63.5 (0.2); L2 rear overhang vs Jetson heatsink top 101.3 (13.1 —
// heatsink height is ⚠ REVIEW, re-gate after caliper).
//
// Print: flange-down, tree supports under the four plate corners; 45°
// flares tie shaft->flange and shaft->plate (stiffness + fewer supports).

$fn = 64;
EPS = 0.05;

CTR = 53.5;                        // shaft/L2 center (x), y 0
FLG_Z0 = 71.9; FLG_T = 4;          // flange on the deck
FLG = [38, 63.3, -20, 20];         // x0 x1 y0 y1
MAST_BX = [44, 60]; MAST_BY = 14;  // riser deck insert positions
SHAFT = [44, 63.3, -9, 9];         // outer x0 x1 y0 y1
BORE  = [13, 11];                  // cable bore: RJ45 head 11.7x8 flat +
                                   // ~O10 DC plug (review fix; ⚠ caliper)
PLATE_Z0 = 110.4; PLATE_T = 4;     // L2 seat plane = 114.4
PLATE_HALF = 19;
PLATE_X1 = 69.1;   // rear edge pulled in: the flare's top corner grazed
                   // the periscope camera envelope (rear face 69.7);
                   // L2 bolt at x 64.75 keeps 4.35 washer room
L2_BCD = 22.5 / 2;                 // 11.25
M3_CLEAR = 3.4;

module flare(x0, x1, y0, y1, X0, X1, Y0, Y1, z0, z1) {
    // linear transition between two rectangles (hull of thin plates)
    hull() {
        translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, EPS]);
        translate([X0, Y0, z1 - EPS]) cube([X1 - X0, Y1 - Y0, EPS]);
    }
}

module l2_mast() {
    difference() {
        union() {
            // base flange
            translate([FLG[0], FLG[2], FLG_Z0])
                cube([FLG[1] - FLG[0], FLG[3] - FLG[2], FLG_T]);
            // flange -> shaft flare. Starts from a SUB-rect at x >= 44 so
            // nothing rises forward of the shaft above z 75.9 — the flare
            // toe grazed the Jetson envelope (gate catch: carrier bottom
            // plane 78.2 vs the old full-flange flare).
            flare(SHAFT[0], FLG[1], -18, 18,
                  SHAFT[0], SHAFT[1], SHAFT[2], SHAFT[3],
                  FLG_Z0 + FLG_T - EPS, 87);
            // shaft
            translate([SHAFT[0], SHAFT[2], FLG_Z0])
                cube([SHAFT[1] - SHAFT[0], SHAFT[3] - SHAFT[2],
                      PLATE_Z0 - FLG_Z0 + EPS]);
            // shaft -> plate flare
            flare(SHAFT[0], SHAFT[1], SHAFT[2], SHAFT[3],
                  CTR - PLATE_HALF, PLATE_X1, -PLATE_HALF, PLATE_HALF,
                  100.5, PLATE_Z0 + EPS);
            // top plate (L2 seat)
            translate([CTR - PLATE_HALF, -PLATE_HALF, PLATE_Z0])
                cube([PLATE_X1 - (CTR - PLATE_HALF), 2 * PLATE_HALF, PLATE_T]);
        }
        // cable bore, full height (plate slot 15x11 down to the flange)
        translate([CTR - BORE[0] / 2, -BORE[1] / 2, FLG_Z0 - EPS])
            cube([BORE[0], BORE[1], PLATE_Z0 + PLATE_T - FLG_Z0 + 2 * EPS]);
        translate([CTR - 7.5, -6, PLATE_Z0 - 6])
            cube([15, 12, PLATE_T + 6 + EPS]);
        // flange screws: M3x10 down into the riser deck inserts (see
        // header — longer screws puncture the stack envelope)
        for (bx = MAST_BX, sy = [-1, 1]) {
            translate([bx, sy * MAST_BY, FLG_Z0 - EPS])
                cylinder(d = M3_CLEAR, h = FLG_T + 12);
            translate([bx, sy * MAST_BY, FLG_Z0 + FLG_T])
                cylinder(d = 7, h = 30);     // head well (finger-start room)
        }
        // L2 bolt pattern: 4x M3x8 from BELOW the plate into the L2 base
        for (sx = [-1, 1], sy = [-1, 1])
            translate([CTR + sx * L2_BCD, sy * L2_BCD, PLATE_Z0 - EPS])
                cylinder(d = M3_CLEAR, h = PLATE_T + 2 * EPS);
    }
}

l2_mast();
