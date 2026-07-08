// =============================================================================
// NOVA chassis — forward HEAD (D456 face + L2 crown), bolts to the NECK BRACKET
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (+x FRONT, z up).
//
// RE-ARCHITECTURE 2026-07-07 (docs/head-rearchitecture-plan.md): the head moved
// OFF the riser front and FORWARD onto the FRONT-SHOULDER top (the "neck"), so
// it projects ahead like a fox instead of perching as a turret. It no longer
// touches the riser at all — it bolts to a SEPARATE neck_bracket.scad that
// adapts the front-shoulder deck. Head = a modular removable unit (4 bolts to
// the bracket wall); the shoulder stays gate-clean + print-2-identical.
//
// PLACEMENT (forward_head_study.py, DX+73 DZ+6 from the retired riser head,
// re-verified vs the REAL swept front-leg cloud + the shoulder deck top + the
// horn-plate flanges):
//   * L2 crown center x126.5 (optical ~z160), body x89..164, z128..193; kept
//     HIGH for the 360deg mapping vantage (fennec = forehead/skull crown).
//   * D456 back-face center (143,0,111.5), 27deg down; body x136.4..172.7,
//     z86.8..124.4, y+-61.9. Camera bottom +2.0 over the horn-plate top 84.75,
//     +7.2 over the deck 79.55. Camera top +3.6 under the L2 body. 0 leg hits.
//   * The whole head rose +6 vs the study's rigid +73 translate so the tilted
//     camera bottom clears the front horn-plate top flanges (z82.75 + heads).
//
// MOUNT (mirrors the retired riser wall-row, proven): a REAR BOSS (x121..133)
//   sits against the bracket's front mount face (x121) and takes 4x M3x16 that
//   thread REARWARD into the bracket wall heat-sets (rows z89/100, y+-11 — a
//   tall couple vs the forward-tipping moment). Bolt heads counterbored on the
//   boss front (x133), reached before the D456 face + styling close in.
// STRUCTURE (trunk mm):
//   REAR BOSS -> COLUMN -> CROWN (L2 seat z124..128; L2 on its 4x M3 22.5
//     square, bolted from BELOW, ball-key). Cable bore x126.5, y+-5.5 drops the
//     L2 pigtail through the boss bottom (z84) into the bracket cable slot ->
//     deck window -> C-box -> trunk (RJ45 11.7x8 + DC plug; caliper).
//   FACE PILLAR (x128..138) hangs off the column front, BEHIND the camera
//     back-corner (x136.4), and backs the tilted FACE PLATE that carries the
//     D456 on its rear 2x M3 centerline (94.4 apart) + a +-3 z-slot. Right-
//     angle USB-C (BOM) exits a plate window -> down the pillar/column front ->
//     boss bottom -> C-box.
// REMOVABLE: L2 = its 4 crown screws from below. Head = the 4 boss->bracket
//   bolts -> lifts off with the L2 + camera attached. Camera bolts to the plate
//   ON THE BENCH (rear screws unreachable installed).
// FIT GATE: check_fit.py HEAD case (head+bracket vs trunk/riser/case/shoulders
//   + the front-leg sweep at hfe -50 + the L2 360/CoM), at the forward x.
// PRINT: BOSS-DOWN (rear boss face on the bed): the column + crown + face rise
//   as a short tower; tree supports under the tilted face-plate overhang. PA6-CF.

$fn = 64;
EPS = 0.05;
M3_CLEAR = 3.4;
STYLE = true;    // FENNEC fox styling (ears + antenna bores). GATE-CLEAN at the
                 // fwd position: ears root on a REARWARD SKULL SHELF behind the
                 // L2 (x<89) so they clear the seated L2 body + touch only the
                 // blind rear LiDAR sector. First pass — STILL TODO (deferred;
                 // they touch sensor FoV so they need the L2 ring / D456 cone
                 // gate): L2 skull shroud, D456 eye-band accent, pointed snout.
                 // Set false for the bare functional head.
