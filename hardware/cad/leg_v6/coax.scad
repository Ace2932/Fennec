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
//     side: LOAD/RETENTION split (#67 fix, 2026-07-12, supersedes the #53
//     removable-plate design): the #53 fix bored the WHOLE inboard-arm disc
//     (x 12.9..16.05, r16 about the HFE axis) open to clear femur insertion,
//     making the entire arm a removable plate -- but the disc's own
//     X-thickness (3.15mm) turned out too thin for ANY captured hardware
//     (nut, heat-set) mounted through it, and every fastener redesign
//     attempted against that thin plate ended up either sealed (unreachable)
//     or reaching for a self-tap (rejected outright, see the hard rule).
//     MEASURED (trimesh insertion-sweep probe, femur+HFE-servo assembly
//     swept +Y 0..68mm against every point in the old bore): the femur
//     assembly does NOT sweep the whole disc -- only a wedge (the HFE
//     servo's own embedded body, which travels WITH the femur and whose
//     horn bolts to this yoke). Clear (integral) at the back (x<13.3);
//     narrow high-y/mid-z band swept in the middle (13.3..14.9); nearly the
//     whole disc only right at the front (>=14.9, open to the horn seat).
//     Shrink the bore to that wedge -- coax_hfe_bore() below -- and leave
//     the rest INTEGRAL coax block (the STUB, continuous with the main
//     body, carries the joint's compressive load same as the old integral
//     arm did). A small CAP (coax_hfe_plate.scad, same file, redesigned)
//     fills just the bored wedge, captures the horn (all 4 M2.5 bolts --
//     MEASURED, none of the 4 land outside the swept envelope, see that
//     file), and slides in AFTER the femur is seated. The cap fastens to
//     the stub via a REAL M3 heat-set (coax_hfe_ear_channel() /
//     coax_hfe_fastener_neg() below) -- axis +Y (not the disc's thin X
//     axis), embedded in the BRIDGE (integral, 46mm deep in Y, plenty for
//     a 6.2mm insert) via a narrow riser + wide head that stays clear of
//     the femur's own r16.7 rotation keepout the whole way (that keepout
//     tops out at z=7.2, strictly below the bridge's own z=7.4 floor -- see
//     coax_hfe_ear_channel()'s own comment). Assembly unchanged from #53:
//     femur slides in (+Y) with the wedge open, wheel bolts to the
//     integral outboard boss, THEN the cap slides on and its heat-set bolt
//     draws it against the stub to capture the horn.
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
// (wheel-boss) side stays integral; the INBOARD (horn) side needs SOME
// removable feature so the femur can pass. #53 made that removable feature
// the WHOLE disc (bore r=ARM_HALF_YZ=16, x=PLATE_X0..ARM_IN_X1); #67 (below)
// shrinks it to just the femur's real swept wedge, leaving most of the disc
// INTEGRAL.
//
// INSERTION AXIS FINDING (trimesh sweep, all 6 axis directions tested):
// the femur+HFE-servo assembly's real insertion path is +Y (REARWARD
// translation), not axial +-X as first assumed -- both X directions stay
// solid-blocked even with the arm gone (the HAA housing's own pocket wall
// blocks -X toward the horn side; the integral outboard arm blocks +X).
// +Y is clean full-travel once (a) the swept wedge is open and (b) a small
// sharp-corner graze at (BLK_X,BLK_YF) is notched (see the corner-notch
// cut, measured 0.95mm penetration). Assembly: femur approaches from
// behind the coax (+Y), slides forward (-Y) until horn/wheel align at
// Y=HFE_Y, wheel bolts to the integral outboard boss, THEN the cap
// (coax_hfe_plate.scad) slides on and bolts to capture the horn.
//
// #67 fix (2026-07-12): LOAD/RETENTION split. MEASURED (trimesh
// insertion-sweep probe: femur_R.stl + knee_arm.stl + the HFE-embedded
// servo -- pts0, transformed the SAME way insertion_checks() does --
// tagged per-source and swept +Y in 0.5mm steps, t=0..68): every point
// that ever lands inside the old x=PLATE_X0..ARM_IN_X1, r<=ARM_HALF_YZ
// bore is tagged 'servo' -- 100% of the hits. Neither femur_R.stl's own
// solid (x>=16.05 always, a pure +Y translation never changes x) nor
// knee_arm.stl (mounted at the femur's OWN knee end, its transformed
// footprint sits at x=12.05..16.05 but z=-132..-68, nowhere near this
// zone's z=-25.5..6.5 disc) ever crosses into this bore -- it's the HFE
// SERVO's own case (embedded in the femur, horn bolted to this yoke,
// travels rigidly with it) that needs the clearance. Its footprint here:
//   x<13.3            : NEVER swept (0 hits at any sampled t) -> INTEGRAL
//   x=13.3..14.9 (mid) : swept only in a narrow high-y/mid-z band
//                        (measured y>=9.0..27.6, z=-12.1..-6.8)
//   x>=14.9 (front)    : swept over nearly the whole disc (measured down to
//                        y=1.6 at the front face) -- full-disc bore kept
//                        here for robustness/simplicity, not hand-fit to
//                        the last mm of the (very thin, load-free) low-y
//                        sliver that stays technically clear even there.
// coax_hfe_bore() below cuts exactly that wedge (with margin: mid-band x
// starts 0.2mm before the first measured hit, y/z pad ~1-2mm, front-band
// starts 0.1mm before the measured near-full-disc jump at x=15.00). The
// STUB is everything else in the old disc footprint: the ENTIRE x<13.3
// slab (full r16 disc) plus most of x=13.3..14.9 (all but the mid-band
// rectangle) -- both remain continuous, single-body coax block, verified
// via mesh_health.py.
//
// #67 FASTENER (supersedes the #53/rejected-attempt mount history below):
// the disc's own X-thickness (3.15mm, PLATE_X0..ARM_IN_X1) is too thin for
// ANY captured hardware mounted through it, at ANY (y,z) -- MEASURED via a
// dilated depth probe over the whole disc footprint (max clear X-run
// anywhere: 3.25mm, at the disc's own low-y edge) -- so the fastener does
// NOT live in the disc at all. It lives in the BRIDGE (z=BRIDGE_Z0..13.4,
// 46mm deep in Y) instead, reached by a narrow riser (coax_hfe_ear_channel()
// below) that rises from the cap's own mid-band body (x=STUB_MIDX0..
// STUB_MIDX1, safely x<16.05, so it NEVER enters the femur's r16.7 rotation
// keepout regardless of z) up to the bridge's underside, then widens into a
// HEAD once past z=BRIDGE_Z0=7.4 -- safe to widen there because the r16.7
// keepout (cylinder from x=ARM_IN_X1+EPS outward) tops out at
// z=HFE_Z+16.7=7.2, strictly BELOW the bridge floor (7.4): nothing at
// bridge height can ever be inside that keepout, at any x. The head holds
// a real M3 heat-set (HEATSET_D/HEATSET_L, unchanged spec) axis +Y, bored
// from the bridge's own open rear tip (y=EAR_Y1=27.6 -- 0.65mm shy of the
// y>=28.25 haa-roll/shoulder clearance limit an earlier attempt measured in
// this same z-band) inward into solid bridge material. See
// coax_hfe_ear_channel()/coax_hfe_fastener_neg() below and
// coax_hfe_plate.scad's own header for the cap-side ear + reachability
// proof.
//
// (superseded mount history, kept for context: the very first #53 mount
// put through-bolts at x18-25 along the bridge and found the same z~7.3
// keepout wall this fix routes around; a 2nd revision tried a through-bolt
// + captured nut from the coax top through the 6mm bridge and found the
// bridge too thin for a Z-axis blind insert -- the SAME reason #67's
// fastener uses the bridge's Y-axis depth (46mm) instead of its Z-axis
// depth (6mm).)
STUB_MIDX0 = 13.3;   STUB_MIDX1 = 14.9;   // mid-band bore x-span
STUB_MIDY0 = 7.0;    STUB_MIDY1 = 28.0;   // mid-band bore y-span
STUB_MIDZ0 = -13.0;  STUB_MIDZ1 = -6.0;   // mid-band bore z-span
STUB_FRONTX0 = 14.9;                      // front-band: full r16 disc from
                                           // here to the open horn seat

