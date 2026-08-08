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
//   sits against the bracket's front mount face (x121) + takes 4x M3x12 (rows
//   z89/100, y+-10 — a tall couple vs the fwd-tipping moment) driven from BEHIND
//   the bracket wall into heat-sets in the BOSS (access audit 2026-07-08).
//   BREAKAWAY FUSE (#42): these 4 are NYLON M3 — a faceplant shears them at the
//   x121 joint plane (single shear) so the head + L2 + D456 POP OFF (tethered on
//   their cables) instead of snapping the neck or cracking the LiDAR. The joint
//   has no interlock, so it separates cleanly. ⚠ tune preload at bench: must
//   hold trot/vibration (<<nylon M3 ~200N shear) yet shed on a hard fall.
// STRUCTURE (trunk mm):
//   REAR BOSS -> COLUMN -> CROWN (L2 seat z124..128; L2 on its 4x M3 on the
//     Ø51 (±18) BCD, bolted from BELOW, ball-key). Cable bore x126.5, y+-5.5 drops the
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
// PRINT: PA6-CF. The EARS print SEPARATELY (head_ear.scad ×2) — the head body
//   is then compact (x74..150, z84..131, no tall spans). Orient CROWN/PAD-DOWN
//   (the flat crown top on the bed = best L2-seat + ear-pad surface); the boss
//   + tilted face + cheeks rise -> tree supports under the tilted-face + cheek
//   overhangs. (#184: material was already in this block, just on a
//   continuation line instead of the opening PRINT: line — invisible to
//   slice_plate.py's parser, which only reads the line starting "PRINT:", and
//   to a human skimming the header for the same reason.) ⚠ verify the support
//   layout in the slicer (the tilted face is the one real overhang). Alt:
//   face-plate-down (tilt 27°) for the cleanest face.

$fn = 64;
EPS = 0.05;
M3_CLEAR = 3.4;
STYLE = true;    // FENNEC fox styling — GATE-CLEAN + FoV-CLEAN (head_fov_check.py).
                 // Ears on a rear skull shelf (blind rear sector); FACETED CHEEKS
                 // flare the crown into the wide D456 eye-band (the fox face) +
                 // a BROW visor; the tilted eye-face reads as a down-muzzle. All
                 // kept BEHIND the camera (x<136) + BELOW the L2 seat (z<128) so
                 // neither sensor FoV is touched. (L2 skull SHROUD + pointed
                 // SNOUT are RULED OUT, not deferred — a shroud blocks the L2
                 // ring/down-cone, a snout enters the D456 ground view.)
                 // Set false for the bare functional head.
EAR_T = 6;

// ---- placement (forward_head_study.py) --------------------------------------
CTR       = 126.5;                // L2 / column center x
TILT      = 27;                   // D456 down about +y
CAM_M     = [143, 0, 111.5];      // D456 back-face center (mount reference)

// ---- mount boss -> bracket wall ---------------------------------------------
MB_X0 = 121; MB_X1 = 133;         // rear face x121 mates bracket front x121
MB_Y  = 14;                        // half-span (can't grow — the bracket side
                                   // webs sit at y16..20; instead the head-mount
                                   // bolts moved inboard, HM_Y 11->8, for wall)
MB_Z0 = 84; MB_Z1 = 106;
HM_Z  = [89, 100];                 // bolt rows (MUST match neck_bracket HM_Z)
HM_Y  = 10;                        // bolt half-span: centered between the cable bore (y5.5) and the boss edge (y14) -> ~1.7-2.2mm insert wall both sides (fastener audit)

// ---- column + crown (L2) ----------------------------------------------------
COL_X0 = 121; COL_X1 = 138;       // rear FLUSH with the boss/bracket-wall face
                                  // (x121) so it never laps into the wall; the
                                  // crown rear lip (x108..121) cantilevers
