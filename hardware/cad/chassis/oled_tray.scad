// =============================================================================
// OLED TRAY — SSD1331 flat on the REAR SHOULDER's top deck (#35)
// =============================================================================
// PRINT: PETG-CF, BEZEL-FACE-DOWN (+Z on the bed) — zero supports.
//   Every feature on this part hangs off ONE face: the four legs stand off the
//   bezel underside and nothing protrudes from the top. Bezel-top-down therefore
//   puts all of it pointing UP, and the measured unsupported area is 0.0 mm^2.
//   *** Do not add anything to the top face. *** A revision that put the insert
//   bosses up there was measured and REJECTED for exactly this: features on two
//   faces means one set becomes a large elevated plane on four point contacts,
//   whichever way it goes on the bed.
//
// WHY THIS EXISTS. `oled_mount` (DELETED 2026-08-10, this part replaced it)
// bolted the display to control_pod's deck +y EDGE, and measured, that was a
// cantilever on a cantilever:
//   * the panel occupies y26..57.3 while the pod deck ends at y=26 -> 100% of
//     the plate hangs past the edge;
//   * control_pod (x-103..-63.4) itself overhangs riser_bay (ends x-66.5).
// It also lands 1.36 mm from the E-stop mushroom -- against a Ø40 that is a
// VENDOR-PAGE number nobody has calipered (dimensions.md marks the cap
// ⬜ CALIPER NEEDED; it interferes above Ø42.7) -- and its near bolt has only
// Ø5 of driver access because the panel wall stands 3 mm away.
//
// This tray RETIRES that caliper dependency rather than inheriting it. The cap
// is centred at x=-87 (control_pod.scad ES) and this plate starts at x=-113, so
// the rim would have to reach Ø52 to touch it: Ø40 -> 6.00mm gap, Ø42.7 -> 4.65,
// Ø45 -> 3.50. oled_mount failed above Ø42.7; this part does not care.
//
// WHY THE TOP DECK AND NOT THE WEB BETWEEN THE LEGS. There IS a wall between
// the rear hips (X≈-112.5, Y ±40, Z 14..70) and it is the obvious place. The
// rear legs sweep it, low down: worst usable width over the gated haa range
// (-40..+15) is 4.4 mm at Z 14..21, and only reaches the needed 31.3 mm above
// Z 42 -- leaving a 28 mm clear band for a 34.7 mm panel. Short by ~7 mm, and
// landscape does not help (it then needs 34.7 of WIDTH where 31 exists).
//
// The top deck has no such problem. MEASURED min clearance from the legs to
// this part, over the FULL mechanical range (hfe -86..+86 in 4 deg steps, kfe
// -109..+109 in 23 steps INCLUDING the endpoints, haa -40..+40, all four hips):
// see check_fit.py's printed number, which is the authority and is
// negative-controlled (widen this plate to y +-75 and it goes to 0.00 and red).
//
// CAUTION for anyone revisiting this. "The legs stay below the deck" is FALSE
// and I asserted it first: past about |hfe| 35 the rear leg swings up through
// z=170, far above the 79.55 deck. It misses this tray in Y, not in Z -- the
// leg is out at |y| ~ 39 and the plate stops at 26. So a clearance argument
// here MUST be 3D. The first version of the gate compared z alone and reported
// a 96 mm intersection that does not exist.
//
// AND THE HOLES ALREADY EXIST. shoulder.scad's NECK_HS_XY puts four M3x3.8
// heat-set bores in the deck top for the NECK BRACKET on the FRONT shoulder.
// The same part is printed twice, so on the REAR shoulder all four are unused.
// Verified in the mesh by contiguous solid runs (not min/max, which is how the
// same measurement lied twice on the way here): bore 4.3 deep, 2.1 mm floor,
// full 6.3 mm deck 4 mm away. So this part costs four heat-sets and no reprint
// of a load-bearing member.
//
// -----------------------------------------------------------------------------
// NO BOSSES — and that is the whole point of this revision.
// -----------------------------------------------------------------------------
// The first version hung four Ø5.0 x 3.4 bosses under the bezel to host the M2
// inserts, copying oled_mount's
//     BOSS_H = 3.4;  // calipered glass-front -> PCB-back. Sets the standoff.
// That one line conflates the board's THICKNESS with its STANDOFF, and both
// files then claimed the screws "pull the board flat against the window". They
// cannot. A Ø5.0 boss does not enter a ~Ø2.2 M2 clearance hole, so the board
// seats ON THE BOSS TIPS and stands off by BOSS_H. Measured: a board placed
// flush put 10150 of 200000 sampled surface points INSIDE the tray solid, ~2500
// at each boss. Consequences were a 6.40 mm well over the display and only
// 3.20 mm of cavity under the PCB -- half what the header claimed.
//
// The boss only ever existed because a 4.0 insert plus a 1.5 blind floor needs
// 5.5 mm and the plate was 3.0. So: make the plate 5.5 and delete the boss. The
// bore now lives in the plate, the underside is FLAT, and the board bears on
// the window rim (2.0 mm of border on each long edge -- a picture-frame contact
// on the glass surround, which is how every panel bezel does it).
// oled_mount carried the same bug and was DELETED rather than fixed (#35):
// there is one display, and this part is the better mount on every measured
// criterion. control_pod's 2x M2 heat-sets that served it went with it --
// which also retired a <=0.2mm wall that check_hole_breakout had flagged.

