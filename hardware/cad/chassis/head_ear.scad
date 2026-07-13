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
//   INBOARD (y10) of the panel base so a driver drops straight onto them clear
//   of the panel (access audit 2026-07-08). Antenna BOSS at the tip: SMA
//   bulkhead, whip points UP (vertical -> omni RF).
//
// EDGE-ON YAW (2026-07-13, occlusion_ear.py): the L2 does 360deg horizontal
//   mapping; the ears sit in its REAR sector and used to face the L2 broad-side
//   (flat panel normal ~+x, straight at the L2) -> blocked ~27.7deg of arc EACH.
//   The blade is now YAWED EAR_YAW about the vertical mount axis so its thin
//   EDGE faces the L2 instead of the flat face: at +45deg the blocked arc drops
//   to ~13.6deg/ear (~28deg total FoV recovered across the pair), and the tip
//   moves FURTHER from the L2 body (24.5mm clearance, was 18.8). The blade leans
//   back over the neck as a result. The foot + bolt holes stay axis-aligned on
//   their fixed pad heat-sets (head.scad L281) — only the blade+boss+whip yaw.
//   The whip stays VERTICAL (yaw is about z), so the omni RF pattern is
//   unchanged. Tune EAR_YAW freely; head.scad + the check_fit ear-pad gate are
//   unaffected (the pad heat-sets don't move).
//
// PRINT + MATERIAL: **plain PETG or ASA — NOT a CF filament.** The ear is an
//   antenna mast; carbon fiber is CONDUCTIVE at 2.4/5 GHz and detunes/absorbs
//   the whip (several dB loss). A rigid low-loss dielectric (plain PETG/ASA/
//   nylon) holds the mast stiff without the RF penalty. If the ears are pure
//   styling (no antenna), any filament is fine. Panel FLAT on the bed, minimal
//   supports, ~5 g. print 2 (R here + L mirror). First-article: the +45deg
//   lean-back is a longer cantilever on the ~10mm base — check base stiffness
//   / add a fillet if it wobbles.

$fn = 32; EPS = 0.05; M3_CLEAR = 3.4;
PAD_Z = 131;            // head ear-pad top = the bolt face
EAR_YAW = 45;           // deg, blade yaw about the mount axis (edge-on to L2)
PIVOT = [80, 10];       // yaw axis (x,y) = bolt-pattern center; foot stays here

module head_ear() {
    difference() {
        union() {
            // foot flange on the pad (x74..87, y4..21) — bolts down into the pad.
            // AXIS-ALIGNED + fixed (mates the pad's fixed heat-sets); the blade
            // yaws relative to it.
            translate([74, 4, PAD_Z]) cube([13, 17, 4]);

            // blade + antenna boss, yawed EAR_YAW about the vertical mount axis
            // so the thin edge faces the L2. The base fan is rooted over the
            // pivot so it stays ON the foot at any yaw.
            translate([PIVOT[0], PIVOT[1], 0])
                rotate([0, 0, EAR_YAW])
                    translate([-PIVOT[0], -PIVOT[1], 0]) {
                // broad triangular panel: 10mm base fan on the foot -> splays up
                // + out to the leaning-back tip
                hull() {
                    translate([80,  7, PAD_Z + 3]) cube([6, 5, 4], center = true);
                    translate([80, 17, PAD_Z + 3]) cube([6, 5, 4], center = true);
                    translate([71, 50, 205])       cube([6, 5, 4], center = true);
                }
                // antenna boss at the tip (holds the SMA bulkhead)
                translate([71, 50, 198]) cylinder(d = 10, h = 15);
            }
        }
        // 2x M3 foot bolts (clearance, from the foot top down into the pad) —
        // FIXED at (77,10),(83,10), matching head.scad's ear-pad heat-sets.
        for (ex = [77, 83])
            translate([ex, 10, PAD_Z - EPS]) cylinder(d = M3_CLEAR, h = 4 + 2 * EPS);
        // SMA bulkhead bore up the tip (whip UP) — yawed with the blade.
        translate([PIVOT[0], PIVOT[1], 0])
            rotate([0, 0, EAR_YAW])
                translate([-PIVOT[0], -PIVOT[1], 0])
                    translate([71, 50, 191]) cylinder(d = 6.5, h = 30);
    }
}

head_ear();
