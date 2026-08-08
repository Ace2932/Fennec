// LEFT coax = X-mirror of the right part (lateral axis = X in coax frame).
// PRINT: PA6-CF (as coax.scad — INFERRED, NOT SOURCED, see that file's #184
//   note), rear face (+Y) DOWN — SAME as coax_R. An X-mirror does not flip
//   this face (unlike coax_hfe_block_L, whose directive is expressed on the
//   X axis and DOES flip); the y-normal is unaffected by mirror([1,0,0]).
//   supports=normal under the yoke bridge span, brim — as coax_R.
$fn = 64;
use <coax.scad>
// LA-2 fix (2026-07-11): the old 2nd dot (-12,-17.25,8) targeted the same
// open horn-face plane as the old (buggy) base dot -- cut air (ray-cast: 0
// solid hits), so LEFT coax also printed with 0 dots. mirror([1,0,0]) only
// flips X, so the base dot's real face (y=BLK_YF=+22.2 rear/floor plane,
// BLK_YF hardcoded here -- `use` doesn't import coax.scad's variables) is
// UNCHANGED after mirroring; its mirrored image lands at (x=+12, z=8).
// New 2nd dot at (x=+12, z=-8): same rear face, spaced 16mm in z from the
// base dot's image so 1-vs-2 dots is unambiguous on one face. Ray-cast
// confirmed solid.
difference() {
    mirror([1, 0, 0]) coax_v6();
    // 2nd side dot: 2 dots = LEFT (same face as the base dot, mirrored)
    translate([12, 22.25, -8]) rotate([90, 0, 0]) cylinder(d = 3, h = 1.1);
}