EAR_X0 = STUB_MIDX0; EAR_X1 = STUB_MIDX1;   // riser: same x-span as the
                                             // mid-band bore (stays x<16.05,
                                             // clear of the femur keepout
                                             // at every z)
EAR_Y0 = 24.0;        EAR_Y1 = 27.6;        // ear/head y-span == the
                                             // bridge's own natural rear-tip
                                             // extent (2*ARM_HALF_YZ+HFE_Y)
HEAD_X0 = 12.9;       HEAD_X1 = 18.9;       // wide head, z>=BRIDGE_Z0 ONLY
                                             // (see the keepout-exempt note
                                             // above) -- room for the M3
                                             // clearance hole + SHCS head
HEATSET_CX = (HEAD_X0 + HEAD_X1) / 2;       // 15.9
HEATSET_CZ = (BRIDGE_Z0 + 13.4) / 2;        // 10.4, bridge mid-height

// coax_hfe_plate's disc back face -- and the depth this coax body must be
// bored open to (see the coax_hfe_bore() cut below). 12.9: the HAA
// servo's own case reaches x=12.4 max in its installed pose (CASE_HW,
// MEASURED via direct servo-vertex check against the coax_pose transform)
// -- 12.9 keeps 0.5mm clear of the actual servo body (matches CLR_POCKET's
// own 0.45 slip-fit convention), not just the pocket-cavity void boundary.
PLATE_X0 = 12.9;

