// LEFT coax HFE plate = X-mirror of the right (same convention as
// coax_L.scad / shoulder_plate_L.scad).
$fn = 64;
use <coax_hfe_plate.scad>
// side marker: 2 dots = LEFT. Base (RIGHT) dot sits at world x=+12.95 (the
// disc's back face, PLATE_X0+EPS); mirror([1,0,0]) flips its sign, so on
// this LEFT part that same face lands at world x=-12.95 (coax_L.scad's own
// convention -- see its header comment for the same base-dot-mirrors
// pattern). 2nd dot at the SAME mirrored face (x=-12.95), offset in y
// (y=+6 instead of the base dot's -2) so 1-vs-2 dots reads unambiguously;
// rotate sign flipped to still cut INWARD (+x) from this now-negative-x
// outward face.
difference() {
    mirror([1, 0, 0]) coax_hfe_plate_R();
    translate([-12.95, 6, -9.5]) rotate([0, 90, 0]) cylinder(d = 3, h = 1.1);
}
