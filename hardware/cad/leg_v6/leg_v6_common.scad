// =============================================================================
// NovaSM3 Leg V6 — functional STS3215 leg, designed for assembly
// =============================================================================
// V5 carved cavities into the stock closed shells — no insertion path, no
// retention, no serviceable joints. V6 is a ground-up functional design built
// around how the STS3215 actually mounts (same pattern as the stock NovaSM3
// hobby-servo legs and the SO-ARM100 brackets):
//
//   * servo DROPS INTO an open-top pocket, 4x M2.5 screws through the pocket
//     floor into the case's threaded bottom-face holes (STEP-verified square)
//   * the DRIVEN link is a YOKE: top arm bolts to the Ø20 output horn
//     (4x M2.5 on Ø14 BCD + center screw); bottom arm pivots on an M3
//     shoulder screw into a HEAT-SET BOSS in the pocket floor, coaxial with
//     the spline. (NOT the Ø20 bottom wheel: that bolt-on wheel and the
//     case-screw square both occupy r<10 of the bottom face — mutually
//     exclusive with floor mounting. The floor boss routes joint side-load
//     into the printed bracket instead of the servo case. M3 x D4.6 x L5.7
//     insert.)
//   * every joint separates with 5 screws (4x M2.5 horn + 1x M3 idler);
//     every servo lifts out after removing its 4 floor screws
//
// KINEMATICS ARE LOCKED to the measured B2 numbers (dimensions.md §6):
//   femur hfe->kfe 106.9 | tibia kfe->foot pin 129.0 | lateral jog 30.5
// so nova.urdf.xacro / LegParams stay valid for v6 parts.
//
// All servo dims STEP-verified (feetech_servo_models STS3215_03a v1.step),
// same source as leg_v5_common.scad / leg_v5_screwlock/sts3215_mount.scad.

$fn = 64;
EPS = 0.05;

// ---- STS3215 (STEP-verified) ----------------------------------------------
SERVO_L   = 45.40;   // body length  (local X; spline end = +X)
SERVO_W   = 24.80;   // body width   (local Y)
SERVO_H   = 34.30;   // body height between horn-disc faces (shaft = local Z)
SPLINE_X  = 12.50;   // spline axis offset from body center along +X

HORN_OD        = 20.0;   // top output horn disc
HORN_THK       = 2.5;
HORN_BCD       = 14.0;   // 4x M2.5 at ±45° from cardinal
BOT_DISC_OD    = 20.0;   // bottom reaction disc (idler bearing surface)
BOT_DISC_THK   = 2.1;

// case mounting square, BOTH shaft-normal faces (STEP-extracted, screwlock doc)
CASE_HOLE_X = [7.55, 17.45];    // cavity-local X
CASE_HOLE_Y = [-4.95, 4.95];    // cavity-local Y

// ---- printed-fit tolerances (PA6-CF) ---------------------------------------
CLR_POCKET   = 0.25;  // servo body drop-in fit per side
CLR_HORN     = 0.15;  // horn disc in coupling recess
CLR_DISC     = 0.15;  // bottom disc in idler recess
M25_CLEAR    = 2.9;   // M2.5 clearance hole
M3_CLEAR     = 3.4;   // M3 clearance (horn center screw)

// ---- structural defaults ----------------------------------------------------
WALL        = 3.2;   // side/end walls
FLOOR       = 3.0;   // pocket floor (M2.5 pass-through into case threads)
ARM_THK     = 4.0;   // yoke arm thickness
IDLER_PAD_H = 2.0;   // raised pivot pad under the floor at the spline axis
IDLER_PAD_D = 10.0;
HEATSET_D   = 4.6;   // M3 x D4.6 heat-set insert
HEATSET_L   = 5.7;
// yoke inner faces, measured from the DRIVEN servo's body mid-plane (z=0):
YOKE_TOP_IN = SERVO_H/2 + 0.3;                        // 17.45 (horn side)
YOKE_BOT_IN = SERVO_H/2 + FLOOR + IDLER_PAD_H + 0.3;  // 22.45 (pad side)

