// V5 Femur SHELL — RIGHT. Original shell STL + STS3215 cavity.
include <leg_v5_common.scad>
include <femur_params.scad>

difference() {
    import(FEMUR_SHELL_R, convexity = 8);
    translate(FEMUR_CAVITY_CENTER_R) rotate(FEMUR_CAVITY_ROT_R) sts3215_cavity();
}
