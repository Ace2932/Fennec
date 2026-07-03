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
// shoe-key notches) extruded 20.1, jogged 30.5 OUTBOARD like stock: legs
// hang straight with feet directly under the leg columns, semi-wide track
// (~207mm) — the right call for quasi-static v1 bring-up. Costs ~0.6 N*m
// holding per hip (stock paid the same; overtemp limp guard covers it).
// An INBOARD jog (foot 3.3mm from the roll axis, near-zero holding torque,
// narrow 84mm track) was evaluated 2026-07-02 and shelved until a balance
// controller exists — see nova-proj/project-b2-cad-pass memory.
//
// Print: tab face (-Z) down; support pillars under the blade slab.

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
TAB_Z0      = -FOOT_JOG - TAB_THK/2;   // -40.55 (outboard, stock stance)
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
                translate([112, 0, SLAB_Z0])
                    cylinder(r = FOOT_R, h = 13);   // taper keeps the BOTTOM
                                                    // flush (jog is below)
            }
            // toe tab: EXACT stock outline
            translate([0, 0, TAB_Z0])
                linear_extrude(TAB_THK) polygon(TOE_PROFILE);
            // angled web: blade bottom -> tab top face
            hull() {
                translate([106, 0, SLAB_Z0]) cylinder(r = FOOT_R, h = 12);
                translate([122, 0, TAB_Z0 + TAB_THK - 4]) cylinder(r = 12, h = 4);
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
