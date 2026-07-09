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
// CASE ORIENTATION (user-confirmed 2026-07-08):
//   * long axis || X (~110), fan/vent lid UP;
//   * the removable SLIDE-ON BEZEL is the +Y face = robot's LEFT flank (the
//     board-access panel; measured FLUSH at y46.95 -> the +Y locating lip
//     clears it, no change needed);
//   * PORTS / I-O are on the -Y face = robot's RIGHT flank -> cables exit -Y
//     (sideways), NOT the rear end (see #38 / cable routing);
//   * the case is ASSEMBLED OFF-ROBOT (bezel on) then DROPPED into the cradle
//     -> the cradle only has to CLEAR + RETAIN a finished closed box. (The bezel
//     can't come off in place anyway: the front lip + rear shoulder wall block
//     any fore-aft slide -> service = pull the case, off the 4 clamps.)
//   * case world AABB x -62.0..48.3, y +-46.95, z 71.9..110.1 (peak). The top
//     is FACETED: the SOLID CORNER COLUMNS top out at z ~102.8 (MEASURED), the
//     central fan/vent peak at ~110.1. Retention grabs the corners (102.8).
//
// REWORK 2026-07-08 (backlog #33/#34/#38 — the old 4 fixed corner tabs were
//   (a) set to the PEAK z110.1 so they floated ~6.3 above the real corners
//   = zero hold-down, and (b) fixed + inward-overhanging so the case couldn't
//   be dropped in). New scheme:
//   1. LOCATE (shear): low lips (case + 0.4/side) on FRONT (+x) + the +Y side;
//      the -X rear shoulder wall backstops; the -Y side is LEFT OPEN (short end
//      stubs only) for the port cables. Lip h9 so the hex vents breathe.
//   2. RETAIN (lift/tumble, ~250-510 g): 4 corner UPRIGHTS in the +-y strips
//      rise to the real corner height (z102.8), each with a VERTICAL M3
//      heat-set in its top. After the case DROPS IN (uprights are outboard in
//      y -> nothing overhangs, straight drop), 2 REMOVABLE CLAMP BARS
//      (jetson_clamp_bar.scad, #44 — one per ±y side, each spans its 2 uprights
//      + 2x M2 down) bolt DOWN into the upright tops and cap the case's solid
//      corner columns. NO case drilling (bear-only); add a TPU/EVA shim on the
//      bar pads for preload + damping. Lift path: case corner -> bar -> upright
//      -> deck-tie(M2) -> riser deck.
//   3. TIE TO DECK: each upright bolts straight down (M3) into a riser-deck
//      cradle heat-set under it (riser CRADLE_TIE — keep in sync).
//
// ASSEMBLY: press the upright BASE heat-sets (from below) + TOP heat-sets (from
//   above) -> bolt the cradle to the deck -> drop the assembled case in -> set
//   the 2 clamp bars + 4x M2x8 down into the upright tops. Bezel is already on.
// Print: base-down (deck face on the bed); uprights rise (no overhangs now).
//   PA6-CF, ONE piece. Bars print separately (jetson_clamp_bar.scad, x2, flat).
//
// Fit gate: check_fit.py (the case is an AABB envelope there). build_all.sh.

$fn = 48;
EPS = 0.05;

// ---- case placement (calipered; place_case.py) ------------------------------
CX0 = -62.0; CX1 = 48.3;          // case x span (rear .. front)
CYH = 46.95;                       // case half-width (y)
CASE_PEAK = 110.1;                 // fan/vent peak z (reference only)
CORNER_Z  = 102.8;                 // MEASURED solid corner-column top = clamp seat
DECK = 71.9;

// ---- cradle geometry ---------------------------------------------------------
LIP = 0.4;                         // locating clearance per side
WALL = 2.4;                        // locating-lip wall thickness
WALL_H = 9;                        // low lip height (vents breathe above)
FRONT_WALL = 1.8;                  // thinner: only 3.0 to the mast flange
POST_W = 6.0;                      // corner-post square (in the +-y strip)
POST_TOP = CORNER_Z;               // 102.8 — uprights end AT the real corner top
M3_CLEAR = 3.4;
HEATSET_D = 4.0; HEATSET_L = 6.2;  // Ruthex M3 (deck ties — structural)
// The 6mm uprights can't give an M3 insert (OD4.6) its >=1.5mm wall, so the
// LIGHT hold-downs (clamps + cowl) use M2 inserts (OD3.2 -> 1.4mm wall in a 6mm
// post). M2 is plenty for a bear-only clamp + a fall-shield. (fastener audit)
M2_HD = 3.0; M2_HL = 4.0;          // Ruthex M2 insert bore + length