EAR_T = 6;

// ---- placement (forward_head_study.py) --------------------------------------
CTR       = 126.5;                // L2 / column center x
TILT      = 27;                   // D456 down about +y
CAM_M     = [143, 0, 111.5];      // D456 back-face center (mount reference)

// ---- mount boss -> bracket wall ---------------------------------------------
MB_X0 = 121; MB_X1 = 133;         // rear face x121 mates bracket front x121
MB_Y  = 14;                        // half-span
MB_Z0 = 84; MB_Z1 = 106;
HM_Z  = [89, 100];                 // bolt rows (MUST match neck_bracket HM_Z)
HM_Y  = 11;

// ---- column + crown (L2) ----------------------------------------------------
COL_X0 = 121; COL_X1 = 138;       // rear FLUSH with the boss/bracket-wall face
                                  // (x121) so it never laps into the wall; the
                                  // crown rear lip (x108..121) cantilevers
COL_Y  = 15;
COL_Z0 = 106;                      // = boss top
CROWN_Z0 = 124; CROWN_T = 4;       // seat top 128 = L2 body bottom
CROWN_X0 = 108; CROWN_X1 = 145;    // holds the L2 22.5 square (x115.25/137.75)
CROWN_HALF_Y = 19;
L2_BCD = 22.5 / 2;                 // 11.25

// ---- front lobe : D456 face -------------------------------------------------
PILLAR = [128, 138, -16, 16];     // backs the plate, behind the cam back-corner
PILLAR_Z0 = 95; PILLAR_Z1 = 124;
FACE_T      = 5;                   // plate thickness (behind the mount plane)
FACE_HALF_Y = 60;                  // < camera 61.9; holds the +-47.2 bolts
FACE_HALF_Z = 14.5;                // = camera half-height
MOUNT_Y     = 47.2;                // 2x centerline holes 94.4 apart (CALIPER)
MOUNT_SLOT  = 3;                   // +-3 z-tolerance (unverified)

// ---- cable bore -------------------------------------------------------------
BORE = [13, 11];                   // x-span 13, y-span 11 (RJ45 + DC plug)

module flare(x0, x1, y0, y1, X0, X1, Y0, Y1, z0, z1) {
    hull() {
        translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, EPS]);
        translate([X0, Y0, z1 - EPS]) cube([X1 - X0, Y1 - Y0, EPS]);
    }
}

