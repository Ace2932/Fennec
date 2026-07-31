// =============================================================================
// V6 Coax HFE BLOCK — removable OUTBOARD bearing arm (#226 option C, 2026-07-31)
// =============================================================================
// REPLACES coax_hfe_plate.scad, which is retired. That cap could never be
// installed: MEASURED blocked in all six axes against the seated femur AND
// against a bare coax, in the #67 revision AND the pre-#7-fix one, while its
// seated pose was itself legitimate (boolean intersection with the coax =
// 0.0 mm3). A valid final position with no path to it — a ship in a bottle.
// Aiden's printed coax refused it on the bench ("doesn't really slide in"),
// which is not a tolerance problem: no path exists at any tolerance.
// check_fit.removable_member_checks() now gates that whole class.
//
// WHY THE REMOVABLE MEMBER MOVED OUTBOARD. The inboard side has 3.15mm of slot
// and 0.5mm to the HAA servo; the outboard side has ~8mm of material and open
// air past x=62.4. The cap was on the cramped side, and its fasteners could not
// be driven (0.8-4.5mm of driver run against the 15-20mm needed). Inverting
// which arm is removable puts the serviced member where the access is, and
// opens the +X AXIAL insertion path for the femur — coax.scad's own #53 header
// recorded "+X blocked by the integral outboard arm", so making that arm
// removable is exactly what unblocks it. MEASURED: femur withdraws +X with 0
// points over t=2..50mm.
//
// WHY A TENON AND NOT BOLTS IN TENSION. This joint's binding case is FATIGUE,
// not the 400 N static couple: coax.scad records the arm-to-bridge junction as
// "the only member on the robot under SF 15" (~14 MPa at the 4-thick root under
// a 20 N lateral/turning foot load, fatigue SF ~1.9 per stride, halved to ~6MPa
// by the gusset this part now carries). Any bridge-level interface sits ~22mm
// above the boss, so the 133 N cyclic axial load becomes ~2.95 N.m at the joint
// = ~490 N per bolt on a 10mm face — past M3 heat-set pull-out in wet PA6-CF.
// A concentric spigot would shorten the lever, but MEASURED there is no room:
// the femur occupies r 10..16 at the boss station, leaving no free annulus.
//
// So the tenon reacts the moment in BEARING over its own length (2.95 N.m /
// 12.05mm = 245 N on ~92 mm2 = 2.7 MPa) and the 2x M3 drop to retention
// (cyclic 133/2 = 66 N each vs ~175-245 N wet pull-out -> SF 2.6-3.7). That is
// the same move #7-fix made for the cap — shape key carries, bolt retains —
// including its hard-won corollary: the key must be CLOSED in BOTH directions,
// because a compression-only key cannot react peel. This tenon is shrunk
// CLR_TENON off y0/y1/z0/z1 and flush only at the mating plane.
//
// Geometry proof + negative control: hfe_block_study.py.
//
// Print: PA6-CF, MATING FACE (x=SPLIT_X) DOWN — the tenon and boss then rise
// as the only overhangs and the bearing faces land on the bed. Same material
// and settings as the coax (4 walls / 40% / 0.2).
include <leg_v6_common.scad>

// Mirrors coax.scad's constants byte-for-byte — `include` does not share
// variables across files, same convention every part in this set follows.
FEMUR_MID   = 33.8;
HFE_Y       = 11.6;
HFE_Z       = -9.5;
ARM_THK     = 4.0;
ARM_HALF_YZ = 16;
BRIDGE_Z0   = 7.4;
ARM_OUT_X0  = FEMUR_MID - YOKE_BOT_IN;   // 56.2
ARM_OUT_X1  = ARM_OUT_X0 + ARM_THK;      // 60.2
SPLIT_X     = ARM_OUT_X0;
BOSS_X0     = FEMUR_MID - WHEEL_Z0;      // 51.55

MORT_X0 = 43.8;  MORT_Y0 = 0.0;   MORT_Z0 = 9.5;
MORT_Y1 = 23.2;  MORT_Z1 = 13.5;
CLR_TENON = 0.15;
BOLT_YS = [5.0, 18.0];
BOLT_Z  = 11.5;
M3_CLEAR_D = 3.4;
SHCS_HEAD_D = 6.0;
SHCS_HEAD_H = 3.2;

module arm_plate(x0, x1) {
    hull() {
        translate([x0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = x1 - x0);
        translate([x0, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
            cube([x1 - x0, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
    }
}

module coax_hfe_block_R() {
    difference() {
        union() {
            // the outboard arm itself
            arm_plate(ARM_OUT_X0, ARM_OUT_X1);
            // ROOT DOUBLER (backlog #26) — travels with the arm it stiffens
            hull() {
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, 0])
                    cube([2, 2*ARM_HALF_YZ, 13.4]);
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, -1.5])
                    cube([0.5, 2*ARM_HALF_YZ, 14.9]);
            }
            // wheel boss reaching inboard to the femur wheel face
            translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
                wheel_boss_pos();
            // TENON — shrunk on y0/y1/z0/z1 (closed both ways in Z), flush at
            // the mating plane. This is the member that carries the moment.
            translate([MORT_X0 + CLR_TENON, MORT_Y0 + CLR_TENON, MORT_Z0 + CLR_TENON])
                cube([SPLIT_X - MORT_X0 - CLR_TENON,
                      (MORT_Y1 - MORT_Y0) - 2*CLR_TENON,
                      (MORT_Z1 - MORT_Z0) - 2*CLR_TENON]);
        }

        // wheel-screw couple through the boss + arm (unchanged geometry — this
        // is the femur idler side, it just lives on a separate part now)
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
            wheel_couple_neg();

        // 2x M3 retention: clearance through the tenon + head counterbore
        // opening on the OUTBOARD face, driven from +X open air.
        for (by = BOLT_YS) {
            translate([MORT_X0, by, BOLT_Z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR_D, h = ARM_OUT_X1 + 3 - MORT_X0);
            translate([ARM_OUT_X1 - SHCS_HEAD_H, by, BOLT_Z]) rotate([0, 90, 0])
                cylinder(d = SHCS_HEAD_D, h = SHCS_HEAD_H + 3);
        }

        // side marker: 1 dot = RIGHT (the _L wrapper adds a 2nd, 3mm away in z)
        // ON THE GUSSET'S OUTBOARD FACE (x=62.3), not the arm's. Two earlier
        // sites failed the depth gate at 0.00mm: y+10/z-12 sat at r=15.6
        // against a 16 rim so the dimple spilled off the edge, and y+8/z-8
        // landed on a WHEEL-SCREW COUNTERBORE, which had already recessed the
        // face -- probed flat, so the dot cut air. This face measures flat at
        // 62.30 across a +-1.4mm neighbourhood. Cut starts outside so it
        // breaks the surface.
        translate([62.3 + 0.4, HFE_Y + 8, 6.0]) rotate([0, -90, 0])
            cylinder(d = 3, h = 1.2);
    }
}

coax_hfe_block_R();
