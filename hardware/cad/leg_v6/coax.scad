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
//     X-thickness (3.15mm, the OLD #53 full-disc span PLATE_X0..ARM_IN_X1 --
//     NOT the #67 cap's own thickness, see below) turned out too thin for
//     ANY captured hardware (nut, heat-set) mounted through it, and every
//     fastener redesign attempted against that thin plate ended up either
//     sealed (unreachable) or reaching for a self-tap (rejected outright,
//     see the hard rule).
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
//     #7-fix (2026-07-16, load-analysis.md §7): the #67 cap's real
//     independent front-band thickness at the horn BCD bolts was only
//     1.15mm (NOT the 3.15mm above -- see the STUB_FRONTX0 note below) --
//     SF 2.5 wet, exactly on the floor -- and the single M3 clamp bolt
//     failed outright (SF 0.44 wet) under the conservative assumption that
//     the mid-band box's slip-fit can't react a +Z peel (its Z1 face is
//     flush/internal, no stub wall there). Fixed with two NEW standalone
//     bearing/engagement bands (BAND_* below, coax_hfe_bore()) bracketing
//     the horn-bolt BCD circle in already-measured never-swept territory --
//     thickens the cap to 2.75mm there AND gives it closed 4-wall (Y0/Y1/
//     Z0/Z1) stub engagement right at the load, killing the single-
//     fastener dependency. See load-analysis.md §7 for the full SF table.
//   * cables: bay faces +Y (rear); tunnel exits the BOTTOM end toward the
//     femur — wires drop down the leg. CALIPER-CONFIRMED 2026-07-10: the
//     servo body + cable dropping out the bottom needs ~37mm; the pocket's
//     vertical drop-channel is ~52mm (coax z -38.4..+13.8) → ~15mm spare,
//     clears. NB the cable routes out the BOTTOM, NOT beside the servo —
//     the pocket WIDTH is only 25.4mm (fits the 24.8 case + ~0.6, no room
//     for a cable alongside). Harness plan #31.
//
// MATERIAL BASIS (#184): PA6-CF — INFERRED, NOT SOURCED. Nothing in this file
// states a material. The inference is the leg batch: every part that mates to
// this one (shoulder, shoulder_plate, coax_hfe_plate, knee_arm) is PA6-CF, and
// this is the haa load path. CONFIRM before the first structural print.
// Print: PA6-CF, rear face (+Y) down; supports under the yoke bridge span.
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

// ---------------------------------------------------------------------------
// #226 OPTION C (2026-07-31): the removable member moves OUTBOARD.
//
// The inboard cap (coax_hfe_plate) is retired. It could never be installed:
// blocked in all six axes against the seated femur AND against a bare coax, in
// the #67 revision AND the pre-#7-fix one, while its seated pose was itself
// legitimate (boolean intersection with this part = 0.0 mm3). A valid final
// position with no path to it. Aiden's printed coax refused it on the bench;
// check_fit.removable_member_checks() now gates the class.
//
// So: the INBOARD arm becomes integral (arm_plate(PLATE_X0, ARM_IN_X1) below,
// replacing the bored wedge + cap), and the OUTBOARD arm + gusset + wheel boss
// become a separate bolt-on part, coax_hfe_block.scad. The femur then enters
// AXIALLY (+X, with the block off) instead of laterally -- this file's own #53
// header noted "+X blocked by the integral outboard arm", and making that arm
// removable is exactly what opens it. MEASURED clear, 0 pts over t=2..50mm.
//
// JOINT = MORTISE AND TENON, not bolts in tension. Any bridge-level interface
// sits ~22mm above the boss, so the 133 N cyclic axial load (20 N lateral foot
// -> 4.72 N.m / 35.5mm disc spacing) becomes ~2.95 N.m at the joint = ~490 N
// per bolt on a 10mm face, past M3 heat-set pull-out in wet PA6-CF. A
// concentric spigot would shorten the lever but there is no room: MEASURED,
// the femur occupies r 10..16 at the boss station. The tenon reacts the moment
// in BEARING over its own length (245 N on ~92 mm2 = 2.7 MPa) and the bolts
// drop to retention -- the same move #7-fix made for the cap, including its
// corollary that the key must be CLOSED both ways (a compression-only key
// cannot react peel), hence the shrink on y0/y1/z0/z1 and flush only at x1.
//
// MOUTH RULED OUT (#221 candidate F, retired with hfe_mouth_study.py). Before
// C, the idea was to keep the cap architecture and cut a rear MOUTH so the
// horn could slide out sideways. Measured with the mask removed: 4,477 hits,
// of which 2,339 are on the O19 INTEGRAL OUTBOARD boss -- not on the cap at
// all, so no mouth cut anywhere in the cap could ever reach them. The mouth
// cannot work, and not by a margin a better mouth closes. Recorded here
// because the study that proved it is retired.
//
// The geometry proof for THIS joint (and its negative control: at equal boss/
// bore radii the two graze at r 9.47..9.49 and both the femur and the block
// read trapped) lived in hfe_block_study.py, also retired -- check_fit's
// insertion_checks + removable_member_checks now gate the same properties
// against the shipped STLs, which is strictly better than a study that
// rebuilds them.
SPLIT_X     = ARM_OUT_X0;        // 56.2 -- block mating plane
BOSS_X0     = FEMUR_MID - WHEEL_Z0;   // 51.55 = the femur wheel contact face
BOSS_X0_CLR = BOSS_X0 - 2;            // bore starts a little inboard of it
BOSS_BORE_R = 10.0;              // boss r9.5 + 0.5. At EQUAL radii the boss and
                                 // bore graze at r 9.47..9.49 and both the femur
                                 // and the block read trapped (measured -- it is
                                 // hfe_block_study's negative control).
