// LEFT femur = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <femur.scad>
// LA-2 fix (2026-07-11): the old 2nd dot at (28,-10,21.4) landed on the
// mirrored UNDERSIDE (R-frame z~-21.4..-22.5, the floor) while the base
// (RIGHT) dot lives on the pocket-rim TOP face -- opposite faces, so a
// glance at either face alone could never distinguish 1-dot vs 2-dot.
// Relocated to the SAME functional face as the (now-fixed) base dot: the
// pocket-rim top, which after the Z-mirror sits at L-frame z ~ -14.7 (not
// +22.2). (50,-10) is on that face, x50 stays clear of the fork hull's
// rounded-cap taller-top zone (starts ~x55.95, same reasoning as the base
// dot), spaced 5mm/20mm from the base dot's mirrored image at (45,10) so
// "1 vs 2 dots" reads unambiguously on one face.
difference() {
    mirror([0, 0, 1]) femur_v6();
    // 2nd side dot: 2 dots = LEFT (same face as the base dot, mirrored)
    translate([50, -10, -14.9]) cylinder(d = 3, h = 1.1);
}
