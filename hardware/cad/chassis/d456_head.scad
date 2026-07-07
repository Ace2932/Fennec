// =============================================================================
// NOVA chassis — D456 HEAD BRACKET v3: PERISCOPE (screw-in, user call)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (+x FRONT).
// D456 123.8 x 26 x 29. Mount = the REAR-FACE 2x M3 CENTERLINE pattern
// (CALIPER 2026-07-07): two holes 94.4 apart on the back-face centerline
// (y +/-47.2, centered on the 26 width -> plate z-center 95). This SUPERSEDES
// the old (wrong) 4x corner +-54 slot pattern. A +-3 vertical slot absorbs
// residual z tolerance; still CALIPER-verify on the real camera before print.
//
// Gate history (why the camera lives up here):
//   v1 riser-wall z 34..63  -> shoulder shear webs own y +/-51..55 there.
//   v2 under-chin z -16..12 -> the folded FRONT FEMUR is a diagonal bar
//     through that volume from hfe ~+35 (crouch needs +40), tibia crosses
//     the full camera width. No front-fold ROM cap could be tolerated.
//   v3 periscope z 80.5..109.5: above the shoulder deck extension (79.55),
//     below the L2 (114.4). Legs never reach z >= 80 at x < 100.
// KNOWN COST: the camera's top-front corner clips the L2's -45 deg bottom
// cone by ~3.5 deg in the forward sector — rays that would hit ground
// ~150-165mm ahead, i.e. exactly the D456's own prime zone. Accepted
// (same class as the Jetson hood clipping the rear-down cone).
//
// Structure: stem (x 63.45..69.5, y +/-25.5, z 58..80) rises through the
// shoulder-flange center notch against the riser front wall; cross-plate
// (x 65.5..69.5, y +/-58, z 80..101) carries the camera on its front
// face. Plate top 101 clears the mast flare (x < 63.8 below z 101).
// Cable: RIGHT-ANGLE USB-C (BOM) through the plate window (y 2..19,
// z 86..99), down the STEM CHANNEL (y 11..17.5 — the solid stem blocked
// a center path entirely; review catch), into the riser wall's 10x6
// grommet slot at (14, 61.5). Channel clears both row bores by 1.8.
// Mount: 4x M3x10 into the riser row (y -21/-7/+7/+21, z 67.4) — heads
// proud on the stem face, driver passes UNDER the camera (bottom 80.5).
// Camera bolts to the bracket ON THE BENCH first (rear screws are
// unreachable installed); service = the 4 row screws, camera rides along.
// Print: back-face down, zero supports.
// Fit gate: check_fit.py case 8 + crouch sweep (head + camera targets).

$fn = 64;
EPS = 0.05;

STEM_X0 = 63.45;  STEM_X1 = 69.5;    // 0.1 off the riser wall (63.35)
ROW_Y = [-21, -7, 7, 21];  ROW_Z = 67.4;
PLT_X0 = 65.5;  PLT_X1 = 69.5;
PLT_Z0 = 80;  PLT_Z1 = 101;
HALF_W = 58;
MOUNT_Y = 47.2;                       // 2 centerline holes, 94.4 apart (CALIPER
                                      // 2026-07-07; was 4x corner +-54)
MOUNT_Z = 95;                         // camera vertical ctr (env 80.5..109.5)
MOUNT_SLOT = 3;                       // +-3 vertical tolerance (z unverified)
M3_CLEAR = 3.4;

module d456_head() {
    difference() {
        union() {
            // stem through the flange notch, against the riser wall
            translate([STEM_X0, -25.5, 58])
                cube([STEM_X1 - STEM_X0, 51, PLT_Z0 - 58 + EPS]);
            // cross-plate (camera rear face seats on x 69.5)
            translate([PLT_X0, -HALF_W, PLT_Z0])
                cube([PLT_X1 - PLT_X0, 2 * HALF_W, PLT_Z1 - PLT_Z0]);
        }
        // riser-row screw channels
        for (ry = ROW_Y)
            translate([STEM_X0 - EPS, ry, ROW_Z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = STEM_X1 - STEM_X0 + 2 * EPS);
        // camera 2x CENTERLINE M3 (vertical slot absorbs the z tolerance)
        for (sy = [-1, 1]) hull() for (dz = [-MOUNT_SLOT, MOUNT_SLOT])
            translate([PLT_X0 - EPS, sy * MOUNT_Y, MOUNT_Z + dz]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = PLT_X1 - PLT_X0 + 2 * EPS);
        // cable window (aligned over the stem channel)
        translate([PLT_X0 - EPS, 2, 86])
            cube([PLT_X1 - PLT_X0 + 2 * EPS, 17, 13]);
        // stem cable channel down to the riser grommet at (14, 61.5)
        translate([STEM_X0 - EPS, 11, 58 - EPS])
            cube([STEM_X1 - STEM_X0 + 2 * EPS, 6.5, 80 - 58 + 2 * EPS]);
    }
}

d456_head();
