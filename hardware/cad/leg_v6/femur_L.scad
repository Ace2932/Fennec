// LEFT femur = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <femur.scad>
mirror([0, 0, 1]) femur_v6();
