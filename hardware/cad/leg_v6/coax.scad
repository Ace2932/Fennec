// =============================================================================
// V6 Coax (rev 2) — houses the HAA STS3215, yoke-drives the femur at HFE.
// =============================================================================
// Local frame (RIGHT leg; mirror for left):
//   haa axis = Y AXIS through the origin (spline). Horn faces -Y (shoulder).
//   +X = OUTBOARD. +Z = up.
//   hfe axis = X line at (y = +11.6, z = -9.5)  [MEASURED, A360 assembly]
//   femur mid-plane at x = +33.8  ->  foot 33.8 + 30.5 = 64.3 = IK d ✓
//
// Joints:
//   * SHOULDER yokes this servo: front arm bolts the haa horn; the shoulder's
//     rear-arm boss reaches through THIS part's floor window and bolts the
//     haa BOTTOM WHEEL (rev-2 pattern, both sides bolted)
//   * FEMUR yoke: outboard arm (INTEGRAL) at x 56.2..60.2 carries a Ø19 boss
//     inboard to 51.5 = the femur wheel face, and bolts it. Inboard (horn)
//     side is now a REMOVABLE plate (coax_hfe_plate.scad, #53 fix
//     2026-07-11) bolted to this bridge -- the old integral inboard arm
//     made this a rigid closed U with no femur insertion path. Assembly:
//     femur slides in from the open inboard side, wheel bolts to the
//     integral outboard boss, THEN coax_hfe_plate bolts on to capture the
//     horn. See that file for the horn coupling + mount geometry.
//   * cables: bay faces +Y (rear); tunnel exits the BOTTOM end toward the
//     femur — wires drop down the leg. CALIPER-CONFIRMED 2026-07-10: the
//     servo body + cable dropping out the bottom needs ~37mm; the pocket's
//     vertical drop-channel is ~52mm (coax z -38.4..+13.8) → ~15mm spare,
//     clears. NB the cable routes out the BOTTOM, NOT beside the servo —
//     the pocket WIDTH is only 25.4mm (fits the 24.8 case + ~0.6, no room
//     for a cable alongside). Harness plan #31.
//
// Print: rear face (+Y) down; supports under the yoke bridge span.
//
// ASSEMBLY RULE (backlog #18 / LA-14, --cable WARN gate LA-20): the HIP
// service loop anchored at this part's tunnel-exit shrinks to ~60-79mm
// separation across hfe ROM, below the >=40mm-radius spec. Fold hfe to
// its mechanical limit FIRST, THEN zip the loop, so it's slack (not
// taut) at full fold. See leg_v6 README "Free-loop length" note.

include <leg_v6_common.scad>

HFE_Y     = 11.6;
HFE_Z     = -9.5;
FEMUR_MID = 33.8;

BLK_X  = CASE_HW + CLR_POCKET + WALL;     // ±15.85
BLK_Y0 = -HORN_Z1;                        // -17.2 front (horn-face plane)
BLK_YF = -FLOOR_BOT;                      // +22.2 rear (floor bottom)

ARM_IN_X1  = FEMUR_MID - HORN_Z1;            // 16.05 (femur horn seat face;
                                              // was stale at 16.6). #53 fix
                                              // (2026-07-11): this used to
                                              // also be arm_plate()'s FRONT
                                              // face -- the inboard arm is
                                              // now a SEPARATE bolt-on part
                                              // (coax_hfe_plate.scad); see
                                              // that file for ARM_IN_X0's
                                              // replacement (PLATE_X0).
ARM_OUT_X0 = FEMUR_MID - YOKE_BOT_IN;        // 56.2 (femur floor bottom +0.2)
ARM_OUT_X1 = ARM_OUT_X0 + ARM_THK;           // 60.2
ARM_HALF_YZ = 16;
BRIDGE_Z0  = 7.4;                            // femur disc sweep tops at 6.35; raised 0.5 after a corner graze at the sweep gate

