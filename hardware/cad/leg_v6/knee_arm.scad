// =============================================================================
// V6 Knee Arm — bolt-on top arm of the femur's knee yoke (print 4, no mirror).
// =============================================================================
// Separate part so the horn-seat face prints ON THE BED (the integral arm's
// underside printed over supports = rough seat, bad horn contact). Bolts to
// the femur fork shelf with 4x M3 into heat-sets; the screws register it.
// FEMUR-frame: plate spans z 17.75..21.75, shelf zone x 59..80, horn at 106.9.
// (rev 3, 2026-07-10: seat plane moved 17.2->17.75, caliper gap fix — see
// leg_v6_common.scad HORN_Z1.)
// Part-local: underside = z0 (PRINT THIS FACE DOWN), knee axis at x = KNEE_X.
// PRINT: PA6-CF, UNDERSIDE (horn-seat face, z0) DOWN — zero/minimal supports,
//   4 walls / 0.2 / 40% (print-batch §2). print 4 (no mirror).
// LA-23 (2026-07-11): the center horn counterbore (HORN_CTR_D x HORN_CTR_DEEP
// below) cuts into the ARM_THK=4.0 plate to depth 2.5, leaving a floor of
// EXACTLY 1.5mm -- the print-margin gate's minimum, zero slack. ARM_THK is a
// leg_v6_common.scad constant shared by every arm-plate feature across the
// whole leg (coax/femur yoke arms too), so bumping it here isn't a local
// change -- it ripples load-bearing geometry elsewhere and isn't "trivial."
// Shallowing HORN_CTR_DEEP instead would trade floor margin for horn
// screw-head clearance margin (same tradeoff coax.scad's LA-7 fix made),
// not eliminate the risk. Left as-is: non-load-bearing clearance pocket.
// FIRST-ARTICLE CHECK: after printing, probe the counterbore floor
// thickness (should read ~1.5mm) and confirm no witness/pinhole from a
// thin top layer before trusting this pocket on later reprints.
include <leg_v6_common.scad>

X0 = 59;                 // femur-frame plate start
KNEE_X = 106.9 - X0;     // 47.9 part-local
TIP_R = 15.85;

difference() {
    // plate: shelf rectangle blended to the knee disc
    // squared-end corners ROUNDED R8 (#50, 2026-07-11): fillet the cube end's
    // 2 sharp corners at (0, ±TIP_R) via offset(r)+offset(-delta) on the 2D
    // profile (rounds convex corners, leaves straight edges + the knee disc
    // unchanged). Mount bolts (6/16, ±8) sit >=6.8mm clear of the corners so
    // nothing is clipped; the corners are outside the bolt pattern
    // (non-structural overhang) + not a mating face -> free outline change,
    // ARM_THK / horn floor / holes all untouched.
    ROUND_R = 8;
    linear_extrude(ARM_THK)
        offset(r = ROUND_R) offset(delta = -ROUND_R)
            hull() {
                translate([0, -TIP_R]) square([80 - X0, 2*TIP_R]);
                translate([KNEE_X, 0]) circle(r = TIP_R);
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
    // horn coupling at the knee: locating recess on the UNDERSIDE + screws.
    // Center: Ø6.5 x 2.5 deep blind counterbore (rev 3) clears the horn's
    // own proud retention screw head (Ø5.4, ~1.5mm proud, MEASURED) — was
    // Ø3.4/M3_CLEAR through the full 4mm arm, too narrow to clear it.
    translate([KNEE_X, 0, -EPS]) {
        cylinder(d = HORN_OD + 2*CLR_HORN, h = 0.4 + EPS);
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                cylinder(d = M25_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = HORN_CTR_D, h = HORN_CTR_DEEP + EPS);
    }
}