// #67 bore: mid-band partial box + front-band full disc (see the header
// comment above for the measured wedge this covers).
module coax_hfe_bore() {
    translate([STUB_MIDX0, STUB_MIDY0, STUB_MIDZ0])
        cube([STUB_MIDX1 - STUB_MIDX0, STUB_MIDY1 - STUB_MIDY0,
              STUB_MIDZ1 - STUB_MIDZ0]);
    translate([STUB_FRONTX0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
        cylinder(r = ARM_HALF_YZ, h = (ARM_IN_X1 + 0.1) - STUB_FRONTX0);
}

// #67 ear channel: narrow riser (stays inboard, x<16.05 -- never enters the
// femur keepout) connecting the cap's mid-band body up to the bridge
// underside, then a wide head (safe to widen -- z>=BRIDGE_Z0 is
// unconditionally outside the femur's r16.7 keepout, see header) that
// holds the M3 clearance hole + head counterbore into the cap's ear.
module coax_hfe_ear_channel() {
    translate([EAR_X0, EAR_Y0, STUB_MIDZ1])
        cube([EAR_X1 - EAR_X0, EAR_Y1 - EAR_Y0, BRIDGE_Z0 - STUB_MIDZ1]);
    translate([HEAD_X0, EAR_Y0, BRIDGE_Z0])
        cube([HEAD_X1 - HEAD_X0, EAR_Y1 - EAR_Y0, 13.4 - BRIDGE_Z0]);
}

// #67 fastener negative: bolt clearance + SHCS head counterbore through the
// cap's ear (open at y=EAR_Y1, the bridge's own exterior rear-tip face),
// THEN a real M3 heat-set bore (HEATSET_D/HEATSET_L, unchanged spec) from
// y=EAR_Y0 (where the ear ends) further -Y into solid, integral bridge
// material -- axis +Y the whole way (never the disc's thin X axis).
module coax_hfe_fastener_neg() {
    // rotate([90,0,0]): local +Z -> world -Y, so each cylinder (naturally
    // h along +Z from its base) extends in -Y from its translate point --
    // i.e. INWARD, from the open rear face toward the stub.
    translate([HEATSET_CX, EAR_Y1 + EPS, HEATSET_CZ]) rotate([90, 0, 0]) {
        cylinder(d = M3_CLEAR, h = (EAR_Y1 - EAR_Y0) + 2*EPS);
        cylinder(d = 5.5, h = 2.2 + EPS);   // head counterbore, recessed
    }
    translate([HEATSET_CX, EAR_Y0, HEATSET_CZ]) rotate([90, 0, 0])
        cylinder(d = HEATSET_D, h = HEATSET_L + EPS);
}

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
        // #67 fix: cap clearance = just the measured femur-swept wedge (was
        // the FULL r=ARM_HALF_YZ disc under #53) -- see coax_hfe_bore()'s
        // own comment above for the measurement. Everything else in the old
        // disc footprint stays INTEGRAL stub material.
        coax_hfe_bore();
        // #67 fastener: ear channel (riser + head, cap-side clearance) and
        // the heat-set bore itself -- see both modules' own comments above.
        coax_hfe_ear_channel();
        coax_hfe_fastener_neg();
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0]) {
            // outboard arm + boss = "bottom arm" (+z -> -x inboard)
            wheel_couple_neg();
        }

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
        // same sharp edge). Kept SMALL; its footprint (x=13.85..16.85,
        // y=20.2..23.2) sits 0.8mm clear of the #67 ear/head zone
        // (y=EAR_Y0..EAR_Y1 = 24.0..27.6) by construction.
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
