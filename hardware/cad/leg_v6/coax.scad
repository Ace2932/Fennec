// =============================================================================
// V6 Coax — houses the HAA (hip-roll) STS3215, yoke-drives the femur at HFE.
// =============================================================================
// Local frame (RIGHT leg; mirror for left):
//   haa axis  = Y AXIS through the origin (spline line). Horn faces -Y (the
//               shoulder). +X = OUTBOARD. +Z = up.
//   hfe axis  = X line at (y = +11.6, z = -9.5)   [MEASURED from the A360
//               assembly: hfe sits 30.0 behind the haa horn-center plane and
//               9.5 below the haa axis]
//   femur mid-plane at x = +33.8  ->  foot plane 33.8 + 30.5 = 64.3 = IK d ✓
//
// Assembly story:
//   1. HAA servo slides in HORN-FIRST from the front (-Y) opening; 4x
//      countersunk M2.5 enter from the REAR floor into the case's rear-face
//      threads (the case mount square exists on both shaft-normal faces)
//   2. the SHOULDER yokes this servo: front arm bolts the horn, rear arm =
//      M3 shoulder screw into the rear floor's heat-set pad
//   3. the FEMUR hangs in the side yoke: its horn bolts into the INBOARD
//      arm (screws driven from outboard through the arm), its floor pad
//      takes the M3 idler through the OUTBOARD arm
//   4. wires exit the pocket's top wall
//
// Print: rear face (+Y) down. Pocket opening prints sideways-free; the yoke
// bridge needs supports under its outboard span (or print with tree supports).

include <leg_v6_common.scad>

HFE_Y   = 11.6;    // hfe axis, behind haa spline plane (MEASURED)
HFE_Z   = -9.5;    // hfe axis, below haa axis (MEASURED)
FEMUR_MID = 33.8;  // femur body mid-plane outboard of haa axis (v6-derived)

// pocket block extents (haa servo: L vertical, W lateral, shaft along Y)
BLK_X  = SERVO_W/2 + CLR_POCKET + WALL;          // ±15.65
BLK_Y0 = -(SERVO_H/2 + HORN_THK);                // -19.65 front (horn face)
BLK_YF =  SERVO_H/2 + FLOOR;                     // +20.15 rear floor face
// block z: body spans -35.2..10.2 (L vertical, bulk down) + walls

// femur yoke arms (plates normal to X), features centered (HFE_Y, HFE_Z)
ARM_IN_X0  = FEMUR_MID - 17.15 - 0.3 - ARM_THK;  // 12.35
ARM_IN_X1  = FEMUR_MID - 17.15 - 0.3;            // 16.35 (femur rim +0.3)
ARM_OUT_X0 = FEMUR_MID + 22.15 + 0.3;            // 56.25 (femur pad +0.3)
ARM_OUT_X1 = ARM_OUT_X0 + ARM_THK;               // 60.25
ARM_HALF_YZ = 16;                                // arm plate half-extent
BRIDGE_Z0  = 6.9;                                // swept femur disc tops at 6.35

module arm_plate(x0, x1) {
    hull() {
        translate([x0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = x1 - x0);
        // merge upward into the bridge
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
            // rear idler pad ring (shoulder rear-arm pivot, on haa axis)
            translate([0, BLK_YF - EPS, 0]) rotate([-90, 0, 0])
                cylinder(d = IDLER_PAD_D, h = IDLER_PAD_H + EPS);
            // femur yoke: inboard arm, bridge, outboard arm
            arm_plate(ARM_IN_X0, ARM_IN_X1);
            arm_plate(ARM_OUT_X0, ARM_OUT_X1);
            translate([BLK_X - 2, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
                cube([ARM_OUT_X1 - BLK_X + 2, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
        }

        // ---- HAA pocket: spline = Y axis, horn -Y, L vertical (bulk down),
        //      open toward -Y (servo enters horn-first from the front)
        rotate([0, -90, 0]) rotate([90, 0, 0])
            translate([-SPLINE_X, 0, 0]) servo_pocket_neg(extra_top = 25);

        // rear heat-set bore (M3, into pad + floor) on the haa axis
        translate([0, BLK_YF + IDLER_PAD_H + EPS, 0]) rotate([90, 0, 0])
            cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

        // haa horn clearance through the front face
        translate([0, BLK_Y0 - 1, 0]) rotate([-90, 0, 0])
            cylinder(d = HORN_OD + 3, h = HORN_THK + 1.5);

        // ---- HFE couplings on the X axis at (HFE_Y, HFE_Z) ----
        translate([0, HFE_Y, HFE_Z]) {
            // inboard arm: horn seat opens OUTBOARD (+X), screws through arm
            translate([ARM_IN_X1 - HORN_THK - 0.3, 0, 0]) rotate([0, 90, 0])
                cylinder(d = HORN_OD + 2*CLR_HORN, h = HORN_THK + 0.35);
            // 4x M2.5 BCD14 + M3 center, drilled through the inboard arm
            for (a = [45 : 90 : 315])
                translate([ARM_IN_X0 - 1,
                           HORN_BCD/2*cos(a), HORN_BCD/2*sin(a)])
                    rotate([0, 90, 0]) cylinder(d = M25_CLEAR, h = ARM_THK + 2);
            translate([ARM_IN_X0 - 1, 0, 0]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = ARM_THK + 2);
            // outboard arm: M3 idler through-hole + head counterbore outside
            translate([ARM_OUT_X0 - 1, 0, 0]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = ARM_THK + 2);
            translate([ARM_OUT_X1 - 1.8, 0, 0]) rotate([0, 90, 0])
                cylinder(d = 6.4, h = 2);
        }

        // retention-strap pilots: strap screws across the FRONT opening over
        // the servo's lower end (z=-33), pilots into the side-wall front faces
        for (sx = [-1, 1])
            translate([sx*(BLK_X - 1.6), BLK_Y0 - EPS, -33]) rotate([-90, 0, 0])
                cylinder(d = 2.05, h = 8);

        // femur swept clearance: full revolve of the femur hip disc + slab
        // between the arms (keeps the bridge from intruding)
        translate([ARM_IN_X1 + EPS, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = 16.2, h = ARM_OUT_X0 - ARM_IN_X1 - 2*EPS);
    }
}

coax_v6();
