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
            // NO strap on the femur (sweep-gate find 2026-07-05): anything
            // above the rim at x 26..36 sits inside the COAX's swept
            // envelope (block corners reach r~41 about the hfe axis).
            // Retention = the 4 case-column screws (the SO-ARM standard);
            // once the coax yoke bolts the horn+wheel the servo is captive.
            // knee fork block, top = FLAT SHELF at 17.2: the top arm is a
            // separate bolt-on plate (knee_arm.scad) so its horn-seat face
            // prints on the bed (the integral arm printed over supports —
            // rough seat). Bonus: femur now prints with zero bridging and
            // the tibia drops in from above.
            hull() {
                translate([FORK_X0, 0, YOKE_BOT_IN - ARM_THK])
                    cylinder(r = TIP_R,
                             h = YOKE_TOP_IN - (YOKE_BOT_IN - ARM_THK));
                translate([FEMUR_LEN, 0, YOKE_BOT_IN - ARM_THK])
                    cylinder(r = TIP_R,
                             h = YOKE_TOP_IN - (YOKE_BOT_IN - ARM_THK));
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
        translate([FEMUR_LEN, 0, 0])
            wheel_couple_neg();    // bottom arm + boss: wheel screws
        // knee-arm plate mounting: 4x M3 heat-sets in the shelf top
        for (hx = [65, 75], hy = [-8, 8])
            translate([hx, hy, YOKE_TOP_IN - HEATSET_L])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

        // side-wall vent window (servo heat relief; hips hold ~22%% torque
        // continuously). CR-6 fix (2026-07-09): the old 16mm-tall raw-cube
        // cut left SF ~1.39 wet (kept only ~18%% of wall section modulus)
        // with zero fillet on its 4 vertical reentrant corners (FDM crack
        // risk). Shrunk to 5mm tall + stadium (fully rounded, r=2.5) profile
        // -> residual strips top 12.2 / bottom 19.7mm, Z 263->573 mm^3,
        // femur SF dry ~6.1 / wet ~3.0 (M=14.2 N*m, 151/75 MPa PA6-CF).
        vent_window_neg(x0 = 2, w = 22, z_ctr = 0, h = 5, y0 = -17, y1 = 17);

        // side marker: 1 dot = RIGHT (the L mirror wrapper adds a 2nd —
        // mirrored parts are otherwise near-identical at assembly)
        translate([22, 10, SLAB_Z1 - 0.8]) cylinder(d = 3, h = 1);

        // ---- cable management (review 2026-07-03) ----
        // NOTE: the fork-block hull footprint spans x 56.15..122.75 at full
        // depth (-26.4) — underside features must stay x < 56 or cut the
        // block/arm faces explicitly.
        // groove along the open underside: tunnel exit -> block edge
        translate([40, -8, SLAB_Z0 - EPS]) cube([16, 16, 2]);
        // zip anchors: flank the tunnel exit + at the block edge
        zip_pair_neg(44, 0, SLAB_Z0 - 1, 12);
        zip_pair_neg(52, 0, SLAB_Z0 - 1, 12);
        // knee-crossing anchors: through the yoke BOTTOM ARM plate near the
        // axis (23mm out) — the bundle ties here, then a short loop jumps
        // to the tibia's tunnel anchors
        zip_pair_neg(84, 0, YOKE_BOT_IN - ARM_THK - 1, ARM_THK + 2);
    }
}

femur_v6();
