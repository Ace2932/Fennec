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
// Print: flat on the -Z face. NOTE (LA-6, 2026-07-11, issue #24): the
// underside is now planarized/ramped down to the fork's floor (SUB_FLOOR
// -26.6) for x >= SUB_X0 -- see the SUB_X0/X1/X2 block below. This closes
// MOST of the old float, but NOT all of it: check_fit's own hip-pitch
// sweep (--sweep, r13-disc-interface excluded) shows COAX's outboard yoke
// arm (coax.scad arm_plate(ARM_OUT_X0,ARM_OUT_X1), ARM_HALF_YZ=16 disc)
// sitting a constant 0.40mm below the femur's CURRENT floor across the
// ENTIRE +-93deg hfe sweep (rotation-invariant -- it's centered on the hfe
// axis) for femur-local x roughly -16..+20 (r<=~16-20 of the axis). That
// volume is real, occupied assembly space, not open air -- verified by
// direct probe against coax_R.stl AND by reading coax.scad's own
// ARM_OUT_X0 = FEMUR_MID - YOKE_BOT_IN definition (coax's bottom arm is
// deliberately built to seat right there). It CANNOT be deepened without
// fouling the coax joint at every hip angle, so x < SUB_X0 (=24, chosen
// with an 8mm/8mm margin: coax silhouette to ~20, then a real M2
// case-column screw at x32.8 pushed the ramp out further -- see below)
// stays at the ORIGINAL SLAB_Z0 -22.2, unchanged, and still floats above
// the new deeper bed contact -> still wants support, but over a ~40mm
// hip-cap span (x -16..24) instead of the old ~56mm. A same-strategy
// reorientation (print on a +-Y side face instead of fork-down) was
// evaluated and REJECTED: mesh overhang analysis on the unmodified STL
// shows it nearly DOUBLES the sub-45deg down-facing area (5949mm^2 vs
// 3881mm^2) because the open-top servo pocket becomes a horizontal bore.
// Do not read this file as claiming a fully support-free underside --
// budget support for the remaining ~40mm hip-cap span at print time.

include <leg_v6_common.scad>

FEMUR_LEN = 106.9;            // hfe -> kfe axis distance (MEASURED, B2)
SLAB_W    = 2*(CASE_HW + CLR_POCKET + WALL);   // 32.1
SLAB_Z0   = FLOOR_BOT;                          // -22.2
SLAB_Z1   = CASE_TOP;                           // +14.7
FORK_X0   = 72;
TIP_R     = SLAB_W/2;

// ---- LA-6 underside planarization (2026-07-11, issue #24) -----------------
// femur-LOCAL deep floor -- deliberately NOT touching the shared FLOOR_BOT/
// SLAB_Z0 (leg_v6_common.scad), so tibia/coax are byte-identical. Matches
// the knee-fork/yoke-shelf bottom exactly, so the ramp lands flush/coplanar
// with the existing fork hull where they overlap.
SUB_FLOOR = YOKE_BOT_IN - ARM_THK;              // -26.6 (== fork bottom)
// SUB_X0: ramp start. MEASURED (hfe +-100deg sweep vs coax_R.stl, r13
// disc-interface excluded, matches check_fit.py's own methodology) --
// coax's outboard yoke arm blocks x < ~20 (worst-case full-width margin
// +0.45mm at x=18, -0.91mm/clear at x=20) at EVERY hfe angle. x=24 gives
// ~4.8mm margin there. Also must clear the real M2 case-column screw at
// x=32.8 (leg_v6_common.scad COL_PTS, femur-frame after the 180 rotate) --
// handled by a local screw-hole extension below rather than pushing the
// ramp out to 36+ and giving up another 12mm of planarization.
SUB_X0    = 24;
SUB_X1    = 28;    // ramp end/full depth: rise 4.4 over run 4 = 47.7deg
                   // from horizontal -- a self-supporting overhang needs
                   // >=45deg from horizontal (STEEP, not shallow -- a
                   // shallow ramp is closer to the flat-ceiling worst case,
                   // not safer; first draft had this backwards at run=8/
                   // 28.8deg and was corrected). Re-verified vs coax_R.stl
                   // across the whole ramp footprint (all y, full +-100deg
                   // hfe sweep): worst-case clearance -4.85mm (clear) at
                   // the shallow end (x24), improving to -8.79mm by x28.
SUB_X2    = 60;    // flat continuation to here -- inside the fork hull's
                   // own footprint (starts ~x55.95), clean manifold overlap.

// Added-material wedge: flush with the EXISTING slab bottom (SLAB_Z0) at
// SUB_X0 (zero added thickness there), linearly ramping down to SUB_FLOOR
// by SUB_X1, then flat at SUB_FLOOR out to SUB_X2. hull() of a near-zero
// sliver and a full-depth block gives an exact linear ramp between them.
module underside_fill() {
    hull() {
        translate([SUB_X0, -SLAB_W/2, SLAB_Z0])
            cube([EPS, SLAB_W, EPS]);
        translate([SUB_X1, -SLAB_W/2, SUB_FLOOR])
            cube([EPS, SLAB_W, SLAB_Z0 - SUB_FLOOR + EPS]);
    }
    translate([SUB_X1, -SLAB_W/2, SUB_FLOOR])
        cube([SUB_X2 - SUB_X1, SLAB_W, SLAB_Z0 - SUB_FLOOR + EPS]);
}

