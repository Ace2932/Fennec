// =============================================================================
// V6 servo retention strap — screws over the servo tail (print 4+ per robot).
// =============================================================================
// plate, 2x Ø2.9 (M2.5 self-tap clearance) holes at ±14.25,
// matching strap_pilot_neg() in leg_v6_common.scad. Sits on the pocket rims
// (rim top = servo body top): clamps the body down into the pocket.
$fn = 48;
difference() {
    hull() for (sy = [-1, 1])
        translate([0, sy*13, 0]) cylinder(d = 8, h = 2.5);
    for (sy = [-1, 1])
        translate([0, sy*14.25, -0.1]) cylinder(d = 2.9, h = 2.8);
}
