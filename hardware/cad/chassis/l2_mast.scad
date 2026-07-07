// =============================================================================
// NOVA chassis — L2 LiDAR MAST (riser deck -> Unitree L2, optical ctr ~+100)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame. L2: 75 x 75 x 65,
// 230g, bottom mount 4x M3 on 22.5 square, thread depth 6 (dimensions.md).
//
// JETSON-CASE PIVOT (2026-07-07): the official Jetson case (110.3 x 93.9 x
// 38.2) now owns the deck (x -62..48.3). The old center-front mast base
// (flange x38 / shaft x44) cannot coexist with it. RESOLUTION (place_case.py):
// the L2 OPTICAL POSITION is UNCHANGED (plate CTR 53.5) but the mast BASE is
// COMPACTED into the FRONT STRIP the rearward-shifted case leaves free
// (flange/shaft x51.3..63.0, 3.0 clear of the case front), and the plate is
// LIFTED 3mm (z110.4->113.4) so it cantilevers OVER the case top (110.1)
// with 3.3 clearance. The L2 CoM sits ~over the base (CTR 53.5 vs base ctr
// ~57) so the static cantilever moment is tiny; dynamic loads on the 4x M3
// are far inside proof load (the nylon fuses are still the intended stop).
//
// Stack: compact base flange on the riser deck (bolts the underslung deck
// inserts at (54/59.0, +/-14), **M3x10** from ABOVE, counterbored — longer
// screws puncture the stack envelope) -> hollow shaft -> top plate at
// z 113.4..117.4. L2 bottom seats at 117.4 -> optical center ~150 = trunk
// top + 103.
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
// Clearances (gate-enforced): flange/shaft front wall x 51.3 vs case front
// x 48.3 (3.0); rear edge x 63.0 vs the shoulder deck-ext fin at x 63.5
// (0.5) and the D456 stem at x 63.45 (0.45); plate bottom z 113.4 vs case
// top z 110.1 (3.3) and vs D456 periscope top z 109.5 (3.9).
//
// Print: flange-down, tree supports under the four plate corners; 45°
// flares tie shaft->flange and shaft->plate (stiffness + fewer supports).

$fn = 64;
EPS = 0.05;

CTR = 53.5;                        // shaft/L2 center (x), y 0 — UNCHANGED
FLG_Z0 = 71.9; FLG_T = 4;          // flange on the deck
FLG = [51.3, 63.0, -20, 20];       // COMPACT front-strip base (case pivot):
                                   // front 51.3 = 3.0 clear of the case
                                   // (front 48.3); rear 63.0 = 0.5 to the
                                   // deck-ext fin / 0.45 to the D456 stem
MAST_BX = [54, 59.0]; MAST_BY = 14; // riser deck insert positions (front-strip
                                    // couple 5.5; L2 CoM ~over base, moment
                                    // tiny — see header)
SHAFT = [51.6, 63.0, -9, 9];       // outer x0 x1 y0 y1 — front 0.3 BEHIND the
                                   // flange front (51.3) so the flange front
                                   // face isn't coplanar with the flare front
                                   // (coplanarity -> non-manifold union)
BORE  = [13, 11];                  // cable bore: RJ45 head 11.7x8 flat +
                                   // ~O10 DC plug (review fix; ⚠ caliper)
PLATE_Z0 = 113.4; PLATE_T = 4;     // LIFTED +3 (case pivot): L2 seat = 117.4,
                                   // 3.3 over the case top (110.1)
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
            // shaft -> plate flare. RAISED to z110.6 (case pivot): below the
            // case top (110.1) only the shaft (x51.6..63) exists — clear of
            // the case (front 48.3) by 3.3. The rearward-widening gusset lives
            // entirely ABOVE the case top so it never enters the case volume.
            // (A 100.5-start flare dipped to x~44 at z104-108, INSIDE the
            // case — gate catch 2026-07-07.) Short steep gusset -> support it.
            flare(SHAFT[0], SHAFT[1], SHAFT[2], SHAFT[3],
                  CTR - PLATE_HALF, PLATE_X1, -PLATE_HALF, PLATE_HALF,
                  110.6, PLATE_Z0 + EPS);
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