GROW_X0     = 40.0;              // bridge grows over x GROW_X0..SPLIT_X ...
GROW_Z1     = 16.0;              // ... to here, to host the mortise. CORRECTED
                                 // from 18.0: at 18 the grown bridge HITS the
                                 // shoulder at haa -40 (66 pts, inside the +-40
                                 // limit). An earlier headroom probe said 7.76mm
                                 // clear, but it sampled x 50..62 while the
                                 // growth is actually built over x 40..56.2 --
                                 // it measured a different volume than the one
                                 // built. 16.0 measures 0 pts at every swept
                                 // haa angle.
MORT_X0 = 46.4;  MORT_Y0 = 0.0;   MORT_Z0 = 9.5;
MORT_Y1 = 23.2;  MORT_Z1 = 13.5;   // 2.1mm wall below, 2.5 above  // mortise; x1 = SPLIT_X (open at the face)
CLR_TENON  = 0.15;               // same convention as CLR_KEY
BOLT_YS    = [5.0, 18.0];        // 2x M3 retention, cyclic 133/2 = 66 N each
BOLT_Z     = 11.5;               // vs ~175-245 N wet pull-out -> SF 2.6-3.7

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
// the disc's own X-thickness (3.15mm, PLATE_X0..ARM_IN_X1 -- the OLD #53
// full-disc span, not the #67/#7-fix cap's own thickness) is too thin for
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
                                           // here to the open horn seat.
                                           // NOTE: the cap's OWN independent
                                           // material at this front-band is
                                           // only HORN_SEAT-STUB_FRONTX0 =
                                           // 16.05-14.9 = 1.15mm -- NOT the
                                           // 3.15mm (PLATE_X0..ARM_IN_X1 =
                                           // 12.9..16.05) either .scad header
                                           // used to quote for "the cap's
                                           // thickness" -- 3.15mm was only
                                           // ever the OLD #53 full-disc
                                           // plate's span; measured load-
                                           // analysis.md §7a caught the
                                           // stale claim (2026-07-16). See
                                           // BAND_* below for the #7-fix that
                                           // actually thickens the bolt zone.

