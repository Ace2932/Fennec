// V5 Tibia — LEFT, SCREW-LOCK variant. Houses the KNEE STS3215.
// Cavity + 4x M2.5 case mount holes (placement from leg_v5/tibia.scad).
// L is Y-curved — VERIFY CAVITY_CENTER/ROT in OVERLAY before printing.
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftTibia.stl";
OVERLAY = false;

CAVITY_CENTER = [-45, 0, 20];   // SEED — VERIFY in OVERLAY (L is Y-curved)
CAVITY_ROT    = [0, 0, 0];

if (OVERLAY) {
    color("yellow", 0.7) import(ORIGINAL_STL, convexity = 8);
    color([0.2, 0.4, 1, 0.5]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_solid();
    color([1, 0, 0, 0.3]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    color([0, 0, 1, 0.6]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
} else {
    difference() {
        import(ORIGINAL_STL, convexity = 8);
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_mount_holes();
    }
}
