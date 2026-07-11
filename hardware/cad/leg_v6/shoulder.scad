// =============================================================================
// V6 Shoulder — one crossmember per trunk end (SAME part both ends; print 2).
// =============================================================================
// Frame: X = lateral from robot centerline, Y = fore-aft with 0 at the hip
// stations (+Y = horn/forward side), Z = 0 at the haa axes.
// Hips at x = ±39.05; trunk end face at y = -77.7 (both ends, measured).
//
// STRUCTURE DICTATED BY THE COAX SWEPT WEDGE (haa ±40°+): the coax bottom
// corner sweeps r41.5, reaching ~x2.8 of centerline; top corners r20.8.
// Between the wheel plane (-17.75) and horn plane (+17.75) nothing may exist
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
HORN_Y    = 17.75;             // horn face plane (haa spline-z -> shoulder y)
                                // rev 3 (2026-07-10): 17.2->17.75, caliper
                                // gap fix, matches leg_v6_common HORN_Z1 +
                                // shoulder_plate.scad FACE_Y0.
WHEEL_FACE_Y = -17.75;         // wheel face plane, same rev-3 fix (was -17.7)
REAR_W0   = -32.1;  REAR_W1 = -28.1;  // face 0.5 behind the coax YOKE-ARM
                                       // extreme (-27.6 — the yoke reaches
                                       // 5.4 PAST the coax floor; sweep-gate
                                       // find 2026-07-06). Boss Ø19 x 10.4.
DECK_Z0   = 35;     DECK_Z1 = 41.5;   // 6.5 thick. RAISED from 23.5 (sweep-gate:
                                       // the coax BRIDGE, r24-38 about the haa
                                       // axis, rolls up to z~34 inside the deck
                                       // span at 40deg — 1.0 clearance now)
DECK_Y1   = 17.0;                     // stops 0.75 short of the plate face
                                       // (LA-28 doc fix 2026-07-11: was
                                       // stale at 0.2 pre-rev-3; plate
                                       // FACE_Y0 moved 17.2->17.75)
CHEEK_X1  = 59.4;   // CHEEK_X0 removed (LA-28, 2026-07-11): dead constant,
                     // grep-confirmed unused anywhere in the repo
FLANGE_Y0 = -77.7;  FLANGE_Y1 = -73.7;
TRUNK_HOLE_X = 51.75;
TRUNK_HOLE_Z = [-33.05, -14.05];
WALL_Z0   = -25;
// plate flange bore grid (shared with shoulder_plate.scad)
PLATE_BX  = [27, 51];
PLATE_BY  = [6.2, 15.2];

// ---- neck_bracket base-bolt heat-set pilots (backlog #36 + NO-DRILL fix,
// 2026-07-10) --------------------------------------------------------------
// chassis/neck_bracket.scad has 4 M3x8 BOLT_XY bolts (trunk frame) that land
// on the FRONT shoulder's deck top. These are REAL modeled M3x3.8 heat-set
// pockets (not cosmetic dimples, not drill-at-assembly) -- the bracket base
// clearance holes pass through into these pilots, brass inserts pressed in,
// no drilling and no nuts anywhere in the joint.
// Transform: FRONT shoulder placement (preview_assembly.py / chassis/
// check_fit.py) is S2T = [[0,1,0,HIP_FA],[1,0,0,0],[0,0,1,HIP_Z],[0,0,0,1]]
// (end=+1), i.e. world = M @ shoulder-local. Inverting: shoulder-local
// sx = world_y, sy = world_x - HIP_FA(141.2), sz = world_z - HIP_Z(38.05).
// DECK_TOP (neck_bracket.scad, 79.55) - 38.05 = 41.5 = DECK_Z1 exactly,
// confirming the deck top surfaces coincide under this transform.
// neck_bracket BOLT_XY -> shoulder-local (all at DECK_Z1):
//   (117, 20)   -> (20, -24.2)   (117, -20)  -> (-20, -24.2)
//   (146, 19.5) -> (19.5, 4.8)   (146, -19.5)-> (-19.5, 4.8)
// Front pair moved sy -31.2->-24.2 (trunk x110->x117, 7mm more central) to
// get OFF the 22.5mm-tall thin rear-wall rib (REAR_W0..REAR_W1 =
// -32.1..-28.1, no flat landing / no heat-set spot there) and ONTO the flat
// 6.5 thick deck, matching neck_bracket.scad's x110->x117 fix. All 4 clear
// the lightening window (|sx|<=16, |sy| -14..12) and the horn-plate heat-set
// grid (sx=+-27/+-51, sy=6.2/15.2).
NECK_HS_D      = 4.0;    // M3 brass heat-set bore dia (matches HEATSET_D pattern)
NECK_HS_DEPTH  = 4.2;    // blind pocket depth from the deck top (DECK_Z1);
                          // deck is 6.5 thick -> 2.3mm floor remains. Fits
                          // the M3x3.8 SHORT insert (fastener-schedule.md)
                          // + ~0.4mm seat.
