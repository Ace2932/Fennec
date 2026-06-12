// Femur cavity placement — shared by shell + cover scripts so holes match.
// 2026-06-07: servo shifted toward the coax (active-horn) side so the output
// reaches the coax horn-ring. Active horn = +Z local (thick Ø20 disc / splined
// shaft); it must point at the coax. L horn → −Y, R horn → +Y (true mirror).
// NOTE: R rotation is now −90 (was +90). A proper Y-mirror flips the rotation
// sign; the old +90 left R's servo buried facing the wrong way. VERIFY both in
// OVERLAY / your Fusion assembly — Y=±24 is a starting pick (≈16 mm reach,
// still ~⅔ of the body gripped); nudge to match the real horn→coax gap.
FEMUR_CAVITY_CENTER_R = [37, 24, 10];
FEMUR_CAVITY_ROT_R    = [-90, 0, 0];     // true mirror of L (was +90 — bug)
FEMUR_CAVITY_CENTER_L = [37, -24, 10];   // shifted −6 toward coax (active side)
FEMUR_CAVITY_ROT_L    = [90, 0, 0];

FEMUR_SHELL_L = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_LeftFemur.stl";
FEMUR_SHELL_R = "/Users/afox/codebases/NOVA/original_body_files/SM3_Frame_RightFemur.stl";
FEMUR_COVER_L = "/Users/afox/codebases/NOVA/original_body_files/Covers/SM3_Cover_LeftFemur.stl";
FEMUR_COVER_R = "/Users/afox/codebases/NOVA/original_body_files/Covers/SM3_Cover_RightFemur.stl";
