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
//     femur — wires drop down the leg. CALIPER-CONFIRMED 2026-07-10: the
//     servo body + cable dropping out the bottom needs ~37mm; the pocket's
//     vertical drop-channel is ~52mm (coax z -38.4..+13.8) → ~15mm spare,
//     clears. NB the cable routes out the BOTTOM, NOT beside the servo —
//     the pocket WIDTH is only 25.4mm (fits the 24.8 case + ~0.6, no room
//     for a cable alongside). Harness plan #31.
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
BRIDGE_Z0  = 7.4;                            // femur disc sweep tops at 6.35; raised 0.5 after a corner graze at the sweep gate

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
            // outboard-arm ROOT DOUBLER (backlog #26, stress audit
            // 2026-07-06): the arm-to-bridge junction was the only member
            // on the robot under SF 15 — ~14 MPa at the 4-thick root under
            // a 20 N lateral/turning foot load = fatigue SF ~1.9 per
            // stride. 2-thick outboard gusset over the junction (z 0..13.4,
            // tapering out by z -1.5) doubles the root modulus -> ~6 MPa.
            // Taper stops ABOVE the wheel-screw head zone (top BCD heads
            // reach z -1.95; ARM_THK itself is shared by every couple cut
            // and cannot change). L mirror: symmetric in y, mirrors clean.
            hull() {
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, 0])
                    cube([2, 2*ARM_HALF_YZ, 13.4]);
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, -1.5])
                    cube([0.5, 2*ARM_HALF_YZ, 14.9]);
            }
            // outboard-arm boss reaching the femur wheel (56.2 -> 51.5)
            translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
                wheel_boss_pos();
            // front strap pads (0.8 proud: the case top cap ridge stands
            // 0.2 proud of the horn-face plane); full wall-width blocks
            // outboard edge held to x15.6: at 16.6 it grazed the femur rim
            // plane at full hip swing (sweep-gate find)
            for (sx = [-1, 1])
                translate([min(sx*12.6, sx*15.6), BLK_Y0 - 0.8, -36])
                    cube([3, 0.8 + EPS, 10]);
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
            // LA-7 fix (2026-07-11): the default HORN_CTR_DEEP=2.5 assumes a
            // full ARM_THK=4.0 slab behind the counterbore, but here the
            // inboard arm's back face butts the HAA pocket cavity wall
            // (CASE_HW+CLR_POCKET=12.85) at only 3.2mm from the horn seat
            // (16.05) -- NOT the 4.0mm ARM_THK gives -> floor was 0.7mm
            // (ray-cast confirmed; disabling the femur-swept-clearance void
            // entirely made ZERO difference, so that void -- the audit's
            // original suspect -- isn't the actual cause). "Add material
            // behind" isn't possible either: that space IS the servo pocket
            // clearance wall, a hard fit constraint. Shallow the cut instead:
            // ctr_deep=1.65 -> floor 3.2-1.65=1.55mm (>=1.5 gate, 0.05
            // spare) and screw-head margin 1.65-1.5(proud)=0.15mm (thin but
            // positive -- the 3.2mm local budget can't give both more than
            // this split).
            horn_couple_neg(ctr_deep = 1.65);
            // screw-head counterbores into the pocket wall's inner face
            // (heads must not intrude into the haa servo space). Depth 4
            // (was 3): the 3-deep bores ended COINCIDENT with the pocket
            // void surface and the L-mirror's CSG re-run left a -7.8 mm3
            // inverted shell there (mesh-audit find 2026-07-06) — punch
            // decisively through so the cuts merge.
            for (a = [45 : 90 : 315])
                rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                    translate([0, 0, YOKE_TOP_IN + ARM_THK - EPS])
                        cylinder(d = 5.4, h = 4);
            translate([0, 0, YOKE_TOP_IN + ARM_THK - EPS])
                cylinder(d = 5.6, h = 4);
        }
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0]) {
            // outboard arm + boss = "bottom arm" (+z -> -x inboard)
            wheel_couple_neg();
        }

        // side marker: 1 dot = RIGHT (L wrapper adds a 2nd).
        // LA-2 fix (2026-07-11): the old site (6, BLK_Y0-EPS, 8) targeted
        // the HORN-FACE plane (y=BLK_Y0=-17.75) -- but that plane is the
        // HAA pocket's open coupling face (spline=Y, horn faces -Y per the
        // file header), not a closed wall: ray-cast confirmed 0 solid hits
        // across the whole scanned x/z grid there. Relocated to the REAR
        // face (y=BLK_YF=+22.2, the pocket-floor-equivalent plane, closed
        // except at the column-screw/wheel-window/tunnel cuts): (x=-12,
        // z=8) ray-cast confirmed solid to a depth of >=1.5mm (real
        // material, clear of those cuts) and air just outside y=22.2.
        translate([-12, BLK_YF + EPS, 8]) rotate([90, 0, 0]) cylinder(d = 3, h = 1);

        // vent window, OUTBOARD (-X) wall only (the inboard wall carries
        // the femur-yoke arm root)
        translate([-BLK_X - 1, -8, -30]) cube([4.5, 16, 24]);

        // zip anchors flanking the bottom cable-tunnel exit (hip service
        // loop anchors here; the femur's first anchor takes the other end)
        // LA-16 fix (2026-07-11): the old pair sat on the OUTBOARD wall
        // (x=-BLK_X-1, y=3±5) but the tunnel exit (common-frame tunnel,
        // rotated into this part) opens at world x~0, y~16.85, z
        // -42.4..-31.2 -- ~22mm away, straight path through solid ~50% of
        // it (raw 90° corner). Relocated to genuinely flank the tunnel:
        // grid-scanned the real mesh at the tunnel's own z-band and found a
        // clean gap x[-9,9], y[14,19] at z=-36 (below z=-34, where the HAA
        // pocket cavity ALSO overlaps and thins the side walls to 3.2mm).
        // Holes now start at x=∓7 (inside the open tunnel void -- reachable
        // from the tunnel, robust CSG overlap) and punch straight out
        // through the side wall (genuine through-hole, not a blind pocket --
        // matches the femur/tibia LA-4 convention: a blind pocket can't
        // loop a zip tie). y=17 matches the tunnel's own y-center.
        for (sx = [-1, 1])
            translate([sx * 7, 17, -36]) rotate([0, sx*90, 0])
                cylinder(d = 3.2, h = BLK_X - 6);

        // femur swept clearance between the arms (stops at the boss face)
        translate([ARM_IN_X1 + EPS, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = 16.7, h = (FEMUR_MID - WHEEL_Z0) - ARM_IN_X1 - 0.1);   // disc r16.05 + 0.65 (was 16.4/0.35 — under print tol)
    }
}

coax_v6();
