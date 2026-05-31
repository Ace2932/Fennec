// V5 Femur SHELL — LEFT. Original shell STL + STS3215 cavity.
include <leg_v5_common.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_SHELL_L, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_L) rotate(FEMUR_CAVITY_ROT_L) sts3215_cavity();
}
