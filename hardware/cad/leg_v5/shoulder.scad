// V5 Shoulder Middle — holds hip-roll STS3215.
// Frame is open in the middle; servo slides in. No body cavity needed.
// Possible mods (uncomment + tune if needed after test print):
//   - Enlarge horn cutout if original is sized for hobby horn (Ø ~14)
//     STS3215 horn disc Ø 20 mm.
include <leg_v5_common.scad>

SHELL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_FrontShoulderMiddle.stl";

import(SHELL_STL, convexity = 8);

// Example horn-cutout enlargement (commented; tune position/rot if used):
// difference() {
//     import(SHELL_STL, convexity = 8);
//     // +X face horn cutout
//     translate([35, 0, 35]) rotate([0, 90, 0])
//         cylinder(d = HORN_DISC_OD + 2, h = 10, center = true);
//     // -X face horn cutout
//     translate([-35, 0, 35]) rotate([0, 90, 0])
//         cylinder(d = HORN_DISC_OD + 2, h = 10, center = true);
// }