// #7-fix (2026-07-16, load-analysis.md §7 rework): load-analysis.md's
// first-article audit found the cap's real independent bearing section at
// the 4x horn BCD bolts was only 1.15mm (front-band alone, see the
// STUB_FRONTX0 note above) -- SF 2.5 wet, exactly on the floor -- AND the
// cap's ONLY stub engagement in the Z direction was one-sided (mid-band
// box's Z0 floor reacts compression; its Z1/X1 faces are flush/internal,
// see coax_hfe_plate.scad -- no wall reacts a +Z "peel" at all), so the
// single M3 clamp bolt was the sole path for that peel (SF 0.44 wet,
// FAILS). Fix: two NEW standalone engagement/bearing bands, same x-column
// as the mid-band bore (13.3..14.9, MEASURED never-swept there -- see
// coax_hfe_bore()'s own header), bracketing the horn-bolt BCD circle
// (all 4 bolts sit at r=7 about the hfe axis, z=-4.55/-14.45 -- both
// outside the mid-band bore's own z=-13..-6 span, confirmed via a direct
// trimesh probe of the built STLs, 2026-07-16) with >=0.5mm margin off the
// mid-band bore's own measured-swept z-limits (-12.1/-6.8) so neither band
// reopens that insertion clearance. Effect: (a) the cap's independent
// thickness at every bolt grows to front-band(1.15) + band(1.6) = 2.75mm
// (b) unlike the mid-band box, EVERY side of these bands (Y0,Y1,Z0,Z1) is a
// genuine stub-facing wall (no flush/internal escape) -- a slip-fit, but a
// CLOSED one: the cap cannot move +Z OR -Z here without compressing against
// real stub material, right at the load application point (near-zero lever
// arm for any local prying). This directly answers the "needs a real
// interference/engagement spec, not hope" bar -- the engagement is a
// measured, closed 4-wall pocket, not an assumption.
BAND_X0 = STUB_MIDX0;  BAND_X1 = STUB_MIDX1;      // 13.3..14.9, same column
BAND_Y0 = 3.0;   BAND_Y1 = 20.0;   // covers both bolt y's (6.65 low, 16.55
                                   // high) with >=3mm radial margin each
BAND_LO_Z0 = -17.0;  BAND_LO_Z1 = -12.6;   // brackets bolt z=-14.45; stops
                                            // 0.5mm clear of the mid-band
                                            // bore's own measured swept
                                            // floor (z=-12.1)
