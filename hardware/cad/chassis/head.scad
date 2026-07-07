// =============================================================================
// NOVA chassis — integrated forward HEAD (D456 face + L2 crown), ONE part
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (+x FRONT, z up).
// REPLACES the two retired front sensor parts (l2_mast.scad periscope-era
// mast + d456_head.scad periscope). Study: head_study.py (deliverable 1).
//
// WHY (2026-07-07): the periscope tilted the D456 UP behind the chassis and
// the trunk front cut the bottom of its view (near-ground occlusion). This
// head puts the camera FORWARD of the chassis (x70..100, past the front wall
// x63.5) as a DOWN-TILTED 27deg "face", so the ground ahead is in frame, and
// carries the L2 as a "crown" on top — one printed part, two sensors.
//
// GEOMETRY (head_study.py, verified vs the REAL swept front-leg cloud with
// the front hfe capped -50, the deck-ext fins, the Jetson case, the L2 ring):
//   * D456 body back-face center on the tilted face at (70, 0, 105.5),
//     tilt 27deg down about +y. Body corners x63.4..99.7 (fwd margin +0.3 to
//     the x100 leg limit — but that corner is at z107, far above any leg),
//     z80.8..118.4 (lowest pt +1.2 over the fin top 79.55). 0 leg-sweep hits.
//   * L2 crown seat top z121 (L2 body bottom) -> optical center ~z154, 360deg
//     ring clear (camera top 118.4 is 2.6 below the L2 bottom, 36 below the
//     ring). L2 optical x kept at 53.5 (UNCHANGED from the mast) so the
//     rear-down cone stays maximally open (blind only below -83deg vs the
//     Jetson case; v1-accepted) and CoM barely moves.
//   * fwd down-cone: the camera's fwd-top corner sits at -45.4deg, i.e. just
//     OUTSIDE the L2's -45deg FoV edge -> the camera no longer clips the L2
//     forward cone (the periscope clipped it ~3.5deg). Improvement.
//
// STRUCTURE (all trunk-frame mm):
//   REAR LOBE (L2 tower, reuses the mast): deck flange (x51.3..63, y±20) bolts
//     the riser deck inserts at (54/59.0, ±14) M3x10 from ABOVE (counterbored);
//     column x51.6..64 y±9 rises to the crown; crown plate z117..121 carries
//     the L2 on its 4x M3 22.5 square (bolted from BELOW, ball-key). Cable bore
//     13x11 down the column -> the deck L2 drop (53.5,0) -> trunk interior
//     (passes the RJ45 11.7x8 head + the ~O8 3.5x1.35 DC plug; caliper).
//   FRONT LOBE (D456 face): stem x63.45..70 y±22 drops through the shoulder
//     center notch (y±26) to the riser front-wall row (4x M3 at y ∓21/∓7/±7/±21,
//     z67.4 — driver passes UNDER the camera); tilted face plate carries the
//     camera on its REAR 2x M3 centerline pattern (94.4 apart, ±47.2) + a
//     ±3 z-slot; a face pillar (x63.45..70) backs the plate and ties the stem
//     to the crown. RIGHT-ANGLE USB-C (BOM) exits a plate window -> stem
//     channel -> the riser wall grommet at (14, 61.5).
//   The two lobes fuse ABOVE the deck-ext fin (z>79.55): the column (y±9,
//     clears the fin in the y±26 notch) meets the stem at x63.45..64, and the
//     face plate + pillar bridge the stem to the crown.
//
// REMOVABLE: L2 = its 4 crown-plate screws from below (head/riser untouched).
//   Head = 4 wall-row M3 (front) + 4 deck M3 (under, ball-key) -> lifts off
//   with the L2 attached. Camera bolts to the plate ON THE BENCH (rear screws
//   unreachable installed); service = the 4 wall-row screws, camera rides.
// Fit gate: check_fit.py case 7+8 fused into the HEAD case (vs trunk/riser/
//   case/shoulders + the front-leg sweep at hfe -50 + the L2 360/CoM).
// PRINT: FACE-DOWN is impossible (tilted + tall). Print CROWN-DOWN (crown
//   plate on the bed): the column + stem + face plate rise as a tower; tree
//   supports under the tilted face-plate overhang + the stem's wall-side.
//   PA6-CF. Alt: split at z~100 (crown/L2-tower vs face) if the tower warps —
//   deferred; single part first.

