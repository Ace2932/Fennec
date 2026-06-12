// V5 Femur COVER — LEFT, SCREW-LOCK variant. SAME cavity + mount holes as shell.
include <../leg_v5/leg_v5_common.scad>
include <sts3215_mount.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_COVER_L, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_L) rotate(FEMUR_CAVITY_ROT_L) sts3215_cavity();
    translate(FEMUR_CAVITY_CENTER_L) rotate(FEMUR_CAVITY_ROT_L) sts3215_mount_holes();
}