// #53 BLOCKER fix (2026-07-11): the coax's femur yoke was a rigid closed U
// (integral inboard arm + bridge + integral outboard arm) -- no removable
// side, so the femur's horn+wheel disc pack had NO insertion path. Mirrors
// the KFE (knee_arm.scad) / HAA (shoulder_plate.scad) pattern: the OUTBOARD
// (wheel-boss) side stays integral; the INBOARD (horn) side is now a
// separate bolt-on plate, coax_hfe_plate.scad.
//
// INSERTION AXIS FINDING (trimesh sweep, all 6 axis directions tested):
// the femur+HFE-servo assembly's real insertion path is +Y (REARWARD
// translation), not axial +-X as first assumed -- both X directions stay
// solid-blocked even with the arm gone (the HAA housing's own pocket wall
// blocks -X toward the horn side; the integral outboard arm blocks +X).
// +Y is clean full-travel (0 hits, 31k-pt sample, 0..70mm) once (a) the
// inboard arm is gone and (b) the main block's own wall in that footprint
// is ALSO bored open (see PLATE_X0 clearance cut below -- removing just
// the arm was NOT sufficient, mesh-probe confirmed real block material
// independently fills that footprint) and (c) a small sharp-corner graze
// at (BLK_X,BLK_YF) is notched (see the corner-notch cut, measured 0.95mm
// penetration). Assembly: femur approaches from behind the coax (+Y),
// slides forward (-Y) until horn/wheel align at Y=HFE_Y, wheel bolts to
// the integral outboard boss, THEN coax_hfe_plate bolts on to capture the
// horn -- same net result the task asked for ("femur slides in, wheel
// bolts first, plate captures the horn"), the mechanism is a Y-slide-and-
// seat rather than a pure axial slide.
//
// coax_hfe_plate MOUNT (2026-07-11, revised after a 2nd finding): first
// attempt put the mount bolts OUTBOARD along the bridge (x18-25) -- but the
// plate's own disc naturally tops out at z=6.5 (r=ARM_HALF_YZ=16 around the
// HFE axis), z 7.4..13.4 is the BRIDGE's own domain, and reaching a tab up
// to bolt directly under the bridge there re-enters the femur's r16.7
// swept-clearance keepout below z~7.3 -- nowhere near enough headroom.
// Splitting the bridge itself to give the plate a same-height tab (tried)
// left the coax's own outboard-arm/bridge stub DISCONNECTED from the main
// block with no other part installed (mesh_health: 2 bodies, unprintable
// standalone) -- rejected.
// FIX: stay INBOARD instead -- mount the plate entirely within its own disc
// footprint (x=PLATE_X0..ARM_IN_X1, i.e. x<16.1, before the r16.7 keepout
// even starts) AND below the bridge (z<BRIDGE_Z0), not through it -- these
// two parts don't need to share X to avoid collision, only Z: the plate's
// disc can share (x,y) with the bridge as long as it stays under z=7.4
// (the bridge's own bottom face) while the bridge stays above it. A THIRD
// finding (2nd revision) confirmed the "spare material above the disc
// bore" isn't a thin independent cap -- it mesh-probes as the BRIDGE
// ITSELF (same 6mm-thick rib the original x18-25 attempt already found too
// thin for a blind HEATSET_L=6.2 bore). Still not enough for a blind
// insert -- FIX: THROUGH-BOLT + captured M3 nut (not a heat-set) run from
// the block's true top face (z=13.4) down THROUGH the bridge, continuing
// through open air (below the bridge, above the disc-bore's own natural
// ~z6.5 peak) into a small local "ear" raised off the plate's disc top (a
// <=1mm bump closing that gap -- see coax_hfe_plate.scad) with its own
// clearance hole, nut captured at the ear's underside (accessible before
// the plate is offered up -- the nut is dropped/glued in ahead of time).
// Y picked at the disc's own tallest point (near HFE_Y=11.6) to minimize
// the ear's bump height. Mesh-verified clear of the corner-notch, the
// disc-bore, and the femur's r16.7 keepout (irrelevant here -- x<16.1).
PLATE_MT_X = [13.5, 15.5];
PLATE_MT_Y = [8, 15];
// coax_hfe_plate's disc back face -- and the depth this coax body must be
// bored open to (see the PLATE_X0 clearance cut below). 12.9: the HAA
// servo's own case reaches x=12.4 max in its installed pose (CASE_HW,
// MEASURED via direct servo-vertex check against the coax_pose transform)
// -- 12.9 keeps 0.5mm clear of the actual servo body (matches CLR_POCKET's
// own 0.45 slip-fit convention), not just the pocket-cavity void boundary.
PLATE_X0 = 12.9;