$fn = 64;
EPS = 0.05;
M3_CLEAR = 3.4;

// ---- REAR LOBE : L2 tower (reuses l2_mast.scad values) -----------------------
CTR       = 53.5;                 // L2 / column center x (UNCHANGED vs mast)
FLG_Z0    = 71.9; FLG_T = 4;      // deck flange
FLG       = [51.3, 63.0, -20, 20];
MAST_BX   = [54, 59.0]; MAST_BY = 14;      // deck insert bolts
COL       = [51.6, 64.0, -9, 9];  // column outer x0 x1 y0 y1 (front 64 laps
                                  //  the stem 63.45; y±9 rides the notch so
                                  //  the x63.5..64 sliver clears the fin)
BORE      = [13, 11];             // cable bore (RJ45 11.7x8 + DC plug; caliper)
CROWN_Z0  = 118.0; CROWN_T = 4;   // crown seat = L2 bottom 122 (raised vs the
                                  //  mast 117.4 to clear the tilted face plate
                                  //  top 120.7 + the camera top 118.4)
CROWN_X0  = 34.5; CROWN_X1 = 70;  // 34.5 = CTR-19; 70 laps the face pillar
CROWN_HALF_Y = 19;
L2_BCD    = 22.5 / 2;             // 11.25

// ---- FRONT LOBE : D456 face --------------------------------------------------
STEM_X0   = 63.45; STEM_X1 = 70;  // 0.1 off the riser wall (63.35)
STEM_HALF_Y = 22;
ROW_Y     = [-21, -7, 7, 21]; ROW_Z = 67.4;    // riser front-wall bolt row
STEM_Z1   = 100;                  // stem top (laps the face plate + pillar)
PILLAR    = [63.45, 70, -16, 16]; // face-plate backbone x0 x1 y0 y1
PILLAR_Z0 = 98; PILLAR_Z1 = 119;  // ties stem (z100) to crown (z117)

// D456 tilted mount (head_study.py)
TILT      = 27;                   // down about +y
CAM_M     = [70, 0, 105.5];       // back-face center (mount reference)
FACE_T    = 5;                    // plate thickness (behind the mount plane)
FACE_HALF_Y = 60;                 // < camera 61.9; holds the ±47.2 bolts
FACE_HALF_Z = 14.5;               // = camera half-height (tilt lifts the rear-
                                  //  top corner to z120.7; more would hit the
                                  //  L2 bottom 122)
MOUNT_Y   = 47.2;                 // 2x centerline holes 94.4 apart (CALIPER)
MOUNT_SLOT = 3;                   // ±3 z-tolerance (unverified)

module flare(x0, x1, y0, y1, X0, X1, Y0, Y1, z0, z1) {
    hull() {
        translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, EPS]);
        translate([X0, Y0, z1 - EPS]) cube([X1 - X0, Y1 - Y0, EPS]);
    }
}

