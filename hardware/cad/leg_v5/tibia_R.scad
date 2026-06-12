// =============================================================================
// V5 Tibia — RIGHT. Houses the KNEE STS3215.
// =============================================================================
// CORRECTION (2026-06-07): tibia is NOT passive — knee servo lives here (stock
// NovaSM3 layout). STS3215 recarves the original hobby-servo box at the +X end;
// it is bigger than stock so the cavity is tight against the box walls (like
// coax) — FIRST-ARTICLE print to confirm material at every face.
//
// Placement confirmed by PNG-overlay (2026-06-07): servo body fills the +X box,
// horn (top, +Z) over the stock output boss. R is the cleaner of the two
// variants; still recommend an OVERLAY check.
include <leg_v5_common.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightTibia.stl";
OVERLAY = false;

CAVITY_CENTER = [50, 0, 19];
CAVITY_ROT    = [0, 0, 0];

if (OVERLAY) {
    color("yellow", 0.7) import(ORIGINAL_STL, convexity = 8);
    color([0.2, 0.4, 1, 0.5]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_solid();
    color([1, 0, 0, 0.3]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
} else {
    difference() {
        import(ORIGINAL_STL, convexity = 8);
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    }
}
