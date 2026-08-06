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
// MATERIAL BASIS (#184): PA6-CF. SOURCED in this file — the safety factors
// below are computed for it (151/75 MPa dry/wet). Printing this in PETG-CF
// would pass every geometric gate here (identical STL) and fail on the robot.
// Print: PA6-CF, flat on the -Z face. SUPPORTS: NORMAL, under the servo-pocket
// end -- 555 mm^2 of FLAT underside floats 4.40mm above the bed for x < SUB_X0,
// cantilevered off the ramp with nothing anchoring its far end (measured
// 2026-08-03). This line used to stop at "flat on the -Z face", and because
// slice_plate.py reads its support setting from these headers, femur was the one
// leg part registered with supports=none. NOTE (LA-6, 2026-07-11, issue #24, extended
// 2026-07-11 per issue #24/LA-6 continuation): the underside is planarized/
// ramped down to the fork's floor (SUB_FLOOR -26.6) for x >= SUB_X0 -- see
// the SUB_X0/X1/X2 block below. This closes MOST of the old float, but NOT
// all of it: check_fit's own hip-pitch sweep (--sweep, r13-disc-interface
// excluded) shows COAX's yoke arms (coax.scad arm_plate(), both the inboard
// AND outboard arm share the same ARM_HALF_YZ=16 disc radius) sit a
// CONSTANT clearance = (femur-local x - 16.0) below the femur's underside,
// across the ENTIRE hfe sw ROM (rotation-invariant -- the disc is centered
// on the hfe axis, so distance depends only on radial position, not angle).
// RECONCILED (2026-07-11, rigorous probe: full-depth SUB_FLOOR candidate
// plane, femur-local x -5..45 x full slab width x hfe -86..+86 in 0.25deg /
// 0.5mm steps, r13 disc-interface excluded, vs the real coax_R.stl mesh):
// the true nearest coax edge is x=16.0 EXACTLY (clearance = x-16.0 to
// <0.001mm across every resolution tested) -- this IS the ARM_HALF_YZ=16
// disc radius, confirmed both by direct probe and by reading coax.scad's
// own constant. The prior x~19-20 / "4.8mm margin at x=24" claim in this
// file was WRONG (stale/coarser measurement) -- the real margin at the old
// SUB_X0=24 was 8.0mm, not 4.8mm, meaning ~7mm of the ramp was left on the
// table. SUB_X0 is now 17 (0.5mm design floor -> max-inboard would be 16.5;
// 17 keeps a clean 1.0mm true clearance, 2x the target and 2x LA-19's
// existing 0.4mm precedent, for a moving joint). x < SUB_X0 (=17) stays at
// the ORIGINAL SLAB_Z0 -22.2, unchanged, and still floats above the new
// deeper bed contact -> still wants support, but over a ~33mm hip-cap span
// (x -16.05..17) instead of the prior ~40mm (x -16.05..24). A same-strategy
// reorientation (print on a +-Y side face instead of fork-down) was
// evaluated and REJECTED: mesh overhang analysis on the unmodified STL
// shows it nearly DOUBLES the sub-45deg down-facing area (5949mm^2 vs
// 3881mm^2) because the open-top servo pocket becomes a horizontal bore.
// Do not read this file as claiming a fully support-free underside --
// budget support for the remaining ~33mm hip-cap span at print time.

include <leg_v6_common.scad>

// ---- cable groove cross-section (2026-08-06) --------------------------------
// TOP must equal the tunnel's 19.0: any narrower and the wire drops out of a
// 19 mm channel onto a ledge. BOTTOM adds a 1.5 mm/side 45 deg flare so the
// skin opening is a funnel, not a square-edged slot.
GRV_W_TOP = 19.0;
GRV_W_BOT = 22.0;


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
// SUB_X0: ramp start. RECONCILED 2026-07-11 (issue #24/LA-6 continuation):
// full-depth SUB_FLOOR candidate plane vs coax_R.stl, femur-local x -5..45,
// full slab width (9 y-bands refined to 65), hfe -86..+86deg in steps down
// to 0.25deg -- true nearest coax edge is x=16.0 EXACTLY (the ARM_HALF_YZ=16
// yoke-arm disc, coax.scad; clearance = x-16.0 to <0.001mm at every tested
// resolution, confirming it's rotation-invariant/exact, not sampling noise).
// The prior comment here (x~20, 4.8mm margin at x=24) was WRONG -- real
// margin at the old SUB_X0=24 was 8.0mm. Max-inboard for the >=0.5mm design
// floor (matches LA-19's precedent, don't run tighter) would be x=16.5;
// SUB_X0=17 keeps a clean 1.0mm true worst-case clearance (2x margin) on a
// moving joint. Also must clear the real M2 case-column screw at x=32.8
// (leg_v6_common.scad COL_PTS, femur-frame after the 180 rotate) -- still
// handled by the local screw-hole extension below (col_screw_ext_neg),
// unaffected since 32.8 is still well past the new SUB_X1.
SUB_X0    = 17;
SUB_X1    = 21;    // ramp end/full depth: rise 4.4 over run 4 = 47.7deg
                   // from horizontal -- a self-supporting overhang needs
                   // >=45deg from horizontal (STEEP, not shallow -- a
                   // shallow ramp is closer to the flat-ceiling worst case,
                   // not safer; first draft had this backwards at run=8/
                   // 28.8deg and was corrected). run stays 4 (SUB_X1 =
                   // SUB_X0+4) so the 47.7deg angle is unchanged by the
                   // SUB_X0 move. Coax clearance at the shallow end (x17,
                   // the tightest point) is 1.0mm true (see SUB_X0 note);
                   // clearance only grows moving outboard from there.
