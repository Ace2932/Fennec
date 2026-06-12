// V5 Tibia — RIGHT, SCREW-LOCK variant. Houses the KNEE STS3215.
// Cavity + 4x M2.5 case mount holes (placement from leg_v5/tibia_R.scad).
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightTibia.stl";

CAVITY_CENTER = [50, 0, 19];
CAVITY_ROT    = [0, 0, 0];

difference() {
    import(ORIGINAL_STL, convexity = 8);
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
}
