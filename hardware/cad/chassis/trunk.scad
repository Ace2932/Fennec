// =============================================================================
// NOVA chassis — DERIVED TRUNK (stock Nova-SM3 geometry, PRINTED holes)
// =============================================================================
// User decision (2026-07-10): KEEP the stock Nova-SM3 trunk GEOMETRY as-is
// (no shape redesign) but stop drilling it at assembly. This file imports
// the stock mesh unmodified and subtracts every fastener hole that the
// chassis lane's other parts currently document as "drill Ø_ at first
// assembly", so the printed part comes off the bed ready to bolt.
//
// Frame: SAME as the stock mesh / battery_pocket.scad / check_fit.py — z0 =
// floor bottom, +x = FRONT (stock "F" arrow), y = lateral.
//
// RETENTION for every hole below is a CLEARANCE bore only — the nut or
// heat-set lives in the MATING part, never on the trunk itself (verified
// per-hole against the source files; see each comment). That means every
// cut here is a plain (or countersunk) cylinder subtracted from the shell,
// no nut-trap geometry needed in this file.
//
// SOURCE PATH: the stock shell is VENDORED inside proj/, in the URDF's mesh
// folder, so a relative import reaches it and this file no longer depends on
// one laptop's checkout (#166). The comment that used to sit here argued the
// opposite — that original_body_files/ lives above proj/, so a relative path
// was "unreachable". That was true before the mesh was vendored; it is not
// now. The vendored copy is byte-identical to the root-repo original.
// OpenSCAD resolves this relative to THIS file, not the caller's cwd.
TRUNK_STL = "../../../ros2_ws/src/nova_description/meshes/SM3_Frame_ChassisTrunk.stl";

$fn = 48;
EPS = 0.05;

// -----------------------------------------------------------------------
// SET 1 — belly battery mount, 6x M3 clearance through the floor.
// Source: battery_pocket.scad BOSS_X=[-40,0,40], BOSS_Y=26.5, M3_CLEAR=3.4.
// "6x M3 x8 driven from INSIDE the trunk, through the 3.9 floor slab, into"
// a side-loaded nut trap carried in battery_pocket.scad's own rim-flange
// pads (AUD-1 top-flange mount) — the nut lives in battery_pocket, NOT
// here. Trunk just needs a straight Ø3.4 clearance bore; the CSK for the
// screw head is cut in floor_plate.scad (its own top z5.9), not the stock
// shell. Probed 2026-07-10 (probe_trunk.py): floor is solid z 0.00..3.90
// at all 6 XY, no pre-existing hole -- clean new cut.
// -----------------------------------------------------------------------
BATT_BOSS_X   = [-35, 0, 40];   // #68/#72 (2026-07-12): -x col -40->-35 (==
                                //  trunk_build.py BATT_BOSS_X / battery_pocket
                                //  BOSS_X / floor_plate BAT_X -- the built STL)
BATT_BOSS_Y   = 27.5;           // #72: was 26.5 (stale) -- == the AUD-11 axis
BATT_CLEAR_D  = 3.4;
BATT_BORE_Z0  = -2;      // starts below the floor bottom (z0)
BATT_BORE_H   = 8;        // ends well above the floor top (z3.9) -- clean cut

// -----------------------------------------------------------------------
// SET 2 — shoulder flange-foot CSK, 4x M3x14 through the floor corners.
// Source: leg_v6/shoulder.scad FOOT_BOLT_X=42, FOOT_BOLT_Y=-81.7
// (shoulder-local), placed at both ends via the front/rear S2T transforms
// (preview_assembly.py / check_fit.py: front S2T=[[0,1,0,141.2],[1,0,0,0],
// [0,0,1,38.05]], rear end=-1 sign-flip) -> trunk (x=+/-59.5, y=+/-42),
// matching shoulder.scad's own comment "-> trunk (59.5, +/-42)".
// "M3x14 CSK from BELOW the floor ... head flush, belly pack clears,
// nyloc + washer on top of the pad" -- the nyloc lives on the shoulder's
// foot pad ABOVE the floor (reached through the open trunk end aperture),
// NOT on the trunk. Trunk needs a Ø3.4 clearance bore with a 90-deg
// countersink on the UNDERSIDE (z0, the belly-facing face) so the CSK
// head seats flush there. Probed 2026-07-10 (probe_trunk.py): floor solid
// z 0.00..3.83/3.90 at all 4 XY (a second, unrelated solid band appears
// z~29.6..38.3 -- the corner wedge/plateau structure well above the foot
// joint's own z4..8 pad -- not part of this bore's path).
// -----------------------------------------------------------------------
FOOT_XY       = [[59.5, 42], [59.5, -42], [-59.5, 42], [-59.5, -42]];
FOOT_CLEAR_D  = 3.4;
FOOT_CSK_D    = 6.4;                             // M3 CSK head seat dia
FOOT_CSK_H    = (FOOT_CSK_D - FOOT_CLEAR_D) / 2;  // 1.5mm at 90 deg
FOOT_BORE_H   = 8;                                // through + margin above

// -----------------------------------------------------------------------
// SET 3 — shoulder-flange end-wall clearance -- ALREADY STOCK, NOT CUT HERE.
// Source: leg_v6/shoulder.scad TRUNK_HOLE_X=51.75, TRUNK_HOLE_Z=[-33.05,
// -14.05] (shoulder-local, heat-set side) -> trunk (x=+/-63.5ish end face,
// y=+/-51.75, z=5.0/24.0), transformed the same way as SET 2 above.
// shoulder.scad's own header (L20) already calls these "the stock shell's
// own holes (measured)"; measure_trunk.py + chassis/README.md §"What the
// trunk ACTUALLY is" independently confirm: "shoulder bolt bores | Ø3.16
// along x at (y +/-51.75, z 5 & 24), 6.5 deep, both ends -- matches
// shoulder.scad". Re-probed 2026-07-10 directly against this STL
// (probe_trunk.py, ray cast along +x through the exact bore centerlines):
// the side wall is solid from x -50..48.8, then OPEN (no material) from
// x 48.8 all the way to the trunk edge (63.5) at every one of the 4
// (y,z) combinations on both ends -- i.e. the bore path is already clear.
// NOTHING to subtract here; re-cutting an already-open hole would be a
// no-op. check_fit.py's new alignment case (below) still gates this axis
// so a stock-mesh swap or shoulder rev can't silently break it.
// -----------------------------------------------------------------------

module trunk() {
    difference() {
        import(TRUNK_STL, convexity = 10);

        // SET 1 — battery mount, 6x
        for (bx = BATT_BOSS_X, sy = [1, -1])
            translate([bx, sy * BATT_BOSS_Y, BATT_BORE_Z0])
                cylinder(d = BATT_CLEAR_D, h = BATT_BORE_H);

        // SET 2 — shoulder foot CSK, 4x (CSK opens at the underside z0)
        for (xy = FOOT_XY) {
            translate([xy[0], xy[1], -EPS])
                cylinder(d1 = FOOT_CSK_D, d2 = FOOT_CLEAR_D,
                         h = FOOT_CSK_H + EPS);
            translate([xy[0], xy[1], FOOT_CSK_H])
                cylinder(d = FOOT_CLEAR_D, h = FOOT_BORE_H);
        }
    }
}

trunk();