// FASTENERS — derived, not guessed. This project has already paid for a
// "MEASURED" fastener spec that bottomed out (HFE retention M3x22 into a 16.8mm
// span), so the arithmetic is written down:
//
//   deck screw: through LEG_H 10.5 + PLATE_T 5.5 = 16.0mm of tray, then into
//   shoulder.scad's NECK_HS (M3x3.8 insert in a 4.2-deep bore).
//     M3x16  -> 0.0mm  never reaches the insert
//     M3x18  -> 2.0mm engagement (0.67xD)
//     M3x20  -> 4.0mm engagement (1.33xD), still 0.2 clear of the bore floor
//               *** USE THIS ***
//     M3x22  -> 6.0mm into a 4.2 bore   BOTTOMS OUT, do not fit
//
//   board screw: M2x6 from BELOW through the PCB into the M2x4 inserts. The
//   screw crosses the CALIPERED glass-front -> PCB-back depth of 3.4
//   (dimensions.md:561) before it reaches the insert, so engagement is
//   6 - 3.4 = 2.6mm (1.30xD). M2x8 engages 4.6 into a 4.0 bore and BOTTOMS OUT.
//   PCB thickness is NOT needed for this and was never the blocker.
//
// CAVITY: 7.10 mm from the PCB back face down to the deck, and it CLEARS on
// measured numbers, not assumed ones. The back-side depths were calipered in
// the same 2026-08-08 session as the outline: dimensions.md:559 glass-front ->
// TALLEST BACK COMPONENT (excl. pins) = 4.8, :561 glass-front -> PCB-back = 3.4.
// So the back components stand 4.8 - 3.4 = 1.4 proud of the PCB, and against
// 7.10 that leaves *** 5.70 mm clear ***.
//
// The only unmeasured part is the header PIN protrusion, and it cannot bottom:
// the 7-pin header is at the board's -X edge (x=-146.85) and the deck's own
// opening is OPEN THROUGH its full 6.5 mm thickness there (probed Y -13..+13,
// all clear), so the pins hang through the deck rather than into the cavity.
//
// An earlier revision of this header called the back-side height "uncalipered".
// That was wrong -- it was on record the whole time.

$fn = 48; EPS = 0.05;

// ---- mount: the rear shoulder's four UNUSED neck-bracket bores -------------
// shoulder-local NECK_HS_XY [[20,-24.2],[-20,-24.2],[19.5,4.8],[-19.5,4.8]] at
// DECK_Z1=41.5, mapped through check_fit's rear S2T (X = -sy-141.2, Y = sx,
// Z = sz+38.05). The two rows are NOT the same |Y| -- 20.0 vs 19.5 -- so they
// are listed out rather than mirrored, which would silently move a hole.
BOLT = [[-146.0,  19.5], [-146.0, -19.5],
        [-117.0,  20.0], [-117.0, -20.0]];
DECK_Z = 79.55;                  // shoulder deck top in trunk frame
M3_CLEAR = 3.4;