NECK_HS_CHAMF  = 0.3;    // mouth chamfer depth, insert start
NECK_HS_D_TOP  = 4.6;    // chamfer mouth dia
NECK_HS_XY = [[20, -24.2], [-20, -24.2], [19.5, 4.8], [-19.5, 4.8]];

module neck_heatset(x, y) {
    translate([x, y, DECK_Z1 - NECK_HS_DEPTH])
        cylinder(d = NECK_HS_D,
                 h = NECK_HS_DEPTH - NECK_HS_CHAMF + EPS);
    translate([x, y, DECK_Z1 - NECK_HS_CHAMF])
        cylinder(d1 = NECK_HS_D, d2 = NECK_HS_D_TOP,
                 h = NECK_HS_CHAMF + EPS);
}

// ---- flange floor FEET + deck gussets (2026-07-06, joint-stiffening) --------
// The C-box hangs 77.7 fore of the trunk end on a 4-bolt flange whose
// bolt couple is only 19 tall and sits LOW (user catch: "barely
// connected"). Feet bolt the flange bottom down to the trunk floor's
// solid corner bands (mesh-mapped: bolts at trunk (|x| 59.5, y +/-42)
// land solid on ALL four corners; the rear -y pad tip overhangs the
// rear floor opening by ~2 — 85% bearing, fine). M3x14 CSK from BELOW
// the floor — modeled clearance hole + 90° CSK in trunk.scad /
// trunk_build.py (DERIVED TRUNK, 2026-07-10): printed in, NO drilling
// at assembly (was: drill Ø3.2 + csk at first assembly, same practice
// as the old battery-sandwich holes — both now printed-in). Head
// flush, belly pack clears; nyloc + washer on top of the pad, reached
// through the open end aperture BEFORE the riser goes on. Retention =
// the nyloc on THIS part's pad, never the trunk. Gussets triangulate the
// flange to the deck-extension underside at x +/-40 (clear of the
// O12 grommets, which end at x 38).
FOOT_X0   = 38;    FOOT_X1 = 46;   // wall inner face 48.93 -> 2.9 gap
FOOT_Y1   = -86.7;                 // 9.0 onto the floor (trunk x 54.5)
FOOT_Z0   = -34.05;                // floor top z 3.9 + 0.1 drop-in gap
FOOT_THK  = 4;
FOOT_BOLT_X = 42;  FOOT_BOLT_Y = -81.7;   // -> trunk (59.5, +/-42)
GUSSET_X  = 40;                    // pair, 4 thick, centered +/-40

// ---- battery-lead notch (AUD-12b, 2026-07-10) --------------------------------
// flange bottom center, x +/-10, z -38.1..-26 — the belly pack's leads (both
// ends: pack->MRBF at the rear, D456 right-angle USB-C at the front, same
// part) rise unsupported from the pack (trunk x~-78) into this notch. It was
// a zero-radius 90deg through-cut in abrasive PA6-CF — chafe risk on every
// vibration cycle. Chamfered on all 4 nominal edges at BOTH flange mouths
// (entry + exit) below; the nominal 20x12.1 opening is untouched in the
// middle, still >> the ~7mm lead-pair bundle. (The notch's own bottom, z=
// -38.1, is 0.1 past the flange's real bottom edge z=-38 — same EPS-overcut
// idiom as the y-direction -0.1 below, not a 4th real material edge; chassis/
// lead_notch_grommet.scad — the TPU liner riding this chamfer — lines the
// genuine 3 edges: left/right (x+/-10) and top (z=-26).)
NOTCH_X0 = -10;    NOTCH_X1 = 10;      // x +/-10 (nominal, matches the cut below)
NOTCH_Z0 = -38.1;  NOTCH_Z1 = -26;     // z -38.1..-26 (trunk z 0..12ish)
NOTCH_CHAMF_Y  = 1.0;    // chamfer depth into the flange, each mouth
NOTCH_CHAMF_XZ = 1.0;    // opening growth (x AND z) at each mouth (~45deg)

