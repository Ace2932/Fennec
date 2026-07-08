// =============================================================================
// NOVA chassis — trunk RISER BAY (+25mm rim, replaces the stock lid)
// =============================================================================
// Top-level design: docs/design-outline.md (chassis lane).
// Frame = TRUNK frame: z0 = trunk floor bottom, x fore-aft (+x FRONT, the
// stock "F" arrow), y lateral, trunk outer 127 x 110 x 46.91.
//
// Every mate dim below is MESH-MEASURED from SM3_Frame_ChassisTrunk.stl
// (measure_trunk.py, 2026-07-06). The stock trunk is NOT a tub: floor slab
// (top z 3.9) + two 6mm side walls (inner y +/-48.93, top z 29.0) + four
// corner wedge ramps with 10.2 x 6.1 plateau tabs at z 46.91. The ENDS ARE
// OPEN — closed at assembly by the v6 shoulder flanges (leg_v6/shoulder.scad),
// whose inner faces sit at x +/-63.5 and rise to trunk z 79.55.
//
// Seating: side skirts rest on the wall tops (z 29.0, primary datum, two
// full-length rails); end walls stop 0.1 above the wedge plateaus
// (secondary). Lateral register: 4 tabs inside the wall inner faces
// (0.45 clearance, leg_v6 drop-in doctrine). Fore-aft register + hold-down:
// 4x M3x10 HORIZONTAL through the shoulder-flange holes into heat-set pads
// in the riser end walls (2 front + 2 rear, trunk y +/-40 z 65) — ZERO
// mods to the stock shell. Riser is NEVER structural; lifts off with the
// robot standing: D456 head shell off (2) + 4 flange screws.
//
// Deck top z 71.9 = trunk top + 25 (outline-locked silhouette). Deck top is
// FLAT — every fixture is an UNDERSLUNG boss so the part prints deck-face
// on the bed with zero supports.
//
// JETSON: the bespoke tray+hood is RETIRED (heatsink calipered 34.9, not
// 21.5 -> collides the L2 plate). The OFFICIAL CASE (110.3 x 93.9 x 38.2)
// now sits on the deck, held by jetson_case_mount.scad (deck cradle). The
// old 96.5 x 75.4 Jetson standoff grid + hood pads are GONE. See README
// "Jetson enclosure decision" + place_case.py (the placement study).
//   case world AABB x -62.0..48.3, y +-46.95, z 71.9..110.1; PORT END -x
//   (rear), heatsink end +x. Cables exit the -x port end into the shoulder
//   center notch (y+-26) + the deck CASE_SLOT below it.
//
// HEAD MOUNT — RETIRED FROM THE RISER 2026-07-07. The head moved FORWARD onto
// the front-shoulder top (the "neck") via the separate neck_bracket.scad, so it
// no longer bolts to the riser at all. The old riser head anchors (L2-column
// deck base 54/59,±14; L2 cable drop; front-wall camera register z67.4; USB-C
// grommet 14,61.5) are REMOVED. SMA bulkheads KEPT (still MIMO candidate; may
// yet relocate to the head ears once the fennec styling lands). See head.scad +
// neck_bracket.scad + README "head interface".
//
// Deck fixtures (trunk x,y) after the case pivot:
//   CASE_SLOT x -58..-46, y +-18: the case PORT-END cable exit (into the
//     shoulder notch) AND the case bottom-vent breather.
//   SMA bulkheads 2x O6.5 at (57, +/-40) — RELOCATED to the front strip
//     (the case covers the old +y deck spots); 80 apart (MIMO). !! pigtail
//     reach from the rear-facing ports is UNVERIFIED (flagged for review).
//   Cradle deck ties 4x O3.4 at (47.3/-59.0, +/-50.35): M3 up from below
//     into the cradle post-base heat-sets.
// Wall fixtures: riser<->flange pads (both ends, y +/-40, bores z 67.4). Vent
//   slots both sides, z 52..66. (The HEAD front-wall camera register + USB-C
//   grommet that lived here are RETIRED — see HEAD MOUNT above.)
//
// The head's forward face + L2 crown live ABOVE the shoulder DECK EXTENSION
// (which spans trunk z 73.05..79.55 over x 63.5..109 at both ends); the head
// stem/column ride the y+-26 flange notch through that band. See head.scad.
//
// Fit gate: check_fit.py (riser vs trunk mesh + stack envelope + shoulders
// + CROUCH-pose legs). Run build_all.sh after every geometry change.

$fn = 64;
EPS = 0.05;