// LA-6: the x=32.8 M2 case-column screw (leg_v6_common.scad COL_PTS,
// femur-frame) sits just past SUB_X1, i.e. now under a full SUB_FLOOR-deep
// floor instead of the original SLAB_Z0 -- its shared-module bore
// (FLOOR_BOT-1 .. FLOOR_BOT+7.1) and countersink (cut at FLOOR_BOT-EPS)
// no longer reach the true (deeper) exterior. Local extension only --
// does NOT touch leg_v6_common.scad, so tibia/coax are unaffected.
module col_screw_ext_neg() {
    for (sy = [-1, 1]) {
        translate([32.8, sy*10.25, SUB_FLOOR - EPS])
            cylinder(d = M2_CLEAR, h = (FLOOR_BOT - 1) - SUB_FLOOR + EPS);
        translate([32.8, sy*10.25, SUB_FLOOR - EPS])
            cylinder(d1 = 4.6, d2 = M2_CLEAR, h = 1.4);   // countersink, re-cut at the new true exterior
    }
}

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
            // LA-6 (2026-07-11, issue #24): underside planarization ramp,
            // SUB_X0..SUB_X2 -- see the module + constants above.
            underside_fill();
            // pocket front platform (rings the wheel window)
            rotate([0, 0, 180]) pocket_platform_pos();
            // NO strap on the femur (sweep-gate find 2026-07-05): anything
            // above the rim at x 26..36 sits inside the COAX's swept
            // envelope (block corners reach r~41 about the hfe axis).
            // Retention = the 4 case-column screws (the SO-ARM standard);
            // once the coax yoke bolts the horn+wheel the servo is captive.
            // knee fork block, top = FLAT SHELF at 17.75 (rev 3, LA-28 doc
            // fix 2026-07-11: was stale at 17.2, see leg_v6_common.scad
            // HORN_Z1): the top arm is a
            // separate bolt-on plate (knee_arm.scad) so its horn-seat face
            // prints on the bed (the integral arm printed over supports —
            // rough seat). Bonus: the TOP ARM is now zero-bridging (the old
            // integral overhanging arm is gone) and the tibia drops in from
            // above. This does NOT mean the whole part is bridge/support-
            // free -- see the file-header PRINT note (LA-6): the underside
            // is now ramped/planar for x >= SUB_X0 (24), but the x < SUB_X0
            // hip cap still floats above the new deeper bed contact (coax
            // clearance blocks lowering it -- see SUB_X0's own comment).
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

        // LA-6: extend the x32.8 case-column screw bore/countersink down to
        // the new (deeper) true exterior -- see col_screw_ext_neg() above.
        col_screw_ext_neg();

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
        // block/arm faces explicitly. LA-6 (2026-07-11): x=40/44/52 below
        // are all >= SUB_X1 (32), i.e. already sitting on the new SUB_FLOOR
        // (-26.6) exterior, not the old SLAB_Z0 (-22.2) -- cuts re-based to
        // SUB_FLOOR so they still reach the true (now deeper) exterior.
        // groove along the open underside: tunnel exit -> block edge.
        // LA-1 fix (2026-07-11): the common-frame tunnel (leg_v6_common.scad
        // sts_pocket_neg, after the 180 deg rotation) lands at femur-frame
        // x[31.2,42.4], z[-19.8,-13.9]. The old h=2 groove topped out at
        // z-20.25 -- 0.45mm short of the tunnel's z-19.8 floor, leaving a
        // solid membrane (verified: 0.05mm z-scan at x41,y0 showed SOLID
        // z[-20.20,-19.80]) that dead-ended the HFE cable. Grown to top
        // z-19.05 -> 0.75mm real overlap with the tunnel, continuous void
        // tunnel->groove confirmed by re-scan. LA-6: base + height re-based
        // to SUB_FLOOR (was SLAB_Z0) so it still reaches the true exterior
        // across its whole x[40,56] footprint (x40..44 sit on the ramp,
        // where the true exterior is shallower than SUB_FLOOR -- cutting
        // past it there is harmless, already-open air, not solid).
        translate([40, -8, SUB_FLOOR - EPS]) cube([16, 16, (-19.05) - (SUB_FLOOR - EPS)]);
        // zip anchors: flank the tunnel exit + at the block edge.
        // LA-4 fix (2026-07-11): h=12 was a BLIND pocket (top z-11.2, 25.9mm
        // of solid slab remained above it to SLAB_Z1 14.7) -- a zip tie could
        // not loop through to clamp cable_clip. h=40 matches the x62/84
        // through-hole convention elsewhere in this file (top z16.8, 2.1mm
        // clear past SLAB_Z1) -- genuine through-holes, ray-cast verified.
        // LA-6: both sit at x >= SUB_X1 (32), i.e. on the new SUB_FLOOR
        // exterior -- z0 + h re-based (was SLAB_Z0-1 / 40) so the bore still
        // starts at the true exterior and reaches the same top (z16.8).
        zip_pair_neg(44, 0, SUB_FLOOR - 1, 44.4);
        zip_pair_neg(52, 0, SUB_FLOOR - 1, 44.4);
        // knee-crossing anchors: through the yoke BOTTOM ARM plate near the
        // axis (23mm out) — the bundle ties here, then a short loop jumps
        // to the tibia's tunnel anchors
        zip_pair_neg(84, 0, YOKE_BOT_IN - ARM_THK - 1, ARM_THK + 2);
    }
}

femur_v6();