module head() {
    difference() {
        union() {
            // --- rear lobe: deck flange -> column -> crown ---
            translate([FLG[0], FLG[2], FLG_Z0])
                cube([FLG[1] - FLG[0], FLG[3] - FLG[2], FLG_T]);
            // flange -> column flare (starts behind the wall, y±18)
            flare(COL[0], FLG[1], -18, 18, COL[0], COL[1], COL[2], COL[3],
                  FLG_Z0 + FLG_T - EPS, 90);
            // column
            translate([COL[0], COL[2], FLG_Z0])
                cube([COL[1] - COL[0], COL[3] - COL[2], CROWN_Z0 - FLG_Z0 + EPS]);
            // column -> crown flare. STARTS at z110.6 (above the Jetson case
            // top 110.1): below that only the column (x51.6..64, forward of the
            // case front 48.3) exists — the rearward-widening gusset to x34.5
            // lives entirely above the case, cantilevering over its top like
            // the old mast plate did.
            flare(COL[0], COL[1], COL[2], COL[3],
                  CROWN_X0, CROWN_X1, -CROWN_HALF_Y, CROWN_HALF_Y,
                  110.6, CROWN_Z0 + EPS);
            // crown plate (L2 seat)
            translate([CROWN_X0, -CROWN_HALF_Y, CROWN_Z0])
                cube([CROWN_X1 - CROWN_X0, 2 * CROWN_HALF_Y, CROWN_T]);

            // --- front lobe: stem -> face pillar -> tilted face plate ---
            // stem through the notch to the wall row
            translate([STEM_X0, -STEM_HALF_Y, ROW_Z - 3])
                cube([STEM_X1 - STEM_X0, 2 * STEM_HALF_Y,
                      STEM_Z1 - (ROW_Z - 3) + EPS]);
            // face pillar (backbone; ties stem top to the crown)
            translate([PILLAR[0], PILLAR[2], PILLAR_Z0])
                cube([PILLAR[1] - PILLAR[0], PILLAR[3] - PILLAR[2],
                      PILLAR_Z1 - PILLAR_Z0]);
            // pillar -> crown blend
            flare(PILLAR[0], PILLAR[1], PILLAR[2], PILLAR[3],
                  55, CROWN_X1, -CROWN_HALF_Y, CROWN_HALF_Y,
                  PILLAR_Z1 - 4, CROWN_Z0 + EPS);
            // tilted face plate (D456 seats on its +x local face)
            translate(CAM_M) rotate([0, TILT, 0])
                translate([-FACE_T, -FACE_HALF_Y, -FACE_HALF_Z])
                    cube([FACE_T, 2 * FACE_HALF_Y, 2 * FACE_HALF_Z]);
        }
        // --- L2 cable bore + crown pigtail slot ---
        translate([CTR - BORE[0] / 2, -BORE[1] / 2, FLG_Z0 - EPS])
            cube([BORE[0], BORE[1], CROWN_Z0 + CROWN_T - FLG_Z0 + 2 * EPS]);
        translate([CTR - 7.5, -6, CROWN_Z0 - 6])
            cube([15, 12, CROWN_T + 6 + EPS]);
        // --- deck flange screws: M3x10 down into the riser inserts ---
        for (bx = MAST_BX, sy = [-1, 1]) {
            translate([bx, sy * MAST_BY, FLG_Z0 - EPS])
                cylinder(d = M3_CLEAR, h = FLG_T + 12);
            translate([bx, sy * MAST_BY, FLG_Z0 + FLG_T])
                cylinder(d = 7, h = 40);          // head well (ball-key start)
        }
        // --- L2 bolts: 4x M3x8 from BELOW the crown into the L2 base ---
        for (sx = [-1, 1], sy = [-1, 1])
            translate([CTR + sx * L2_BCD, sy * L2_BCD, CROWN_Z0 - EPS])
                cylinder(d = M3_CLEAR, h = CROWN_T + 2 * EPS);
        // --- riser front-wall bolt row (axis x, from the front) ---
        for (ry = ROW_Y)
            translate([STEM_X0 - EPS, ry, ROW_Z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = STEM_X1 - STEM_X0 + 2 * EPS);
        // --- D456 2x centerline M3 (±3 z-slot), through the tilted plate ---
        translate(CAM_M) rotate([0, TILT, 0])
            for (sy = [-1, 1]) hull() for (dz = [-MOUNT_SLOT, MOUNT_SLOT])
                translate([-FACE_T - EPS, sy * MOUNT_Y, dz]) rotate([0, 90, 0])
                    cylinder(d = M3_CLEAR, h = FACE_T + 3);
        // --- USB-C cable path: face-plate window -> stem channel -> grommet ---
        // window through the tilted plate, offset +y toward the grommet (14)
        translate(CAM_M) rotate([0, TILT, 0])
            translate([-FACE_T - EPS, 3, -13]) cube([FACE_T + 2 * EPS, 16, 13]);
        // stem channel down to the riser wall grommet at (14, 61.5)
        translate([STEM_X0 - EPS, 8, ROW_Z - 3 - EPS])
            cube([STEM_X1 - STEM_X0 + 2 * EPS, 9, 92 - (ROW_Z - 3)]);
    }
}

head();
