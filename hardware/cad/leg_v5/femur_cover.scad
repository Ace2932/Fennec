// V5 Femur COVER — LEFT. Original cover STL + SAME STS3215 cavity as shell.
include <leg_v5_common.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_COVER_L, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_L) rotate(FEMUR_CAVITY_ROT_L) sts3215_cavity();
}
