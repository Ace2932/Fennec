// LEFT coax = X-mirror of the right part (lateral axis = X in coax frame).
$fn = 64;
use <coax.scad>
difference() {
    mirror([1, 0, 0]) coax_v6();
    // 2nd side dot: 2 dots = LEFT
    translate([-12, 16.15, 8]) rotate([-90, 0, 0]) cylinder(d = 3, h = 1.1);
}
