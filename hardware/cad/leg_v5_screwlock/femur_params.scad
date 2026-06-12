// Femur cavity placement — shared by shell + cover scripts so holes match.
// Copied verbatim from leg_v5/femur_params.scad (paths are absolute).
// 2026-06-07: synced with leg_v5 — servo shifted toward coax (active-horn side),
// R rotation corrected to a true mirror (−90, was +90). See leg_v5/femur_params.
FEMUR_CAVITY_CENTER_R = [37, 24, 10];
FEMUR_CAVITY_ROT_R    = [-90, 0, 0];
FEMUR_CAVITY_CENTER_L = [37, -24, 10];
FEMUR_CAVITY_ROT_L    = [90, 0, 0];

FEMUR_SHELL_L = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftFemur.stl";
FEMUR_SHELL_R = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightFemur.stl";
FEMUR_COVER_L = "/Users/afox/codebases/NOVA/original_body_files/Covers/SM3_Cover_LeftFemur.stl";
FEMUR_COVER_R = "/Users/afox/codebases/NOVA/original_body_files/Covers/SM3_Cover_RightFemur.stl";
