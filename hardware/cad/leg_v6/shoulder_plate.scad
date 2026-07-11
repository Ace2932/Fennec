// =============================================================================
// V6 Shoulder horn plate — RIGHT side (mirror for left). Print 2 + 2.
// =============================================================================
// L-bracket hanging from the shoulder deck: vertical face bolts the haa
// HORN (rear surface = the horn plane y 17.75); top flange bolts DOWN onto
// the deck (4x M3 into its heat-sets). Removing the 4 deck screws + one
// cable unplug drops the whole leg — the horn stays on this plate.
// Sweep-safe by construction: every solid lives at y >= 17.75 or z >= 30.
// Print: horn-seat face DOWN (perfect seat, knee_arm doctrine).
// rev 3 (2026-07-10): seat plane moved 17.2->17.75 (caliper gap fix — see
// leg_v6_common.scad HORN_Z1); matches shoulder.scad's HORN_Y.

include <leg_v6_common.scad>

HIP_X   = 39.05;
FACE_Y0 = 17.75; FACE_Y1 = 21.75;     // vertical face (4 thick)
FLAN_Z0 = 41.5;  FLAN_Z1 = 44.7;      // top flange on the deck (deck top 41.5)
PLATE_BX = [27, 51];
PLATE_BY = [6.2, 15.2];

module shoulder_plate_R() {
    difference() {
        union() {
            // vertical face: covers the horn + rises past the deck edge
            hull() {
                translate([HIP_X, FACE_Y0, 0]) rotate([-90, 0, 0])
                    cylinder(r = 14, h = FACE_Y1 - FACE_Y0);
                translate([23, FACE_Y0, FLAN_Z1 - 6])
                    cube([32, FACE_Y1 - FACE_Y0, 6]);
            }
            // top flange rearward over the deck
            translate([23, PLATE_BY[0] - 4.2, FLAN_Z0])
                cube([32, FACE_Y1 - (PLATE_BY[0] - 4.2), FLAN_Z1 - FLAN_Z0]);
        }
        // horn coupling on the REAR surface of the face. Center: Ø6.5 x 2.5
        // deep blind counterbore (rev 3) clears the horn's own proud
        // retention screw head (Ø5.4, ~1.5mm proud, MEASURED) — was
        // Ø3.4/M3_CLEAR through the full 4mm face, too narrow to clear it.
        translate([HIP_X, FACE_Y0 - EPS, 0]) rotate([-90, 0, 0]) {
            cylinder(d = HORN_OD + 2*CLR_HORN, h = 0.4 + EPS);  // locating recess
            for (a = [45 : 90 : 315])
                rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                    cylinder(d = M25_CLEAR, h = FACE_Y1 - FACE_Y0 + 2*EPS);
            cylinder(d = HORN_CTR_D, h = HORN_CTR_DEEP + EPS);
        }
        // 4x M3 down through the flange (diagonal pair close-fit = dowels)
        for (bx = PLATE_BX, by = PLATE_BY) {
            dowel = (bx == PLATE_BX[0] && by == PLATE_BY[0])
                 || (bx == PLATE_BX[1] && by == PLATE_BY[1]);
            translate([bx, by, FLAN_Z0 - EPS])
                cylinder(d = dowel ? 3.1 : M3_CLEAR,
                         h = FLAN_Z1 - FLAN_Z0 + 2*EPS);
            translate([bx, by, FLAN_Z1 - 1.8]) cylinder(d = 6.4, h = 2);
        }

        // side marker (LA-2, 2026-07-11): shoulder_plate carried NO L/R
        // convention at all before this fix. 1 dot = RIGHT (L wrapper adds
        // a 2nd). Front face of the vertical face (y=FACE_Y1=21.75, the
        // face opposite the horn) at (x=45,z=10): clear of the horn BCD
        // screw holes (radius 7 about HIP_X=39.05, holes at z+-4.95) and
        // the flange dowel/clear holes (higher z, FLAN_Z0..FLAN_Z1).
        // Ray-cast confirmed solid to ~3mm depth (real material, the face
        // is 4mm thick) and air just outside y=21.75.
        translate([45, FACE_Y1 + EPS, 10]) rotate([90, 0, 0])
            cylinder(d = 3, h = 1);
    }
}

shoulder_plate_R();
