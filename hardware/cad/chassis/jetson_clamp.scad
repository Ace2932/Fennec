// =============================================================================
// JETSON CASE CLAMP — removable corner hold-down (jetson_case_mount rework)
// =============================================================================
// backlog #33/#34 (2026-07-08). The cradle can't have FIXED inward top tabs —
// the case (assembled off-robot, bezel on) must DROP straight in between the
// corner uprights. So retention is 4 of THESE: after the case is in, each clamp
// drops onto an upright top and an M3x8 pulls it down; its far pad caps the
// case's SOLID CORNER COLUMN (z102.8), stopping lift/tumble. Bear-only (NO case
// drilling). Add a TPU/EVA shim on the pad underside for preload + damping.
//
// Local print frame: FLAT on the bed (z0..4). Bolt hole at the origin (over the
// upright); the bearing pad reaches +x by REACH to sit over the corner column.
// preview_assembly.py places 4 (rotated toward each corner). Print 4x, PA6-CF.

$fn = 32; EPS = 0.05;
M3_CLEAR = 3.4;
CLAMP_T = 4;          // plate thickness
REACH   = 10;         // bolt(upright) -> pad(corner column) centre distance

module jetson_clamp() {
    difference() {
        hull() {
            cylinder(d = 10, h = CLAMP_T);                 // over the upright (bolt)
            translate([REACH, 0, 0]) cylinder(d = 12, h = CLAMP_T);  // over the corner col
        }
        translate([0, 0, -EPS]) cylinder(d = M3_CLEAR, h = CLAMP_T + 2 * EPS);  // M3
    }
}

jetson_clamp();