module head() {
    difference() {
        union() {
            // --- rear boss (bolts to the bracket wall) ---
            translate([MB_X0, -MB_Y, MB_Z0])
                cube([MB_X1 - MB_X0, 2 * MB_Y, MB_Z1 - MB_Z0]);
            // boss -> column blend
            flare(MB_X0, MB_X1, -MB_Y, MB_Y, COL_X0, COL_X1, -COL_Y, COL_Y,
                  MB_Z1 - 6, COL_Z0 + EPS);
            // --- column (boss top -> crown) ---
            translate([COL_X0, -COL_Y, COL_Z0])
                cube([COL_X1 - COL_X0, 2 * COL_Y, CROWN_Z0 - COL_Z0 + EPS]);
            // --- crown plate (L2 seat) ---
            translate([CROWN_X0, -CROWN_HALF_Y, CROWN_Z0])
                cube([CROWN_X1 - CROWN_X0, 2 * CROWN_HALF_Y, CROWN_T]);

            // --- face pillar (backs the tilted plate; ties to the column) ---
            translate([PILLAR[0], PILLAR[2], PILLAR_Z0])
                cube([PILLAR[1] - PILLAR[0], PILLAR[3] - PILLAR[2],
                      PILLAR_Z1 - PILLAR_Z0]);
            // tilted face plate (D456 seats on its +x local face)
            translate(CAM_M) rotate([0, TILT, 0])
                translate([-FACE_T, -FACE_HALF_Y, -FACE_HALF_Z])
                    cube([FACE_T, 2 * FACE_HALF_Y, 2 * FACE_HALF_Z]);

            // ===== FENNEC styling (first pass at the fwd position 2026-07-07)
            // Ears rooted on a REARWARD SKULL SHELF, BEHIND the L2 (x<89) per
            // the LOCKED anatomy — they touch only the blind rear LiDAR sector,
            // keeping the side/forward mapping clear. (L2 skull shroud + D456
            // eye accent + snout deferred: they touch sensor FoV, need the
            // ring/down-cone gate.)
            if (STYLE) {
                // REAR SKULL SHELF: extends the crown rearward (x74..112) to
                // root the ears clear of the L2 footprint. Top z127.5 stays
                // BELOW the L2 body bottom (128), so even the under-L2 part
                // (x89..112) doesn't lift into the seated L2.
                translate([74, -CROWN_HALF_Y, CROWN_Z0])
                    cube([38, 2 * CROWN_HALF_Y, 3.5]);
                // EARS: big splayed triangular blades, base BEHIND the L2
                // (x72..88, 1mm off the L2 rear face x89), leaning rearward +
                // outward + up to tall fennec tips. Each houses an SMA antenna.
                for (sy = [-1, 1])
                    hull() {
                        translate([72, sy * 14 - EAR_T / 2, CROWN_Z0 + 1])
                            cube([16, EAR_T, 4]);            // broad base on shelf
                        translate([64, sy * 44 - EAR_T / 2, 200])
                            cube([12, EAR_T, 4]);            // tall splayed tip
                    }
            }
        }
        // --- L2 cable bore + crown pigtail slot ---
        translate([CTR - BORE[0] / 2, -BORE[1] / 2, MB_Z0 - EPS])
            cube([BORE[0], BORE[1], CROWN_Z0 + CROWN_T - MB_Z0 + 2 * EPS]);
        translate([CTR - 7.5, -6, CROWN_Z0 - 6])
            cube([15, 12, CROWN_T + 6 + EPS]);
        // --- boss -> bracket bolts: 4x M3x16 rearward into the wall heat-sets,
        //     counterbored on the boss front (x133) for the head + ball-key ---
        for (z = HM_Z, sy = [-1, 1]) {
            translate([MB_X0 - EPS, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = MB_X1 - MB_X0 + 2 * EPS);
            translate([MB_X1 - 5, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = 6.5, h = 6);          // head counterbore + ball-key
        }
        // --- L2 bolts: 4x M3x8 from BELOW the crown into the L2 base ---
        for (sx = [-1, 1], sy = [-1, 1])
            translate([CTR + sx * L2_BCD, sy * L2_BCD, CROWN_Z0 - EPS])
                cylinder(d = M3_CLEAR, h = CROWN_T + 2 * EPS);
        // --- D456 2x centerline M3 (+-3 z-slot), through the tilted plate ---
        translate(CAM_M) rotate([0, TILT, 0])
            for (sy = [-1, 1]) hull() for (dz = [-MOUNT_SLOT, MOUNT_SLOT])
                translate([-FACE_T - EPS, sy * MOUNT_Y, dz]) rotate([0, 90, 0])
                    cylinder(d = M3_CLEAR, h = FACE_T + 3);
        // --- USB-C path: face-plate window -> pillar/column front -> boss ---
        translate(CAM_M) rotate([0, TILT, 0])
            translate([-FACE_T - EPS, 3, -13]) cube([FACE_T + 2 * EPS, 16, 13]);
        // channel down the column front (x behind the plate) to the boss bottom
        translate([COL_X1 - 11, 6, MB_Z0 - EPS])
            cube([11, 9, PILLAR_Z1 - MB_Z0]);
        // --- FENNEC: SMA antenna bore up each ear root (O6.5, U.FL->SMA) ---
        if (STYLE)
            for (sy = [-1, 1])
                translate([80, sy * 14, CROWN_Z0 - EPS])
                    cylinder(d = 6.5, h = 50);
    }
}

head();
