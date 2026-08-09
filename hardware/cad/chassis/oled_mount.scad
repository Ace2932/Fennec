// =============================================================================
// OLED MOUNT — SSD1331 display bracket (split off the E-stop pod, #40)
// =============================================================================
// The OLED used to be fused to control_pod (a +y deck extension + a panel that
// dodged the Ø40 mushroom cap). Split off: this small bracket BOLTS to the pod
// deck's +y edge (2× M2 into the pod heat-sets at x-96/-71, y23) and stands a
// panel that FACES -X (rearward) beside + behind the mushroom, readable by an
// operator behind the robot. The pod deck is symmetric again.
// SPI cable (7-wire) drops off the panel back down to the Arduino Nano in the bay.
// World/trunk frame (matches control_pod).
// PRINT: OPEN ITEM (#184) — not a directive this file can state yet. The part
//   is deliberately UNPRINTABLE right now (see below: no board mount holes
//   until #35's caliper session lands). The old note here, "PETG/PA6-CF,
//   foot-down, ~5 g", was never a real answer either: "PETG/PA6-CF" names two
//   materials, and "foot-down" names a feature, not an axis. Both are still
//   open once #35 lands. slice_plate.py carries the full reasoning under
//   UNRESOLVED["oled_mount"]; do not resolve either one here by guessing.
//
// -----------------------------------------------------------------------------
// 2026-08-08 (#35 defect a / #281): pod-foot M2 holes were breaking out of
//   the -y edge (1.0mm to the edge against an r=1.15 bore -- 0.15mm open,
//   28% of the wall per check_hole_breakout.py). Fixed with two local tabs
//   under the holes (FOOT_TAB_* below) rather than moving the holes -- their
//   position is fixed by control_pod's heat-sets -- or widening the whole
//   foot, which would have eaten the mushroom dodge. See the FOOT_TAB_Y0
//   comment for the numbers. Defect (b) below (display-window holes) is
//   UNCHANGED -- still genuinely blocked on the caliper session.
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

// ---- pod-foot M2 holes (#281/#35b): breakout fix ----
// Foot was a flat 30x5x3 pad (x-99..-69, y22..27) with 2x M2 holes at y23 --
// 1.0mm from the y22 edge against an r=1.15 clearance bore, so each bore
// opened ~0.15mm past the face (28% of its wall, check_hole_breakout.py).
// fastener-schedule.md:7 -- M2 wants >=1.0mm real wall around a hole, so the
// wall needs to reach y <= 23 - 1.15 - 1.0 = 20.85. Hole positions are FIXED
// (mate into control_pod's heat-sets at x-96/-71, y23 -- fastener-schedule.md
// row "OLED bracket -> pod deck"), so the fix is more pad, not moved holes.
// Extending the WHOLE foot's -y edge would bring it within ~0.5mm of
// control_pod's Ø40 E-stop mushroom (center x-87, y0, r20) at x=-87 --
// the part was deliberately drawn with a 2mm dodge there (foot was y22 =
// mushroom r20 + 2mm). Instead: two LOCAL tabs, one per hole. The holes
// sit 9mm/16mm off the mushroom's x-87 center line, so even reaching
// FOOT_TAB_Y0 the nearest tab corner clears the mushroom circle by
// 1.4mm/4.3mm (measured by hand, see PR body) -- the original dodge at
// x=-87 is untouched.
FOOT_TAB_Y0 = 20.5;    // wall = 23 - 1.15 - 20.5 = 1.35mm (>= the 1.0mm rule)
FOOT_TAB_HW = 3;       // tab half-width in x, hole +-3mm

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
            // local tabs under each M2 hole (breakout fix, see FOOT_TAB_* above)
            for (mx = [-96, -71])
                translate([mx - FOOT_TAB_HW, FOOT_TAB_Y0, 95])
                    cube([2 * FOOT_TAB_HW, 22 - FOOT_TAB_Y0, 3]);
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
