// LEFT tibia = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <tibia.scad>
difference() {
    mirror([0, 0, 1]) tibia_v6();
    // 2nd side dot: 2 dots = LEFT
    translate([28, -10, 21.4]) cylinder(d = 3, h = 1.1);
}