COL_Y  = 15;
COL_Z0 = 106;                      // = boss top
CROWN_Z0 = 124; CROWN_T = 4;       // seat top 128 = L2 body bottom
CROWN_X0 = 105; CROWN_X1 = 148;    // grown to hold the REAL L2 pattern (±18)
CROWN_HALF_Y = 21;
// L2 mount = the REAL Unitree L2 base pattern (MEASURED from the STEP 2026-07-07:
// 4 holes on a Ø51 bolt circle, R25.5, 90° apart). Placed at 45° -> a 36 mm
// square: holes at CTR±18, ±18 (R25.5). REPLACES the wrong 22.5 square (±11.25)
// the mast/head had assumed. M3 clearance up from below into the L2 base threads.
L2_BCD = 18.0;                     // = 25.5·cos45 (Ø51 BCD at 45°)

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
            // --- crown plate (L2-adapter seat) ---
            translate([CROWN_X0, -CROWN_HALF_Y, CROWN_Z0])
                cube([CROWN_X1 - CROWN_X0, 2 * CROWN_HALF_Y, CROWN_T]);
            // crown FRONT LIP: captures the L2-adapter front tongue — it slides
            // into the slot, under the z130.5 hook (no front bolt; the front
            // was unreachable). Above the D456 (z<124), below the L2 (z<133).
            difference() {
                translate([146, -15, CROWN_Z0 + CROWN_T - 1])
                    cube([14, 30, 5.5]);               // x146..160, z127..132.5 (laps crown z128)
                translate([145, -16, CROWN_Z0 + CROWN_T - EPS])
                    cube([13.5, 32, 2.5]);             // tongue slot z128..130.5
            }

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
                // REAR SKULL SHELF -> EAR-MOUNT PAD: the crown extends rearward
                // (x74..112) to a 6mm-thick pad (z124..130). The EARS ARE NOW
                // SEPARATE bolt-on parts (head_ear.scad) — the head no longer
                // prints the tall/warpy ears (see PRINT note). The pad carries
                // 2x M3 heat-sets per side; the ear foot bolts down onto it.
                // Top z130 stays BELOW the L2 body bottom (only where x<89 does
                // the pad go this high; the x89..112 part is capped at 127.5).
                translate([71, -CROWN_HALF_Y, CROWN_Z0])
                    cube([16, 2 * CROWN_HALF_Y, 7]);         // x71..87 pad z124..131
                                                              //  (2mm clear of L2 x89; rear
                                                              //  extended 74->71 so the x77
                                                              //  ear heat-set clears the edge
                                                              //  — fastener audit 2026-07-08)
                translate([84, -CROWN_HALF_Y, CROWN_Z0])
                    cube([28, 2 * CROWN_HALF_Y, 3.5]);       // x84..112 thin (overlaps
                                                              //  the tall pad -> one body)
                // FACETED CHEEKS: flare the narrow crown (y±21, under the L2)
                // out to the wide D456 eye-band -> the fox FACE. Kept BEHIND the
                // camera back-corner (x<136 -> never in the 87x58 view) and
                // BELOW the L2 seat (z<128). FoV-gated.
                for (sy = [-1, 1])
                    flare(128, 135, min(sy*46, sy*56), max(sy*46, sy*56),
                          112, 134, min(sy*16, sy*21), max(sy*16, sy*21),
                          101, 124);
                // BROW: an angular visor over the eyes — behind the lens plane
                // (x<136) + above the FoV cone. The fennec expression.
                hull() {
                    translate([120, -24, 123]) cube([14, 48, 3]);
                    translate([131, -26, 116]) cube([4, 52, 3]);
                }
            }
        }
        // --- L2 cable bore + crown pigtail slot ---
        translate([CTR - BORE[0] / 2, -BORE[1] / 2, MB_Z0 - EPS])
            cube([BORE[0], BORE[1], CROWN_Z0 + CROWN_T - MB_Z0 + 2 * EPS]);
        translate([CTR - 7.5, -6, CROWN_Z0 - 6])
            cube([15, 12, CROWN_T + 6 + EPS]);
        // cable-bore mouth chamfer at the x121 breakaway plane (#42): in a
        // tethered faceplant the head separates HERE and the L2/D456 cables
        // tension over this raw edge as the head pops off — soften the
        // corner (AUD-12c, cheap/low-risk while already in this area,
        // 2026-07-10).
        BORE_CHAMF = 0.75;
        hull() {
            translate([MB_X0 - EPS, -BORE[1] / 2 - BORE_CHAMF, MB_Z0 - BORE_CHAMF])
                cube([EPS, BORE[1] + 2 * BORE_CHAMF,
                      CROWN_Z0 + CROWN_T - MB_Z0 + 2 * BORE_CHAMF]);
            translate([MB_X0 + BORE_CHAMF, -BORE[1] / 2, MB_Z0])
                cube([EPS, BORE[1], CROWN_Z0 + CROWN_T - MB_Z0]);
        }
        // --- boss -> bracket bolts: driven from the OPEN REAR (behind the
        //     bracket wall, x<113 = open above the deck). HEAT-SETS in the boss
        //     (from its rear face x121, +x); the wall has clearance; M3 from
        //     behind. (The old front-drive was BLOCKED by the pillar/face-plate
        //     at z100 — access audit 2026-07-08.) ---
        for (z = HM_Z, sy = [-1, 1])
            translate([MB_X0 - EPS, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = 4.0, h = 6.2 + EPS);   // heat-set x121..127 from rear
        // --- L2 ADAPTER mount (l2_adapter.scad — the L2 bolts to the adapter
        //     on the bench, not direct; 2 of its 4 bolts are unreachable on the
        //     assembled head, access audit 2026-07-08). 2x M3 from BELOW the
        //     crown rear lip up into the adapter heat-sets; the adapter's front
        //     tongue slides under the crown front lip (added in the union). ---
        for (sy = [-1, 1])
            translate([114, sy * 9, CROWN_Z0 - EPS])         // (was 110,±14 — moved to
                cylinder(d = M3_CLEAR, h = CROWN_T + 2 * EPS);  // 114,±9 so the adapter insert
                                                             // clears the L2 CSK at 108.5,±18
                                                             // — fastener audit 2026-07-08)
        // --- D456 2x centerline M3 (+-3 z-slot), through the tilted plate ---
        translate(CAM_M) rotate([0, TILT, 0])
            for (sy = [-1, 1]) hull() for (dz = [-MOUNT_SLOT, MOUNT_SLOT])
                translate([-FACE_T - EPS, sy * MOUNT_Y, dz]) rotate([0, 90, 0])
                    cylinder(d = M3_CLEAR, h = FACE_T + 3);
        // --- D456 driver-access pockets (cheek behind each bolt, Ø11) ---
        if (STYLE)
            translate(CAM_M) rotate([0, TILT, 0])
                for (sy = [-1, 1])
                    translate([-FACE_T - 1, sy * MOUNT_Y, 0]) rotate([0, -90, 0])
                        cylinder(d = 11, h = 22);
        // --- USB-C path: face-plate window -> pillar/column front -> boss ---
        translate(CAM_M) rotate([0, TILT, 0])
            translate([-FACE_T - EPS, 3, -13]) cube([FACE_T + 2 * EPS, 16, 13]);
        // channel down the column front, offset under the face-plate window
        // — REROUTED 2026-07-10 (AUD-12, confirmed defect): the old channel
        // was a straight cube (x127..138, y6..15) run all the way down to
        // the boss bottom (z84), which hollowed out the ENTIRE +y insert
        // column of the rear-boss->bracket bolts (HM_Y=10, z89 & z100) — 0mm
        // insert floor/wall measured at both (2 of 4 head-boss bolts void).
        // There is no separate channel width available past the boss: the
        // insert danger zone (y6.5..13.5, +-3.5mm around the y10 bore) backs
        // right up against both the L2-bore edge (y5.5) and the boss edge
        // (y14), leaving <1mm clear either side — not enough for a
        // connector-sized channel. Fix: below the boss top (COL_Z0=106,
        // ABOVE both insert z-bands) the USB-C path shares the existing L2
        // CABLE BORE instead of cutting new boss material (13x11, already
        // proven clear of the inserts — the -y mirror, which never had a
        // channel, stayed solid). The offset run (x125..138, y6..15 — widened
        // x127->125 from the original design: the old 11x9 cross-section
        // couldn't actually clear a ~12x6.5 USB-C overmold in either
        // orientation, measured while verifying this fix; 13x9 does, still
        // lines up under the face-plate window above) is kept for z>=109; a
        // short taper merges it down to the L2-bore footprint (x120..133,
        // y-6..6) exactly at z106 — entirely within the column (z106..124),
        // never touching the boss (z84..106), so the insert bosses stay
        // fully solid. check_fit.py case 14 gates all 4 boss floors + the
        // channel cross-section going forward.
        translate([COL_X1 - 13, 6, 109])
            cube([13, 9, PILLAR_Z1 - 109]);
        flare(120, 133, -6, 6, 125, 138, 6, 15, COL_Z0, 109);
        // --- FENNEC: SMA antenna bore up each ear root (O6.5) — the SOLE home
        //     for the Jetson WiFi 2x2 MIMO antennas (riser bulkheads retired):
        //     U.FL->SMA pigtail up the neck -> bulkhead here -> whip. Highest,
        //     clearest-of-CF spot. PROVISION — onboard WiFi works; order only
        //     if bench range needs it (verify the card exposes U.FL). ---
        // ear-mount M3 heat-sets in the pad (2 per side, from the pad TOP z131
        // before the ears go on). The ear foot bolts down into these. (The SMA
        // antenna bore now lives in head_ear.scad, not here.)
        // #70 fix (2026-07-12): SHORT M3 insert (Ruthex M3x3.8, bore 4.2)
        // instead of the full 6.2 -- the pad sits over a cavity (can't deepen
        // down) and raising the pad top would shift the ear mate, so the short
        // insert lifts the floor 0.80->2.8mm. Light antenna-ear mount, 3.8mm
        // engagement is ample. BOM: these 4 = M3x3.8 short (not full).
        if (STYLE)
            for (sy = [-1, 1], ex = [77, 83])
                translate([ex, sy * 10, CROWN_Z0 + 7 - 4.2])
                    cylinder(d = 4.0, h = 4.2 + EPS);
        // (#46 TPU fox-mask snout-anchor bores REMOVED 2026-07-10: the fox
        //  mask was banked, so these were dead — and their z86 Ø4 bore
        //  overlapped the z89 HM breakaway-insert bore, breaking that insert's
        //  360° wall (CR-3). Removing them clears CR-3.)
    }
}

head();
