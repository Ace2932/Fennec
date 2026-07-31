// Full RIGHT-leg v6 assembly preview: coax + femur + tibia + ghost servos.
// Coax frame: haa = Y axis, +X outboard, leg hangs -Z.
include <leg_v6_common.scad>
// REAL servo mesh (spline moved to origin) — same geometry the fit gate uses,
// from the vendored copy in proj/ rather than the ROOT repo (#166). Relative
// to THIS file, so it renders on any checkout.
module sts3215_real() {
    translate([-12.5, 0, 0])
        import("../assets/servo.stl", convexity = 6);
}
use <femur.scad>
use <knee_arm.scad>
use <tibia.scad>
use <coax.scad>

HFE_Y = 11.6; HFE_Z = -9.5; FEMUR_MID = 33.8; FEMUR_LEN = 106.9;

coax_v6();
color([0.9,0.8,0.3]) import("coax_hfe_block.stl");  // #226 option C: bolt-on OUTBOARD HFE arm
color([0.2,0.4,1,0.45])  // haa servo ghost
  rotate([0,-90,0]) rotate([90,0,0]) sts3215_real();

// femur hangs straight down from the hfe axis
translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0,0,180]) rotate([0,90,0]) {
  femur_v6();
  // bolt-on knee arm (knee_arm.scad prints separately; placed here)
  color([0.9,0.8,0.3]) translate([59, 0, 17.75]) import("knee_arm.stl");
  color([1,0.2,0.2,0.45]) rotate([0,0,180]) sts3215_real();
  // tibia at the knee
  translate([FEMUR_LEN,0,0]) {
    tibia_v6();
    color([0.1,0.7,0.2,0.45]) rotate([0,0,180]) sts3215_real();
  }
}
