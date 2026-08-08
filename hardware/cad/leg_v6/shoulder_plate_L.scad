// LEFT shoulder horn plate = X-mirror of the right.
//
// HANDEDNESS IS NOMINAL (measured 2026-08-02, full working in
// shoulder_plate.scad's header). The R body is symmetric about its own
// midplane x=39, so the mirror below is a pure TRANSLATION -- this part and
// the R are the SAME SHAPE, and the only difference between the two STLs is
// the 2nd dot added here (volume delta 7.41 mm^3 = one dot).
// PRINT: PA6-CF (as shoulder_plate.scad), back face DOWN — SAME orientation
//   as the R. LA-3's "L variants do not share the R orientation" applies to
//   femur_L/tibia_L (Z-mirrors), NOT to this part: an X-mirror of an
//   X-symmetric body rests on the same face. (Corrected 2026-08-07, #184:
//   this line used to say "PRINT HORN-SEAT-DOWN", a stale copy of
//   shoulder_plate.scad's own pre-correction wording — "back face" is the
//   achievable bed face, see that file's header; horn-seat-down is
//   geometrically impossible, the flange dips below that plane.)
//   -> A plate fitted to the wrong side is mechanically a non-event. The dots
//      are bookkeeping here, unlike femur/tibia/coax where a swap is real.
//   -> A plate fitted to the wrong side is mechanically a non-event. The dots
//      are bookkeeping here, unlike femur/tibia/coax where a swap is real.
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
