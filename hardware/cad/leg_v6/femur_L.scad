// LEFT femur = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <femur.scad>
difference() {
    mirror([0, 0, 1]) femur_v6();
    // 2nd side dot: 2 dots = LEFT
    translate([28, -10, 13.9]) cylinder(d = 3, h = 1.1);
}
