// =============================================================================
// OLED MOUNT — SSD1331 display bracket (split off the E-stop pod, #40)
// =============================================================================
// The OLED used to be fused to control_pod (a +y deck extension + a panel that
// dodged the Ø40 mushroom cap). Split off: this small bracket BOLTS to the pod
// deck's +y edge (2× M2 into the pod heat-sets at x-96/-71, y23) and stands a
// panel that FACES -X (rearward) beside + behind the mushroom, readable by an
// operator behind the robot. The pod deck is symmetric again.
// SPI cable (7-wire) drops off the panel back down to the Arduino Nano in the bay.
// World/trunk frame (matches control_pod). PRINT: PETG/PA6-CF, foot-down, ~5 g.
//
// -----------------------------------------------------------------------------
// 2026-07-28 (#35): panel RESIZED to the real board; mount holes REMOVED.
// -----------------------------------------------------------------------------
// The panel was 27 x 26 mm and the SSD1331 module is 27.3 x 30.7 — the board
// overhung the plate it bolts to, on both axes. That was never going to
// assemble, and it is independent of the fault #35 was filed on (2 of the 4
// mount holes opened into the display window, the other 2 breached its edge by
// 0.15 mm).
//
// The 4 board mount holes are now ABSENT, deliberately. The vendor drawing
// gives the outline (27.3 x 30.7), a bottom-centre notch (14 wide, 6.65 in from
// each edge) and Ø2 holes — but NOT the hole PITCH on either axis, and the
// pattern was already flagged as unsourced (dimensions.md: "not standardized;
// many modules have none"). Cutting holes to a guessed pitch is how this part
// got here. They go back in when the owned board is calipered; until then the
// bracket is deliberately not printable, which is the honest state.
//
// STILL NEEDED, from the board in hand:
//   * hole pitch along the 27.3 axis   (mm, centre-to-centre)
//   * hole pitch along the 30.7 axis   (mm, centre-to-centre)
//   * active display area: size AND its offset from the board datum
// The window below is CARRIED OVER at 20 x 16 and re-centred on the new board
// footprint — it is NOT re-derived, because the drawing does not locate the
// glass. Treat it as provisional and fix it in the same caliper session.

$fn = 32; EPS = 0.05; M2_CLEAR = 2.3;

// ---- SSD1331 module, vendor drawing 2026-07-28 ----
BOARD_Y = 27.3;      // board width  -> panel +y axis
BOARD_Z = 30.7;      // board height -> panel +z axis (header up, cable drops)
RIM     = 2.0;       // plate margin around the board, all four sides

// ---- panel geometry (derived, so the board size drives the plate) ----
PANEL_X0 = -99; PANEL_T = 3;                 // 3 mm plate, faces -X
PANEL_Y0 = 26;  PANEL_Y1 = PANEL_Y0 + BOARD_Y + 2 * RIM;   // 26 .. 57.30
PANEL_Z0 = 98;  PANEL_Z1 = PANEL_Z0 + BOARD_Z + 2 * RIM;   // 98 .. 132.70
BOARD_Y0 = PANEL_Y0 + RIM;  BOARD_Z0 = PANEL_Z0 + RIM;

// window: PROVISIONAL (see header) — carried over 20 x 16, centred on the board
WIN_Y = 20; WIN_Z = 16;
WIN_Y0 = BOARD_Y0 + (BOARD_Y - WIN_Y) / 2;
WIN_Z0 = BOARD_Z0 + (BOARD_Z - WIN_Z) / 2;

module oled_mount() {
    difference() {
        union() {
            // foot on the pod deck +y edge (z95..98)
            translate([-99, 22, 95]) cube([30, 5, 3]);
            // panel: vertical, faces -X (rear), on the +y side behind the mushroom
            translate([PANEL_X0, PANEL_Y0, PANEL_Z0])
                cube([PANEL_T, PANEL_Y1 - PANEL_Y0, PANEL_Z1 - PANEL_Z0]);
        }
        // 2x M2 down into the pod deck heat-sets
        for (mx = [-96, -71])
            translate([mx, 23, 95 - EPS]) cylinder(d = M2_CLEAR, h = 3 + 2 * EPS);
        // OLED window (on the -X face). NO board mount holes — see header.
        translate([PANEL_X0 - EPS, WIN_Y0, WIN_Z0])
            cube([PANEL_T + 2 * EPS, WIN_Y, WIN_Z]);
    }
}

oled_mount();
