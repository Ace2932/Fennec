// =============================================================================
// V6 CABLE CLIP (TPU 95A — print 20: 16 install + spares)
// =============================================================================
// Backlog #18 (2026-07-06): haa +/-40 / kfe +/-109 at trot = ~1e5 flex
// cycles/hour and quadruped harnesses classically die at the hip — the
// zip anchors take cable TENSION but nothing defined the BEND at the
// anchor exits, so the service loop kinks and fatigues at one spot.
//
// This clip is a saddle + BELL-MOUTH horns that sit under the bundle at
// each flex-zone anchor. The existing zip tie does double duty: it
// threads the leg part's zip-pair holes AND this clip's matching holes,
// clamping bundle to clip to leg — no leg reprints, clip retrofits any
// O3.2-pair anchor (10 mm spacing).
//
// Install (4 per leg, both ends of each service loop):
//   coax tunnel-exit pair + femur x44 pair   = the HIP loop (haa+hfe)
//   femur x84 (yoke plate) + tibia x44 pair  = the KNEE loop (kfe)
// Spiral wrap (O6, BOM) covers the free loop BETWEEN clips; loop radius
// >= 40 (8x bundle O5). Assembly checklist: leg_v6 README "cable
// dressing" + tug-test every anchor.
//
// Print: TPU 95A, flat (base down), 100% infill, ~2 g each.

$fn = 48;
EPS = 0.05;

L = 18;            // along the cable
W = 16;            // across (holes at +/-5 = the anchor pair spacing 10)
BASE_T = 2.4;
WALL_Z1 = 6.4;
CH_D = 6.0;        // bundle channel (daisy link + VCC spur, ~O5)
CH_Z = 4.0;        // channel axis height -> floor z1, crest z7 (proud of
                   // the walls: the tie wraps the bundle directly)

module cable_clip() {
    difference() {
        union() {
            translate([0, -W/2, 0]) cube([L, W, BASE_T]);
            for (sy = [-1, 1])
                translate([0, min(sy*3.2, sy*7.2), 0])
                    cube([L, 4, WALL_Z1]);
        }
        // bundle channel
        translate([-1, 0, CH_Z]) rotate([0, 90, 0])
            cylinder(d = CH_D, h = L + 2);
        // bell-mouth horns (the actual bend-radius control): flare to
        // ~2x bundle at both exits so the loop leaves on an arc, never
        // a corner
        translate([L - 5, 0, CH_Z]) rotate([0, 90, 0])
            cylinder(d1 = CH_D, d2 = 13, h = 5.6);
        translate([5, 0, CH_Z]) rotate([0, -90, 0])
            cylinder(d1 = CH_D, d2 = 13, h = 5.6);
        // zip-tie holes — match the leg part's O3.2 pair (tie threads
        // leg + clip together)
        for (sy = [-1, 1])
            translate([L/2, sy*5, -EPS])
                cylinder(d = 3.4, h = WALL_Z1 + 2*EPS);
        // tie groove across the wall tops (tie seats down onto the
        // bundle instead of riding the wall crests)
        translate([L/2 - 2, -W/2 - EPS, 3.6])
            cube([4, W + 2*EPS, WALL_Z1]);
    }
}

cable_clip();
