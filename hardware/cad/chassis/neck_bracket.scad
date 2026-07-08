// =============================================================================
// NOVA chassis — NECK BRACKET: front-shoulder-deck adapter for the fwd HEAD
// =============================================================================
// Head re-architecture 2026-07-07 (docs/head-rearchitecture-plan.md). The head
// moves OFF the riser front and FORWARD onto the FRONT-SHOULDER top (the
// "neck"), projecting ahead like a fox. Interface = this SEPARATE bracket
// (user call): the shoulder stays ONE gate-clean print-2-identical part; the
// head stays a modular removable unit; the bolted joint is the cantilever weak
// point, so it is a TALL rear vertical bolt face (good pitch couple), NOT a
// thin neck.
//
// Placement study: forward_head_study.py -> DX+73 DZ+6 from the riser head:
//   L2 crown center x126.5 (optical z~160); D456 back-face (143,0,111.5), 27deg
//   down, body x136.4..172.7 z86.8..124.4 y+-61.9.
//
// FRAME: trunk (+x FRONT, z up). Front-shoulder deck TOP = z79.55, spans
//   x109..158, y+-59.4. Occupied deck zones the bracket MUST avoid:
//     * horn-plate TOP FLANGES  x143..158, y+-23..55, z79.55..82.75 (legs)
//     * horn-plate heat-sets    x147/156, y+-27/+-51
//     * deck lightening window  x127..153, y+-16 (open to the C-box below)
//   Free deck-solid the bracket bolts to: the CENTER SPINE y+-21 (between the
//   window y16 and the horn flanges y23), rear band x109..127.
//
// CANTILEVER (study): nothing may sit ABOVE z86.8 forward of x136 (D456 body).
//   So the head-mount face lives REARWARD of the camera, under the L2 crown.
//
// MOUNT SCHEME (mirrors the retired riser wall-row, proven):
//   - BASE PLATE flat on the deck (z79.55..83.55); bolts DOWN through the deck
//     at 4 corners = drill O3.4 at first assembly, M3 + washer + NYLOC on the
//     underside (reached through the deck window + open trunk-end aperture,
//     BEFORE the riser goes on) — the accepted flange-foot / battery-sandwich
//     practice. NO shoulder-mesh change -> shoulder stays gate-clean.
//   - REAR VERTICAL FACE at x121 rising z83.55..106, 4x M3 HEAT-SETS (from its
//     rear face); the head's rear boss bolts FROM BEHIND into them (M3x14).
//     Tall bolt rectangle (z89 & z100, y+-11) resists the fwd-tipping moment.
//   - GUSSETS fore+aft tie the face to the base plate.
// PRINT: base-down (deck face on the bed); the wall + gussets rise. PA6-CF.
//   4mm walls. No overhangs needing support beyond the gusset undersides.

$fn = 64;
EPS = 0.05;
M3_CLEAR = 3.4;
HEATSET_D = 4.0;   // M3 brass heat-set OD (leg_v6: 4.0 pilot)
HEATSET_L = 6.0;

DECK_TOP = 79.55;

// ---- base plate on the deck (center spine, clears window + horn flanges) ----
BASE = [107, 150, -21, 21];       // x0 x1 y0 y1
BASE_T = 4;                        // z79.55..83.55
// deck-through bolts: drill-at-assembly M3, nyloc below. In the y+-20 solid
// spine, clear of the window (y16) + horn bores (y>=27). Fore-aft span 36;
// front pair pulled inboard/rearward of the horn+servo cluster for wrench
// access to the underside nyloc.
BOLT_XY = [[110, 20], [110, -20], [146, 19], [146, -19]];

// ---- rear vertical mount face (the head bolts to this) ----------------------
WALL_X0 = 113; WALL_X1 = 121;     // 8mm face (front x121): holds M3 heat-sets
WALL_Y  = 16;                      // half-span
WALL_Z0 = 79.55; WALL_Z1 = 106;   // rises from the deck to under the L2 body
HM_Z    = [89, 100];               // bolt rows (tall couple vs the fwd moment)
HM_Y    = 11;                      // bolt half-span

module gusset(x_apex, z_apex, x_base0, x_base1, y0, y1) {
    // wedge in the x-z plane, extruded across y
    hull() {
        translate([x_base0, y0, DECK_TOP]) cube([x_base1 - x_base0, y1 - y0, EPS]);
        translate([x_apex, y0, z_apex - EPS]) cube([EPS, y1 - y0, EPS]);
    }
}

module neck_bracket() {
    difference() {
        union() {
            // base plate on the deck
            translate([BASE[0], BASE[2], DECK_TOP])
                cube([BASE[1] - BASE[0], BASE[3] - BASE[2], BASE_T]);
            // rear vertical mount face
            translate([WALL_X0, -WALL_Y, WALL_Z0])
                cube([WALL_X1 - WALL_X0, 2 * WALL_Y, WALL_Z1 - WALL_Z0]);
            // AFT gusset: wall base -> rear of base plate. This is the load-
            // bearing one — it + the base-bolt couple react the head's forward-
            // tipping moment. (No FORE gusset: the head BOSS occupies x121..133
            // from z84 up, so any bracket web forward of the wall would collide
            // it — the base plate alone bridges the deck window there.)
            gusset(WALL_X0, WALL_Z1 - 6, 107, WALL_X0 + EPS, -WALL_Y, WALL_Y);
            // side webs: tie the wall ends down to the spine edges (roll)
            for (sy = [-1, 1])
                translate([WALL_X0, sy * WALL_Y - (sy > 0 ? 0 : 4), DECK_TOP])
                    cube([WALL_X1 - WALL_X0 + 10, 4, 12]);
        }
        // ---- deck-through bolt holes (drill-at-assembly clearance) ----
        for (b = BOLT_XY)
            translate([b[0], b[1], DECK_TOP - EPS])
                cylinder(d = M3_CLEAR, h = BASE_T + 2 * EPS);
        // ---- head-mount heat-sets, bored from the FRONT face (x121) so the
        // iron is reached from the head side BEFORE the head goes on; the
        // head boss bolts M3 rearward into them. 6mm bore in the 8mm wall.
        for (z = HM_Z, sy = [-1, 1])
            translate([WALL_X1 - HEATSET_L, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
        // ---- deck lightening-window passthrough (cable route L2->trunk) ----
        // a slot in the base plate over the window center for the L2 pigtail
        // to drop into the C-box / trunk (RJ45 + DC plug; caliper).
        translate([128, -7, DECK_TOP - EPS])
            cube([18, 14, BASE_T + 2 * EPS]);
    }
}

neck_bracket();
