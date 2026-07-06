// Jetson standoff spacer — 4 needed + spares (print 8). Sits between the
// flat riser deck and the Orin Nano carrier at each mount bore; M3x16
// passes through carrier + spacer + deck into the underslung heat-set.
// 6.3 tall -> carrier board plane at trunk z 78.2: clears the mast base
// flange corner under the Jetson edge AND lifts the port row over the
// deck slot (see riser_bay.scad header).
$fn = 48;
difference() {
    cylinder(d = 8, h = 6.3);
    translate([0, 0, -0.05]) cylinder(d = 3.4, h = 6.5);
}
