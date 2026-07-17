// =============================================================================
// V6 servo retention strap — zip-tied over the servo tail (print 4+ per robot).
// =============================================================================
// plate, 2x Ø3.2 zip-tie bores at ±15.60 (CONVERTED 2026-07-16, owner
// decision — was 2x Ø2.9 M2.5 self-tap clearance holes at ±14.25). The
// M2.5 self-tap pilot (strap_pilot_neg() in leg_v6_common.scad) measured
// only 0.374mm of wall to the servo cavity — no insert/nut fits that, and
// self-tapping into filament is banned project-wide. Swapped to zip-tie
// retention instead: a tie loops up through this bore, through the
// matching Ø3.2 through-bore in leg_v6_common.scad's strap_pilot_neg()
// (now a zip cut, not a screw pilot; NAME kept for tibia.scad's call-site
// compatibility — see that module's own comment), and cinches the strap
// flush. Hole shifted outboard from 14.25 to 15.60 to line up with that
// bore's own OUTBOARD-shifted position (needed on the common-module side
// for servo-cavity wall clearance — see its comment for the exact
// numbers) — 15.60 still leaves 1.44mm of wall to this plate's own outer
// edge (TRIMESH-PROBED), comfortably >=1.0mm.
// Bearing-pad geometry (the hull() shape spanning the servo tail) is
// UNCHANGED — only the fastener holes moved/resized.
// Sits on the pocket rims (rim top = servo body top): clamps the body
// down into the pocket. (Backup-only now the anti-rotation ribs take the
// torque — coax + tibia use it, femur has none.)
// PRINT: PA6-CF (in the leg batch) or PETG-CF, FLAT (2.5 plate on the bed),
//   ~100% infill, zero supports, ~1 g.
$fn = 48;
difference() {
    hull() for (sy = [-1, 1])
        translate([0, sy*13, 0]) cylinder(d = 8, h = 2.5);
    for (sy = [-1, 1])
        translate([0, sy*15.60, -0.1]) cylinder(d = 3.2, h = 2.8);
}
