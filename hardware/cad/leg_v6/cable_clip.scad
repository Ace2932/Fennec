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
// Install (5 per leg, both ends of each service loop):
//   coax tunnel-exit pair + femur x44 pair   = the HIP loop (haa+hfe)
//   femur x84 (yoke plate) + tibia x58 pair  = the KNEE loop (kfe)
//   coax +Y connector-bay pair + shoulder's Ø12 flange grommet = the HAA
//     loop (haa roll -- LA-29, cable-management review 2026-07-16; the
//     shoulder-side end is the grommet itself, no clip needed there)
// tibia's original x44 pair stays in place as the tunnel-exit strain
// relief (LA-4/#31) -- it is NOT part of the KNEE loop's span calc any
// more (LA-30, same review: the KNEE loop now anchors at tibia x58,
// farther from the kfe axis, to close some of the 39.2mm-at-full-fold
// gap below). Spiral wrap (O6, BOM) covers the free loop BETWEEN clips;
// loop radius >= 40 (8x bundle O5). Assembly checklist: leg_v6 README
// "cable dressing" + tug-test every anchor.
//
// ASSEMBLY RULE (backlog #18 / LA-14, --cable WARN gate LA-20/LA-29/
// LA-30): anchor separation shrinks below the >=40 spec across ROM (KNEE
// ~39.2mm -> ~51.6mm at kfe full fold after the LA-30 x58 anchor move,
// still short of spec; HIP ~60-81mm across hfe; HAA ~57-63mm across haa,
// LA-29) -- mitigated by geometry where practical (LA-30) and by
// discipline for the remainder. Fold the joint to its mechanical limit
// FIRST, THEN zip the loop to this clip, so the loop is slack (not taut)
// at full fold. See leg_v6 README "Free-loop length" note.
//
// Print: TPU 95A, flat (base down), 100% infill, ~1 g each (LA-28,
// 2026-07-11: was "~2 g" -- measured mesh volume 850.7mm^3 (post LA-24
// wall fix) x TPU 95A density ~1.2 g/cm^3 = ~1.0 g).

$fn = 48;
EPS = 0.05;

L = 18;            // along the cable
W = 16;            // across (holes at +/-5 = the anchor pair spacing 10)
BASE_T = 2.4;
WALL_Z1 = 6.4;
CH_D = 6.0;        // bundle channel (daisy link + VCC spur, ~O5)
CH_Z = 4.0;        // channel axis height -> floor z1, crest z7 (proud of
                   // the walls: the tie wraps the bundle directly)
// LA-24 fix (2026-07-11): the bell-mouth cutters (d2=13 cone, below) reach
// radius 6.125 by the true mouth face (x=0 / x=L) -- against the old
// WALL_Y_OUT=7.2 outer wall edge that left only 1.075mm of wall at the
// flex-critical mouth (< 1.2mm guideline, ray-cast confirmed). Grew the
// OUTER wall profile (not the bore) to 7.5 -> 1.375mm remaining wall at
// both mouths. Still 0.5mm inside the W=16 base half-width (8), so the
// base's own outer lip just shrinks from 0.8 to 0.5mm (non-structural).
WALL_Y_IN  = 3.2;
WALL_Y_OUT = 7.5;
WALL_W = WALL_Y_OUT - WALL_Y_IN;

module cable_clip() {
    difference() {
        union() {
            translate([0, -W/2, 0]) cube([L, W, BASE_T]);
            for (sy = [-1, 1])
                translate([0, min(sy*WALL_Y_IN, sy*WALL_Y_OUT), 0])
                    cube([L, WALL_W, WALL_Z1]);
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
