// =============================================================================
// V6 Femur — houses the HFE (hip-pitch) STS3215, yoke-drives the tibia at KFE.
// =============================================================================
// Local frame: hfe axis = Z axis THROUGH THE ORIGIN. +X toward the knee.
// kfe axis = Z line at x = FEMUR_LEN (106.9, measured — do not change without
// re-running B2 / test_urdf_sync).
//
// Assembly story:
//   1. drop HFE servo into the open-top pocket (horn up), 4x M2.5 through the
//      floor into the case bottom threads
//   2. the COAX's yoke grabs this servo: its top arm bolts to the horn, its
//      bottom arm rides the exposed bottom reaction disc
//   3. the TIBIA's knee end slides into the knee yoke slot; the tibia's servo
//      horn bolts up into the yoke top arm (4x M2.5 + M3 center), its bottom
//      disc drops into the bottom-arm recess
//   4. wires run out the pocket's knee-side wall into the open top channel
//
// Print: flat on its back (-Z face down), no supports in the pocket.

include <leg_v6_common.scad>

FEMUR_LEN = 106.9;            // hfe -> kfe axis distance (MEASURED, B2)
SLAB_W    = SERVO_W + 2*WALL + 2*CLR_POCKET;   // 31.7
SLAB_Z0   = -(SERVO_H/2 + FLOOR);              // -20.15 floor bottom
SLAB_Z1   =  SERVO_H/2;                        // +17.15 rim = body top
FORK_X0   = 72;               // yoke fork begins
TIP_R     = SLAB_W/2;

module femur_v6() {
    difference() {
        union() {
            // main slab: hip rounded end (around origin) to fork
            translate([FORK_X0/2, 0, SLAB_Z0])
                slab(FORK_X0 + SLAB_W, SLAB_W, SLAB_Z1 - SLAB_Z0);
            // knee fork block: taller than slab (holds both yoke arms)
            hull() {
                translate([FORK_X0, 0, -(YOKE_BOT_IN + ARM_THK)])
                    cylinder(r = TIP_R, h = YOKE_BOT_IN + YOKE_TOP_IN + 2*ARM_THK);
                translate([FEMUR_LEN, 0, -(YOKE_BOT_IN + ARM_THK)])
                    cylinder(r = TIP_R, h = YOKE_BOT_IN + YOKE_TOP_IN + 2*ARM_THK);
            }
            // hip idler pad (coax yoke bottom arm pivots here, M3 heat-set)
            idler_pad_pos(SLAB_Z0);
        }

        // ---- HFE servo pocket: spline axis AT ORIGIN, body toward knee ----
        rotate([0, 0, 180]) translate([-SPLINE_X, 0, 0]) servo_pocket_neg();

        // hip idler heat-set bore (M3 x D4.6, into pad + floor)
        idler_heatset_neg(SLAB_Z0);

        // ---- knee yoke slot: open at +X and open-ended in Y ----
        // asymmetric: tibia slides in with horn up (+17.45) and floor+pad
        // down (-22.45); femur/tibia body mid-planes end up coplanar
        translate([FORK_X0 + 8, -(SLAB_W + 2)/2, -YOKE_BOT_IN])
            cube([FEMUR_LEN - FORK_X0 + TIP_R + 10, SLAB_W + 2,
                  YOKE_BOT_IN + YOKE_TOP_IN]);

        // ---- KFE couplings at x = FEMUR_LEN ----
        translate([FEMUR_LEN, 0, 0]) {
            horn_couple_neg(YOKE_TOP_IN);   // top arm: horn seat + screws
            idler_screw_neg(-YOKE_BOT_IN);  // bottom arm: M3 idler pivot
        }

        // retention-strap pilots (strap.scad screws over the servo tail)
        strap_pilot_neg(31);

        // ---- wire channel: pocket exit continues open-top to the fork ----
        translate([36, -7, SLAB_Z1 - 6])
            cube([FORK_X0 - 36 + 8, 14, 12.1]);
    }
}

femur_v6();
