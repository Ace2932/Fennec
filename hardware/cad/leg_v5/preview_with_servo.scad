// =============================================================================
// PREVIEW: original coax STL + STS3215 servo placed at cavity location
// Shows how servo fits in the bracket.
// =============================================================================
// Change PART to "coax", "coax_R", "femur", "tibia", "shoulder" etc.
// Reads cavity placement params from the corresponding .scad file (manual sync).

include <leg_v5_common.scad>

PART = "shoulder";

// Mirror per-part param table (keep in sync with the .scad files)
STL_FOR = [
    ["coax",      "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftCoax.stl",  [-11.6,   8, 28.8], [90, 90, 0]],
    ["coax_R",    "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightCoax.stl", [-11.6,  -8, 28.8], [90, 90, 0]],
    ["femur",     "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftFemur.stl",   [40,  0, 17.3], [90, 0, 90]],
    ["femur_R",   "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightFemur.stl",  [40,  0, 17.3], [90, 0, 90]],
    ["tibia",     "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftTibia.stl",   [40,  0, 19.2], [90, 0, 90]],
    ["tibia_R",   "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightTibia.stl",  [40,  0, 19.2], [90, 0, 90]],
    ["shoulder",  "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_FrontShoulderMiddle.stl", [0, 0, 0], [0, 0, 0]],
];

// Lookup
function lookup_part(name) =
    [for (row = STL_FOR) if (row[0] == name) row][0];

P = lookup_part(PART);
STL_PATH   = P[1];
CAV_CENTER = P[2];
CAV_ROT    = P[3];

// Render: bracket (yellow) + carved cavity (translucent red) + servo (blue solid)
difference() {
    color("yellow", 0.85) import(STL_PATH, convexity = 8);
    translate(CAV_CENTER) rotate(CAV_ROT) sts3215_cavity();
}

// STS3215 servo placed at same coords as cavity
color([0.2, 0.4, 1, 0.9]) translate(CAV_CENTER) rotate(CAV_ROT) sts3215_solid();
