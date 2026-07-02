// LEFT tibia = Z-mirror of the right part (lateral axis = Z in part frame).
$fn = 64;
use <tibia.scad>
mirror([0, 0, 1]) tibia_v6();
