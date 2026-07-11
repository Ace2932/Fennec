// LEFT shoulder horn plate = X-mirror of the right.
$fn = 64;
use <shoulder_plate.scad>
// LA-2 fix (2026-07-11): shoulder_plate_L carried no marker at all (just
// a bare mirror). mirror([1,0,0]) only flips X, so the base (RIGHT) dot's
// face (y=FACE_Y1=21.75, hardcoded here -- `use` doesn't import
// shoulder_plate.scad's variables) is unchanged; its mirrored image lands
// at (x=-45,z=10). 2nd dot at (x=-45,z=-10): same front face, spaced 20mm
// in z so 1-vs-2 dots reads unambiguously on one face. Ray-cast confirmed
// solid.
difference() {
    mirror([1, 0, 0]) shoulder_plate_R();
    // 2nd side dot: 2 dots = LEFT (same face as the base dot, mirrored)
    translate([-45, 21.80, -10]) rotate([90, 0, 0]) cylinder(d = 3, h = 1.1);
}
