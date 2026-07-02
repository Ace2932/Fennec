// LEFT coax = X-mirror of the right part (lateral axis = X in coax frame).
$fn = 64;
use <coax.scad>
mirror([1, 0, 0]) coax_v6();
