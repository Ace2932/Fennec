// =============================================================================
// V6 Tibia (rev 2) — houses the KFE STS3215, blade down to the stock toe.
// =============================================================================
// Local frame: kfe axis = Z THROUGH THE ORIGIN (spline). +X toward the foot.
// Foot hole axis = Z line at x = TIBIA_LEN (129.0, MEASURED — locked to B2).
//
// Knee end = the standard rev-2 pocket: open top, bay-seat floor, wheel
// window (the femur's bottom-arm boss bolts the wheel through it), 4x M2
// case-column screws, strap bosses, rear cable tunnel toward the foot.
//
// FOOT = stock toe outline (toe_profile.scad, mesh-extracted with both
// shoe-key notches) extruded 20.1 — but jogged INBOARD (+z, the horn side),
// the OPPOSITE of stock: foot plane lands 33.8-30.5 = 3.3mm from the haa
// roll axis => near-zero standing roll torque on the hip servos (stock's
// outboard jog costs ~0.77 N*m/hip holding, 26% of rating). Wide stance is
// recovered on demand by rolling the hips out. Swept-verified: tab+shoe
// orbit the knee at r>=114.7, femur fork reaches r<=15.85 -> clear at any
// fold; inboard tab z-band (20.45..40.55) never overlaps the femur slab.
//
// Print: pocket rim (+Z) up, flat on -Z; supports under the raised tab.

include <leg_v6_common.scad>
include <toe_profile.scad>

TIBIA_LEN   = 129.0;   // kfe axis -> foot hole axis (MEASURED, B2)
SLAB_W      = 2*(CASE_HW + CLR_POCKET + WALL);   // 31.7
SLAB_Z0     = FLOOR_BOT;                          // -22.2
SLAB_Z1     = CASE_TOP;                           // +14.7
TIP_R       = SLAB_W/2;

FOOT_HOLE_D = 7.0;     // stock boot plug hole (measured 6.98)
FOOT_JOG    = 30.5;    // tab mid-plane outboard of kfe plane (MEASURED)
TAB_THK     = 20.1;    // stock toe tab thickness
TAB_Z0      =  FOOT_JOG - TAB_THK/2;   // +20.45 (INBOARD jog, see header)
FOOT_R      = 9.0;
POCKET_END_X = 40;

module tibia_v6() {
    difference() {
        union() {
            // knee pocket block
            translate([POCKET_END_X/2, 0, SLAB_Z0])
                slab(POCKET_END_X + SLAB_W, SLAB_W, SLAB_Z1 - SLAB_Z0);
            rotate([0, 0, 180]) pocket_platform_pos();
            // strap bosses (strap clears the case top cap)
            for (sy = [-1, 1])
                translate([31, sy*14.25, SLAB_Z1 - EPS])
                    cylinder(d = 7, h = 3.2);
            // blade toward the foot
            hull() {
                translate([POCKET_END_X, 0, SLAB_Z0])
                    cylinder(r = TIP_R, h = SLAB_Z1 - SLAB_Z0);
                translate([112, 0, SLAB_Z1 - 13])
                    cylinder(r = FOOT_R, h = 13);   // taper keeps the TOP flush
                                                    // (jog + web are above now)
            }
            // toe tab: EXACT stock outline
            translate([0, 0, TAB_Z0])
                linear_extrude(TAB_THK) polygon(TOE_PROFILE);
            // angled web: blade top -> tab underside
            hull() {
                translate([106, 0, SLAB_Z1 - 12]) cylinder(r = FOOT_R, h = 12);
                translate([122, 0, TAB_Z0]) cylinder(r = 12, h = 4);
            }
        }

        // ---- KFE servo pocket: spline AT ORIGIN, body toward foot ----
        rotate([0, 0, 180]) sts_pocket_neg();

        // strap pilots (into the raised bosses)
        strap_pilot_neg(31, 14.25, SLAB_Z1 + 3.2);

        // zip-tie anchors through the blade
        for (zx = [62, 84])
            translate([zx, 0, SLAB_Z0 - 1]) cylinder(d = 3.2, h = 40);

        // Ø7 boot-plug through-hole at the measured foot point, chamfered
        translate([TIBIA_LEN, 0, TAB_Z0 - EPS]) {
            cylinder(d = FOOT_HOLE_D, h = TAB_THK + 2*EPS);
            cylinder(d1 = FOOT_HOLE_D + 1.6, d2 = FOOT_HOLE_D, h = 1);
            translate([0, 0, TAB_THK - 1 + 2*EPS])
                cylinder(d1 = FOOT_HOLE_D, d2 = FOOT_HOLE_D + 1.6, h = 1);
        }
    }
}

tibia_v6();
