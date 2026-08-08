// Jetson standoff spacer — 4 needed + spares (print 8). Sits between the
// flat riser deck and the Orin Nano carrier at each mount bore; **M3x14**
// through carrier + spacer + deck into the underslung heat-set (5.2mm
// engagement; x16 would graze the stack envelope, x12 only bites 3.2).
// 6.3 tall -> carrier board plane at trunk z 78.2: clears the mast base
// flange corner under the Jetson edge AND lifts the port row over the
// deck slot (see riser_bay.scad header).
// PRINT: OPEN ITEM (#184) — no material recorded anywhere for this part,
//   here or in print-batch.md §2. slice_plate.py lists it UNRESOLVED for
//   exactly that reason. Not guessed: a small non-structural standoff is
//   plausibly PETG-CF like its riser-deck neighbors, but that has not
//   actually been decided.
$fn = 48;
difference() {
    cylinder(d = 8, h = 6.3);
    translate([0, 0, -0.05]) cylinder(d = 3.4, h = 6.5);
}
