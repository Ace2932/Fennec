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
// FOOT = stock-clone TOE TAB (measured from SM3_Frame_RightTibia +
// SM3_Foot): tab 20.1 thick, ~28 wide at the Ø7 through-hole, rounded tip
// r6 ending 9 past the hole — the stock SM3_Foot rubber bootie wraps this
// tab and its plug snaps into the hole. Tab plane centered z = -30.5 =
// the measured lateral jog (blade stays straight; an angled web bridges
// blade -> tab).
//
// Print: tab outboard face (-Z) down; blade underside sits 20 above the
// bed -> needs support pillars under the blade slab (flat, easy removal);
// pocket still prints support-free.

include <leg_v6_common.scad>
include <toe_profile.scad>

TIBIA_LEN   = 129.0;   // kfe axis -> foot pin axis (MEASURED, B2)
SLAB_W      = SERVO_W + 2*WALL + 2*CLR_POCKET;   // 31.7
SLAB_Z0     = -(SERVO_H/2 + FLOOR);              // -20.15
SLAB_Z1     =  SERVO_H/2;                        // +17.15
TIP_R       = SLAB_W/2;

FOOT_HOLE_D = 7.0;     // stock boot plug hole (measured 6.98)
FOOT_JOG    = 30.5;    // tab mid-plane outboard of kfe plane (MEASURED)
TAB_THK     = 20.1;    // stock toe tab thickness (boot cavity height)
TAB_Z0      = -FOOT_JOG - TAB_THK/2;   // -40.55
FOOT_R      = 9.0;     // blade end radius
POCKET_END_X = 40;     // pocket block ends (body wall at 38.4)

module tibia_v6() {
    difference() {
        union() {
            // knee pocket block: rounded knee end (around origin) to x=40
            translate([POCKET_END_X/2, 0, SLAB_Z0])
                slab(POCKET_END_X + SLAB_W, SLAB_W, SLAB_Z1 - SLAB_Z0);
            // blade: tapers toward the foot, ends before the toe web
            hull() {
                translate([POCKET_END_X, 0, SLAB_Z0])
                    cylinder(r = TIP_R, h = SLAB_Z1 - SLAB_Z0);
                translate([112, 0, SLAB_Z0])
                    cylinder(r = FOOT_R, h = 13);
            }
            // toe tab: EXACT stock outline (toe_profile.scad, mesh-extracted)
            // so the SM3_Foot crescent shoe keys on unmodified
            translate([0, 0, TAB_Z0])
                linear_extrude(TAB_THK) polygon(TOE_PROFILE);
            // angled web: blade end -> tab inboard face
            hull() {
                translate([106, 0, SLAB_Z0]) cylinder(r = FOOT_R, h = 12);
                translate([122, 0, TAB_Z0 + TAB_THK - 4]) cylinder(r = 12, h = 4);
            }
            // knee idler pad (femur bottom arm pivots here)
            idler_pad_pos(SLAB_Z0);
        }

        // ---- KFE servo pocket: spline axis AT ORIGIN, body toward foot ----
        rotate([0, 0, 180]) translate([-SPLINE_X, 0, 0]) servo_pocket_neg();

        // knee idler heat-set bore
        idler_heatset_neg(SLAB_Z0);

        // retention-strap pilots (strap.scad screws over the servo tail)
        strap_pilot_neg(31);

        // wire exit channel: open-top groove continuing the pocket slot
        translate([38, -7, SLAB_Z1 - 6]) cube([18, 14, 12.1]);

        // zip-tie anchors through the blade
        for (zx = [62, 84])
            translate([zx, 0, SLAB_Z0 - 1]) cylinder(d = 3.2, h = 40);

        // Ø7 boot-plug through-hole at EXACTLY the measured foot point,
        // light chamfer both faces for the rubber plug
        translate([TIBIA_LEN, 0, TAB_Z0 - EPS]) {
            cylinder(d = FOOT_HOLE_D, h = TAB_THK + 2*EPS);
            cylinder(d1 = FOOT_HOLE_D + 1.6, d2 = FOOT_HOLE_D, h = 1);
            translate([0, 0, TAB_THK - 1 + 2*EPS])
                cylinder(d1 = FOOT_HOLE_D, d2 = FOOT_HOLE_D + 1.6, h = 1);
        }
    }
}

tibia_v6();
