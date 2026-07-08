// =============================================================================
// NOVA HEAD EAR — one fennec ear / WiFi antenna mast, bolts to the head pad
// =============================================================================
// SPLIT OFF the head (2026-07-07 review): the tall leaning ears made the head a
// warpy, support-heavy multi-branch print. As a separate part the head body
// prints compact + the ears print flat. Also modular: the ears are OPTIONAL
// (WiFi-antenna decision, backlog #32) — no antennas -> don't print/attach them.
//
// This file = the +Y (RIGHT) ear. Build the LEFT with head_ear_L.scad (mirror).
// MOUNT: the foot flange sits on the head ear-pad (top z131, x74..87) and bolts
//   DOWN with 2x M3 into the pad's heat-sets at (77,±10),(83,±10). The bolts sit
//   INBOARD (y10) of the panel base (y15.5+) so a driver drops straight onto
//   them clear of the panel (access audit 2026-07-08). The broad triangular
//   panel rises + splays out (behind the L2, x<89 -> rear LiDAR sector only). Antenna BOSS at the tip: SMA bulkhead, whip points UP (omni
//   RF). Cable: U.FL->SMA pigtail up the neck -> the bulkhead (route TBD once
//   antennas are decided).
// PRINT: PETG-CF (low warp) or PA6-CF, panel FLAT on the bed, minimal supports,
//   ~5 g. print 2 (R here + L mirror).

$fn = 32; EPS = 0.05; M3_CLEAR = 3.4;
PAD_Z = 131;        // head ear-pad top = the bolt face

module head_ear() {
    difference() {
        union() {
            // foot flange on the pad (x74..87, y4..21) — bolts down into the pad
            // (extends to y4 so the y10 bolts clear the panel base above them)
            translate([74, 4, PAD_Z]) cube([13, 17, 4]);
            // broad triangular panel, rising + splaying out, leaning back
            hull() {
                translate([82, 18, PAD_Z + 3]) cube([6, 5, 4], center = true);
                translate([82, 36, PAD_Z + 3]) cube([6, 5, 4], center = true);
                translate([71, 50, 205])       cube([6, 5, 4], center = true);
            }
            // antenna boss at the tip (holds the SMA bulkhead)
            translate([71, 50, 198]) cylinder(d = 10, h = 15);
        }
        // 2x M3 foot bolts (clearance, from the foot top down into the pad)
        for (ex = [77, 83])
            translate([ex, 10, PAD_Z - EPS]) cylinder(d = M3_CLEAR, h = 4 + 2 * EPS);
        // SMA bulkhead bore up the tip (whip UP)
        translate([71, 50, 191]) cylinder(d = 6.5, h = 30);
    }
}

head_ear();
