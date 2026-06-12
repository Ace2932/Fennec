// =============================================================================
// STS3215 case mounting + horn-coupling screw patterns (add-on to leg_v5)
// =============================================================================
// Adds the screw features the canonical leg_v5 cavity lacks, so the servo can
// be bolted in and locked, not just press-fit into the carved pocket.
//
// HOLE PATTERN — STEP-extracted (not guessed):
//   Source: feetech_servo_models/feetech_sts3215-1.snapshot.6/
//           feetech-sts3215/STS3215_03a v1.step
//   The 18 Ø2.5 (r=1.25) circles in that solid resolve to a 4-hole square on
//   EACH of the two faces normal to the shaft:
//     (x, y) = {7.55, 17.45} x {-4.95, +4.95}  [mm, cavity-local frame]
//   => 9.9 x 9.9 mm square, centered on the spline axis (x = 12.5, y = 0).
//   Frame matches sts3215_cavity(): long axis = X, width = Y, shaft = Z,
//   spline at +X 12.5 — so these holes ride the SAME translate(CAVITY_CENTER)
//   rotate(CAVITY_ROT) as the cavity.
//
// WHICH FACE TO BOLT:
//   Top face (+Z, horn side): the 4 holes sit at R~7 from the spline, INSIDE
//   the Ø20 horn disc / Ø21 horn relief — unusable for body mounting.
//   Bottom face (-Z, back-shaft side): clear of the Ø6 back-shaft relief —
//   THIS is the face to screw through. In coax + femur the back-shaft side
//   faces into solid leg material, so a screw through the leg wall threads into
//   the servo case and clamps the body.
//   The module cuts full-through columns (orientation-robust); the horn-side
//   ends land in the already-void horn relief and do no harm.
//
// VERIFY on a first-article print (per leg_v5/README "first-article every
// shape"): wall thickness at the back face, screw length, and that the columns
// don't foul the femur-mate disc. Tune MOUNT_COL_LEN / MOUNT_SCREW_D below.

include <../leg_v5/leg_v5_common.scad>

MOUNT_X        = [7.55, 17.45];   // STEP-extracted, cavity-local X
MOUNT_Y        = [-4.95, 4.95];   // STEP-extracted, cavity-local Y
MOUNT_SCREW_D  = 2.9;             // M2.5 clearance (matches HORN_SCREW_D)
MOUNT_COL_LEN  = 15;              // column reach past each face (max wall)

// 4x M2.5 clearance columns along the shaft axis at the case-hole square.
// Full-through so whichever face backs solid leg material gets a usable hole.
module sts3215_mount_holes(screw_d = MOUNT_SCREW_D, reach = MOUNT_COL_LEN) {
    h = SERVO_H + 2*reach;
    for (x = MOUNT_X, y = MOUNT_Y)
        translate([x, y, 0])
            cylinder(d = screw_d, h = h, center = true);
}

// Output-horn coupling: 4x M2.5 on the 14 mm BCD at +/-45 deg (HORN_BCD /
// HORN_SCREW_D from leg_v5_common). Use on the DRIVEN link (tibia) to bolt it
// to the knee-servo horn disc. Centered on the horn axis (+Z); caller places
// it at the mate face.
module horn_screw_pattern(screw_d = HORN_SCREW_D, depth = 12) {
    for (a = [45, 135, 225, 315])
        rotate([0, 0, a])
            translate([HORN_BCD/2, 0, 0])
                cylinder(d = screw_d, h = depth, center = true);
}
