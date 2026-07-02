// Visual fit check: femur_v6 with its HFE servo ghosted in the pocket and a
// ghost TIBIA servo held by the knee yoke (as the tibia would present it).
include <leg_v6_common.scad>
use <femur.scad>

femur_v6();
// HFE servo in the pocket (spline at origin, body toward knee)
color([0.2,0.4,1,0.5]) rotate([0,0,180]) translate([-SPLINE_X,0,0]) sts3215_solid();
// tibia's KFE servo as the knee yoke sees it (spline at x=FEMUR_LEN)
color([1,0.2,0.2,0.5]) translate([106.9,0,0]) rotate([0,0,180]) translate([-SPLINE_X,0,0]) sts3215_solid();
