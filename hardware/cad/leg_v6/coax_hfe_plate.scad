// =============================================================================
// V6 Coax HFE cap — small removable retention piece over the femur's
// insertion-swept wedge. #67 fix (2026-07-12), supersedes the #53
// full-disc removable plate.
// =============================================================================
// #53 (2026-07-11) made the WHOLE inboard-arm disc (x=PLATE_X0..ARM_IN_X1,
// r=ARM_HALF_YZ=16 about the HFE axis) a removable plate, because SOME of
// it had to open for femur insertion. But its own X-thickness (3.15mm)
// turned out too thin for any captured hardware (nut or heat-set) mounted
// through it -- every fastener redesign against that thin plate ended up
// either unreachable or reaching for a self-tap (rejected: NEVER self-tap
// into printed filament).
//
// #67 fix: MEASURED (trimesh insertion-sweep probe, femur_R.stl + knee_arm
// .stl + the HFE-embedded servo, tagged per-source, swept +Y in 0.5mm steps
// t=0..68 -- see coax.scad's own header for the full method) the femur
// assembly's real swept footprint inside the old disc is a WEDGE, not the
// whole disc: 100% of the hits are the HFE-embedded servo's own case (never
// femur_R.stl's own solid, which stays x>=16.05 for the whole +Y sweep;
// never knee_arm.stl, whose transformed footprint sits at a totally
// different z-band). Clear at the back (x<13.3, full disc -- INTEGRAL
// stub, part of coax.scad now); a narrow high-y/mid-z band swept in the
// middle (13.3..14.9); nearly the whole disc swept only right at the front
// (>=14.9). This CAP is just that wedge -- coax.scad's coax_hfe_bore() cuts
// the matching void. Everything else (most of the old disc) is now
// INTEGRAL coax block, carrying the joint's compressive load directly
// instead of through a bolted plate.
//
// Geometry (mirrors coax.scad's own constants byte-for-byte -- `include`
// doesn't share variables across files, see that file's header):
//   - MID-BAND body: x=STUB_MIDX0+CLR..STUB_MIDX1, y/z shrunk CLR off the
//     stub walls (y0/y1/z0 -- true stub-facing boundaries). z1=-6 and
//     x1=14.9 are LEFT FLUSH (0 clearance) -- those are internal unions to
//     this cap's own riser / front-band disc, not stub interfaces.
//   - FRONT-BAND body: r=ARM_HALF_YZ-CLR disc (same "shrink off the round
//     stub wall" convention #53's plate already used, PLATE_R), x from
//     14.9 (flush, internal union) to HORN_SEAT=ARM_IN_X1 (flush -- horn
//     seat plane, must NOT shrink, it's the horn's own mating face).
//   - HORN COUPLING: horn_couple_neg(), all 4 M2.5 bolts -- MEASURED
//     (same sweep probe, checked each bolt's own (y,z) at the front face
//     against the swept-point cloud within r<4mm): every one of the 4
//     lands inside the swept envelope (closest, the two "low" bolts at
//     y=6.65, still reads 18-35 swept pts within r<2mm) -- none reach a
//     genuinely clear zone at the horn seat plane. HONEST finding: ALL 4
//     horn bolts are carried by this CAP, ZERO by the integral stub. The
//     stub's own horn-interface contact is bearing-only (the low-y sliver
//     of the disc, x=12.9..16.05, y<~0, still integral, still touches the
//     horn seat plane) -- real, but carries no fastener.
//   - EAR (riser + head): fills coax.scad's coax_hfe_ear_channel() (same
//     shrink convention: y0/y1/the riser's -X face get CLR; the riser/head
//     z-boundary and the riser's +X face are flush internal unions). Holds
//     the M3 bolt CLEARANCE hole + SHCS head counterbore -- the same axis
//     +Y bore coax.scad's coax_hfe_fastener_neg() cuts, stopping exactly at
//     EAR_Y0 where the REAL heat-set (in the integral stub/bridge, not this
//     cap) takes over. See coax.scad for the full fastener writeup and the
//     reachability proof in the fix report.
//
// PRINT: horn-seat face (x=HORN_SEAT) DOWN -- knee_arm.scad/shoulder_plate.
// scad doctrine (flat bed face = clean horn contact). The ear stands up off
// the mid-band body; light support likely under its own overhang. PA6-CF,
// 4 walls / 0.2 / 40%, print 1 (no mirror -- coax_hfe_plate_L.scad covers
// the left side).
//
// LOAD SPLIT (honest, see the fix report for the full acceptance numbers):
// the integral stub now carries the ENTIRE compressive bearing path for
// most of the old disc's footprint (all of x<13.3, most of x=13.3..14.9)
// and reacts the fastener's own clamp load (the M3 heat-set sits in the
// stub/bridge, not this cap). This cap carries 100% of the horn's 4-bolt
// fastener interface (see the HONEST finding above) and a single M3
// clamp bolt. Anti-rotation: the cap is shape-keyed into the bored wedge
// (not a circular disc any more) -- it cannot spin about the single bolt
// axis without the mid-band/front-band walls binding against the stub.
// Flagged for a first-article load check, same as #53.

include <leg_v6_common.scad>

