// =============================================================================
// NovaSM3 Leg V6 — functional STS3215 leg, designed for assembly   (rev 2)
// =============================================================================
// rev 2 (2026-07-02): pocket + joint rebuilt against the FULL servo model
// (feetech_servo_models/converted_stl/servo.stl, from STS3215_03a v1.step).
// The earlier "case mount square" was a misread — those holes belong to the
// horn/wheel discs. Real case anatomy (spline-relative, shaft = +Z):
//   case box     x -35.2..+10.2, y ±12.4, z -15.5..+14.7
//   top rear cap ridge to z 17.4 (x -34.8..-28.5, y ±7)
//   OUTPUT HORN  Ø20 x 2.5, z 14.7..17.2, 4x M2.5 on Ø14 BCD ±45° + center
//   BOTTOM WHEEL Ø20 x 2.1, z -17.7..-15.6, same screw pattern (standard!)
//   connector BAY: rear-bottom drops to z -19.4 over case x < -5.3; the two
//     3-pin sockets sit mid-body facing the rear
//   4x CASE-SCREW COLUMNS (Ø2 self-tap, heads at bottom): the REAL mounting
//     — replace with longer M2 screws through the pocket floor:
//     (-8.3, ±10.2) and (-32.8, ±10.25)
//
// Joint pattern (SO-ARM-style, bolted BOTH sides):
//   * driven yoke TOP arm bolts the horn (underside contacts horn face 17.2)
//   * driven yoke BOTTOM arm carries a Ø19 boss up through the pocket
//     floor's Ø24 window and BOLTS THE WHEEL (face -17.7)
//   * servo body: drops into the open-top pocket; floor seats the bay
//     (-19.7) + a raised front platform (-15.6); 4x M2 x >=22 through-floor
//     into the case columns; printed strap over the tail as backup
//   * cables: plug BEFORE drop-in; wires lie in the bay and exit the rear
//     end wall through the cable tunnel
//
// KINEMATICS LOCKED (dimensions.md §6): femur 106.9 · tibia 129.0 ·
// hip laterals 33.8/0/30.5 (Σ 64.3 = IK d). Unaffected by rev 2.

$fn = 64;
EPS = 0.05;

// ---- STS3215, spline-relative, mesh-verified --------------------------------
CASE_X0   = -35.2;  CASE_X1 = 10.2;      // case box along the long axis
CASE_HW   = 12.4;                        // case half-width (y)
CASE_TOP  = 14.7;                        // top face (pocket rim plane)
CASE_BOT  = -15.5;                       // front-zone bottom face
CAP_TOP   = 17.4;                        // rear top cap ridge
BAY_X1    = -5.3;                        // bay extends CASE_X0..BAY_X1
BAY_BOT   = -19.4;                       // bay bottom face
HORN_Z0   = 14.7;   HORN_Z1 = 17.2;      // output horn disc faces
HORN_OD   = 20.0;
HORN_BCD  = 14.0;                        // 4x M2.5 at ±45° + center (both discs)
WHEEL_Z0  = -17.7;  WHEEL_Z1 = -15.6;    // bottom wheel faces
WHEEL_OD  = 20.0;
COL_PTS   = [[-8.3, 10.2], [-8.3, -10.2], [-32.8, 10.25], [-32.8, -10.25]];

// ---- fits / hardware ---------------------------------------------------------
CLR_POCKET = 0.25;
CLR_HORN   = 0.15;
M2_CLEAR   = 2.3;    // case-column replacement screws (M2 self-tap)
M25_CLEAR  = 2.9;    // horn / wheel disc screws
M3_CLEAR   = 3.4;    // horn center (fits M3; wheel center is M2.5 -> 2.9)
WALL       = 3.2;
FLOOR      = 2.5;    // under the bay seat
FLOOR_TOP  = BAY_BOT - 0.3;              // -19.7 bay seat plane
FLOOR_BOT  = FLOOR_TOP - FLOOR;          // -22.2
ARM_THK    = 4.0;
WHEEL_WIN_D  = 21.5;                     // floor window (wheel Ø20 + boss Ø19 clear)
WHEEL_BOSS_D = 19.0;                     // yoke bottom-arm boss through it
// yoke arm planes (contact, bolted):
YOKE_TOP_IN = HORN_Z1;                   // 17.2  top-arm underside ON horn
YOKE_BOT_IN = FLOOR_BOT - 0.4;           // -22.6 bottom-arm plate top (0.4: PA6-CF shrink robustness)

// =============================================================================
// MODULES — SPLINE AXIS = Z THROUGH ORIGIN. Case body extends toward -X.
// Callers rotate/translate the whole set.
// =============================================================================

// Pocket NEGATIVE: subtract from a solid. Open top (+Z), bay-seat floor,
// wheel window, 4x case-column screw holes (countersunk at FLOOR_BOT),
// rear cable tunnel out the -X end wall.
module sts_pocket_neg(extra_top = 30) {
    c = CLR_POCKET;
    union() {
        // case void, opened upward (clears the rear top cap too)
        translate([(CASE_X0 + CASE_X1)/2, 0,
                   (CASE_BOT - c + CASE_TOP + extra_top)/2])
            cube([CASE_X1 - CASE_X0 + 2*c, 2*(CASE_HW + c),
                  CASE_TOP - CASE_BOT + extra_top + c], center = true);
        // connector bay void (rear-bottom step) — FULL case width: the real
        // bay spans y ±12.35 (fit-gate finding 2026-07-02; the earlier -2mm
        // guess cut 1.7mm into the servo sides on every pocket)
        translate([(CASE_X0 + BAY_X1)/2, 0, (BAY_BOT - c + CASE_BOT + 1)/2])
            cube([BAY_X1 - CASE_X0 + 2*c, 2*(CASE_HW + c),
                  CASE_BOT - BAY_BOT + 1 + 2*c], center = true);
        // wheel window through the floor (bottom-arm boss enters here)
        translate([0, 0, FLOOR_BOT - EPS])
            cylinder(d = WHEEL_WIN_D, h = -FLOOR_BOT + WHEEL_Z1 + 1);
        // 4x case-column screws: through-floor + countersink cones
        for (p = COL_PTS) {
            translate([p[0], p[1], FLOOR_BOT - 1])
                cylinder(d = M2_CLEAR, h = FLOOR + BAY_BOT - FLOOR_BOT + 3);
            translate([p[0], p[1], FLOOR_BOT - EPS])
                cylinder(d1 = 4.6, d2 = M2_CLEAR, h = 1.4);
        }
        // cable tunnel: bay level out the -X end wall
        translate([CASE_X0 - WALL - 4, -9.5, BAY_BOT - 0.4])
            cube([WALL + 8, 19, CASE_BOT - BAY_BOT + 2]);
    }
}

