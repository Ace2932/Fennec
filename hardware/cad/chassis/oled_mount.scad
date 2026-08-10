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
// -----------------------------------------------------------------------------
// 2026-08-09 (#35b): UNBLOCKED — the owned board was calipered 2026-08-08.
// -----------------------------------------------------------------------------
// The three things this file was waiting on are all measured (dimensions.md
// "SSD1331 OLED 0.95in", CALIPERED off the owned board):
//   * hole pitch  26.1 (long axis) x 22.8 (short axis), 2.25 inset all round
//   * aperture    23.3 x 15.8, 2.0 in from each long edge, 5.5 from the TOP
//                 and 9.3 from the BOTTOM -> the display is 1.9 OFF CENTRE,
//                 toward the top. The old 20x16 CENTRED window was wrong twice:
//                 3.3 too narrow (it clipped even the ~20.4 lit region) and
//                 1.95 too low (1.75 of display hidden behind the plate).
//   * depth       glass front -> PCB back 3.4 == BOSS_H below.
//
// MOUNTED FROM BEHIND, and that is forced, not stylistic. An M2 pan head
// (DIN 7985, O3.8) reaches 4.15 in from a hole centre, but the glass starts
// only 2.0 from each long edge -- a front-side screw head fouls the display no
// matter how it is centred. So: panel in front carrying the window, board
// behind it, four bosses on the panel's REAR face, screws entering from behind
// the board into heat-sets in those bosses. Heads bear on the PCB back and
// never touch the front face, and it pulls the board flat against the window.
//
// Header pins protrude perpendicular from the BACK (calipered), i.e. into the
// cable space behind the board -- so the panel needs no relief notch.

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

// ---- SSD1331 module, CALIPERED 2026-08-08 (supersedes the vendor drawing) ----
BOARD_Y = 27.3;      // board width  -> panel +y axis  (calipered 27.3)
BOARD_Z = 30.7;      // board height -> panel +z axis (header up, cable drops)
                     // calipered 30.6; the 0.1 is kept so the plate/RIM maths
                     // below is unchanged. Hole PITCH is used directly rather
                     // than derived from this, so the 0.1 cannot reach a hole.
RIM     = 2.0;       // plate margin around the board, all four sides

// Board mount pattern, CENTRED on the board and driven by the measured PITCH
// (not by inset-from-edge), so the 30.6-vs-30.7 discrepancy above cannot move
// a hole. Both pitches independently imply the same 2.25 inset, which is what
// made the axis assignment provable rather than a guess (dimensions.md).
HOLE_PITCH_Y = 22.8;   // across the 27.3 axis
HOLE_PITCH_Z = 26.1;   // along  the 30.6 axis
BOSS_D  = 5.0;         // 1.0mm wall around the O3.0 insert bore -- the minimum
                       // fastener-schedule.md:5 allows for M2. Not larger: at
                       // the TOP row the boss OD is only 0.8mm clear of the
                       // window edge, and O5.5 would cut that to 0.55.
BOSS_H  = 3.4;         // calipered glass-front -> PCB-back. Sets the standoff.
M2_INS_D = 3.0; M2_INS_L = 4.0;   // Ruthex M2 (same as jetson_case_mount)

// ---- panel geometry (derived, so the board size drives the plate) ----
PANEL_X0 = -99; PANEL_T = 3;                 // 3 mm plate, faces -X
PANEL_Y0 = 26;  PANEL_Y1 = PANEL_Y0 + BOARD_Y + 2 * RIM;   // 26 .. 57.30
PANEL_Z0 = 98;  PANEL_Z1 = PANEL_Z0 + BOARD_Z + 2 * RIM;   // 98 .. 132.70
BOARD_Y0 = PANEL_Y0 + RIM;  BOARD_Z0 = PANEL_Z0 + RIM;

// Window: the MEASURED aperture, positioned by its measured BORDERS. Not
// centred -- the display sits 1.9 high on the board, so centring it is the bug
// that hid 1.75mm of screen behind the plate.
WIN_Y = 23.3; WIN_Z = 15.8;
WIN_Y0 = BOARD_Y0 + 2.0;    // 2.0 in from each long edge (2.0+23.3+2.0 = 27.3)
WIN_Z0 = BOARD_Z0 + 9.3;    // 9.3 from the BOTTOM edge (9.3+15.8+5.5 = 30.6)

// Hole centres, derived once and reused by both the bosses and their bores.
HOLE_Y = [BOARD_Y0 + BOARD_Y/2 - HOLE_PITCH_Y/2,
          BOARD_Y0 + BOARD_Y/2 + HOLE_PITCH_Y/2];
HOLE_Z = [BOARD_Z0 + BOARD_Z/2 - HOLE_PITCH_Z/2,
          BOARD_Z0 + BOARD_Z/2 + HOLE_PITCH_Z/2];

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
            // 4 board-standoff bosses on the panel's REAR face (+x side), so
            // the board hangs behind the window and the screws come in from
            // behind it. Axis is +x, i.e. normal to the panel.
            for (hy = HOLE_Y, hz = HOLE_Z)
                translate([PANEL_X0 + PANEL_T, hy, hz])
                    rotate([0, 90, 0]) cylinder(d = BOSS_D, h = BOSS_H);
        }
        // 2x M2 down into the pod deck heat-sets
        for (mx = [-96, -71])
            translate([mx, 23, 95 - EPS]) cylinder(d = M2_CLEAR, h = 3 + 2 * EPS);
        // OLED window (on the -X face), measured aperture.
        translate([PANEL_X0 - EPS, WIN_Y0, WIN_Z0])
            cube([PANEL_T + 2 * EPS, WIN_Y, WIN_Z]);
        // M2 heat-set bores, entering each boss from its REAR face and running
        // toward the panel. Blind: 3.4 boss + 3.0 panel = 6.4 available, bore
        // 4.0 deep, so 2.4mm of panel is left in front of the insert -- above
        // the >=1.5mm blind-floor convention #70 was filed about. NOT through:
        // a through-bore here would open onto the display face.
        // rotate([0,-90,0]) -> the bore runs in -X, INTO the boss and toward the
        // panel. [0,+90,0] (which the bosses correctly use, since they stand
        // OFF the rear face) points +X and put these bores entirely in free
        // air behind the part -- rendered fine and left the mesh solid.
        for (hy = HOLE_Y, hz = HOLE_Z)
            translate([PANEL_X0 + PANEL_T + BOSS_H + EPS, hy, hz])
                rotate([0, -90, 0]) cylinder(d = M2_INS_D, h = M2_INS_L + EPS);
    }
}

oled_mount();