SUB_X2    = 73;    // flat continuation to here. The fork hull is a rounded cap
                   // (cylinders r=TIP_R=16.05 centered at FORK_X0=72), so it
                   // only reaches FULL width (y +-SLAB_W/2) at x72 -- at x60 it
                   // covers only y+-10.7. Ending the full-width fill at 60 left
                   // TRIANGULAR floating gaps at the outer y-edges x60..72
                   // (the "doesn't merge cleanly into the tibia-servo fork"
                   // notch). Extend to 73 (1mm into the full-width fork) so the
                   // fill overlaps the fork at full width -> clean merge.

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
// femur-frame) sits past SUB_X1 (11.8mm clear of it, 2026-07-11 SUB_X0/X1
// move to 17/21), i.e. now under a full SUB_FLOOR-deep floor instead of the
// original SLAB_Z0 -- its shared-module bore (FLOOR_BOT-1 .. FLOOR_BOT+7.1)
// and countersink (cut at FLOOR_BOT-EPS) no longer reach the true (deeper)
// exterior. Local extension only -- does NOT touch leg_v6_common.scad, so
// tibia/coax are unaffected.
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
            // is now ramped/planar for x >= SUB_X0 (17), but the x < SUB_X0
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
        // are all >= SUB_X1 (21), i.e. already sitting on the new SUB_FLOOR
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
        // x0 = 36, NOT 40 (2026-08-05). LA-1 made this groove reach the tunnel
        // FLOOR; it never checked the groove reached it over enough LENGTH. The
        // tunnel ends at x42.4, so starting at 40 left a 2.4 mm downward slot --
        // against a servo connector head MEASURED at 9.8 x 4.6. A O4.6 sphere
        // cannot traverse it (flood-fill verified), which is consistent with
        // Aiden having to open this exact hole with a file and pliers on the
        // 2026-08-02 femur. Starting at 36 gives a 6.4 mm overlap and it passes.
        // Ramped ends -- see tibia.scad for the reasoning (CR-6 precedent: no
        // square re-entrant corners on this part's tension face). Taper starts
        // at x34 so the near ramp does not eat the tunnel overlap; full depth
        // by x37, tunnel floor broken at ~x36.3 against a tunnel ending x42.4.
        // Width matched to the tunnel + chamfered mouth -- see tibia.scad for
        // the reasoning. Same 1.5 mm/side ledge existed here and this is the
        // part Aiden actually had to file and plier open.
        hull() {
            translate([34, -GRV_W_BOT/2, SUB_FLOOR - EPS]) cube([EPS, GRV_W_BOT, EPS]);
            translate([37, -GRV_W_BOT/2, SUB_FLOOR - EPS]) cube([16, GRV_W_BOT, EPS]);
            translate([37, -GRV_W_TOP/2, -19.05 - EPS]) cube([16, GRV_W_TOP, EPS]);
            translate([56 - EPS, -GRV_W_BOT/2, SUB_FLOOR - EPS]) cube([EPS, GRV_W_BOT, EPS]);
        }
        // zip anchors: flank the tunnel exit + at the block edge.
        // LA-4 fix (2026-07-11): h=12 was a BLIND pocket (top z-11.2, 25.9mm
        // of solid slab remained above it to SLAB_Z1 14.7) -- a zip tie could
        // not loop through to clamp cable_clip. h=40 matches the x62/84
        // through-hole convention elsewhere in this file (top z16.8, 2.1mm
        // clear past SLAB_Z1) -- genuine through-holes, ray-cast verified.
        // LA-6: both sit at x >= SUB_X1 (21), i.e. on the new SUB_FLOOR
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
