// V5 Coax — RIGHT, SCREW-LOCK variant. Copy of leg_v5/coax_R.scad + mount holes.
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightCoax.stl";
CAVITY_CENTER = [-11.6, -8, 28.8];
CAVITY_ROT    = [90, 90, 0];

difference() {
    import(ORIGINAL_STL, convexity = 8);
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
}