// ---- measured trunk mate (measure_trunk.py 2026-07-06) ----------------------
WALL_TOP   = 29.0;    // side wall top plane
WALL_IN    = 48.93;   // side wall inner faces +/-
PLATEAU_Z  = 46.91;   // corner wedge plateau tabs
TRUNK_END  = 63.5;    // trunk end planes = shoulder flange inner faces

// ---- riser envelope ----------------------------------------------------------
OUT_X      = 63.35;   // 0.15 shy of the shoulder flanges (screw-clamped gap)
OUT_Y      = 55.0;    // flush with the trunk side walls
DECK_TOP   = 71.9;    // trunk top 46.91 + 25 (design-outline)
DECK_T     = 4.0;
WALL       = 3.2;
SKIRT_BOT  = 29.0;    // ON the wall tops (contact = designed seat)
END_BOT    = 47.01;   // 0.1 above the plateaus
DECK_BOT   = DECK_TOP - DECK_T;   // 67.9 interior ceiling
CLR_TAB    = 0.45;    // register-tab clearance (leg_v6 drop-in doctrine)

// ---- hardware ----------------------------------------------------------------
HEATSET_D  = 4.0;     // Ruthex M3 insert BORE (insert OD 4.6 — bore 4.0!)
HEATSET_L  = 6.2;
M3_CLEAR   = 3.4;

// ---- fixture positions ---------------------------------------------------------
// Jetson devkit standoff grid RETIRED — the official case sits on the deck
// (jetson_case_mount.scad cradle) instead of a bare board on spacers.
// MAST_BX/MAST_BY/L2_DROP RETIRED 2026-07-07 — head moved fwd onto the neck
// bracket (neck_bracket.scad); these riser L2-column anchors are orphaned.
// Kept commented for the reused-geometry knowledge.
// MAST_BX = [54, 59.0];  MAST_BY = [-14, 14];  // HEAD L2-column base
// L2_DROP = [53.5, 0];                          // head cable-bore drop
CASE_SLOT = [-58, -46, -18, 18];  // case PORT-END cable exit (into the
                                  // shoulder notch) + case bottom-vent breather
SMA  = [[57, 40], [57, -40]];     // O6.5, RELOCATED to the front strip (case
                                  // covers the old +y spots); 80 apart (MIMO)
CRADLE_TIE = [[47.3, 50.35], [47.3, -50.35],         // case-cradle deck ties
              [-59.0, 50.35], [-59.0, -50.35]];      // M3 up from below into
                                                     // the cradle post bases
// End-wall pads live in the z 64.4..70.4 band: above the stack envelope
// (63.9 = 58 + 2.0 floor bosses), fused into the deck underside (67.9),
// horizontal bores at z 67.4 (1.0 pad wall below, 2.5 deck-top web above).
// An earlier z-65-centered pad protruded 0.85 into the stack corners —
// gate catch 2026-07-06.
FLG_Y = [-40, 40];  FLG_Z = 67.4;                    // riser<->flange heat-sets
PAD_Z0 = 64.4; PAD_Z1 = 70.4;
// D456_Y/D456_Z/USB_GROMMET RETIRED 2026-07-07 — head moved fwd onto the neck
// bracket; the camera register + USB-C grommet on this front wall are orphaned
// (USB-C now routes down the neck -> shoulder C-box). Kept commented.
// D456_Y = [-21, -7, 7, 21];  D456_Z = 67.4;   // HEAD camera register row
// USB_GROMMET = [14, 61.5];                     // D456 USB-C front-wall slot
VENT_X0 = -28; VENT_N = 6; VENT_PITCH = 8;           // 3 wide; TWO rows:
VENT_Z = [[52, 14], [33, 12]];  // [z0, height] — upper row at logic level,
                                // LOW row at the under-board buck pocket
                                // (z 6..22 had no airflow; thermal review)

// underslung heat-set bosses: 2.6 tall — bottoms at z 65.3, which caps the
// mezzanine at 63.9 (58 stack + 2.0 floor-boss budget, margin 1.4). Insert
// pressed from BELOW (pull-out direction correct for the mast moment).
BOSS_H = 2.6;
module deck_boss(px, py) {
    translate([px, py, DECK_BOT - BOSS_H]) cylinder(d = 9, h = BOSS_H + EPS);
}
module deck_bore(px, py) {                 // O4 x 6.2 up from boss bottom,
    translate([px, py, DECK_BOT - BOSS_H - EPS]) {  // then O3.4 through
        cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
        cylinder(d = M3_CLEAR, h = DECK_T + BOSS_H + 2 * EPS);
    }
}
module rounded_slot(x0, x1, y0, y1, r) {
    hull() for (px = [x0 + r, x1 - r], py = [y0 + r, y1 - r])
        translate([px, py, DECK_BOT - EPS])
            cylinder(r = r, h = DECK_T + 2 * EPS);
}