module notch_bevel(y_mouth, y_inner, grow) {
    // hull between the nominal-size cross-section (at y_inner, one chamfer
    // depth in from the true flange face) and a GROWN cross-section (at
    // y_mouth, the flange face itself) — kills the 90deg corner on all 4
    // sides without touching the nominal opening beyond the chamfer depth.
    // Same thin-slab hull() idiom as chassis/head.scad's flare().
    hull() {
        translate([NOTCH_X0, y_inner, NOTCH_Z0])
            cube([NOTCH_X1 - NOTCH_X0, EPS, NOTCH_Z1 - NOTCH_Z0]);
        translate([NOTCH_X0 - grow, y_mouth, NOTCH_Z0 - grow])
            cube([NOTCH_X1 - NOTCH_X0 + 2 * grow, EPS,
                  NOTCH_Z1 - NOTCH_Z0 + 2 * grow]);
    }
}

module lead_notch() {
    Y0 = FLANGE_Y0 - 0.1;   // mouth, interior (-y) flange face
    Y1 = FLANGE_Y1 + 0.1;   // mouth, exterior (+y) flange face
    union() {
        notch_bevel(Y0, Y0 + NOTCH_CHAMF_Y, NOTCH_CHAMF_XZ);
        translate([NOTCH_X0, Y0 + NOTCH_CHAMF_Y, NOTCH_Z0])
            cube([NOTCH_X1 - NOTCH_X0,
                  (Y1 - NOTCH_CHAMF_Y) - (Y0 + NOTCH_CHAMF_Y),
                  NOTCH_Z1 - NOTCH_Z0]);
        notch_bevel(Y1, Y1 - NOTCH_CHAMF_Y, NOTCH_CHAMF_XZ);
    }
}

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
            // flange floor feet (see header block)
            for (sx = [-1, 1])
                translate([min(sx*FOOT_X0, sx*FOOT_X1), FOOT_Y1, FOOT_Z0])
                    cube([FOOT_X1 - FOOT_X0,
                          FLANGE_Y0 - FOOT_Y1 + 0.5, FOOT_THK]);
            // deck gussets: flange fore face -> deck-extension underside
            for (sx = [-1, 1])
                translate([sx*GUSSET_X - 2, 0, 0]) rotate([90, 0, 90])
                    linear_extrude(4) polygon([
                        [FLANGE_Y1 - 0.5, 6], [FLANGE_Y1 - 0.5, DECK_Z0 + 0.5],
                        [FLANGE_Y1 + 29, DECK_Z0 + 0.5]]);
            // LOWER trunk-bolt insert bosses (backlog #1): the 6.2 insert
            // bore breaks through the 4-thick flange; the UPPER bores are
            // already backed by the shear webs (x 51..55 spans z -25..41.5)
            // but the lower pair (z -33.05) sits below the web bottom —
            // pad to 7 for full engagement (97 N prying SF 2.5 -> ~5).
            // LA-8 (2026-07-11): pad depth 3->3.7 (7.0->7.7 total local
            // thickness) so the 6.2-deep bore leaves a >=1.5mm floor
            // (was 0.8mm — 4+3-6.2). Near/flush edge (at FLANGE_Y1) is
            // unchanged so the boss still merges cleanly into the flange;
            // only the free (deep) end grows, into open C-box air below
            // the shear-web z-band — no collision (checked against
            // FOOT_*/GUSSET_X/shear-web extents, all clear in x and z).
            for (sx = [-1, 1])
                translate([sx*TRUNK_HOLE_X - 4.5, FLANGE_Y1 - EPS,
                           TRUNK_HOLE_Z[0] - 4.5])
                    cube([9, 3.7 + EPS, 9]);
            // D456 head-bracket insert pads: thicken the flange to 7 on
            // its inner face around the 4 bores (bracket = chassis lane;
            // hangs in the open trunk-end aperture, riser end wall is at
            // z >= 47 trunk). Both ends — same part.
            // LA-8 (2026-07-11): same pad-depth fix, mirrored direction
            // (this pad grows on the FLANGE_Y0/interior side) — flush edge
            // at FLANGE_Y0-3.7..-73.65-ish stays anchored to the flange,
            // free end grows deeper; floor 0.8->1.5mm. Checked clear of
            // FOOT_* (x-band 38..46 vs this pad's 13..23/-23..-13) and the
            // lead_notch (x +/-10, doesn't reach x 13).
            for (sx = [-1, 1])
                translate([sx*18 - 5, FLANGE_Y0 - 3.7, -27.05])
                    cube([10, 3.7 + EPS, 22]);
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
            // idler-boss relief (rev 3): the haa wheel has NO retention
            // screw — a black plastic boss (Ø6, ~1-2mm proud, MEASURED)
            // sits proud of the wheel face instead. Blind counterbore from
            // the wheel-seat face (WHEEL_FACE_Y = this boss's own tip)
            // clears it, same treatment as leg_v6_common's wheel_couple_neg.
            translate([sx*HIP_X, WHEEL_FACE_Y - WHEEL_CTR_DEEP, 0])
                rotate([-90, 0, 0])
                    cylinder(d = WHEEL_CTR_D, h = WHEEL_CTR_DEEP + EPS);
        }

        // neck_bracket base-bolt M3x3.8 heat-set pilots (backlog #36,
        // NO-DRILL fix) — FRONT end only in trunk frame, but this is the
        // SAME part both ends, so the rear-mounted copy gets them too
        // (harmless: no rear neck_bracket, and they're on the deck top,
        // clear of everything else there).
        for (xy = NECK_HS_XY)
            neck_heatset(xy[0], xy[1]);

        // plate heat-set bores, down into the deck (4 per side), plus a
        // full-diameter VENT through the remaining floor (insert-audit
        // 2026-07-06: 6.2 bore in the 6.5 deck left a 0.25 floor —
        // guaranteed melt-through mess when setting. The vent lets melt +
        // air escape into the open box below and backs the iron cleanly;
        // same pattern as the riser's through-vented deck bosses.)
        // LA-9 (2026-07-11): vent widened Ø3.0->HEATSET_D(4.0) to match the
        // bore exactly. At Ø3.0 the vent was narrower than the bore, so a
        // 0.5mm-wide x 0.3mm-thick annular shelf (r1.5..r2.0) survived at
        // the bore/vent transition — not a deliberate insert seat (the
        // insert OD 4.6 is already bigger than the bore, so it never rides
        // that ring) and thin enough to crush/crack unpredictably instead
        // of the clean full melt-through the comment above describes.
        // Matching the diameters removes the shelf and makes the whole
        // bore a straight through-hole, exactly the "widen the vent to the
        // counterbore" fix.
        for (sx = [-1, 1], bx = PLATE_BX, by = PLATE_BY) {
            translate([sx*bx, by, DECK_Z1 - HEATSET_L])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
            translate([sx*bx, by, DECK_Z0 - EPS])
                cylinder(d = HEATSET_D, h = DECK_Z1 - DECK_Z0 + 2*EPS);
        }

        // trunk-flange heat-sets (screws from inside the trunk, rearward face)
        for (sx = [-1, 1], hz = TRUNK_HOLE_Z)
            translate([sx*TRUNK_HOLE_X, FLANGE_Y0 - EPS, hz])
                rotate([-90, 0, 0]) cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

        // foot bolt clearance: M3 up from below the floor, nyloc on top
        for (sx = [-1, 1])
            translate([sx*FOOT_BOLT_X, FOOT_BOLT_Y, FOOT_Z0 - 1])
                cylinder(d = 3.4, h = FOOT_THK + 2);

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
        // riser hold-down holes: M3x12 from outside into heat-sets in the
        // riser end walls at (x +/-40, z 29.35) = trunk (y +/-40, z 67.4)
        // (CR-8 #1: stack-verified 2026-07-10 — 4mm flange + 2.0mm clear
        // wall zone + 5.7mm insert engagement = 11.7 min, M3x12 fits with
        // 0.3mm spare before the bore bottom; M3x10 under-engages the
        // insert by 1.7mm. Was mis-commented M3x10, matches fastener-schedule.)
        for (sx = [-1, 1])
            translate([sx*40, FLANGE_Y0 - 1, 29.35]) rotate([-90, 0, 0])
                cylinder(d = 3.4, h = FLANGE_Y1 - FLANGE_Y0 + 2);
        // battery-lead notch: flange bottom center, x +/-10 up to z -26
        // (trunk z 12). The belly pack's leads rise behind the trunk end
        // and enter here to the MRBF block (battery_pocket.scad); at the
        // FRONT end the D456's right-angle USB-C uses the same notch.
        // Kept on both ends — same part. Chamfered both mouths (AUD-12b,
        // see lead_notch() above) — was a zero-radius 90deg through-cut.
        lead_notch();
        // D456 head-bracket heat-set bores: (x +/-18, z -22.05 & -10.05)
        // = trunk (y +/-18, z 16 & 28), pressed from the outer face; the
        // rear pads (union below) thicken the 4mm flange to 7 there
        for (sx = [-1, 1], hz = [-22.05, -10.05])
            translate([sx*18, FLANGE_Y1 + EPS, hz]) rotate([90, 0, 0])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
    }
}

shoulder_v6();
