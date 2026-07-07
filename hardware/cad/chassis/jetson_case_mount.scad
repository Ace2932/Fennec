// =============================================================================
// NOVA chassis — JETSON OFFICIAL-CASE CRADLE (deck mount for the sealed case)
// =============================================================================
// Top-level design: docs/design-outline.md (chassis lane). Trunk frame:
// z0 = trunk floor bottom, +x FRONT ("F" arrow), y lateral. Replaces the
// RETIRED bespoke Jetson tray+hood: the heatsink calipered 34.9 (not 21.5),
// so the board+heatsink+fan now live in the OFFICIAL CASE (110.3 x 93.9 x
// 38.2 CALIPERED; ref mesh jetson_case_ref.stl is ~1.2 oversize) which sits
// on the riser deck. See chassis/README "Jetson enclosure decision".
//
// PLACEMENT (place_case.py, the gating study):
//   case long axis || X, PORT END faces REARWARD (-x), heatsink end +x.
//   case world AABB: x -62.0..48.3, y +-46.95, z 71.9..110.1 (sits on deck).
//   rear port end is 1.5 off the rear shoulder wall (x-63.5) — the shoulder
//   flange is the REAR BACKSTOP (no deck exists past -63.35). Front (+x)
//   locates against a thin lip 3.0 shy of the compact mast (flange x51.3).
//
// Jobs:
//   1. LOCATE (shear): a low locating lip (case + 0.4/side) on FRONT (+x)
//      and BOTH SIDES (+-y); the rear shoulder wall backstops -x. Lip kept
//      low (h 9) so the case hex side-vents breathe.
//   2. RETAIN (pull-out, ~250g on a dynamic quadruped): 4 corner posts (in
//      the +-y deck strips) rise to the case top; each caps the case SOLID
//      corner with a slotted M3 hold-down tab. The user drills the 4
//      case-corner TOP faces + sets an M3 heat-set (or nut); M3x10 down
//      through the tab into it pulls the case UP against the tab. Slots
//      absorb the (unverified) exact solid-corner position — see DRILL NOTE.
//   3. TIE TO DECK: each corner post is bolted straight down (M3) into a
//      riser-deck cradle heat-set directly under it. Lift load path:
//      case -> corner heat-set -> tab -> post -> post-base bolt -> deck.
//
// DRILL NOTE (user, PRINTED case): the 4 solid corners take an M3 heat-set
// in the TOP face, ~5.5 in from the end wall AND ~5.5 in from the side wall
// (world centres FRONT (+42.8, +-41.45) / REAR (-56.5, +-41.45)). The slots
// give +-1.5. Verify the solid-corner extent before drilling — the
// honeycomb bottom means only the corner columns are solid.
//
// Print: base-down (deck face on the bed). Corner posts rise in +z; the
// hold-down tabs bridge ~6mm inward at the top (short, self-supporting /
// 45-deg underside). PA6-CF. Prints as ONE piece.
//
// Fit gate: check_fit.py (the case is an AABB envelope there). build_all.sh.

$fn = 48;
EPS = 0.05;

// ---- case placement (calipered; place_case.py) ------------------------------
CX0 = -62.0; CX1 = 48.3;          // case x span (rear port end .. front)
CYH = 46.95;                       // case half-width (y)
CASE_TOP = 110.1;                  // case top z (bottom 71.9 + 38.2)
DECK = 71.9;

// ---- cradle geometry ---------------------------------------------------------
LIP = 0.4;                         // locating clearance per side
WALL = 2.4;                        // locating-lip wall thickness
WALL_H = 9;                        // low lip height (vents breathe above)
FRONT_WALL = 1.8;                  // thinner: only 3.0 to the mast flange
POST_W = 6.0;                      // corner-post square (in the +-y strip)
POST_TOP = CASE_TOP + 2.0;         // 112.1 — caps just above the case top
TAB_T = 3.0;                       // hold-down tab thickness
M3_CLEAR = 3.4;
HEATSET_D = 4.0; HEATSET_L = 6.2;  // Ruthex M3 (deck ties)

IN_X1 = CX1 + LIP;                 // front inner lip face 48.7
IN_Y  = CYH + LIP;                 // side inner lip face  47.35

// hold-down hole centres: ~5.5 inboard of each case corner (DRILL NOTE)
INSET = 5.5;
FRONT_HX = CX1 - INSET;            // 42.8
REAR_HX  = CX0 + INSET;            // -56.5
HY       = CYH - INSET;            // 41.45

// corner-post + deck-tie centres (in the +-y strip, y47.35..53.35 -> ctr ~50.3)
POST_YC = IN_Y + POST_W / 2;       // 50.35
FRONT_PXC = 47.3;                  // post ctr x, front (x44.3..50.3 in strip)
REAR_PXC  = -59.0;                 // post ctr x, rear  (x-62..-56, 1.5 off wall)

module lip_wall(x0, x1, y0, y1) {
    translate([x0, y0, DECK]) cube([x1 - x0, y1 - y0, WALL_H]);
}

// one corner: post in the +-y strip + inward hold-down tab + deck tie
module corner_clamp(front, sy) {
    pxc = front ? FRONT_PXC : REAR_PXC;
    hx  = front ? FRONT_HX : REAR_HX;
    hy  = sy * HY;
    pyc = sy * POST_YC;
    difference() {
        union() {
            // post (6x6 square column, deck -> just over case top)
            translate([pxc - POST_W / 2, pyc - POST_W / 2, DECK])
                cube([POST_W, POST_W, POST_TOP - DECK]);
            // hold-down tab: post top -> inward over the case top corner,
            // ending in a 9x9 cap centred on the hold-down hole
            hull() {
                translate([pxc - POST_W / 2, pyc - POST_W / 2, POST_TOP - TAB_T])
                    cube([POST_W, POST_W, TAB_T]);
                translate([hx - 4.5, hy - 4.5, POST_TOP - TAB_T]) cube([9, 9, TAB_T]);
            }
        }
        // slotted M3 hold-down hole (slot toward the corner; +-1.5 tolerance),
        // centred in the cap with >=3mm material all round
        hull() for (t = [-1.5, 1.5])
            translate([hx + t * (front ? 1 : -1), hy + t * sy,
                       POST_TOP - TAB_T - EPS])
                cylinder(d = M3_CLEAR, h = TAB_T + 2 * EPS);
        // deck tie: M3 UP from under the deck into a heat-set in the POST
        // BASE (keeps the post top free for the case hold-down). Insert
        // pressed into the downward bore before the cradle drops on the deck.
        translate([pxc, pyc, DECK - EPS])
            cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
    }
}

module jetson_case_mount() {
    // FRONT locating lip (thin — 3.0 to the mast flange)
    lip_wall(IN_X1, IN_X1 + FRONT_WALL, -IN_Y - WALL, IN_Y + WALL);
    // SIDE locating lips (+-y), case length up to the front lip
    lip_wall(CX0, IN_X1 + FRONT_WALL, IN_Y, IN_Y + WALL);
    lip_wall(CX0, IN_X1 + FRONT_WALL, -IN_Y - WALL, -IN_Y);
    // 4 corner clamps (each locates + retains + ties to deck)
    corner_clamp(true, 1);  corner_clamp(true, -1);
    corner_clamp(false, 1); corner_clamp(false, -1);
}

jetson_case_mount();

// deck-tie centres exported for riser_bay.scad (keep in sync):
//   FRONT (+47.3, +-50.35)  REAR (-59.0, +-50.35)  -> riser CRADLE_TIE
