// =============================================================================
// V6 Coax HFE plate — bolt-on inboard (horn) arm of the coax's femur yoke.
// =============================================================================
// #53 BLOCKER fix (2026-07-11): the coax's femur yoke used to be a rigid
// closed U (integral inboard arm + bridge + integral outboard arm) — no
// removable side, so the femur's horn+wheel disc pack had NO insertion
// path. This part replaces the old integral inboard arm (coax.scad's
// removed arm_plate(ARM_IN_X0,ARM_IN_X1)) as a separate bolt-on, mirroring
// the KFE (knee_arm.scad) / HAA (shoulder_plate.scad) bolt-on-arm pattern.
//
// Assembly sequence (coax.scad's own header has the full finding): the
// femur+HFE-servo assembly's real insertion path is +Y (rearward), not
// axial — it slides in from behind the coax, wheel bolts to the coax's
// INTEGRAL outboard boss first, THEN this plate bolts on last to capture
// the horn. With this plate off, nothing blocks the femur's Y-axis
// insertion/removal (trimesh-swept, mesh-verified CLEAN, 0..70mm).
//
// Geometry:
//   - DISC: r=ARM_HALF_YZ=16 around the HFE axis (world Y=11.6,Z=-9.5),
//     x = PLATE_X0..ARM_IN_X1 (12.9..16.05, 3.15mm thick) — matches
//     coax.scad's own clearance bore exactly (byte-identical constants,
//     `include`s the same leg_v6_common.scad). Front face (x=16.05) is the
//     femur HORN SEAT — same plane the old integral arm used, so the
//     joint's seated geometry (35.45mm disc-to-disc gap, horn/wheel
//     spacing) is UNCHANGED. Only PLATE_X0=12.9 differs from the old
//     ARM_IN_X0=12.05 (0.85mm less inboard reach) — mesh-probe forced:
//     the HAA servo's own case reaches x=12.4 in its installed pose, and
//     the coax's own pocket-cavity wall starts ~x12.85 — 12.9 keeps clear
//     of BOTH (a separate bolt-on part isn't protected by the parent's
//     own pocket-cut the way the old integral arm was).
//   - HORN COUPLING: horn_couple_neg(ctr_deep=1.65) — same call, same
//     ctr_deep, coax.scad used at the old integral arm (LA-7 fix): 3.15mm
//     plate thickness (was 3.2mm real, after the old integral arm's own
//     pocket-cut) leaves the SAME ~1.5mm counterbore floor.
//   - MOUNT EARS: 4x, at PLATE_MT_X x PLATE_MT_Y (coax.scad's own
//     constants, kept byte-identical here since `include` doesn't share
//     variables across files — see that file's header for the full
//     mount-location derivation, 3 design iterations). Each ear is a small
//     local bump raising the disc's own natural top surface (peaks at
//     z=6.5 at y=HFE_Y, less off-center) up to EAR_Z1=7.35 — just under
//     coax.scad's BRIDGE_Z0=7.4, so the ear's top face clamps flush
//     against the bridge's underside without occupying the SAME z-band
//     (avoids colliding with the bridge, which is coax's own separate,
//     still-integral material at z 7.4..13.4). M3 THROUGH-BOLT (not a
//     heat-set — the bridge is only 6mm thick, doesn't take a blind
//     HEATSET_L=6.2 bore, see coax.scad's mount-comment history) drives
//     down from the coax's true top face into a captured M3 NUT recessed
//     in this ear's underside.
//
// PRINT: horn-seat face (x=ARM_IN_X1=16.05) DOWN — knee_arm.scad /
// shoulder_plate.scad doctrine (flat bed face = clean horn contact, no
// support witness marks on the mating surface). The 4 mount ears end up
// facing up/sideways; light support likely under their undercut corners.
// PA6-CF, 4 walls / 0.2 / 40%, print 1 (no mirror — coax_hfe_plate_L.scad
// covers the left side).
//
// STRUCTURAL NOTE (flagged, not resolved here — see the #53 fix report):
// the old integral arm reacted the HFE joint's leg load through continuous
// printed material straight into the HAA pocket block. This plate reacts
// the SAME load through (a) 4x M2.5 into the femur horn and (b) 4x M3
// through-bolts into a 6mm-thick bridge rib — a bolted joint is a real
// stiffness/strength step down from a monolithic one, and the bridge
// through-bolt locations are a tight fit (mesh-probed, not a generous
// margin). Flagged for a first-article load check; see the fix report.

