// =============================================================================
// NOVA chassis — BELLY BATTERY POCKET (4S Ovonic 6000, 155 x 46 x 35, 510g)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (z0 = floor bottom,
// +x FRONT). Lowest-CoM pack, swap WITHOUT tools (design-outline service
// table: battery = strap only, 0 screws).
//
// PRINT: PETG-CF, FLOOR-DOWN (tray bottom on the bed; opening + rim bosses up)
//   — zero supports. 3 walls / 0.25 / 20% (print-batch §2). Heat-sets into the
//   rim bosses from the OPEN (cavity) side, iron reaches from above.
//
// Shape: open-TOP tray hanging under the stock shell — the shell floor caps
// the cavity. Pack slides in from the REAR opening; a velcro strap fences
// the opening through two side-wall slots. Front wall + side walls guide,
// tray bottom carries the pack.
//
// Mount: 6x M3 x 12 driven from INSIDE the trunk, through the 3.9 floor
// slab, into heat-set inserts in the rim bosses at (x -40/0/+40,
// y +/-26.5). The stock floor has NO holes there — drill Ø3.4 at first
// assembly. **The part-5 floor boss plate must adopt this same 6-hole
// pattern**: screws then sandwich plate + floor + tray (plate spreads the
// load; the tray bores double as the drill template from below). Inserts
// press from BELOW so screw tension pulls them DEEPER into the boss
// (pack weight = extraction-safe direction).
//
// Pack: 155 fore-aft (overhangs the 127 trunk by ~14.8/end, passing 0.25
// under the shoulder flange bottoms at z 0.05); leads exit the pack's REAR
// face into open air behind the trunk end, rise at x ~-70, and enter the
// trunk through the shoulder flange's NEW bottom-center notch (trunk
// y +/-10 up to z 12) to the MRBF-30 / Blue Sea 5191 block INSIDE.
// ⚠ 5191 block dims not in dimensions.md — block mounting = part-5 plate
// territory, note there.
//
// Clearances (mesh/gate-verified): rim top z -0.2 (0.2 under the floor);
// crouch-pose knees pass outboard (tibia plane y 30..55 vs walls +/-30.5).
// Fit gate: check_fit.py cases 6-7. First article: pack slide fit (0.8/side
// on LISTING dims — caliper the real pack!), strap slot deburr, drill.

$fn = 64;
EPS = 0.05;

PACK = [155, 46.8, 35];          // CALIPER 2026-07-07 (was 46 listing width)
CLR  = 0.6;                       // per side (width caliper landed +0.8 → keep
                                  // ~0.6/side; pack slides on the tray, EVA
                                  // pad + strap preload it, backlog #29)
CAV_X = PACK[0] / 2 + CLR;        // 78.3
CAV_Y = PACK[1] / 2 + CLR;        // 23.8
WALL  = 3.2;
RIM_Z = -0.2;                     // tray top plane (0.2 under the shell)
CAV_Z0 = RIM_Z - (PACK[2] + CLR); // -36.0 cavity floor
BOT_Z  = CAV_Z0 - WALL;           // -39.2 tray bottom
FRONT_X1 = CAV_X + WALL;          // 81.5 front wall outer

BOSS_X = [-40, 0, 40];
BOSS_Y = 26.5;
HEATSET_D = 4.0;  HEATSET_L = 6.2;   // Ruthex M3: bore 4.0
M3_CLEAR = 3.4;

module battery_pocket() {
    difference() {
        union() {
            // bottom
            translate([-CAV_X, -CAV_Y - WALL, BOT_Z])
                cube([FRONT_X1 + CAV_X, 2 * (CAV_Y + WALL), WALL]);
            // side walls
            for (sy = [-1, 1])
                translate([-CAV_X, min(sy * (CAV_Y + WALL), sy * CAV_Y), BOT_Z])
                    cube([FRONT_X1 + CAV_X, WALL, -BOT_Z + RIM_Z]);
            // front wall
            translate([CAV_X, -CAV_Y - WALL, BOT_Z])
                cube([WALL, 2 * (CAV_Y + WALL), -BOT_Z + RIM_Z]);
            // rim mount bosses: FULL-HEIGHT columns fused to the wall
            // outer faces (a hanging 8-deep boss overhung its print
            // orientation — design-review fix; columns print from the bed)
            for (bx = BOSS_X, sy = [-1, 1])
                translate([bx, sy * BOSS_Y, BOT_Z])
                    cylinder(d = 8.5, h = -BOT_Z + RIM_Z);
            // rim flange tying bosses to the wall tops
            for (sy = [-1, 1])
                translate([-45, min(sy * (BOSS_Y + 4.25), sy * CAV_Y), RIM_Z - 4])
                    cube([90, BOSS_Y + 4.25 - CAV_Y, 4]);
        }
        // boss fastening: O3.4 down the column into a side-loaded M3 NUT
        // TRAP at z -8.2 (design-review fix: a full-height column can't
        // take a heat-set from either end, and a nut beats an insert for
        // the pocket's highest-load joint anyway). Nut slides in from the
        // outboard face; M3x12 from inside the trunk engages it fully.
        for (bx = BOSS_X, sy = [-1, 1]) {
            translate([bx, sy * BOSS_Y, RIM_Z - 8.6])
                cylinder(d = M3_CLEAR, h = 8.6 + EPS);
            translate([bx - 2.85, min(sy * (BOSS_Y + 4.3), sy * (BOSS_Y - 2.7)),
                       RIM_Z - 8.3])
                cube([5.7, 7, 2.7]);
        }
        // strap slots AT the rear opening: the strap wraps the pack's REAR
        // CORNER (direct tension against slide-out — friction-only
        // retention was a design-review finding; shake-test at FA)
        for (sy = [-1, 1])
            translate([-77, sy * (CAV_Y + WALL / 2) - (WALL / 2 + EPS),
                       BOT_Z + 6])
                cube([16, WALL + 2 * EPS, 5]);
        // (lead path: the pack's rear face sits at x -78.3, BEHIND the
        //  trunk end — leads rise in open air at x ~-70 and enter the trunk
        //  through the shoulder flange's bottom-center notch (s_x +/-10 to
        //  trunk z 12, shoulder.scad rev) to the MRBF block inside.)
        // strap under-pack groove: strap wraps the pack INSIDE the rear
        // opening; groove across the bottom lets it pass under the pack
        translate([-77, -CAV_Y - WALL - EPS, CAV_Z0 - 2])
            cube([16, 2 * (CAV_Y + WALL) + 2 * EPS, 2 + EPS]);

        // skid-rail key recesses (backlog #15, skid_rail.scad): 0.6 deep
        // in the 3.2 bottom (2.6 remains — pack load spreads over the
        // whole tray floor, bending trivial). Keys take the shear, CA/VHB
        // takes the peel; rails sacrificial + replaceable. Rails at
        // y +/-15, keys centered trunk x -43 / +58 (clear of the strap
        // groove x -77..-61 and the boss columns y +/-26.5).
        for (sy = [-1, 1], kx = [-43, 58])
            translate([kx - 10.3, sy * 15 - 4.3, BOT_Z - EPS])
                cube([20.6, 8.6, 0.6 + EPS]);
    }
}

battery_pocket();
