// =============================================================================
// V6 Coax (rev 2) — houses the HAA STS3215, yoke-drives the femur at HFE.
// =============================================================================
// Local frame (RIGHT leg; mirror for left):
//   haa axis = Y AXIS through the origin (spline). Horn faces -Y (shoulder).
//   +X = OUTBOARD. +Z = up.
//   hfe axis = X line at (y = +11.6, z = -9.5)  [MEASURED, A360 assembly]
//   femur mid-plane at x = +33.8  ->  foot 33.8 + 30.5 = 64.3 = IK d ✓
//
// Joints:
//   * SHOULDER yokes this servo: front arm bolts the haa horn; the shoulder's
//     rear-arm boss reaches through THIS part's floor window and bolts the
//     haa BOTTOM WHEEL (rev-2 pattern, both sides bolted)
//   * FEMUR yoke: inboard arm bolts the femur servo's horn (arm inner face
//     at x = 16.6 = femur horn face); outboard arm at x 56.2..60.2 carries
//     a Ø19 boss inboard to 51.5 = the femur wheel face, and bolts it
//   * cables: bay faces +Y (rear); tunnel exits the BOTTOM end toward the
//     femur — wires drop down the leg
//
// Print: rear face (+Y) down; supports under the yoke bridge span.

include <leg_v6_common.scad>

HFE_Y     = 11.6;
HFE_Z     = -9.5;
FEMUR_MID = 33.8;

BLK_X  = CASE_HW + CLR_POCKET + WALL;     // ±15.85
BLK_Y0 = -HORN_Z1;                        // -17.2 front (horn-face plane)
BLK_YF = -FLOOR_BOT;                      // +22.2 rear (floor bottom)

ARM_IN_X0  = FEMUR_MID - HORN_Z1 - ARM_THK;  // 12.6
ARM_IN_X1  = FEMUR_MID - HORN_Z1;            // 16.6 (contacts femur horn face)
ARM_OUT_X0 = FEMUR_MID - YOKE_BOT_IN;        // 56.2 (femur floor bottom +0.2)
ARM_OUT_X1 = ARM_OUT_X0 + ARM_THK;           // 60.2
ARM_HALF_YZ = 16;
BRIDGE_Z0  = 6.9;                            // femur disc sweep tops at 6.35

module arm_plate(x0, x1) {
    hull() {
        translate([x0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = x1 - x0);
        translate([x0, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
            cube([x1 - x0, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
    }
}

module coax_v6() {
    difference() {
        union() {
            // haa pocket block
            translate([-BLK_X, BLK_Y0, -38.4])
                cube([2*BLK_X, BLK_YF - BLK_Y0, 38.4 + 13.4]);
            // pocket platform, transformed with the pocket
            rotate([0, -90, 0]) rotate([90, 0, 0]) pocket_platform_pos();
            // femur yoke: inboard arm, bridge, outboard arm + wheel boss
            arm_plate(ARM_IN_X0, ARM_IN_X1);
            arm_plate(ARM_OUT_X0, ARM_OUT_X1);
            translate([BLK_X - 2, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
                cube([ARM_OUT_X1 - BLK_X + 2, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
            // outboard-arm boss reaching the femur wheel (56.2 -> 51.5)
            translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
                wheel_boss_pos();
            // front strap bosses (0.8 proud: the case top cap ridge stands
            // 0.2 proud of the horn-face plane)
            for (sx = [-1, 1])
                translate([sx*14.25, BLK_Y0 + EPS, -31]) rotate([90, 0, 0])
                    cylinder(d = 7, h = 0.8);
        }

        // ---- HAA pocket: spline = Y axis, horn -Y, bulk down ----
        rotate([0, -90, 0]) rotate([90, 0, 0]) sts_pocket_neg(extra_top = 25);

        // front strap pilots (through the bosses into the wall rims)
        for (sx = [-1, 1])
            translate([sx*14.25, BLK_Y0 - 0.8 - EPS, -31]) rotate([-90, 0, 0])
                cylinder(d = 2.05, h = 8.8);

        // ---- HFE couplings on the X axis at (HFE_Y, HFE_Z) ----
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0]) {
            // inboard arm: coupling +z maps to -x (inboard); femur horn face
            // lands on x = 16.6, screws run 16.6 -> 12.6
            horn_couple_neg();
            // screw-head counterbores into the pocket wall's inner face
            // (heads must not intrude into the haa servo space)
            for (a = [45 : 90 : 315])
                rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                    translate([0, 0, YOKE_TOP_IN + ARM_THK - EPS])
                        cylinder(d = 5.4, h = 3);
            translate([0, 0, YOKE_TOP_IN + ARM_THK - EPS])
                cylinder(d = 5.6, h = 3);
        }
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0]) {
            // outboard arm + boss = "bottom arm" (+z -> -x inboard)
            wheel_couple_neg();
        }

        // femur swept clearance between the arms (stops at the boss face)
        translate([ARM_IN_X1 + EPS, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = 16.4, h = (FEMUR_MID - WHEEL_Z0) - ARM_IN_X1 - 0.1);
    }
}

coax_v6();
