// =============================================================================
// V5 Tibia — LEFT. Houses the KNEE STS3215.
// =============================================================================
// CORRECTION (2026-06-07): the tibia is NOT passive. Per the stock NovaSM3
// servo layout the knee servo lives in the tibia. The original tibia's servo
// end has a hobby-servo box + output boss; the STS3215 is bigger, so the cavity
// breaches the stock box walls (tight — same situation as coax). Confirm there
// is material at every cavity face on a FIRST-ARTICLE print before batching.
//
// Placement SEED from PNG-overlay fitting (2026-06-07). The LEFT tibia STL is
// Y-curved / oriented differently from the Right, so this seed needs an OVERLAY
// eyeball pass before printing: set OVERLAY = true, F5, nudge CAVITY_CENTER /
// CAVITY_ROT until the servo (blue) body sits in the box and its horn (top, +Z)
// is concentric with the stock output boss. Then OVERLAY = false, F6, export.
include <leg_v5_common.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftTibia.stl";
OVERLAY = false;

CAVITY_CENTER = [-45, 0, 20];   // SEED — VERIFY in OVERLAY (L is Y-curved)
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
