// =============================================================================
// CONTROL POD — E-stop (slap-down) + SSD1331 OLED, rear-top of the robot
// =============================================================================
// The tray HOOD is retired (official Jetson case adopted), which orphaned the
// E-stop pod + OLED. This part re-homes them at the REAR-TOP, in the pocket
// BEHIND the riser rear wall (x < -63.35).
//
// The rear is CONGESTED (all mapped by the free-space probe 2026-07-08):
//   * the two REAR SHOULDERS occupy x-63.5, |y|>14, z45..72 — structure at the
//     wall must stay in the CENTRAL y±14 channel;
//   * the mezzanine STACK sits 0.65 mm behind the 3.2 mm riser wall (x>-59.5),
//     so no INNER heat-set boss fits — the riser instead grows OUTER bosses that
//     protrude into the (clear) central pocket, and the pod bolts to their rear
//     faces (x-66.5). riser_bay POD_MOUNT + the guard exception cover this;
//   * the stock TRUNK rear lip fills the low centre (x≈-67, y±5, z40..58);
//   * the rear SHOULDER tops end at z≈80 -> above that the rear is OPEN.
// So: a CENTRAL COLUMN bolts to the riser pocket-bosses (y±10, z61/66); the deck
// cantilevers back over the pocket; the E-stop block hangs at x-87 (front x-71
// clears the boss/trunk lip, rear x-103 clears the shoulder at x-104); the OLED
// rises above the shoulder line (z>80) where it's clear.
//
// Frame = TRUNK frame (+x FRONT, z up).
// E-STOP (mxuteuk 22mm 2NC, HB2-ES544, VERIFIED specs 2026-07-08: Ø22 hole,
//   Ø40 mushroom, 77 total length, panel max 6mm): UP on the deck (z90, 5mm <
//   6mm max OK). The ~30×30 × ~48-deep contact block hangs into the pocket
//   (gussets flank it at y±17); Ø22 barrel through the Ø22.6 hole + supplied nut.
// OLED: SPLIT OFF (#40), then MOVED OFF this part entirely (#35, 2026-08-10).
// It was a separate bracket (oled_mount.scad) bolting
//   to the pod deck's +y edge (2x M2). The pod deck is back to SYMMETRIC (y±26,
//   E-stop only) — no more +y extension, no fused panel, no OLED-beside-mushroom
//   dodge. The OLED bracket holds the SSD1331 clear of the Ø40 mushroom cap.
// CABLE: E-stop NC pair + OLED SPI drop through the column grommet (Ø12, y0 z63,
//   above the trunk lip) -> the matching riser rear-wall slot -> the bay
//   (power-board NC lines + the Arduino Nano SPI). Provision; route at wiring.
// PRINT: PETG-CF (or PA6-CF), **+Z FACE DOWN** (the DECK TOP on the bed); the
//   column and its gussets rise off it. 3 walls / 20% / ~24 g. print 1.
//
// AXIS RESOLVED 2026-08-16 (#383, Aiden's call) — this line said
// "COLUMN-FACE-DOWN (the flat riser-facing face on the bed)", which names a
// FEATURE and no axis, so slice_plate.py refused the part and it sat MANUAL.
// Same failure as shoulder.scad's #259; the lesson there was that the fix has
// to land in BOTH files, because a .scad corrected on its own leaves the
// registry refusing a part that is actually decided.
//
// Measured bed-contact area for each candidate down-face, on the real STL:
//
//     +Z   1662 mm^2   37 mm tall   slenderness 0.91   <-- 4.7x the runner-up
//     -X    356          40                  2.10
//     +X    260          40                  2.46      <-- the face the old
//     +Y    198          52                  3.69          prose actually named
//     -Y    198          52                  3.69
//     -Z     75          37                  4.27
//
// The old prose pointed at the WORST-but-one face: the riser-facing column
// face is +X at 260 mm^2, against 1662 for the deck. On a warp-prone filament
// that is the whole ball game, and it is why this was worth resolving rather
// than leaving to whoever opened the slicer.
//
// THE TRADE, taken knowingly: deck-down puts the O22.6 E-stop bore MOUTH on the
// bed, so elephant-foot pinches it. Enable elephant-foot compensation, and
// check the bore takes the HB2-ES544 barrel before pressing it. The alternative
// was a 260 mm^2 footprint on a 52 mm-tall part, which risks losing the whole
// print rather than one bore mouth.
//
// NOTE: light central 4x M3 mount — the E-stop is a PALM slap, not a hammer; a
// very hard strike may flex the deck (acceptable).

