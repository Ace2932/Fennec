// =============================================================================
// NOVA chassis — BELLY BATTERY POCKET (4S Ovonic 6000, 155 x 46 x 35, 510g)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (z0 = floor bottom,
// +x FRONT). Lowest-CoM pack, swap WITHOUT tools (design-outline service
// table: battery = strap only, 0 screws).
//
// PRINT: PETG-CF, FLOOR-DOWN (tray bottom on the bed; opening + rim flange
//   up) — zero supports. 3 walls / 0.25 / 20% (print-batch §2).
//
// Shape: open-TOP tray hanging under the stock shell — the shell floor caps
// the cavity. Pack slides in from the REAR opening; a velcro strap fences
// the opening through two side-wall slots. Front wall + side walls guide,
// tray bottom carries the pack.
//
// Mount: TOP-FLANGE MOUNT (AUD-1 fix, 2026-07-10 — replaces the retired
// full-height boss columns, which fouled the pack: their inner edge sat
// 1.15mm inside the pack half-width for the WHOLE column height, and no
// column position cleared the pack without also fouling the leg-sweep ROM;
// see docs/improvement-backlog.md AUD-1 for the full history). 6x M3 x 8
// driven from INSIDE the trunk, through the 3.9 floor slab, into a
// side-loaded M3 NUT TRAP held in a LOCAL PAD thickening the rim flange
// (not a full-height column) at (x -40/0/+40, y +/-26.5) — NOT a heat-set
// insert (a nut beats an insert for this joint, and the flange is too thin
// to take one anyway). The stock floor has NO holes there — drill Ø3.4 at
// first assembly. **The part-5 floor boss plate must adopt this same
// 6-hole pattern** (unchanged XY — only the pocket-side mount depth
// changed): screws sandwich plate + floor + tray (plate spreads the load;
// the tray bores double as the drill template from below). The nut slides
// in from the pad's outboard face (the pad's own outer surface, y=30.75).
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
CAV_X = PACK[0] / 2 + CLR;        // 78.1
CAV_Y = PACK[1] / 2 + CLR;        // 24.0
WALL  = 3.2;
RIM_Z = -0.2;                     // tray top plane (0.2 under the shell)
CAV_Z0 = RIM_Z - (PACK[2] + CLR); // -36.0 cavity floor
BOT_Z  = CAV_Z0 - WALL;           // -39.2 tray bottom
FRONT_X1 = CAV_X + WALL;          // 81.5 front wall outer

BOSS_X = [-40, 0, 40];
BOSS_Y = 26.5;
HEATSET_D = 4.0;  HEATSET_L = 6.2;   // Ruthex M3: bore 4.0
M3_CLEAR = 3.4;
// AUD-1 fix (top-flange mount, 2026-07-10): the 6 nut-trap mounts are now
// LOCAL PADS thickening the rim flange, not full-height boss columns (see
// the union()/difference() comments below for the full writeup).
PAD_Z0  = RIM_Z - 6;      // local pad bottom -> 6mm local flange thickness
                          // (vs the base flange's 4mm; +2mm local, HIGH near
                          // the rim -- old columns reached BOT_Z=-39.2)
PAD_HW  = 4.25;            // pad half-width in x (was the old boss radius)
TRAP_H  = 2.7;              // M3 nut trap height (nut thickness + clearance)
TRAP_Z1 = RIM_Z - 0.6;    // trap top (0.6mm web under the rim, printable
                          // roof over the trap slot)
TRAP_Z0 = TRAP_Z1 - TRAP_H; // trap bottom (leaves ~2.7mm solid to PAD_Z0)

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
            // rim flange tying the wall tops to the front wall — thin,
            // full-length structural rib (KEPT; unrelated to the AUD-1 fix)
            for (sy = [-1, 1])
                translate([-45, min(sy * (BOSS_Y + 4.25), sy * CAV_Y), RIM_Z - 4])
                    cube([90, BOSS_Y + 4.25 - CAV_Y, 4]);
            // AUD-1 FIX (top-flange mount, 2026-07-10): the 6 M3 nut-trap
            // mounts are now LOCAL PADS thickening the rim flange only at
            // (x BOSS_X, y +/-BOSS_Y) — the full-height boss columns are
            // GONE. Their inner edge (26.5-4.25=22.25) sat 1.15mm inside
            // the pack half-width (23.4) for the ENTIRE column height, so
            // the pack could never pass them; pushing them outboard to
            // clear the pack pushed their (also full-height) outer
            // material into the leg-sweep ROM — no column position worked
            // (see docs/improvement-backlog.md AUD-1).
            //
            // Each pad spans y [CAV_Y, BOSS_Y+4.25] = [24.0, 30.75] — the
            // SAME outer edge the old full-height column proved leg-sweep-
            // clean at (check_fit.py case 4 crouch sweep) — and starts
            // flush at CAV_Y, i.e. ALWAYS outboard of the pack (half-width
            // 23.4), never intruding it. Pad depth only reaches PAD_Z0
            // (6mm below the rim, vs the old column's 39mm) — strictly
            // less material at the SAME outer edge that was already
            // gate-clean, so the pad is leg-clean a fortiori (verified by
            // re-running the full crouch sweep after this change).
            //
            // Each pad fuses to the full-height side wall along a whole
            // rectangular face (x 8.5 wide x 6mm tall, at y=CAV_Y+WALL=
            // 27.2, the wall's outer face) — real face-to-face fusion, not
            // the old boss's thin tangent-line contact at the flange top
            // (the old boss only really tied in through the 4mm top
            // flange down a 35mm cantilever — mesh_health said "1 body"
            // but a z-section showed the join was a near-tangent line).
            // Section-verified fused mass: see check_fit.py run notes.
            for (bx = BOSS_X, sy = [-1, 1])
                translate([bx - PAD_HW,
                           min(sy * (BOSS_Y + 4.25), sy * CAV_Y), PAD_Z0])
                    cube([2 * PAD_HW, BOSS_Y + 4.25 - CAV_Y, RIM_Z - PAD_Z0]);
        }
        // AUD-1 FIX (top-flange mount, 2026-07-10): O3.4 clearance bore
        // meets a side-loaded M3 NUT TRAP immediately under the rim (was a
        // deep column bore/trap at RIM_Z-8.6/RIM_Z-5.8, see git history).
        // Nut slides in from the outboard face — the trap spans the pad's
        // FULL y-width (24.0 -> 30.75, the pad's own outer face), same
        // "insert from the outboard face" scheme as before. Load path is
        // now the ~6mm flange pad, not a 39mm column, so a SHORTER screw
        // is used: M3x8 (was M3x12) — CSK head seats in floor_plate.scad's
        // existing countersink (top z5.9), tip lands ~z-2.1, landing
        // mid-trap (trap z[-3.5,-0.8]) for ~1.3mm/48% nut engagement.
        // ⚠ verify engagement at first article (the floor_plate + stock-
        // floor stack above the rim is a fixed ~6.1mm of "dead" reach
        // before the screw even enters the pocket); step to M3x10 if the
        // fit feels marginal. BOM: M3x8 socket/CSK screws replace M3x12
        // for these 6 fasteners; M3 nuts unchanged.
        for (bx = BOSS_X, sy = [-1, 1]) {
            translate([bx, sy * BOSS_Y, TRAP_Z1])
                cylinder(d = M3_CLEAR, h = RIM_Z - TRAP_Z1 + EPS);
            translate([bx - 2.85, min(sy * (BOSS_Y + 4.25), sy * CAV_Y),
                       TRAP_Z0])
                cube([5.7, BOSS_Y + 4.25 - CAV_Y, TRAP_H]);
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
