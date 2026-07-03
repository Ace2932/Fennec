// =============================================================================
// V6 Knee Arm — bolt-on top arm of the femur's knee yoke (print 4, no mirror).
// =============================================================================
// Separate part so the horn-seat face prints ON THE BED (the integral arm's
// underside printed over supports = rough seat, bad horn contact). Bolts to
// the femur fork shelf with 4x M3 into heat-sets; the screws register it.
// FEMUR-frame: plate spans z 17.2..21.2, shelf zone x 59..80, horn at 106.9.
// Part-local: underside = z0 (PRINT THIS FACE DOWN), knee axis at x = KNEE_X.
include <leg_v6_common.scad>

X0 = 59;                 // femur-frame plate start
KNEE_X = 106.9 - X0;     // 47.9 part-local
TIP_R = 15.85;

difference() {
    // plate: shelf rectangle blended to the knee disc
    hull() {
        translate([0, -TIP_R, 0]) cube([80 - X0, 2*TIP_R, ARM_THK]);
        translate([KNEE_X, 0, 0]) cylinder(r = TIP_R, h = ARM_THK);
    }
    // 4x M3 + head counterbores (femur-frame 65/75, ±8). The DIAGONAL pair
    // is close-fit Ø3.1 — the screws register the plate (clearance holes
    // alone let the knee axis wander under cyclic shear).
    for (hx = [65 - X0, 75 - X0], hy = [-8, 8]) {
        dowel = (hx == 65 - X0 && hy == -8) || (hx == 75 - X0 && hy == 8);
        translate([hx, hy, -EPS])
            cylinder(d = dowel ? 3.1 : M3_CLEAR, h = ARM_THK + 2*EPS);
        translate([hx, hy, ARM_THK - 1.8]) cylinder(d = 6.4, h = 2);
    }
    // horn coupling at the knee: locating recess on the UNDERSIDE + screws
    translate([KNEE_X, 0, -EPS]) {
        cylinder(d = HORN_OD + 2*CLR_HORN, h = 0.4 + EPS);
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                cylinder(d = M25_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = M3_CLEAR, h = ARM_THK + 2*EPS);
    }
}
