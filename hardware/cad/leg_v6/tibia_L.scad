// LEFT tibia = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <tibia.scad>
// LA-2 fix (2026-07-11): moved to the SAME functional face as the base
// dot (pocket-rim top, L-frame z~-14.7 after the Z-mirror), same reasoning
// as femur_L. (37,-10) stays inside the tibia's narrow x35.65..40 flat-top
// strip, spaced from the base dot's mirrored image at (39,10).
difference() {
    mirror([0, 0, 1]) tibia_v6();
    // 2nd side dot: 2 dots = LEFT (same face as the base dot, mirrored)
    translate([37, -10, -14.9]) cylinder(d = 3, h = 1.1);
}
