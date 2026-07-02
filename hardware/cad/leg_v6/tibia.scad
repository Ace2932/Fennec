// =============================================================================
// V6 Tibia — houses the KFE (knee) STS3215, blade down to the foot pin.
// =============================================================================
// Local frame: kfe axis = Z THROUGH THE ORIGIN. +X toward the foot.
// Foot pin axis = Z line at x = TIBIA_LEN (129.0, measured — locked to B2).
//
// The knee end is femur's hip end pattern: open-top pocket, horn up (+Z =
// INBOARD once assembled — bolts into the femur yoke's top arm), floor pad
// with M3 heat-set down (femur bottom arm idler).
//
// LATERAL JOG: stock tibia S-curves the blade to put the foot 30.5 mm
// outboard of the kfe plane. V6 keeps the blade straight (stiffer) and gets
// the same offset from a long foot post off the OUTBOARD (-Z) face:
// post spans z -21..-40 -> center -30.5 = measured foot-plane offset.
// Stock Ø7 post (measured 6.98) so the stock SM3_Foot rubber slips on.
//
// Print: flat on the -Z face; post prints as a horizontal cylinder? NO —
// print on -Z face means post points UP... print on +Z (rim) face instead:
// pocket opening down needs supports. RECOMMENDED: print on -Z face with the
// post vertical (up) — no supports in pocket, post gets full-strength
// vertical layers? Vertical-layer post = weak in bending. Best: -Z face down
// WITH the post as a separate press-in pin? Keep it simple: print -Z down,
// post grows up as a vertical cylinder = layer lines across the post axis
// are fine for a compression-loaded pin wrapped in rubber; revisit after
// first-article abuse test.

include <leg_v6_common.scad>

TIBIA_LEN   = 129.0;   // kfe axis -> foot pin axis (MEASURED, B2)
SLAB_W      = SERVO_W + 2*WALL + 2*CLR_POCKET;   // 31.7
SLAB_Z0     = -(SERVO_H/2 + FLOOR);              // -20.15
SLAB_Z1     =  SERVO_H/2;                        // +17.15
TIP_R       = SLAB_W/2;

FOOT_POST_D   = 7.0;    // stock SM3_Foot rubber fits this
FOOT_POST_LEN = 19.0;
FOOT_JOG      = 30.5;   // foot plane outboard of kfe plane (MEASURED)
FOOT_R        = 9.0;    // blade end radius at the foot
POCKET_END_X  = 40;     // pocket block ends (body wall at 38.4)

module tibia_v6() {
    difference() {
        union() {
            // knee pocket block: rounded knee end (around origin) to x=40
            translate([POCKET_END_X/2, 0, SLAB_Z0])
                slab(POCKET_END_X + SLAB_W, SLAB_W, SLAB_Z1 - SLAB_Z0);
            // blade: tapers in width + thins toward the foot (keeps the
            // outboard face flush at SLAB_Z0 so the post root is continuous)
            hull() {
                translate([POCKET_END_X, 0, SLAB_Z0])
                    cylinder(r = TIP_R, h = SLAB_Z1 - SLAB_Z0);
                translate([TIBIA_LEN, 0, SLAB_Z0])
                    cylinder(r = FOOT_R, h = 13);
            }
            // foot post: base boss + Ø7 pin, centered z = -30.5
            translate([TIBIA_LEN, 0, SLAB_Z0 - 0.85])
                cylinder(d = 12, h = 0.9 + EPS);          // root boss
            translate([TIBIA_LEN, 0, SLAB_Z0 - 0.85 - FOOT_POST_LEN])
                cylinder(d = FOOT_POST_D, h = FOOT_POST_LEN + EPS);
            // knee idler pad (femur bottom arm pivots here)
            idler_pad_pos(SLAB_Z0);
        }

        // ---- KFE servo pocket: spline axis AT ORIGIN, body toward foot ----
        rotate([0, 0, 180]) translate([-SPLINE_X, 0, 0]) servo_pocket_neg();

        // knee idler heat-set bore
        idler_heatset_neg(SLAB_Z0);

        // wire exit channel: open-top groove continuing the pocket slot
        translate([38, -7, SLAB_Z1 - 6]) cube([18, 14, 12.1]);

        // zip-tie anchors through the blade
        for (zx = [62, 84])
            translate([zx, 0, SLAB_Z0 - 1]) cylinder(d = 3.2, h = 40);

        // post tip chamfer (rubber slip-on lead-in)
        translate([TIBIA_LEN, 0, SLAB_Z0 - 0.85 - FOOT_POST_LEN - EPS])
            difference() {
                cylinder(d = FOOT_POST_D + 2, h = 1.2);
                cylinder(d1 = FOOT_POST_D - 1.6, d2 = FOOT_POST_D + 0.2, h = 1.25);
            }
    }
}

tibia_v6();
