// =============================================================================
// NOVA chassis — BELLY SKID RAIL (TPU 95A — print 2, one per side)
// =============================================================================
// Backlog #15 (2026-07-06): E-stop limp = collapse BY DESIGN, and the
// battery tray bottom (z -39.2) is the lowest point on the robot — a
// LiPo puncture is a fire. These rails are the sacrificial landing pads:
// collapse-pose check (all joints limp -> nothing holds the body -> the
// belly settles to ground with legs splayed/folded) puts first sustained
// contact HERE. Rails also take rock strikes and deep-crouch bottom-outs.
//
// Mount: 0.6 raised keys drop into matching recesses in the battery
// pocket's bottom face (battery_pocket.scad rev — keying takes the shear,
// glue takes the peel: CA or VHB. Sacrificial + replaceable: peel, clean,
// reglue). Rail body stands 3.0 proud -> robot's new lowest z = -42.2
// (still 127 ground clearance standing).
//
// Placement (trunk frame): y = +/-15 rail centerline (clear of the rim
// boss columns at y +/-26.5 and the strap under-pack groove at
// x -77..-61); x -55..+75, sled-chamfered both ends.
//
// Print: TPU 95A, flat on the key face, 100% infill (it's 6 g).

$fn = 32;
EPS = 0.05;

RAIL_L = 130;          // x -55..+75 in trunk frame
RAIL_W = 12;
RAIL_T = 3.0;          // proud of the tray bottom
KEY_T  = 0.6;          // into the pocket recesses
KEY_L  = 20;  KEY_W = 8;
KEY_X  = [12, 113];    // key CENTERS along the rail (rail local x 0..130)
                       // -> trunk x -43 and +58 (clear of the groove zone)
CHAMF  = 4;            // sled end chamfer

module skid_rail() {
    union() {
        // body with sled ends (45 deg chamfers on the ground face)
        hull() {
            translate([0, 0, 0]) cube([RAIL_L, RAIL_W, EPS]);
            translate([CHAMF, 0, -RAIL_T + EPS])
                cube([RAIL_L - 2 * CHAMF, RAIL_W, EPS]);
        }
        // keys (up into the pocket bottom)
        for (kx = KEY_X)
            translate([kx - KEY_L / 2, (RAIL_W - KEY_W) / 2, -EPS])
                cube([KEY_L, KEY_W, KEY_T + EPS]);
    }
}

skid_rail();