module riser_bay() {
    difference() {
        union() {
            // deck plate
            translate([-OUT_X, -OUT_Y, DECK_BOT])
                cube([2 * OUT_X, 2 * OUT_Y, DECK_T]);
            // side skirts (seat rails)
            for (sy = [-1, 1])
                translate([-OUT_X, min(sy * OUT_Y, sy * (OUT_Y - WALL)), SKIRT_BOT])
                    cube([2 * OUT_X, WALL, DECK_BOT - SKIRT_BOT + EPS]);
            // end walls (stop above the plateaus; flange screws clamp them)
            for (sx = [-1, 1])
                translate([min(sx * OUT_X, sx * (OUT_X - WALL)), -OUT_Y, END_BOT])
                    cube([WALL, 2 * OUT_Y, DECK_BOT - END_BOT + EPS]);
            // register tabs hanging from the deck, INSIDE the wall inner
            // faces (0.45 clearance); 2.4 thick — 1.1 clear of the stack
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx * 40 - 8,
                           min(sy * (WALL_IN - CLR_TAB), sy * (WALL_IN - CLR_TAB - 2.4)),
                           26])
                    cube([16, 2.4, DECK_BOT - 26 + EPS]);
            // (head L2-column deck bosses RETIRED 2026-07-07 — the head moved
            //  fwd onto the neck bracket; this riser interface is orphaned.)
            // riser<->flange heat-set pads (both end walls, inward)
            for (sx = [-1, 1], fy = FLG_Y)
                translate([min(sx * (OUT_X - WALL), sx * (OUT_X - WALL - 5)),
                           fy - 6, PAD_Z0])
                    cube([5, 12, PAD_Z1 - PAD_Z0]);
            // (HEAD camera-register strip RETIRED 2026-07-07 — see above.)
        }
        // deck through-features
        // (head L2-column deck bores + the L2 cable drop RETIRED 2026-07-07 —
        //  the L2 pigtail now drops the neck cable slot -> shoulder C-box.)
        rounded_slot(CASE_SLOT[0], CASE_SLOT[1], CASE_SLOT[2], CASE_SLOT[3], 4);
        // case-cradle deck ties (M3 clearance, up from below into the cradle
        // post-base heat-sets — the head hangs below the deck in open space)
        for (t = CRADLE_TIE)
            translate([t[0], t[1], DECK_BOT - EPS])
                cylinder(d = M3_CLEAR, h = DECK_T + 2 * EPS);
        for (p = SMA)
            translate([p[0], p[1], DECK_BOT - EPS])
                cylinder(d = 6.5, h = DECK_T + 2 * EPS);
        // riser<->flange heat-set bores (axis x). Pressed from the PAD's
        // INNER face (reachable from below, pre-mount) so screw tension
        // seats the insert DEEPER — outer-face press was extraction-loaded
        // (design-review fix). O3.4 continues to the outer face. M3x12.
        for (sx = [-1, 1], fy = FLG_Y) {
            translate([sx * (OUT_X - WALL - 5 - EPS), fy, FLG_Z])
                rotate([0, sx * 90, 0])
                    cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
            translate([sx * (OUT_X + EPS), fy, FLG_Z])
                rotate([0, -sx * 90, 0])
                    cylinder(d = M3_CLEAR, h = 8.2 + 2 * EPS);
        }
        // (HEAD D456 camera-register bore row + USB-C grommet RETIRED
        //  2026-07-07 — the head moved fwd onto the neck bracket; the USB-C now
        //  routes down the neck -> shoulder C-box, not through this front wall.)
        // vent slots (both side skirts, two rows)
        for (sy = [-1, 1], i = [0 : VENT_N - 1], v = VENT_Z)
            translate([VENT_X0 + i * VENT_PITCH - 1.5,
                       sy * (OUT_Y - WALL / 2) - (WALL / 2 + EPS), v[0]])
                cube([3, WALL + 2 * EPS, v[1]]);
        // end-plane guard: nothing may protrude past x +/-63.35 — the
        // Ø9 head L2-column bosses at (60, +/-14) poked 1.15 through the
        // flange notch into the head stem lane (gate catch 2026-07-06)
        for (sx = [-1, 1])
            translate([sx > 0 ? OUT_X : -OUT_X - 10, -OUT_Y - 5, 20])
                cube([10, 2 * (OUT_Y + 5), 60]);
    }
}

riser_bay();
