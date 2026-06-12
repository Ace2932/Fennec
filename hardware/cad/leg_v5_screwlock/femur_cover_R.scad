// V5 Femur COVER — RIGHT, SCREW-LOCK variant. SAME cavity + mount holes as shell.
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_COVER_R, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_R) rotate(FEMUR_CAVITY_ROT_R) sts3215_cavity();
    translate(FEMUR_CAVITY_CENTER_R) rotate(FEMUR_CAVITY_ROT_R) sts3215_mount_holes();
}
