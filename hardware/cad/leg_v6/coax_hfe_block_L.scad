// LEFT coax HFE block = X-mirror of the right (same convention as
// coax_L.scad / coax_hfe_plate_L.scad, which this pair supersedes).
// PRINT: PA6-CF (as coax_hfe_block.scad), MATING FACE (x=SPLIT_X) DOWN —
//   mirrored to **-X**, NOT +X. coax_hfe_block_L is an X-mirror
//   (mirror([1,0,0]) coax_hfe_block_R()), and the R directive is expressed on
//   the X axis, so the mirror FLIPS which face is flat — the same trap LA-3
//   records for femur_L/tibia_L's Z-mirror. Measured (slice_plate.py): +X
//   gives 54.4 mm^2 (s=2.14, an edge), -X gives 366.4 mm^2 (s=0.83) on this
//   mesh. supports=normal, under the 0.5-2.0mm shelf (as coax_hfe_block.scad).
$fn = 64;
use <coax_hfe_block.scad>
// side marker: 2 dots = LEFT. The base (RIGHT) dot sits on the block's own
// OUTBOARD face (x=ARM_OUT_X1=60.2, y=HFE_Y+10=21.6, z=HFE_Z-12=-21.5), cut
// direction -X into the arm. mirror([1,0,0]) flips X only, so on this LEFT
// part it lands at world x=-60.2 with the same y/z and the same (mirrored)
// cut direction — it comes along for free via `mirror(...) block_R()`, no
// separate handling needed.
// 2nd dot: SAME face, offset 5mm in z (z=-12.5) so 1-vs-2 dots reads
// unambiguously and neither dimple falls inside the other's d=3 (r=1.5)
// radius. Both sit well clear of the wheel-screw BCD and the tenon.
// NB the cut STARTS OUTSIDE the face (x = -60.2 - 0.4) and runs 1.2 so it
// removes 0.8 of material. Starting it 0.05 INSIDE instead left a 0.05mm skin
// over the dimple, which mesh_health caught as bodies=2 / NEGATIVE-SHELL -5.6:
// a subtraction that does not break the surface makes an inverted shell, not a
// dimple.
difference() {
    mirror([1, 0, 0]) coax_hfe_block_R();
    translate([-62.3 - 0.4, 19.6, 1.0]) rotate([0, 90, 0])
        cylinder(d = 3, h = 1.2);
}
