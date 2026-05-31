// V5 Femur COVER — RIGHT. Original cover STL + SAME STS3215 cavity as shell.
include <leg_v5_common.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_COVER_R, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_R) rotate(FEMUR_CAVITY_ROT_R) sts3215_cavity();
}
