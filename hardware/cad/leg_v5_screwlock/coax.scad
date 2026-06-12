// =============================================================================
// V5 Coax — LEFT, SCREW-LOCK variant
// Copy of leg_v5/coax.scad + STS3215 case mount-screw holes.
// Source shape + cavity placement unchanged; adds sts3215_mount_holes().
// =============================================================================
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftCoax.stl";
OVERLAY = false;

CAVITY_CENTER = [-11.6, 8, 28.8];   // Y-flipped from Right variant
CAVITY_ROT    = [90, 90, 0];

if (OVERLAY) {
    color("yellow", 0.7) import(ORIGINAL_STL, convexity = 8);
    color([1, 0, 0, 0.4]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    color([0, 0, 1, 0.6]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
} else {
    difference() {
        import(ORIGINAL_STL, convexity = 8);
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
    }
}