// Front-platform POSITIVE: raises the floor to seat the case's front bottom
// face (-15.5) outboard of the bay, ringing the wheel window. Union AFTER
// the main solid, BEFORE subtracting sts_pocket_neg (the pocket void stops
// at CASE_BOT so the platform survives; the wheel window re-cuts it).
module pocket_platform_pos() {
    difference() {
        translate([BAY_X1, -(CASE_HW + CLR_POCKET), FLOOR_TOP - EPS])
            cube([CASE_X1 - BAY_X1 + CLR_POCKET + WALL,
                  2*(CASE_HW + CLR_POCKET),
                  CASE_BOT - 0.1 - FLOOR_TOP]);
        translate([0, 0, FLOOR_BOT - 1]) cylinder(d = WHEEL_WIN_D, h = 30);
    }
}

// Horn coupling NEGATIVE for a yoke TOP arm spanning z [YOKE_TOP_IN,
// YOKE_TOP_IN+ARM_THK]: shallow Ø20 locating recess + 4x M2.5 BCD + center.
module horn_couple_neg() {
    translate([0, 0, YOKE_TOP_IN - EPS]) {
        cylinder(d = HORN_OD + 2*CLR_HORN, h = 0.4 + EPS);   // locating recess
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                cylinder(d = M25_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = M3_CLEAR, h = ARM_THK + 2*EPS);
    }
}

// Wheel coupling for a yoke BOTTOM arm whose plate spans
// z [YOKE_BOT_IN-ARM_THK, YOKE_BOT_IN]: POSITIVE boss reaching the wheel
// face through the floor window + NEGATIVE screws w/ head counterbores.
module wheel_boss_pos() {
    translate([0, 0, YOKE_BOT_IN - EPS]) {
        cylinder(d = WHEEL_BOSS_D, h = WHEEL_Z0 - YOKE_BOT_IN + EPS);
        // shallow locating recess lip around the wheel
        translate([0, 0, WHEEL_Z0 - YOKE_BOT_IN - 0.4])
            cylinder(d = WHEEL_BOSS_D, h = 0.4);
    }
}
module wheel_couple_neg() {
    h_all = (WHEEL_Z0 - YOKE_BOT_IN) + ARM_THK + 1 + 2*EPS;
    translate([0, 0, YOKE_BOT_IN - ARM_THK - 1]) {
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0]) {
                cylinder(d = M25_CLEAR, h = h_all);
                cylinder(d = 5.2, h = 1 + 1.6);   // head counterbore
            }
        cylinder(d = M25_CLEAR, h = h_all);        // center (wheel is M2.5)
        cylinder(d = 5.2, h = 1 + 1.6);
    }
}

// Zip-tie anchor NEGATIVE: Ø3.2 through-hole pair, spacing 10, for
// strain-relieving the cable bundle (daisy link + VCC spur) at tunnel
// exits and along runs. Axis along Z at (x0, y0), full depth h from z0.
module zip_pair_neg(x0, y0 = 0, z0 = -30, h = 60, spacing = 10) {
    for (s = [-1, 1])
        translate([x0, y0 + s*spacing/2, z0]) cylinder(d = 3.2, h = h);
}

// Retention-strap pilots: 2x Ø2.05 self-tap into the side-wall rims (LINK
// frame; wall_y = wall centerline, rim_z = pocket rim = CASE_TOP).
module strap_pilot_neg(x0 = 31, wall_y = 14.25, rim_z = CASE_TOP) {
    for (sy = [-1, 1])
        translate([x0, sy*wall_y, rim_z - 8])
            cylinder(d = 2.05, h = 8 + EPS);
}

// STS3215 solid, spline at origin (preview): case + bay + horn + wheel.
module sts3215_solid() {
    translate([(CASE_X0+CASE_X1)/2, 0, (CASE_BOT+CASE_TOP)/2])
        cube([CASE_X1-CASE_X0, 2*CASE_HW, CASE_TOP-CASE_BOT], center = true);
    translate([(CASE_X0+BAY_X1)/2, 0, (BAY_BOT+CASE_BOT)/2])
        cube([BAY_X1-CASE_X0, 2*(CASE_HW-2), CASE_BOT-BAY_BOT], center = true);
    translate([0, 0, HORN_Z0]) cylinder(d = HORN_OD, h = HORN_Z1 - HORN_Z0);
    translate([0, 0, WHEEL_Z0]) cylinder(d = WHEEL_OD, h = WHEEL_Z1 - WHEEL_Z0);
}

// stadium slab
module slab(l, w, t) {
    hull() for (sx = [-1, 1])
        translate([sx*(l/2 - w/2), 0, 0]) cylinder(r = w/2, h = t);
}