HFE_Y     = 11.6;
HFE_Z     = -9.5;
FEMUR_MID = 33.8;
ARM_IN_X1  = FEMUR_MID - HORN_Z1;      // 16.05, == coax.scad's ARM_IN_X1
HORN_SEAT  = ARM_IN_X1;
ARM_HALF_YZ = 16;                      // == coax.scad's clearance-bore radius
BRIDGE_Z0  = 7.4;                      // == coax.scad's BRIDGE_Z0

CLR = 0.2;   // slip-fit clearance off true stub-facing walls (matches this
             // file set's small-margin convention: CLR_HORN=0.15,
             // CLR_POCKET=0.45)

// == coax.scad's #67 constants, byte-identical (see that file's header for
// the full measured-wedge derivation) ==
STUB_MIDX0 = 13.3;   STUB_MIDX1 = 14.9;
STUB_MIDY0 = 7.0;    STUB_MIDY1 = 28.0;
STUB_MIDZ0 = -13.0;  STUB_MIDZ1 = -6.0;
STUB_FRONTX0 = 14.9;

EAR_X0 = STUB_MIDX0; EAR_X1 = STUB_MIDX1;
EAR_Y0 = 24.0;        EAR_Y1 = 27.6;
HEAD_X0 = 12.9;       HEAD_X1 = 18.9;
HEATSET_CX = (HEAD_X0 + HEAD_X1) / 2;
HEATSET_CZ = (BRIDGE_Z0 + 13.4) / 2;

module coax_hfe_cap_body() {
    // mid-band: shrunk off the true stub walls (y0,y1,z0,x0 = the back
    // face) -- z1 (top, blends into the riser) and x1 (front, blends into
    // the front-band disc) stay flush, 0 clearance, cap-internal unions.
    translate([STUB_MIDX0 + CLR, STUB_MIDY0 + CLR, STUB_MIDZ0 + CLR])
        cube([(STUB_MIDX1 - STUB_MIDX0) - CLR,
              (STUB_MIDY1 - STUB_MIDY0) - 2*CLR,
              (STUB_MIDZ1 - STUB_MIDZ0) - CLR]);
    // front-band: shrunk radius (same convention #53's PLATE_R used), x
    // from the mid-band's own front (flush) to the horn seat (flush --
    // mating face, not shrunk)
    translate([STUB_FRONTX0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
        cylinder(r = ARM_HALF_YZ - CLR, h = HORN_SEAT - STUB_FRONTX0);
    // ear: riser (shrunk off its true stub wall, x0 = -X face; y0/y1 shrunk;
    // x1/z1 flush internal unions) + head (shrunk off y0/y1 only -- x0/x1
    // and the z0 riser-boundary are flush internal unions; z1 top face is
    // the open exterior top of the head, needs its own small shrink so the
    // cap doesn't proud past the bridge's own top plane)
    translate([EAR_X0 + CLR, EAR_Y0 + CLR, STUB_MIDZ1])
        cube([(EAR_X1 - EAR_X0) - CLR, (EAR_Y1 - EAR_Y0) - 2*CLR,
              (BRIDGE_Z0 - STUB_MIDZ1)]);
    translate([HEAD_X0, EAR_Y0 + CLR, BRIDGE_Z0])
        cube([HEAD_X1 - HEAD_X0, (EAR_Y1 - EAR_Y0) - 2*CLR,
              (13.4 - BRIDGE_Z0) - CLR]);
}

module coax_hfe_plate_R() {
    difference() {
        coax_hfe_cap_body();

        // horn coupling -- same call as the #53 plate used (LA-7 ctr_deep):
        // this cap's front-band thickness at the horn seat (3.15mm nominal,
        // matches the old plate) leaves the same ~1.5mm counterbore floor.
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
            horn_couple_neg(ctr_deep = 1.65);

        // fastener: M3 clearance + SHCS head counterbore through the ear,
        // open at y=EAR_Y1 (the bridge's own exterior rear-tip face) --
        // matches coax.scad's coax_hfe_fastener_neg() exactly, stopping at
        // EAR_Y0 where the real heat-set (in the stub) takes over.
        translate([HEATSET_CX, EAR_Y1 + EPS, HEATSET_CZ]) rotate([90, 0, 0]) {
            cylinder(d = M3_CLEAR, h = (EAR_Y1 - EAR_Y0) + 2*EPS);
            cylinder(d = 5.5, h = 2.2 + EPS);
        }

        // side marker: 1 dot = RIGHT (the _L wrapper adds a 2nd, spaced
        // 3mm away in z so the two don't overlap -- see that file's
        // header). The mid-band body's own X-thickness is only 1.4mm
        // (STUB_MIDX0+CLR..STUB_MIDX1) -- too thin behind a 1mm-deep dot
        // on an X-facing wall (would eat most of the wall). Use the
        // Y-facing wall instead (y=STUB_MIDY0+CLR, the mid-band's own
        // "low-y" wall): the mid-band block is 20+mm deep in Y there, so a
        // 0.8mm dimple leaves a huge floor. Dot dia reduced to 2mm (from
        // this file set's usual 3mm) so a 2nd dot fits the same wall's
        // 6.8mm z-span with real separation. x=14.1 (mid of the 1.4mm-wide
        // body), z=-8.0 -- clear of the horn BCD (all near x=16.05) and
        // the ear (y>=24).
        translate([14.1, STUB_MIDY0 + CLR - EPS, -8.0]) rotate([-90, 0, 0])
            cylinder(d = 2, h = 0.8);
    }
}

coax_hfe_plate_R();
