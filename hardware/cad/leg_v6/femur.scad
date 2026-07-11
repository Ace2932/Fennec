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
// Print: flat on the -Z face, no supports in the pocket. NOTE (LA-6,
// 2026-07-11): "no supports" is scoped to the SERVO POCKET CAVITY only
// (open-top, prints clean) -- it is NOT a whole-part claim. The underside
// is NOT planar: main-slab bottom sits at SLAB_Z0 -22.2 (hip end, x<~56)
// but the knee-fork/yoke-shelf bottom sits at YOKE_BOT_IN-ARM_THK -26.6
// (x>~56, full 32mm width) -- a hard 4.4mm step, confirmed by mesh scan
// (flat -22.0 through x56, flat -26.4 from x60 on). The fork MUST be the
// deeper region (it hosts the KFE yoke bottom-arm mating plate -- a load-
// path feature, not something to thin/taper away). A slicer auto-drops
// the part onto its lowest point (the fork, -26.6) -> the hip-end slab's
// underside (x<~56) floats 4.4mm above the bed and DOES need support
// material under it for that ~56mm span. Budget for it at print time;
// do not read this file as claiming a support-free underside.

include <leg_v6_common.scad>

FEMUR_LEN = 106.9;            // hfe -> kfe axis distance (MEASURED, B2)
SLAB_W    = 2*(CASE_HW + CLR_POCKET + WALL);   // 32.1
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
            // rough seat). Bonus: the TOP ARM is now zero-bridging (the old
            // integral overhanging arm is gone) and the tibia drops in from
            // above. This does NOT mean the whole part is bridge/support-
            // free -- see the file-header PRINT note (LA-6): the underside
            // still has a real 4.4mm hip-slab/fork step that wants support.
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
        // LA-10 fix (2026-07-11): the common-frame ANTIROT_X=[-30,-12] ribs
        // land at femur-frame x=30 (far, clears the x32.8 screw column by
        // 0.95mm -- keep) and x=12 (near). The old x0=2 left edge put the
        // vent's x[2,24] squarely over the near rib's x[11.3,12.7] footprint,
        // voiding it z[-2.4,2.4] (point-probed). Trimmed the LEFT edge only
        // (x0 2->14, w 22->10) -- right edge stays x=24 (unchanged far-rib
        // clearance), left edge now 1.3mm clear of the near rib. Width-only
        // trim doesn't touch the h=5 CR-6 SF calc (that depends on vent
        // height, not width) -- SF numbers above are unaffected (if
        // anything conservative, less material removed).
        vent_window_neg(x0 = 14, w = 10, z_ctr = 0, h = 5, y0 = -17, y1 = 17);

        // side marker: 1 dot = RIGHT (the L mirror wrapper adds a 2nd —
        // mirrored parts are otherwise near-identical at assembly).
        // LA-2 fix (2026-07-11): the old (22,10) site sat inside the HFE
        // pocket's XY footprint (pocket cut spans femur-frame x -10.65..
        // 35.65 after the 180 deg rotate) -- the pocket is open-top past
        // z=14.7 (extra_top=30), so this cutter removed nothing (ray-cast:
        // 0 solid hits, ALL RIGHT parts printed with zero dots). Relocated
        // to (45,10): past the pocket's x35.65 boundary, before the fork
        // hull's rounded-cap zone (bulges the top face taller than 14.7
        // starting ~x55.95), clear of the x44/52 zip through-holes (y=+-5)
        // and the x65/75 heat-set columns. Ray-cast confirmed solid at
        // z13.9-14.7 (real material) and air above z14.7 (true external
        // top face) -- see mesh_health/LA-2 verification notes.
        translate([45, 10, SLAB_Z1 - 0.8]) cylinder(d = 3, h = 1);

        // ---- cable management (review 2026-07-03) ----
        // NOTE: the fork-block hull footprint spans x 56.15..122.75 at full
        // depth (-26.4) — underside features must stay x < 56 or cut the
        // block/arm faces explicitly.
        // groove along the open underside: tunnel exit -> block edge.
        // LA-1 fix (2026-07-11): the common-frame tunnel (leg_v6_common.scad
        // sts_pocket_neg, after the 180 deg rotation) lands at femur-frame
        // x[31.2,42.4], z[-19.8,-13.9]. The old h=2 groove topped out at
        // z-20.25 -- 0.45mm short of the tunnel's z-19.8 floor, leaving a
        // solid membrane (verified: 0.05mm z-scan at x41,y0 showed SOLID
        // z[-20.20,-19.80]) that dead-ended the HFE cable. Grown to h=3.2
        // (top z-19.05) -> 0.75mm real overlap with the tunnel, continuous
        // void tunnel->groove confirmed by re-scan.
        translate([40, -8, SLAB_Z0 - EPS]) cube([16, 16, 3.2]);
        // zip anchors: flank the tunnel exit + at the block edge.
        // LA-4 fix (2026-07-11): h=12 was a BLIND pocket (top z-11.2, 25.9mm
        // of solid slab remained above it to SLAB_Z1 14.7) -- a zip tie could
        // not loop through to clamp cable_clip. h=40 matches the x62/84
        // through-hole convention elsewhere in this file (top z16.8, 2.1mm
        // clear past SLAB_Z1) -- genuine through-holes, ray-cast verified.
        zip_pair_neg(44, 0, SLAB_Z0 - 1, 40);
        zip_pair_neg(52, 0, SLAB_Z0 - 1, 40);
        // knee-crossing anchors: through the yoke BOTTOM ARM plate near the
        // axis (23mm out) — the bundle ties here, then a short loop jumps
        // to the tibia's tunnel anchors
        zip_pair_neg(84, 0, YOKE_BOT_IN - ARM_THK - 1, ARM_THK + 2);
    }
}

femur_v6();