// =============================================================================
// MODULES — all in "servo frame": body center at origin, shaft +Z (horn up),
// spline axis at x = +SPLINE_X. Callers translate/rotate the whole set.
// =============================================================================

// Open-top pocket NEGATIVE: subtract from a solid block. Servo drops in from
// +Z; floor stays below (block must extend >= FLOOR beneath body bottom).
module servo_pocket_neg(extra_top = 30) {
    c = CLR_POCKET;
    union() {
        // body void, opened upward
        translate([0, 0, extra_top/2])
            cube([SERVO_L + 2*c, SERVO_W + 2*c, SERVO_H + 2*c + extra_top],
                 center = true);
        // 4x M2.5 floor holes into case bottom threads
        // (use COUNTERSUNK M2.5 — cap heads would foul the yoke arm plane)
        for (hx = CASE_HOLE_X, hy = CASE_HOLE_Y)
            translate([hx, hy, -(SERVO_H/2 + FLOOR + IDLER_PAD_H + 1)])
                cylinder(d = M25_CLEAR, h = FLOOR + IDLER_PAD_H + 2);
        // back-shaft relief (Ø6 x 1.2 stub on the case bottom)
        translate([SPLINE_X, 0, -(SERVO_H/2 + 1.6)])
            cylinder(d = 6 + 0.5, h = 1.7);
        // TTL wire slot out the -X end wall, at cable-exit height
        translate([-(SERVO_L/2 + WALL/2), 0, -SERVO_H/2 + 6])
            cube([WALL + 4, 14, 8], center = true);
    }
}

// Horn coupling NEGATIVE for a yoke TOP arm (arm spans z = [z0, z0+ARM_THK],
// horn pushes up into it from below): Ø20 recess + 4x M2.5 + center M3.
module horn_couple_neg(z0) {
    translate([0, 0, z0 - EPS]) {
        cylinder(d = HORN_OD + 2*CLR_HORN, h = HORN_THK + 0.3 + EPS); // seat
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                cylinder(d = M25_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = M3_CLEAR, h = ARM_THK + 2*EPS);                  // center
    }
}

// Idler-pad POSITIVE + heat-set NEGATIVE for the pocket floor underside:
// Ø10 x 2 pivot pad at the spline axis; the driven yoke's bottom arm rides
// its face on an M3 shoulder screw into the insert.
// Centered on the JOINT AXIS (z through origin) — caller translates to the
// spline position in its own frame.
module idler_pad_pos(floor_bottom_z) {
    translate([0, 0, floor_bottom_z - IDLER_PAD_H])
        cylinder(d = IDLER_PAD_D, h = IDLER_PAD_H + EPS);
}
module idler_heatset_neg(floor_bottom_z) {
    translate([0, 0, floor_bottom_z - IDLER_PAD_H - EPS])
        cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
}

// Idler NEGATIVE for a yoke BOTTOM arm (arm top face at z0): M3 clearance
// through-hole + head counterbore from below.
module idler_screw_neg(z0) {
    translate([0, 0, z0 - ARM_THK - EPS]) {
        cylinder(d = M3_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = 6.4, h = 1.8);   // M3 cap-head counterbore
    }
}

// STS3215 solid (preview / interference eyeball) — same as leg_v5.
module sts3215_solid() {
    union() {
        cube([SERVO_L, SERVO_W, SERVO_H], center = true);
        translate([SPLINE_X, 0, SERVO_H/2])  cylinder(d = HORN_OD, h = HORN_THK);
        translate([SPLINE_X, 0, -SERVO_H/2 - BOT_DISC_THK])
            cylinder(d = BOT_DISC_OD, h = BOT_DISC_THK);
    }
}

// stadium slab: length l along X (rounded ends, radius = w/2), width w,
// thickness t, z = [0, t], centered in XY.
module slab(l, w, t) {
    hull()
        for (sx = [-1, 1])
            translate([sx*(l/2 - w/2), 0, 0])
                cylinder(r = w/2, h = t);
}