include <leg_v6_common.scad>

HFE_Y     = 11.6;
HFE_Z     = -9.5;
FEMUR_MID = 33.8;
HORN_SEAT = FEMUR_MID - HORN_Z1;   // 16.05 == coax.scad's ARM_IN_X1
ARM_HALF_YZ = 16;                  // == coax.scad's clearance-bore radius
PLATE_R = ARM_HALF_YZ - 0.3;       // plate's own disc radius: 0.3 UNDER the
                                    // coax's bore radius -- a same-radius
                                    // disc-in-bore fit collided (mesh-
                                    // verified: coincident-surface CSG
                                    // noise, 1436/8000 plate pts landed
                                    // inside the coax). 0.3 matches this
                                    // file's other yoke-fit clearances
                                    // (CLR_HORN 0.15, CLR_POCKET 0.45).

PLATE_X0 = 12.9;                   // == coax.scad's PLATE_X0 (disc back face)
PLATE_THK = HORN_SEAT - PLATE_X0;  // 3.15mm

EAR_Z1 = 7.35;                     // ear top -- just under coax.scad's
                                    // BRIDGE_Z0=7.4 (0.05mm short: avoids a
                                    // coincident-face manifold issue, same
                                    // fix as the coax-side corner notch)
EAR_R  = 4.0;                      // ear plan-view radius around each mount hole
NUT_D  = 6.4;                      // M3 hex nut trap dia (loose clearance,
                                    // matches the knee_arm/shoulder_plate
                                    // SHCS-head-counterbore convention)
NUT_H  = 2.6;                      // nut trap depth (M3 nut ~2.4mm thick + margin)

PLATE_MT_X = [13.5, 15.5];         // == coax.scad's PLATE_MT_X (byte-identical,
PLATE_MT_Y = [8, 15];              // == coax.scad's PLATE_MT_Y  see that file)

module coax_hfe_plate_R() {
    difference() {
        union() {
            // main disc: horn cheek, sized to the coax's clearance-bore
            // (same x-span, PLATE_R radial clearance -- see its comment)
            translate([PLATE_X0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
                cylinder(r = PLATE_R, h = PLATE_THK);
            // 4x mount ears: local blocks closing the gap from the disc's
            // own curved top surface (its solid interior starts at z=HFE_Z,
            // the disc's own center) up to EAR_Z1 (just under the bridge).
            // Span the SAME full x-range as the disc (PLATE_X0..HORN_SEAT)
            // so they union cleanly with it (no separate x-boundary check
            // needed -- guaranteed inside the disc's own solid prism).
            for (my = PLATE_MT_Y)
                translate([PLATE_X0, my - EAR_R, HFE_Z])
                    cube([PLATE_THK, 2*EAR_R, EAR_Z1 - HFE_Z]);
        }
        // horn coupling -- same call + same ctr_deep the old integral arm
        // used (LA-7 fix): this plate's 3.15mm thickness matches the old
        // arm's real (post-pocket-cut) 3.2mm closely enough to reuse it
        // directly (floor 3.15-1.65=1.5mm, at the print-margin gate exactly,
        // same margin the original fix accepted).
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
            horn_couple_neg(ctr_deep = 1.65);

        // mount holes: through-bolt clearance + captured nut trap on the
        // ear's own underside (near the base of its hull, z=HFE_Z-EAR_R --
        // accessible before the plate is offered up to the coax; the trap
        // opens DOWNWARD, the bolt drives DOWN from the coax's true top
        // face through the bridge, through open air, then into this trap)
        for (mx = PLATE_MT_X, my = PLATE_MT_Y) {
            translate([mx, my, HFE_Z - EAR_R - 1])
                cylinder(d = M3_CLEAR, h = (EAR_R + 1) + (EAR_Z1 - HFE_Z) + 1);
            translate([mx, my, HFE_Z - EAR_R - 1 + EPS])
                cylinder(d = NUT_D, h = NUT_H);
        }

        // side marker: 1 dot = RIGHT (the _L wrapper adds a 2nd), same
        // convention as every other leg_v6 part. Rear face of the disc
        // (x=PLATE_X0, the back face, away from the horn) -- clear of the
        // horn BCD/counterbore (those are all near x=ARM_IN_X1) and the
        // mount ears (all at y>=8, this dot sits at y=-2).
        translate([PLATE_X0 + EPS, -2, HFE_Z]) rotate([0, -90, 0])
            cylinder(d = 3, h = 1);
    }
}

coax_hfe_plate_R();