IN_X1 = CX1 + LIP;                 // front inner lip face 48.7
IN_Y  = CYH + LIP;                 // side inner lip face  47.35

// corner-column (clamp BEARING) centres: ~5.5 inboard of each case corner
INSET = 5.5;
FRONT_HX = CX1 - INSET;            // 42.8
REAR_HX  = CX0 + INSET;            // -56.5
HY       = CYH - INSET;            // 41.45

// corner-post + deck-tie centres (in the +-y strip, y47.35..53.35 -> ctr 50.35)
POST_YC = IN_Y + POST_W / 2;       // 50.35
FRONT_PXC = 47.3;                  // post ctr x, front
REAR_PXC  = -59.0;                 // post ctr x, rear (1.5 off the shoulder wall)

module lip_wall(x0, x1, y0, y1) {
    translate([x0, y0, DECK]) cube([x1 - x0, y1 - y0, WALL_H]);
}

COWL_BOLT_Z = 85;   // -y cowl bolts into the -y uprights at this z

// one corner UPRIGHT: post (deck -> corner height) + top heat-set (clamp bolt)
// + base heat-set (deck tie). NO fixed tab — the removable clamp caps the case.
// The two -Y uprights also get a -y-face heat-set for the bolt-on cable cowl.
module upright(front, sy) {
    pxc = front ? FRONT_PXC : REAR_PXC;
    pyc = sy * POST_YC;
    difference() {
        translate([pxc - POST_W / 2, pyc - POST_W / 2, DECK])
            cube([POST_W, POST_W, POST_TOP - DECK]);
        // clamp heat-set — M2, pressed from the TOP (M2 down through the clamp)
        translate([pxc, pyc, POST_TOP - M2_HL])
            cylinder(d = M2_HD, h = M2_HL + EPS);
        // deck tie heat-set — M2, pressed from BELOW the deck (the 6mm post
        // can't wall an M3; the cradle+case are light -> M2 has huge margin)
        translate([pxc, pyc, DECK - EPS])
            cylinder(d = M2_HD, h = M2_HL + EPS);
        // -Y cowl heat-set — M2, pressed from the -y FACE (jetson_cowl bolts here)
        if (sy < 0)
            translate([pxc, pyc - POST_W / 2 - EPS, COWL_BOLT_Z]) rotate([-90, 0, 0])
                cylinder(d = M2_HD, h = M2_HL + EPS);
    }
}

module jetson_case_mount() {
    // FRONT locating lip (thin — 3.0 to the mast flange)
    lip_wall(IN_X1, IN_X1 + FRONT_WALL, -IN_Y - WALL, IN_Y + WALL);
    // +Y locating lip (full length)
    lip_wall(CX0, IN_X1 + FRONT_WALL, IN_Y, IN_Y + WALL);
    // -Y tie-rail: ties the two -y uprights into one body, OUTBOARD of the
    // CASE_SLOT (y-52..-55, over the skirt) so it does NOT block the cable drop.
    // The -Y CABLE COWL is now a SEPARATE bolt-on part (jetson_cowl.scad) — so
    // you plug the straight cables FIRST (full access), THEN bolt the cowl to the
    // -y uprights' -y-face heat-sets (COWL_BOLT_Z). #38.
    translate([CX0, -53.35, DECK]) cube([IN_X1 + FRONT_WALL - CX0, 1.35, 3]);  // y-53.35..-52
                                          // (outboard edge y-53.35 = the -y upright
                                          //  face so it doesn't poke into the bolt-on
                                          //  cowl seat; inboard clear of the CASE_SLOT)
    // 4 corner uprights (locate + retain via the removable clamps + tie to deck)
    upright(true, 1);  upright(true, -1);
    upright(false, 1); upright(false, -1);
}

jetson_case_mount();

// deck-tie centres exported for riser_bay.scad (keep in sync):
//   FRONT (+47.3, +-50.35)  REAR (-59.0, +-50.35)  -> riser CRADLE_TIE
