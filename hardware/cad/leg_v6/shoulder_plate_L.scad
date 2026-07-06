// LEFT shoulder horn plate = X-mirror of the right.
$fn = 64;
use <shoulder_plate.scad>
mirror([1, 0, 0]) shoulder_plate_R();
