// =============================================================================
// V6 Shoulder — one crossmember per trunk end (SAME part both ends; print 2).
// =============================================================================
// Frame: X = lateral from robot centerline, Y = fore-aft with 0 at the hip
// stations (+Y = horn/forward side), Z = 0 at the haa axes.
// Hips at x = ±39.05; trunk end face at y = -77.7 (both ends, measured).
//
// STRUCTURE DICTATED BY THE COAX SWEPT WEDGE (haa ±40°+): the coax bottom
// corner sweeps r41.5, reaching ~x2.8 of centerline; top corners r20.8.
// Between the wheel plane (-17.7) and horn plane (+17.2) nothing may exist
// below z +23.5 → C-box over the legs:
//   REAR WALL (-26.6..-22.6) with the Ø19 WHEEL BOSSES (0.4 behind the
//     rotating coax floor, same pattern as the leg yokes)
//   TOP DECK (z 35..41.5, y -32.1..17.0) — the only fore-aft span; carries
//     4x heat-set bores per side for the HORN PLATES (shoulder_plate.scad):
//     LEG DETACHES FROM THE TOP: 4x M3 on the deck + one unplug.
//   CHEEKS |x| 55.4..59.4 (coax outer face 54.9)
//   FLANGE at the trunk end: 4x M3 from inside the trunk into heat-sets at
//     (±51.75, z -33.05/-14.05) = the stock shell's own holes (measured);
//     webs x ±51..55 tie flange to wall; 2x Ø12 cable grommets at (±32,-26).
// Print: rear face down; tree supports under the flange span.

include <leg_v6_common.scad>

HIP_X     = 39.05;
HORN_Y    = 17.2;              // horn face plane (haa spline-z -> shoulder y)
WHEEL_FACE_Y = -17.7;          // wheel face plane
REAR_W0   = -32.1;  REAR_W1 = -28.1;  // face 0.5 behind the coax YOKE-ARM
                                       // extreme (-27.6 — the yoke reaches
                                       // 5.4 PAST the coax floor; sweep-gate
                                       // find 2026-07-06). Boss Ø19 x 10.4.
DECK_Z0   = 35;     DECK_Z1 = 41.5;   // 6.5 thick. RAISED from 23.5 (sweep-gate:
                                       // the coax BRIDGE, r24-38 about the haa
                                       // axis, rolls up to z~34 inside the deck
                                       // span at 40deg — 1.0 clearance now)
DECK_Y1   = 17.0;                     // stops 0.2 short of the plate face
CHEEK_X0  = 55.4;   CHEEK_X1 = 59.4;
FLANGE_Y0 = -77.7;  FLANGE_Y1 = -73.7;
TRUNK_HOLE_X = 51.75;
TRUNK_HOLE_Z = [-33.05, -14.05];
WALL_Z0   = -25;
// plate flange bore grid (shared with shoulder_plate.scad)
PLATE_BX  = [27, 51];
PLATE_BY  = [6.2, 15.2];