$fn = 48; EPS = 0.05;
M3_CLEAR = 3.4; M2_CLEAR = 2.3;

BOSS_X   = -66.5;                  // riser pocket-boss REAR face (pod bolts here)
COL_X0   = -70.0;                  // column rear face (behind the boss)
COL_HY   = 14;                     // column half-width (clears shoulders at y15)
MOUNT    = [[-10, 61], [10, 61], [-10, 66], [10, 66]];   // (y,z) — matches riser

ES       = [-87, 0];               // E-stop panel-hole center (x,y)
ES_HOLE  = 22.6;                   // Ø22 thread + clearance
DECK_Z   = 90; DECK_T = 5;         // top deck z90..95 (E-stop mounts here)
DECK_X0  = -103; DECK_X1 = -63.35; // deck x-103..-63.35 (over the pocket)
DECK_Y0  = -26; DECK_Y1 = 26;      // deck SYMMETRIC now (OLED split off, #40)

module control_pod() {
    difference() {
        union() {
            // --- central column: bolts to the riser pocket-bosses, rises to deck
            translate([COL_X0, -COL_HY, 58])
                cube([BOSS_X - COL_X0, 2*COL_HY, DECK_Z - 58 + 1]);   // z58..91 (laps deck)
            // --- top deck (E-stop seat + OLED shelf), cantilevered over pocket ---
            translate([DECK_X0, DECK_Y0, DECK_Z])
                cube([DECK_X1 - DECK_X0, DECK_Y1 - DECK_Y0, DECK_T]);
            // --- gussets: stiffen the deck cantilever. Moved OUTBOARD to y17..21
            //     (were y10..14) to FLANK the real ~30mm E-stop contact block
            //     (y±15) hanging below — the block is wider than the old gap.
            //     (E-stop = mxuteuk 22mm 2NC, Ø40 mushroom, 77 total, ~30×48
            //     block behind the panel; specs 2026-07-08.) ---
            for (sy = [-1, 1])
                translate([DECK_X0, sy > 0 ? 17 : -21, 78])
                    cube([BOSS_X - DECK_X0, 4, DECK_Z - 78 + 1]);
        }
        // ---- mount bolt clearances (axis x, through the column into the bosses)
        for (b = MOUNT)
            translate([COL_X0 - EPS, b[0], b[1]]) rotate([0, 90, 0])
                cylinder(d = M2_CLEAR, h = BOSS_X - COL_X0 + 2*EPS);  // M2 (pinched pad)
        // ---- E-stop panel hole ----
        translate([ES[0], ES[1], DECK_Z - EPS]) cylinder(d = ES_HOLE, h = DECK_T + 2*EPS);
        // 2026-08-10 (#35): the 2x M2 heat-sets that used to sit here, at
        // x-96/-71 y23, are GONE. They existed only so oled_mount could bolt
        // to this deck edge, and oled_mount is deleted -- the OLED now mounts
        // FLAT on the rear shoulder deck (oled_tray.scad), looking up. Removing
        // them also retires a known defect: check_hole_breakout recorded both
        // bores as SUSPECT, leaving <=0.2mm of real wall on one side. This part
        // is not printed yet, so nothing drifts from a physical part.
        // ---- cable grommet: E-stop NC + OLED SPI drop into the bay (y0 z63) ----
        translate([COL_X0 - EPS, 0, 63]) rotate([0, 90, 0])
            cylinder(d = 12, h = BOSS_X - COL_X0 + 2*EPS);
    }
}

control_pod();
