// V5 Tibia — LEFT. PASSIVE shank (no servo inside).
// Driven by knee servo (which lives in femur) via proximal horn-cap mount.
// Kept original geometry. Horn-cap interface mods (if needed) go below.
include <leg_v5_common.scad>

SHELL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftTibia.stl";

import(SHELL_STL, convexity = 8);

// To adapt the proximal horn-cap mount to STS3215 (4x M2.5 on 14mm BCD),
// add cuts here once the mate-face location is known. e.g.:
// translate([HORN_X, HORN_Y, HORN_Z]) rotate([...]) horn_screw_pattern();
