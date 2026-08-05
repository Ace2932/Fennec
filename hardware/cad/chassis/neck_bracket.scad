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
//   - BASE PLATE flat on the deck (z79.55..83.55); 4x M3x8 SHCS drive DOWN
//     through the base clearance holes into M3x3.8 brass heat-sets PRESSED
//     into the shoulder deck (printed pilots, leg_v6/shoulder.scad
//     neck_heatset module) — NO drilling at assembly, NO nuts. FRONT pair
//     sits at trunk x117 (shoulder-local sy -24.2), moved off the shoulder's
//     rear-wall rib onto the flat deck; REAR pair unchanged at x146 (sy 4.8).
//     Minimal shoulder-mesh addition (4 blind pockets on the deck top only)
//     -> both shoulders (front/rear, same print) stay gate-clean.
//   - REAR VERTICAL FACE at x121 rising z83.55..106: the head's rear boss bolts
//     to it. #72 fix (2026-07-12): the M3 HEAT-SETS live in the HEAD BOSS, not
//     this wall (see head.scad) -- this wall carries only the M3 clearance
//     shank + a rear head counterbore. Tall bolt rectangle (z89 & z100, y+-11)
//     resists the fwd-tipping moment.
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
BASE = [107, 150, -22.5, 22.5];   // x0 x1 y0 y1 (CR-5: +-21->+-22; #69 fix
                                   // 2026-07-12: +-22->+-22.5 lifts the x117
                                   // bolt edge margin 0.3->0.8mm. Capped at 22.5:
                                   // MEASURED 22.8 left only 0.15mm to the shoulder
                                   // horn flange (too tight for 2 printed parts);
                                   // 22.5 keeps a safe ~0.45mm flange gap.)
BASE_T = 4;                        // z79.55..83.55
// deck-through bolts: M3x8 SHCS driven from the bracket top through the base
// M3_CLEAR holes into M3x3.8 brass heat-sets pressed into the shoulder deck
// (leg_v6/shoulder.scad neck_heatset pockets) — NO drilling at assembly, NO
// nuts. Clear of the window (y16) + horn flange (solid from y23).
// CR-5 fix 2026-07-09: BASE widened +-21->+-22 and the (then-x146) pair
// centered in the 7mm corridor (y19->19.5). This gives that bolt symmetric
// ~1.8mm margins to window/flange (was 1.3/2.3), lifts its own-plate-edge
// margin 0.3->0.8mm, AND fixes a latent bug: the OTHER pair (y20) previously
// broke out of the +-21 plate edge by 0.7mm (now +0.3mm clear). Span check
// (x-only, was 146-110>=30) unaffected by that fix.
// NO-DRILL fix 2026-07-10: the x110 pair sat over the shoulder's 22.5mm-tall
// thin rear-wall rib — no flat landing, no heat-set spot possible — and was
// still drill-at-assembly, both violations of the project's hard no-drill
// rule. Moved x110->x117 (shoulder-local sy -31.2->-24.2, 7mm more central)
// onto the flat 6.5mm deck, off the rib, and converted to a real M3x3.8
// heat-set like the other pair. New span 146-117 = 29mm (was 36mm): the rear
// VERTICAL-FACE head heat-sets at x121 carry the primary head-cantilever
// moment; these 4 base bolts are secondary hold-down, so 29 vs 30 is
// negligible.
BOLT_XY = [[117, 20], [117, -20], [146, 19.5], [146, -19.5]];

// ---- rear vertical mount face (the head bolts to this) ----------------------
WALL_X0 = 113; WALL_X1 = 121;     // 8mm face (front x121): holds M3 heat-sets
WALL_Y  = 16;                      // half-span
WALL_Z0 = 79.55; WALL_Z1 = 106;   // rises from the deck to under the L2 body
HM_Z    = [89, 100];               // bolt rows (tall couple vs the fwd moment)
HM_Y    = 10;                      // bolt half-span (centered bore<->edge for insert wall; matches head)

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
        // ---- deck-through bolt holes (M3 clearance; land in the shoulder's
        // modeled M3x3.8 heat-sets below — no drilling) ----
        for (b = BOLT_XY)
            translate([b[0], b[1], DECK_TOP - EPS])
                cylinder(d = M3_CLEAR, h = BASE_T + 2 * EPS);
        // ---- head-mount: the HEAD BOSS now holds the heat-sets; the wall has
        // clearance + a rear counterbore. The 4 M3 drive from BEHIND the wall
        // (x<113, open above the deck) — the front approach was blocked by the
        // head pillar at z100 (access audit 2026-07-08).
        for (z = HM_Z, sy = [-1, 1]) {
            translate([WALL_X0 - EPS, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR, h = WALL_X1 - WALL_X0 + 2 * EPS);  // shank
            translate([WALL_X0 - EPS, sy * HM_Y, z]) rotate([0, 90, 0])
                cylinder(d = 6.5, h = 3);          // rear counterbore for the head
        }
        // aft-gusset DRIVER NOTCH: 2 channels for the LOWER (z89) bolts — the
        // gusset (x107..113) blocks that approach. Ø9 to x115 also opens the
        // counterbore mouth, so a socket can reach this row's head.
        for (sy = [-1, 1])
            translate([103, sy * HM_Y, HM_Z[0]]) rotate([0, 90, 0])
                cylinder(d = 9, h = 12);           // x103..115
        // UPPER (z100) DRIVER NOTCH — added 2026-08-05. This row was documented
        // as "above the apex" and therefore needing no notch. It is NOT above
        // it: the apex is WALL_Z1-6 = 100, EXACTLY the bolt height, so the
        // gusset feather sits in the approach. Mesh-probed before the fix:
        // solid at x111.7..112.9 for a Ø9 socket, and x112.7..112.9 even for a
        // 2.5 mm hex key. (The hex key would in practice have gone in anyway —
        // the feather is 0.37 mm there, under one 0.42 mm extrusion, so the
        // slicer cannot render it. The claim was accidentally true, not right.)
        //
        // Unlike the lower notch this one STOPS REARWARD OF THE WALL FACE
        // (x113), for two reasons:
        //   1. neck_bracket_analysis.py hardcodes the wall as a whole 32x8
        //      section (Z = 32*8^2/6). Cutting 2 mm in would drop Z by 44 % and
        //      take the faceplant SF from ~12 to ~7 — at the row that carries
        //      the tipping moment's TENSION, which is the worst place to do it.
        //   2. The Ø6.5 counterbore and its bearing floor stay untouched.
        // Consequence, stated so it is not rediscovered: this row is BALL-END
        // HEX KEY access, not socket. That is the correct tool for a
        // counterbored M3 SHCS anyway; the lower row keeps socket access.
        for (sy = [-1, 1])
            translate([103, sy * HM_Y, HM_Z[1]]) rotate([0, 90, 0])
                cylinder(d = 9, h = 10.05);        // x103..113.05 (EPS into face)
        // ---- deck lightening-window passthrough (cable route L2->trunk) ----
        // a slot in the base plate over the window center for the L2 pigtail
        // to drop into the C-box / trunk (RJ45 + DC plug; caliper).
        translate([128, -7, DECK_TOP - EPS])
            cube([18, 14, BASE_T + 2 * EPS]);
    }
}

neck_bracket();
