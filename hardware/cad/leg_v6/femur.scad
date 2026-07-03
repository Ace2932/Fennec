// =============================================================================
// V6 Femur (rev 2) — houses the HFE STS3215, yoke-drives the tibia at KFE.
// =============================================================================
// Local frame: hfe axis = Z THROUGH THE ORIGIN (spline). +X toward the knee.
// kfe axis = Z line at x = FEMUR_LEN (106.9, MEASURED — locked to B2).
//
// Joint = bolted both sides: knee-yoke top arm bolts the tibia servo's horn
// (arm underside ON the horn face), bottom arm's Ø19 boss reaches through
// the tibia's floor window and bolts the BOTTOM WHEEL. The femur's own horn
// + wheel are grabbed the same way by the coax yoke.
// Servo mounting: 4x M2 x >=22 replacement case screws through the floor
// (countersunk), + retention strap over the tail on raised rim bosses
// (the case's rear top cap ridge stands 2.7 proud of the rim).
// Cables: plug before drop-in; tunnel exits the knee-side end wall at bay
// level, wires run along the blade.
//
// Print: flat on the -Z face, no supports in the pocket.

include <leg_v6_common.scad>

FEMUR_LEN = 106.9;            // hfe -> kfe axis distance (MEASURED, B2)
SLAB_W    = 2*(CASE_HW + CLR_POCKET + WALL);   // 31.7
SLAB_Z0   = FLOOR_BOT;                          // -22.2
SLAB_Z1   = CASE_TOP;                           // +14.7
FORK_X0   = 72;
TIP_R     = SLAB_W/2;

module femur_v6() {
    difference() {
        union() {
            // stage 1: body with the yoke slot already cut (the wheel boss
            // must survive INSIDE the slot, so it unions after this)
            difference() {
                union() {
            // main slab: hip rounded end (around origin) to fork
            translate([FORK_X0/2, 0, SLAB_Z0])
                slab(FORK_X0 + SLAB_W, SLAB_W, SLAB_Z1 - SLAB_Z0);
            // pocket front platform (rings the wheel window)
            rotate([0, 0, 180]) pocket_platform_pos();
            // strap pads: full-width rim blocks (a Ø7 post on a 3.2 wall
            // overhangs + splits under a self-tapper); raised so the strap
            // clears the case's rear top cap ridge
            for (sy = [-1, 1])
                translate([26, min(sy*12.6, sy*16.6), SLAB_Z1 - EPS])
                    cube([10, 4, 3.2 + EPS]);
            // knee fork block (top arm 17.2..21.2, bottom arm -26.4..-22.4)
            hull() {
                translate([FORK_X0, 0, YOKE_BOT_IN - ARM_THK])
                    cylinder(r = TIP_R,
                             h = (YOKE_TOP_IN + ARM_THK) - (YOKE_BOT_IN - ARM_THK));
                translate([FEMUR_LEN, 0, YOKE_BOT_IN - ARM_THK])
                    cylinder(r = TIP_R,
                             h = (YOKE_TOP_IN + ARM_THK) - (YOKE_BOT_IN - ARM_THK));
            }
                }
                // ---- knee yoke slot ----
                translate([FORK_X0 + 8, -(SLAB_W + 2)/2, YOKE_BOT_IN])
                    cube([FEMUR_LEN - FORK_X0 + TIP_R + 10, SLAB_W + 2,
                          YOKE_TOP_IN - YOKE_BOT_IN]);
            }
            // stage 2: bottom-arm wheel boss rises into the slot
            translate([FEMUR_LEN, 0, 0]) wheel_boss_pos();
        }

        // ---- HFE servo pocket: spline AT ORIGIN, body toward knee ----
        rotate([0, 0, 180]) sts_pocket_neg();

        // ---- KFE couplings at x = FEMUR_LEN ----
        translate([FEMUR_LEN, 0, 0]) {
            horn_couple_neg();     // top arm: horn recess + BCD + center
            wheel_couple_neg();    // bottom arm + boss: wheel screws
        }

        // strap pilots (into the raised bosses)
        strap_pilot_neg(31, 14.25, SLAB_Z1 + 3.2);

        // ---- cable management (review 2026-07-03) ----
        // shallow groove along the underside: tunnel exit -> fork (the
        // coax-bound run lies in it, zip-tied at the anchors)
        translate([40, -8, SLAB_Z0 - EPS]) cube([26, 16, 2]);
        // zip anchors: flank the tunnel exit + mid-run
        zip_pair_neg(44, 0, SLAB_Z0 - 1, 12);
        zip_pair_neg(60, 0, SLAB_Z0 - 1, 12);
        // knee-crossing guide: notch through the fork throat wall close to
        // the knee axis (bundle hugs the axis -> small service loop)
        translate([73.5, -8, SLAB_Z0 - 1]) cube([5, 16, 8]);
        zip_pair_neg(70, 0, SLAB_Z0 - 1, 12);
    }
}

femur_v6();
