// =============================================================================
// V5 Coax — LEFT variant
// Source: SM3_Frame_LeftCoax.stl (bbox 37.6 × 46.1 × 57.5)
// =============================================================================
// User-confirmed cavity placement (2026-05-26).
// Right variant: CAVITY_CENTER = [-11.6, -8, 28.8]
// Left variant: Y-flipped from Right (mirror about XZ plane)

include <leg_v5_common.scad>

ORIGINAL_STL = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftCoax.stl";
OVERLAY = false;

CAVITY_CENTER = [-11.6, 8, 28.8];   // Y-flipped from Right variant
CAVITY_ROT    = [90, 90, 0];

if (OVERLAY) {
    color("yellow", 0.7) import(ORIGINAL_STL, convexity = 8);
    color([1, 0, 0, 0.4]) translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
} else {
    difference() {
        import(ORIGINAL_STL, convexity = 8);
        translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    }
}