module shoulder_v6() {
    difference() {
        union() {
            // rear wall
            translate([-CHEEK_X1, REAR_W0, WALL_Z0])
                cube([2*CHEEK_X1, REAR_W1 - REAR_W0, DECK_Z1 - WALL_Z0]);
            // wheel bosses: extend forward from the wall to the wheel face
            for (sx = [-1, 1])
                translate([sx*HIP_X, REAR_W1 - EPS, 0]) rotate([-90, 0, 0])
                    cylinder(d = WHEEL_BOSS_D,
                             h = (WHEEL_FACE_Y - REAR_W1) + EPS);
            // top deck
            translate([-CHEEK_X1, REAR_W0, DECK_Z0])
                cube([2*CHEEK_X1, DECK_Y1 - REAR_W0, DECK_Z1 - DECK_Z0]);
            // NO outboard cheeks: the coax's femur yoke + bridge extend to
            // part-x 60.25 -> shoulder x ~99 and sweep the whole outboard
            // volume (gate find). The deck alone is provably safe (any
            // point entering its band within |x|<=59.4 needs r<=36; the
            // yoke's r>36 points can't get there inside +/-40 deg).
            // trunk flange
            translate([-55, FLANGE_Y0, -38])
                cube([110, FLANGE_Y1 - FLANGE_Y0, DECK_Z1 + 38]);
            // deck extension rearward to the flange
            translate([-CHEEK_X1, FLANGE_Y0, DECK_Z0])
                cube([2*CHEEK_X1, REAR_W0 - FLANGE_Y0 + EPS,
                      DECK_Z1 - DECK_Z0]);
            // shear webs
            for (sx = [-1, 1])
                translate([min(sx*51, sx*55), FLANGE_Y0, WALL_Z0])
                    cube([4, REAR_W0 - FLANGE_Y0 + EPS, DECK_Z1 - WALL_Z0]);
        }

        // ---- wheel couplings, drilled straight along Y ----
        for (sx = [-1, 1]) {
            for (a = [45 : 90 : 315]) {
                translate([sx*HIP_X + HORN_BCD/2*cos(a), REAR_W0 - 1,
                           HORN_BCD/2*sin(a)])
                    rotate([-90, 0, 0])
                        cylinder(d = M25_CLEAR,
                                 h = (WHEEL_FACE_Y - REAR_W0) + 2);
                translate([sx*HIP_X + HORN_BCD/2*cos(a), REAR_W0 - EPS,
                           HORN_BCD/2*sin(a)])
                    rotate([-90, 0, 0]) cylinder(d = 5.2, h = 1.8);
            }
            translate([sx*HIP_X, REAR_W0 - 1, 0]) rotate([-90, 0, 0])
                cylinder(d = M25_CLEAR, h = (WHEEL_FACE_Y - REAR_W0) + 2);
            translate([sx*HIP_X, REAR_W0 - EPS, 0]) rotate([-90, 0, 0])
                cylinder(d = 5.2, h = 1.8);
        }

        // plate heat-set bores, down into the deck (4 per side)
        for (sx = [-1, 1], bx = PLATE_BX, by = PLATE_BY)
            translate([sx*bx, by, DECK_Z1 - HEATSET_L])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

        // trunk-flange heat-sets (screws from inside the trunk, rearward face)
        for (sx = [-1, 1], hz = TRUNK_HOLE_Z)
            translate([sx*TRUNK_HOLE_X, FLANGE_Y0 - EPS, hz])
                rotate([-90, 0, 0]) cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

        // cable grommets
        for (sx = [-1, 1])
            translate([sx*32, FLANGE_Y0 - 1, -26]) rotate([-90, 0, 0])
                cylinder(d = 12, h = FLANGE_Y1 - FLANGE_Y0 + 2);

        // deck lightening/vent window between the hips
        translate([-16, -14, DECK_Z0 - 1])
            cube([32, 26, DECK_Z1 - DECK_Z0 + 2]);

        // ---- riser-bay interface (chassis lane, 2026-07-06) ----
        // center notch: flange + deck-extension strip x +/-26 above z 19.5
        // (trunk z 57.55). Front end: the D456 head bosses + USB3 grommet on
        // the riser front wall reach through here; kept on BOTH ends so the
        // shoulder stays ONE part. Horn plates start at x 27 — untouched.
        translate([-26, FLANGE_Y0 - 0.1, 19.5])
            cube([52, REAR_W0 - FLANGE_Y0 + 0.1 + EPS, DECK_Z1 - 19.5 + 0.1]);
        // riser hold-down holes: M3x10 from outside into heat-sets in the
        // riser end walls at (x +/-40, z 29.35) = trunk (y +/-40, z 67.4)
        for (sx = [-1, 1])
            translate([sx*40, FLANGE_Y0 - 1, 29.35]) rotate([-90, 0, 0])
                cylinder(d = 3.4, h = FLANGE_Y1 - FLANGE_Y0 + 2);
    }
}

shoulder_v6();