BAND_HI_Z0 = -6.3;   BAND_HI_Z1 = -2.0;    // brackets bolt z=-4.55; stops
                                            // 0.5mm clear of the mid-band
                                            // bore's own measured swept
                                            // ceiling (z=-6.8)
                                            // (CLR_KEY, the cap-side shrink
                                            // off these bands, lives in
                                            // coax_hfe_plate.scad only --
                                            // this file cuts the bands at
                                            // full size, same convention as
                                            // the mid-band bore above)

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
// #7-fix (2026-07-16): + two standalone bolt-bearing bands (see the BAND_*
// header comment above) -- same column, flanking z, never-swept territory.
module coax_hfe_bore() {
    translate([STUB_MIDX0, STUB_MIDY0, STUB_MIDZ0])
        cube([STUB_MIDX1 - STUB_MIDX0, STUB_MIDY1 - STUB_MIDY0,
              STUB_MIDZ1 - STUB_MIDZ0]);
    translate([STUB_FRONTX0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
        cylinder(r = ARM_HALF_YZ, h = (ARM_IN_X1 + 0.1) - STUB_FRONTX0);
    translate([BAND_X0, BAND_Y0, BAND_LO_Z0])
        cube([BAND_X1 - BAND_X0, BAND_Y1 - BAND_Y0, BAND_LO_Z1 - BAND_LO_Z0]);
    translate([BAND_X0, BAND_Y0, BAND_HI_Z0])
        cube([BAND_X1 - BAND_X0, BAND_Y1 - BAND_Y0, BAND_HI_Z1 - BAND_HI_Z0]);
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
            // femur yoke. #226 option C: the INBOARD (horn) arm is INTEGRAL
            // again -- it is the load-carrying, never-removed side now -- and
            // the OUTBOARD arm + gusset + wheel boss have left for
            // coax_hfe_block.scad. #53's inboard cap is retired; see the
            // option-C header above for why it could never be installed.
            arm_plate(PLATE_X0, ARM_IN_X1);
            // bridge, now ending at the block's mating plane
            translate([BLK_X - 2, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
                cube([SPLIT_X - BLK_X + 2, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
            // grown bridge section that hosts the mortise (see header).
            //
            // SQUARE STEP, DELIBERATELY, after trying the alternative. A 45deg
            // ramp here relieves the re-entrant corner at z=13.4 -- but the
            // ramp eats the roof over the M3 bore, which starts 0.2mm outboard
            // of GROW_X0: measured roof 0.4mm at x=40.5 and 1.4mm at 41.5,
            // against the >=1.5mm boss-wall spec. Moving the bore clear of the
            // ramp costs 2.2mm of tenon, and the tenon length is what sets the
            // floor bearing load. A true FILLET would need material added
            // INBOARD of x=40, which the shoulder sweep forbids (measured: the
            // shoulder crosses the full y width at x 35.4..39.9 at haa -40).
            //
            // So the step stays, ACCEPTED and quantified: nominal bridge
            // bending is ~8 MPa, Kt ~1.5-2 at a square shoulder gives 12-16
            // MPa against PA6-CF's ~80 MPa -- SF 5-6. It is the least-bad of
            // three options, not a free choice.
            translate([GROW_X0, HFE_Y - ARM_HALF_YZ, 13.4])
                cube([SPLIT_X - GROW_X0, 2*ARM_HALF_YZ, GROW_Z1 - 13.4]);
            // The outboard-arm ROOT DOUBLER (backlog #26) and the wheel boss
            // now live on coax_hfe_block.scad -- they are part of the removable
            // member. Keeping the doubler's rationale here because it is what
            // makes this joint hard and it must not be lost with the geometry:
            // the arm-to-bridge junction was the only member on the robot under
            // SF 15 (~14 MPa at the 4-thick root under a 20 N lateral/turning
            // foot load, fatigue SF ~1.9 per stride); the 2-thick gusset halves
            // it to ~6 MPa. That is precisely why option C's joint carries its
            // moment through a mortise/tenon in BEARING rather than through
            // bolt tension across a printed split line.
            // front strap pads (0.8 proud of BLK_Y0). NB since rev 3 moved the
            // horn seat 17.2->17.75 the case's top cap ridge (CAP_TOP 17.4)
            // sits 0.35 BEHIND that plane, so the strap lands 1.15 clear of
            // the cap, not 0.6 as the pre-rev-3 comment here implied — that is
            // the intended NON-contact (README tolerance map row 15, "cap gap
            // >=0.2": the strap is a lift backstop, it must not press the
            // cap). Full wall-width blocks;
            // outboard edge held to x15.6: at 16.6 it grazed the femur rim
            // plane at full hip swing (sweep-gate find)
            for (sx = [-1, 1])
                translate([min(sx*12.6, sx*15.6), BLK_Y0 - 0.8, -36])
                    cube([3, 0.8 + EPS, 10]);
        }

        // ---- HAA pocket: spline = Y axis, horn -Y, bulk down ----
        rotate([0, -90, 0]) rotate([90, 0, 0]) sts_pocket_neg(extra_top = 25);

        // front strap ZIP-TIE bores (CONVERTED 2026-07-16, coordinator
        // follow-up to the concurrent agent's tibia.scad fix): this part
        // has its OWN separate strap-pilot cut (different axis/face from
        // leg_v6_common.scad's strap_pilot_neg() -- that module bores a
        // Z-axis hole through a SIDE wall; this one bores a Y-axis hole
        // through the FRONT horn-face pads -- so it can't just call the
        // shared module, it's converted by hand, same numbers). The old
        // Ø2.05 self-tap pilot at x=±14.25 measured only ~0.37mm of wall to
        // the HAA servo-pocket cavity (TRIMESH-PROBED against this part's
        // own STL: cavity wall at x=12.85, exterior wall at x=16.05 -- only
        // WALL=3.2mm total between them at this z) -- same defect
        // strap_pilot_neg()'s own header describes, self-tapping into
        // filament banned project-wide. Fix: Ø3.2 (ZIP_BORE_D) at
        // x=±(14.25+ZIP_Y_OUT)=±15.60 -- matches strap_pilot_neg()'s own
        // ZIP_Y_OUT shift AND strap.scad's own zip-tie hole spacing (the
        // SAME strap part must fit both joints) -- gives 1.15mm clear to
        // the cavity wall (TRIMESH-PROBED, the safety-critical side, >=1.0mm
        // per the tibia precedent).
        // HONEST finding (this joint's wall is thinner than tibia's, not
        // just a copy-paste): at x=15.60 the hole's OUTBOARD edge (17.2)
        // runs past this part's own exterior wall (16.05 at this z) by
        // ~1.15mm. Closing that gap by growing the wall outboard would risk
        // the KNOWN femur-rim graze this same pad's own header already
        // found (x=16.6 grazed the femur at full hip swing, "front strap
        // pads" above) -- so the outboard side is left open (a thin slot on
        // the exterior face over the bore's length, not a fully round hole
        // there) rather than reinforced into that collision. This mirrors
        // strap_pilot_neg()'s own precedent -- its outboard/non-cavity side
        // is thin too ("not the safety-critical direction") -- just more so
        // here, because this wall started thinner. Genuine through-bore
        // (not blind): TRIMESH-PROBED the pad face to y=21.0 lands well
        // past the corner-notch's own open void (y>=20.2, punched to true
        // exterior air, see the corner-notch cut below) -- so the tie
        // feeds end-to-end, same convention as zip_pair_neg()/LA-21.
        // BUGFIX (2026-07-16, coordinator follow-up, first-article probe):
        // this comment originally assumed the corner-notch already covered
        // BOTH +/-X sides -- it didn't (cut on +X only, 4+ years of
        // history, its own header even says so). The -X bore (this part's
        // sx=-1 / coax_L's mirrored +x) landed in a genuine ~1.2mm BLIND
        // PLUG at y=21.0..22.2 -- a zip tie could not feed through on that
        // side. Fixed by mirroring the notch itself (see that cut's own
        // updated comment below) rather than adding a redundant one-off
        // exit here, since the notch is the thing both bores actually rely
        // on. TRIMESH-PROBED clear end-to-end on both sides post-fix.
        for (sx = [-1, 1])
            translate([sx*(14.25 + ZIP_Y_OUT), BLK_Y0 - 0.8 - EPS, -31])
                rotate([-90, 0, 0])
                    cylinder(d = ZIP_BORE_D, h = 39.6);

        // ---- HFE couplings on the X axis at (HFE_Y, HFE_Z) ----
        // #53: the inboard horn coupling moved to the removable cap
        // (coax_hfe_plate.scad). BUT the #67 stub keeps the LOW-Y/BACK arm
        // material INTEGRAL here -- and the 4x M2.5 horn bolts (BCD r7, driven
        // through the empty HAA pocket into the horn) pass through THAT stub.
        // BUGFIX 2026-07-12 (full-leg assembly audit): the #53 "nothing left to
        // cut here" was written when the WHOLE arm became a plate; #67 then kept
        // the stub integral, so the stub blocked every horn bolt 2.0-4.9mm
        // (MEASURED, all 4 BCD -- the joint couldn't be assembled; slipped the
        // gates because the sweep's r13 mask + the fastener gate never sample
        // the BCD circle). Restore horn_couple_neg on the parent -- same
        // transform as the cap; the cap cuts its own material, this cuts the
        // stub's, so the union clears all 4 bolt channels.
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
            horn_couple_neg();
        //
        // #226 option C: coax_hfe_bore() / coax_hfe_ear_channel() /
        // coax_hfe_fastener_neg() are GONE -- they existed only to make room
        // for the inboard cap and its M3, and the cap is retired. The inboard
        // arm is solid now, so all four horn-bolt channels are cut by the
        // horn_couple_neg() above (which is why that call stays).
        //
        // Clearance bore for the block's wheel boss. NOT a bearing: the boss
        // is located by the tenon and cantilevered off the block's arm plate;
        // this is assembly clearance only, hence BOSS_BORE_R = boss + 0.5.
        translate([BOSS_X0_CLR, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = BOSS_BORE_R, h = (SPLIT_X + 2) - BOSS_X0_CLR);
        // MORTISE for the block's tenon: open at the mating face (x = SPLIT_X),
        // blind at MORT_X0. Closed in Z both ways by design -- that closure is
        // what reacts the joint moment in bearing.
        translate([MORT_X0, MORT_Y0, MORT_Z0])
            cube([SPLIT_X + EPS - MORT_X0, MORT_Y1 - MORT_Y0, MORT_Z1 - MORT_Z0]);
        // 2x M3 heat-set, bored -X from the mortise's blind end into the grown
        // bridge. Driven from +X (open air past the block) -- the access the
        // inboard cap never had.
        for (by = BOLT_YS)
            translate([MORT_X0 - HEATSET_L, by, BOLT_Z]) rotate([0, 90, 0])
                cylinder(d = HEATSET_D, h = HEATSET_L + EPS);

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

        // HAA connector-bay zip anchor (LA-29, cable-management review
        // 2026-07-16): HFE (femur x44/x52/x84) and KFE (tibia x44/x62/x84)
        // both have zip-anchor pairs PLUS a swept anchor-span WARN gate
        // (check_fit.py cable_checks(), LA-20) -- the HAA roll crossing
        // (coax<->shoulder, the LARGEST ROM on the leg: sw +/-40deg,
        // measured mech stop ~+/-45deg, see shoulder_checks()) had NEITHER.
        // The tunnel-exit pair above flanks the BOTTOM tunnel toward the
        // femur; this new pair instead flanks the REAR (+Y) face next to
        // the connector bay (common-frame BAY_X0..BAY_X1, where the
        // servo's own 2 mid-body sockets sit) -- same style (single Ø3.2
        // hole per +/-X side wall, axis X, starting inside an already-open
        // void and punching out through the solid wall to the exterior),
        // same bore, different (y,z) siting. The MATING fixed-side anchor
        // is the shoulder's own Ø12 flange grommet (shoulder.scad,
        // "2x Ø12 cable grommets at (+/-32,-26)" -- the trunk<->C-box
        // interface; shoulder.scad is a different agent's file this
        // session, read-only here) -- see check_fit.py cable_checks()'s
        // new HAA case for the swept anchor-to-anchor span.
        // GRID-VERIFIED (2026-07-16, same probing method as LA-16): x=+/-7
        // sits inside the bay void (bay void spans x +/-12.85 in this
        // frame) so each hole's inner end is already open air; y=19 clears
        // the corner-notch cut (that notch only exists at y>=20.2 -- was
        // +X side only, MIRRORED to both +/-X 2026-07-16, see the notch's
        // own comment below -- either way y=19 stays below its y>=20.2
        // floor on both sides) and sits 0.85mm inside the bay's own
        // y<=19.85 upper edge; z=-27 keeps a real radial margin (measured
        // ~2.3mm) clear of the femur-swept clearance cylinder (r16.7 about
        // the hfe axis at y=11.6,z=-9.5 -- distance from (19,-27) to that
        // axis is ~19.0mm) and sits below the #67 HFE bore's own mid-band
        // (z=-13..-6) and front-disc reach, so this cannot reopen into the
        // coax_hfe_plate cavity on the +X (outboard) side.
        for (sx = [-1, 1])
            translate([sx * 7, 19, -27]) rotate([0, sx*90, 0])
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
        // the main block's sharp rear-outboard-top corner (x=+BLK_X,
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
        // MIRRORED 2026-07-16 (coordinator follow-up): this was cut on the
        // +X side ONLY for 4+ years of history -- the femur assembly that
        // motivated it only ever exists at +X (its own insertion sweep
        // "stays solid-blocked" toward -X per the header above, i.e. there
        // is NOTHING femur-related to graze on the -X side, so mirroring
        // costs nothing there) -- but the front strap zip-tie bore
        // (below, both +/-15.60) relies on THIS notch to reach true
        // exterior air at its rear end, and a Ø2.05 self-tap pilot never
        // needed to (it was blind, only 8.8mm deep, never reached y=20).
        // The -X strap bore was landing in a genuine BLIND POCKET (~1.2mm
        // solid plug at y=21.0..22.2, TRIMESH-PROBED post-conversion,
        // coax_R.stl -x side / coax_L.stl mirrored +x side) because the
        // notch was never mirrored. Fixed by cutting BOTH corners
        // (sx=+/-1) -- re-verified clear against the full insertion +
        // hip-pitch + shoulder-roll sweeps (`check_fit.py --sweep`) after
        // this change, exit 0, see load-analysis / build log.
        for (sx = [-1, 1])
            translate([sx > 0 ? BLK_X - 2 : -(BLK_X + 1), BLK_YF - 2, -38.4 - EPS])
                cube([2 + 1, 2 + 1, 38.4 + 13.4 + 2*EPS]);   // +1: punch 1mm
                                                              // past the
                                                              // block's own
                                                              // edge (BLK_X/
                                                              // BLK_YF) so
                                                              // the cut face
                                                              // isn't
                                                              // coincident
                                                              // with it
                                                              // (coincident
                                                              // faces gave a
                                                              // non-manifold
                                                              // mesh)
    }
}

coax_v6();
