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
// OLED (SSD1331 96×64, ~27×20 active): the Ø40 E-stop mushroom cap fouls any
//   panel directly behind it, so the OLED sits BESIDE it — the deck extends to
//   +y48 (above the shoulder line, clear) and a vertical panel there faces -x
//   for an operator behind-right. 4x M2 + a window.
// CABLE: E-stop NC pair + OLED SPI drop through the column grommet (Ø12, y0 z63,
//   above the trunk lip) -> the matching riser rear-wall slot -> the bay
//   (power-board NC lines + the Arduino Nano SPI). Provision; route at wiring.
// PRINT: PETG-CF (or PA6-CF), COLUMN-FACE-DOWN (the flat riser-facing face on the
//   bed); deck + OLED panel rise -> light supports under the deck + OLED. 3 walls
//   / 20% / ~24 g. print 1. NOTE: light central 4x M3 mount — the E-stop is a
//   PALM slap, not a hammer; a very hard strike may flex the deck (acceptable).

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
DECK_Y0  = -26; DECK_Y1 = 48;      // deck asymmetric: +y extension carries the OLED
OLED_X   = -100;                   // OLED panel face (x), beside the mushroom (+y)

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
            // --- OLED panel: VERTICAL, on the +y deck extension beside the
            //     mushroom (y22..46, clear of the Ø40 cap), faces -x ---
            translate([OLED_X, 22, 88]) cube([3.5, 24, 30]);        // z88..118 (laps deck)
        }
        // ---- mount bolt clearances (axis x, through the column into the bosses)
        for (b = MOUNT)
            translate([COL_X0 - EPS, b[0], b[1]]) rotate([0, 90, 0])
                cylinder(d = M2_CLEAR, h = BOSS_X - COL_X0 + 2*EPS);  // M2 (pinched pad)
        // ---- E-stop panel hole ----
        translate([ES[0], ES[1], DECK_Z - EPS]) cylinder(d = ES_HOLE, h = DECK_T + 2*EPS);
        // ---- OLED window + 4x M2 (on the vertical +y panel, x-face) ----
        translate([OLED_X - EPS, 34, 96]) cube([3.5 + 2*EPS, 21, 20]);   // window, ctr y34 z106
        for (my = [-1, 1], mz = [-1, 1])
            translate([OLED_X - EPS, 34 + my*10, 106 + mz*8]) rotate([0, 90, 0])
                cylinder(d = M2_CLEAR, h = 3.5 + 2*EPS);                 // 4x M2 corners
        // ---- cable grommet: E-stop NC + OLED SPI drop into the bay (y0 z63) ----
        translate([COL_X0 - EPS, 0, 63]) rotate([0, 90, 0])
            cylinder(d = 12, h = BOSS_X - COL_X0 + 2*EPS);
    }
}

control_pod();