module arm_plate(x0, x1) {
    hull() {
        translate([x0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = x1 - x0);
        translate([x0, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
            cube([x1 - x0, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
    }
}

module coax_v6() {
    difference() {
        union() {
            // haa pocket block
            translate([-BLK_X, BLK_Y0, -38.4])
                cube([2*BLK_X, BLK_YF - BLK_Y0, 38.4 + 13.4]);
            // pocket platform, transformed with the pocket
            rotate([0, -90, 0]) rotate([90, 0, 0]) pocket_platform_pos();
            // femur yoke: bridge, outboard arm + wheel boss. #53 fix: the
            // INBOARD (horn) arm is no longer integral -- see coax_hfe_plate.scad
            arm_plate(ARM_OUT_X0, ARM_OUT_X1);
            translate([BLK_X - 2, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
                cube([ARM_OUT_X1 - BLK_X + 2, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
            // outboard-arm ROOT DOUBLER (backlog #26, stress audit
            // 2026-07-06): the arm-to-bridge junction was the only member
            // on the robot under SF 15 — ~14 MPa at the 4-thick root under
            // a 20 N lateral/turning foot load = fatigue SF ~1.9 per
            // stride. 2-thick outboard gusset over the junction (z 0..13.4,
            // tapering out by z -1.5) doubles the root modulus -> ~6 MPa.
            // Taper stops ABOVE the wheel-screw head zone (top BCD heads
            // reach z -1.95; ARM_THK itself is shared by every couple cut
            // and cannot change). L mirror: symmetric in y, mirrors clean.
            hull() {
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, 0])
                    cube([2, 2*ARM_HALF_YZ, 13.4]);
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, -1.5])
                    cube([0.5, 2*ARM_HALF_YZ, 14.9]);
            }
            // outboard-arm boss reaching the femur wheel (56.2 -> 51.5)
            translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
                wheel_boss_pos();
            // front strap pads (0.8 proud: the case top cap ridge stands
            // 0.2 proud of the horn-face plane); full wall-width blocks
            // outboard edge held to x15.6: at 16.6 it grazed the femur rim
            // plane at full hip swing (sweep-gate find)
            for (sx = [-1, 1])
                translate([min(sx*12.6, sx*15.6), BLK_Y0 - 0.8, -36])
                    cube([3, 0.8 + EPS, 10]);
        }

        // ---- HAA pocket: spline = Y axis, horn -Y, bulk down ----
        rotate([0, -90, 0]) rotate([90, 0, 0]) sts_pocket_neg(extra_top = 25);

        // front strap pilots (through the bosses into the wall rims)
        for (sx = [-1, 1])
            translate([sx*14.25, BLK_Y0 - 0.8 - EPS, -31]) rotate([-90, 0, 0])
                cylinder(d = 2.05, h = 8.8);

        // ---- HFE couplings on the X axis at (HFE_Y, HFE_Z) ----
        // #53 fix (2026-07-11): the inboard horn coupling (was horn_couple_neg()
        // + its pocket-wall screw-head counterbores, cut into the old integral
        // arm) moved ENTIRELY to coax_hfe_plate.scad -- that part is now a
        // self-contained bolt-on, same pattern as knee_arm.scad/shoulder_plate.scad
        // (horn_couple_neg() cut into THEIR OWN plate, not the parent). Nothing
        // left to cut here for it.
        //
        // coax_hfe_plate CLEARANCE bore (2026-07-11, mesh-probe find): just
        // removing arm_plate(ARM_IN_X0,ARM_IN_X1) from the union does NOT by
        // itself free up room for the new plate -- the main HAA-pocket block
        // (BLK_X=15.85 half-width) independently fills nearly this whole
        // footprint (direct trimesh probe: x=13.05..16.0, r<=15.5 around the
        // HFE axis read 56/60 SOLID even after the arm was removed). That
        // wall is real block material, not leftover arm -- coax_hfe_plate
        // would collide with it if left in place. Bore it out (plain
        // cylinder, NOT the full arm_plate() hull -- the hull's box lid
        // reaches z 7.4..13.4, which is the BRIDGE's own domain now, and
        // bridge must stay solid for the mount bores below). r=ARM_HALF_YZ
        // matches the plate's own disc radius; PLATE_X0=12.9 keeps 0.5mm
        // clear of the actual HAA servo body (not just the pocket void).
        translate([PLATE_X0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = ARM_IN_X1 - PLATE_X0);
        // coax_hfe_plate EAR clearance (2026-07-11, mesh-probe find): the
        // r=ARM_HALF_YZ bore above is a plain cylinder, so away from
        // Y=HFE_Y its own top curves BELOW z=7.4 (e.g. z~5.1 at y=5) --
        // real coax wall material survives in that gap (bore-top..7.4) at
        // the plate's mount-ear Y stations, which collided with
        // coax_hfe_plate.scad's ears (mesh-verified: 1400+/8000 plate pts
        // landed inside the coax before this cut). Match the ears exactly
        // (same PLATE_MT_Y/EAR_R/EAR_Z1) so both sides agree.
        PLATE_EAR_R = 4.0; PLATE_EAR_Z1 = 7.35;
        for (my = PLATE_MT_Y)
            translate([PLATE_X0, my - PLATE_EAR_R, HFE_Z])
                cube([ARM_IN_X1 - PLATE_X0, 2*PLATE_EAR_R, PLATE_EAR_Z1 - HFE_Z]);
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0]) {
            // outboard arm + boss = "bottom arm" (+z -> -x inboard)
            wheel_couple_neg();
        }
        // coax_hfe_plate mount: 4x M3 through-bolt (captured nut inside the
        // empty HAA pocket cavity, not a heat-set) -- see the PLATE_MT_X/Y
        // comment above for why. Punches from the block's true top face
        // (z=13.4) down into the pocket cavity void below.
        for (mx = PLATE_MT_X, my = PLATE_MT_Y)
            translate([mx, my, -5])
                cylinder(d = M3_CLEAR, h = 13.4 + 5 + EPS);

        // side marker: 1 dot = RIGHT (L wrapper adds a 2nd).
        // LA-2 fix (2026-07-11): the old site (6, BLK_Y0-EPS, 8) targeted
        // the HORN-FACE plane (y=BLK_Y0=-17.75) -- but that plane is the
        // HAA pocket's open coupling face (spline=Y, horn faces -Y per the
        // file header), not a closed wall: ray-cast confirmed 0 solid hits
        // across the whole scanned x/z grid there. Relocated to the REAR
        // face (y=BLK_YF=+22.2, the pocket-floor-equivalent plane, closed
        // except at the column-screw/wheel-window/tunnel cuts): (x=-12,
        // z=8) ray-cast confirmed solid to a depth of >=1.5mm (real
        // material, clear of those cuts) and air just outside y=22.2.
        translate([-12, BLK_YF + EPS, 8]) rotate([90, 0, 0]) cylinder(d = 3, h = 1);

        // vent window, OUTBOARD (-X) wall only (the inboard wall carries
        // the femur-yoke arm root)
        translate([-BLK_X - 1, -8, -30]) cube([4.5, 16, 24]);

        // zip anchors flanking the bottom cable-tunnel exit (hip service
        // loop anchors here; the femur's first anchor takes the other end)
        // LA-16 fix (2026-07-11): the old pair sat on the OUTBOARD wall
        // (x=-BLK_X-1, y=3±5) but the tunnel exit (common-frame tunnel,
        // rotated into this part) opens at world x~0, y~16.85, z
        // -42.4..-31.2 -- ~22mm away, straight path through solid ~50% of
        // it (raw 90° corner). Relocated to genuinely flank the tunnel:
        // grid-scanned the real mesh at the tunnel's own z-band and found a
        // clean gap x[-9,9], y[14,19] at z=-36 (below z=-34, where the HAA
        // pocket cavity ALSO overlaps and thins the side walls to 3.2mm).
        // Holes now start at x=∓7 (inside the open tunnel void -- reachable
        // from the tunnel, robust CSG overlap) and punch straight out
        // through the side wall (genuine through-hole, not a blind pocket --
        // matches the femur/tibia LA-4 convention: a blind pocket can't
        // loop a zip tie). y=17 matches the tunnel's own y-center.
        for (sx = [-1, 1])
            translate([sx * 7, 17, -36]) rotate([0, sx*90, 0])
                cylinder(d = 3.2, h = BLK_X - 6);

        // femur swept clearance between the arms (stops at the boss face)
        translate([ARM_IN_X1 + EPS, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = 16.7, h = (FEMUR_MID - WHEEL_Z0) - ARM_IN_X1 - 0.1);   // disc r16.05 + 0.65 (was 16.4/0.35 — under print tol)

        // #53 fix, insertion-sweep corner graze (2026-07-11): with the
        // inboard arm gone, the femur+HFE-servo assembly's real insertion
        // path is a +Y (rearward) translation, not axial +-X (both X
        // directions stay solid-blocked -- the HAA housing's own pocket
        // wall on the horn side, and the integral outboard arm on the wheel
        // side). That +Y sweep is CLEAN except a small graze (trimesh
        // sweep-checked, max 0.95mm penetration, <=16 sample pts) against
        // the main block's sharp rear-outboard-top corner (x=BLK_X,
        // y=BLK_YF) -- a plain 90-degree box corner with zero fillet. This
        // corner sits OUTSIDE the HAA pocket cavity's own Y footprint
        // (cavity Y max ~15.95 < BLK_YF 22.2) -- pure wall/floor material,
        // not near the servo cavity or the horn coupling -- safe to notch.
        // 2mm square notch (>2x the 0.95mm measured penetration), full
        // block Z height (the sweep was only angle-sampled at 2mm steps, so
        // the danger zone may extend past the 2 sampled z-bands on this
        // same sharp edge). Kept SMALL and mesh-probe-verified clear of the
        // PLATE_MT_X/Y mount bores (now inboard, x<=15.5, well clear of
        // this x>=13.85 notch's own footprint by construction).
        translate([BLK_X - 2, BLK_YF - 2, -38.4 - EPS])
            cube([2 + 1, 2 + 1, 38.4 + 13.4 + 2*EPS]);   // +1: punch 1mm past
                                                          // the block's own
                                                          // edge (BLK_X/BLK_YF)
                                                          // so the cut face
                                                          // isn't coincident
                                                          // with it (coincident
                                                          // faces gave a non-
                                                          // manifold mesh)
    }
}

coax_v6();
