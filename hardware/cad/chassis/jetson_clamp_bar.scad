// =============================================================================
// JETSON CLAMP BAR — one side's case hold-down (consolidates 2 corner clamps)
// =============================================================================
// #44: the 4 separate `jetson_clamp` corner pieces → 2 of THESE bars (one per
// ±Y side). Each bar spans the side's 2 uprights, bolts to both upright tops
// (2× M2), and its underside caps the case's 2 SOLID CORNER COLUMNS (z102.8) —
// the case-top mid-side is ≤102.5 (measured) so a FLAT bar clears it (no arch).
// Fewer loose parts at assembly; same drop-in-then-bolt scheme.
// Bear-only (NO case drilling); add a TPU/EVA shim on the bearing pads.
// World/trunk frame (matches jetson_case_mount — keep consts in sync).
// PRINT: PA6-CF, flat, ~4 g. print 2 (both sides identical — mirror-symmetric
//   in y about the corners, so ONE part serves +y AND -y).

$fn = 32; EPS = 0.05; M2_CLEAR = 2.3;

FRONT_PXC = 47.3; REAR_PXC = -59.0;   // upright x centres (this side)
POST_YC = 50.35;                       // upright y centre (bolt)
HY = 41.45;                            // corner-column y (bearing) — |y| for +y side
CORNER_Z = 102.8; BAR_T = 4;

module jetson_clamp_bar() {
    difference() {
        // flat bar: x across both uprights, y from the corner column out to the
        // upright bolt. Inner edge at the column (HY) so it never rides inboard
        // onto the rising faceted top.
        translate([REAR_PXC - 3, HY, CORNER_Z])
            cube([FRONT_PXC - REAR_PXC + 6, POST_YC + 3 - HY, BAR_T]);
        // 2x M2 clearance at the upright tops
        for (px = [FRONT_PXC, REAR_PXC])
            translate([px, POST_YC, CORNER_Z - EPS])
                cylinder(d = M2_CLEAR, h = BAR_T + 2 * EPS);
    }
}

jetson_clamp_bar();