// ---- stack ----------------------------------------------------------------
// LEG_H is the standoff between the deck and the bezel UNDERSIDE -- i.e. the
// cavity the board hangs in. (Nothing to do with the robot's legs; it is the
// four printed posts.) 10.5 is chosen with PLATE_T so the deck screw lands on a
// stock M3x20 at 1.33xD -- see FASTENERS above.
LEG_H   = 10.5;
PLATE_T = 5.5;                   // 4.0 insert + 1.5 blind floor. NOT arbitrary.
PLATE_Z = DECK_Z + LEG_H;        // bezel underside 90.05, top 95.55
LEG_W   = 7.0;                   // square leg; 3.4 clear needs >=1.8 wall

// ---- SSD1331, CALIPERED 2026-08-08 ----------------------------------------
BOARD_X = 30.7;    // the 30.6 axis runs FORE-AFT
BOARD_Y = 27.3;    // the 27.3 axis runs LATERAL
CX = -131.5;       // board centre = bolt-rectangle centre ((-146 + -117)/2)
CY = 0;
HOLE_PITCH_X = 26.1;   // along the 30.6 axis
HOLE_PITCH_Y = 22.8;   // across the 27.3 axis
M2_INS_D = 3.0; M2_INS_L = 4.0;   // Ruthex M2, same as jetson_case_mount

// Window from the MEASURED borders, not centred: the display sits 1.9 off
// centre toward the header edge. Header points -X so the 7-pin cable drops
// through the deck's own central opening (shoulder-local |sx|<15, sy -11..9
// -> trunk X -150.2..-130.2, Y ±15) instead of routing around an edge.
WIN_X = 15.8; WIN_Y = 23.3;
BX0 = CX - BOARD_X/2;                 // -146.85, the header (-X) edge
WIN_X0 = BX0 + 5.5;                   // 5.5 border on the header side
WIN_Y0 = CY - WIN_Y/2;                // 2.0 in from each long edge

HOLE_X = [CX - HOLE_PITCH_X/2, CX + HOLE_PITCH_X/2];
HOLE_Y = [CY - HOLE_PITCH_Y/2, CY + HOLE_PITCH_Y/2];

// bezel: covers every bolt (X -146..-117, Y ±20) with margin, and the board
PLATE_X0 = -150.0; PLATE_X1 = -113.0;
PLATE_Y0 =  -26.0; PLATE_Y1 =   26.0;

module oled_tray() {
    difference() {
        union() {
            // bezel
            translate([PLATE_X0, PLATE_Y0, PLATE_Z])
                cube([PLATE_X1-PLATE_X0, PLATE_Y1-PLATE_Y0, PLATE_T]);
            // four legs down to the deck, one per existing heat-set
            for (b = BOLT)
                translate([b[0]-LEG_W/2, b[1]-LEG_W/2, DECK_Z])
                    cube([LEG_W, LEG_W, LEG_H + EPS]);
        }
        // M3 clearance straight through leg AND bezel: the screw drops in from
        // above, head lands on the bezel top, and threads into the deck's
        // existing insert. Keeps all four fasteners reachable from outside --
        // the failure oled_mount had, where the panel wall left Ø5.
        for (b = BOLT)
            translate([b[0], b[1], DECK_Z - EPS])
                cylinder(d = M3_CLEAR, h = LEG_H + PLATE_T + 2*EPS);
        // display window through the bezel
        translate([WIN_X0, WIN_Y0, PLATE_Z - EPS])
            cube([WIN_X, WIN_Y, PLATE_T + 2*EPS]);
        // M2 heat-set bores, entering the plate from BELOW (the board side) and
        // running UP into it. Blind: 4.0 of bore in 5.5 of plate leaves a 1.5mm
        // floor, the minimum the blind-pocket convention allows (#70). NOT
        // through: that would open onto the display face. The board mounts from
        // behind because an M2 pan head reaches 4.15 from a hole centre while
        // the glass starts 2.0 in from each long edge -- a screw entering from
        // the display side fouls the glass however it is centred.
        for (hx = HOLE_X, hy = HOLE_Y)
            translate([hx, hy, PLATE_Z - EPS])
                cylinder(d = M2_INS_D, h = M2_INS_L + EPS);
    }
}

oled_tray();
