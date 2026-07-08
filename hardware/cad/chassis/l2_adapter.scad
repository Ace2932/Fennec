// =============================================================================
// L2 ADAPTER PLATE — accessible mount for the Unitree L2 (access audit 2026-07-08)
// =============================================================================
// The L2's Ø51 (R25.5) 4-hole base pattern doesn't match the head crown, and 2
// of the 4 bolts are UNREACHABLE on the assembled head (the head's front
// structure sits directly under them). This plate fixes it:
//   1. the L2 bolts to THIS plate ON THE BENCH — all 4 accessible (M3 up from
//      below, heads countersunk flush into the plate bottom).
//   2. the plate (with the L2 on it) drops onto the crown: a FRONT TONGUE slides
//      under a crown lip + 2 REAR bolts from BELOW the crown into the plate's
//      heat-sets (both reachable). No front bolt needed.
// Decouples the sensor pattern from the head; L2 stays field-swappable.
//
// Frame: head/world (trunk mm). Sits on the crown top (z128), 5 mm thick
//   (z128..133); the L2 base then sits at z133 (optical ~z165, still fine).
// PRINT: PA6-CF or PETG-CF, FLAT (bottom on the bed), ~6 g. print 1.

$fn = 48; EPS = 0.05; M3_CLEAR = 3.4;
Z0  = 128;  T = 5;                 // adapter on the crown top z128, 5 thick
CTR = 126.5; L2_BCD = 18;          // L2 Ø51 pattern at 45° -> holes at ±18

module l2_adapter() {
    difference() {
        union() {
            translate([104, -24, Z0]) cube([42, 48, T]);       // main plate x104..146
            translate([146, -14, Z0]) cube([12, 28, 2]);        // front tongue x146..158, 2 thin
                                                                // (starts at x146 = crown-lip start so the
                                                                //  lip only ever hooks the THIN tongue, never
                                                                //  the 5mm main plate — clash fix 2026-07-08)
        }
        // 4x L2 bolts: CSK from the BOTTOM (heads flush), M3 up into the L2 base
        for (sx = [-1, 1], sy = [-1, 1]) {
            translate([CTR + sx * L2_BCD, sy * L2_BCD, Z0 - EPS])
                cylinder(d = M3_CLEAR, h = T + 2 * EPS);
            translate([CTR + sx * L2_BCD, sy * L2_BCD, Z0 - EPS])
                cylinder(d1 = 6.2, d2 = M3_CLEAR, h = 2.2);      // countersink
        }
        // 2x REAR crown-mount heat-sets (from the plate BOTTOM z128, +z 4mm) —
        // the bolt comes UP from below the crown rear lip into these.
        for (sy = [-1, 1])
            translate([110, sy * 14, Z0 - EPS]) cylinder(d = 4.0, h = 4.2);
    }
}

l2_adapter();
