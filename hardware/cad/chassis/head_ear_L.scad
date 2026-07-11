// LEFT head ear = Y-mirror of the right part (head_ear.scad).
$fn = 32;
use <head_ear.scad>
mirror([0, 1, 0]) head_ear();
