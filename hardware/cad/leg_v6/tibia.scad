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
// FOOT = **toe_v2 designed SEAT** (2026-07-06 mesh survey v3, supersedes the
// raw stock outline: its radius wandered 6.5..21 and never mated the shoe's
// inner face — sloppy ring, user catch). The SM3_Foot crescent has THREE
// mating features (all MEASURED, dimensions.md "SM3_Foot"):
//   1. inner face r 12.53 over the core band (|z| < 7.3 of the 20 width)
//   2. retention LIPS r 10.35 at both band edges (|z| 7.3..10), band-bottom
//      120 deg only — they snap over the core disc's faces
//   3. two key TABS mid-band (z +/-2.4, tips r 6.88) at band-ctr +/-80.4
// Seat = two tiers about the post: core disc r 12.35 x 14.2 (mates the
// inner face, sits between the lips, rim chamfered for snap-over) on a
// boss r 10.15 x full 20.1 (clears/undercuts the lips), plus two sector
// key pockets (floor r 6.6, half-angle 19 deg, 6.0 tall, mid-band only so
// the disc rims stay continuous). Pockets symmetrized about the band
// center so the L mirror fits the same shoe (tabs measured 34.6/31 deg
// spans — max + clearance used for both). Tread band centered on
// STANCE-PLUMB (-36 deg from +x); shoe mount theta = 54 deg (shoe band
// ctr 270 + 54 -> -36). Neck wedge to the blade sits in the crescent's
// opening (68..220 tibia az). Jogged 30.5 OUTBOARD like stock (stance
// rationale: nova-proj/project-b2-cad-pass; costs ~0.6 N*m holding/hip).
//
// MATERIAL BASIS (#184): PA6-CF. SOURCED in this file — the safety factors
// below are computed for it (151/75 MPa dry/wet).
// Print: PA6-CF, tab face (-Z) down; support pillars under the blade slab.

include <leg_v6_common.scad>
// toe_profile.scad (stock outline extraction) retired from the build —
// kept on disk as the stock-toe reference only.

TIBIA_LEN   = 129.0;   // kfe axis -> foot hole axis (MEASURED, B2)
SLAB_W      = 2*(CASE_HW + CLR_POCKET + WALL);   // 32.1
SLAB_Z0     = FLOOR_BOT;                          // -22.2
SLAB_Z1     = CASE_TOP;                           // +14.7
TIP_R       = SLAB_W/2;

FOOT_HOLE_D = 7.0;     // stock boot plug hole (measured 6.98)
FOOT_JOG    = 30.5;    // tab mid-plane outboard of kfe plane (MEASURED)
TAB_THK     = 20.1;    // stock toe tab thickness (= shoe band width)
TAB_Z0      = -FOOT_JOG - TAB_THK/2;   // -40.55 (outboard, stock stance)
FOOT_R      = 9.0;
POCKET_END_X = 40;

// ---- toe_v2 seat (shoe numbers: dimensions.md SM3_Foot, mesh survey v3) -----
SEAT_R      = 12.35;   // core disc: shoe inner face r 12.53 - 0.18 clearance
CORE_W      = 14.2;    // core disc width: shoe 14.6 between lips - 0.4
BOSS_R      = 10.15;   // full-width boss under the lips (lip r 10.35 - 0.2)
SEAT_CH     = 1.0;     // disc rim chamfer (45 deg) — shoe snap-over lead-in
BAND_CTR    = -36;     // tread band center = stance-plumb direction
KEY_OFF     = 80.4;    // tab centers: band-ctr +/- 80.4 (measured 189.4/350.2
                       // shoe az about band ctr 270)
KEY_HW      = 19;      // pocket half-angle: tab half-span 17.3 + clearance
KEY_R0      = 6.6;     // pocket floor (tab tips reach r 6.88)
KEY_ZH      = 6.0;     // pocket height (tabs z +/-2.4 -> +/-3.0), mid-band
NECK_A0     = 115; NECK_A1 = 180;   // blade wedge, inside the crescent
                                    // opening (opening spans 68..220)

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
            // toe_v2 seat: full-width boss (under the shoe lips) + chamfered
            // core disc (mates the inner face, between the lips) + neck wedge
            translate([TIBIA_LEN, 0, TAB_Z0]) {
                cylinder(r = BOSS_R, h = TAB_THK, $fn = 96);
                translate([0, 0, TAB_THK/2 - CORE_W/2])
                    rotate_extrude($fn = 96) polygon([
                        [0, 0], [SEAT_R - SEAT_CH, 0], [SEAT_R, SEAT_CH],
                        [SEAT_R, CORE_W - SEAT_CH], [SEAT_R - SEAT_CH, CORE_W],
                        [0, CORE_W]]);
            }
            translate([0, 0, TAB_Z0]) linear_extrude(TAB_THK)
                polygon(concat([[TIBIA_LEN, 0]],
                    [for (a = [NECK_A0 : 5 : NECK_A1])
                     [TIBIA_LEN + 24*cos(a), 24*sin(a)]]));
            // angled web: blade bottom -> tab top face, clipped to the
            // crescent's OPENING sector (70..218 about the post) — the shoe
            // band + horns own every other azimuth at tab z (gate-caught)
            intersection() {
                hull() {
                    translate([106, 0, SLAB_Z0]) cylinder(r = FOOT_R, h = 12);
                    translate([122, 0, TAB_Z0 + TAB_THK - 4]) cylinder(r = 12, h = 4);
                }
                translate([TIBIA_LEN, 0, -60]) linear_extrude(80)
                    polygon(concat([[0, 0]],
                        [for (a = [70 : 4 : 218]) [60*cos(a), 60*sin(a)]]));
            }
        }

        // ---- KFE servo pocket: spline AT ORIGIN, body toward foot ----
        rotate([0, 0, 180]) sts_pocket_neg();

        // side-wall vent window (servo heat relief; hips hold ~22%% torque
        // continuously). CR-6 fix (2026-07-09): the old 16mm-tall raw-cube
        // cut left SF ~1.32 wet (kept only ~18%% of wall section modulus)
        // with zero fillet on its 4 vertical reentrant corners (FDM crack
        // risk). Shrunk to 5mm tall + stadium (fully rounded, r=2.5) profile
        // -> residual strips top 12.2 / bottom 19.7mm, Z 263->573 mm^3,
        // tibia SF dry ~5.8 / wet ~2.9 (M=14.95 N*m, 151/75 MPa PA6-CF;
        // 12kg toe proof).
        // LA-10 bonus fix (2026-07-11): the tibia shares the exact same
        // pocket rotation + ANTIROT_X + vent params as femur.scad:86 (not
        // separately named in the LA-10 finding, but the geometry is
        // identical) -- the near rib at tibia-frame x=12 was bisected by
        // this vent the same way. Same fix: trim the left edge only
        // (x0 2->14, w 22->10), right edge unchanged at x=24.
        vent_window_neg(x0 = 14, w = 10, z_ctr = 0, h = 5, y0 = -17, y1 = 17);

        // side marker: 1 dot = RIGHT (the L mirror wrapper adds a 2nd —
        // mirrored parts are otherwise near-identical at assembly).
        // LA-2 fix (2026-07-11): same bug as femur.scad -- (22,10) sat
        // inside the KFE pocket's open-top XY footprint, cutting air (0
        // solid hits). Relocated to (39,10): the tibia's flat full-height
        // top face only survives x35.65..40 (pocket cut boundary to the
        // blade taper start) -- narrow but clear of the pocket, the
        // x44 zip hole, and the x31 strap bosses. Ray-cast confirmed solid
        // z13.9-14.7, air above.
        translate([39, 10, SLAB_Z1 - 0.8]) cylinder(d = 3, h = 1);

        // strap pilots (into the raised bosses)
        strap_pilot_neg(31, 14.25, SLAB_Z1 + 3.2);

        // ---- CABLE GROOVE: tunnel exit -> underside (added 2026-08-05) ----
        // 🔴 THE TUNNEL HAD NO EXIT. sts_pocket_neg's cable tunnel (shared, 19
        // wide x 5.9 tall, floor z-19.80) ran x36..~43 and then stopped in
        // SOLID MATERIAL: mesh-probed cross-sections showed the tunnel walled
        // on all four sides at x40, and x44/x48 solid across the whole
        // y[-17,17] z[-23,-7] window except the two O3.2 zip bores. A blind
        // pocket. The KFE servo's cable could not leave the tibia.
        //
        // femur.scad has exactly this groove and its LA-1 comment says why:
        // the earlier shallow version "left a solid membrane that DEAD-ENDED
        // the HFE cable". That fix was made on the femur and never propagated
        // here, even though both parts get their tunnel from the SAME shared
        // module. The x44 anchors are even commented "flank the tunnel exit",
        // which reads as confirmation that an exit exists.
        //
        // Geometry mirrors the femur's: cut from the underside exterior
        // (MEASURED flat at z-22.15 across x38..60; SLAB_Z0 = -22.2) up to
        // z-19.05, i.e. 0.75mm PAST the tunnel floor at -19.80, so the void is
        // continuous rather than leaving another membrane. 16 wide clears the
        // 9.8mm servo connector head. Spans both zip anchors (x44, x58) so the
        // cable is captured in the groove, as on the femur.
        //
        // ⚠️ check_fit.py's cable_checks() did NOT catch this: it measures the
        // knee-loop SPAN between anchors and assumes the cable can reach them.
        // x0 = 36, NOT 40. The groove must OVERLAP the tunnel by more than the
        // connector is thick, or the cable can reach the opening and still not
        // get through it. Tunnel runs x36..~43; starting at 40 leaves a 3 mm
        // downward slot against a 4.6 mm connector head, and a O4.6 sphere
        // cannot traverse it (flood-fill verified). Starting at 36 makes the
        // overlap 7 mm and the sphere passes. NB the femur's groove starts at
        // 40 against a tunnel ending at 42.4 -- a 2.4 mm slot -- and fails the
        // same test; that is the part Aiden had to open with a file and pliers.
        translate([36, -8, SLAB_Z0 - EPS])
            cube([24, 16, (-19.05) - (SLAB_Z0 - EPS)]);

        // zip anchors: flank the tunnel exit (strain relief before the
        // plug — cable tension must never reach the servo socket), plus
        // the original pair along the blade.
        // LA-4 fix (2026-07-11): h=12 was a BLIND pocket (matches the
        // femur.scad x44/x52 finding — same shared zip_pair_neg default
        // usage). h=40 matches the x62/84 through-hole convention below.
        zip_pair_neg(44, 0, SLAB_Z0 - 1, 40);
        // LA-30 fix (cable-management review, 2026-07-16): the KNEE loop
        // (femur x84 <-> this tunnel-exit x44 pair, check_fit.py
        // cable_checks()) collapsed to 39.2mm span at the kfe118 mech stop
        // vs the 80mm (2x40mm bend radius) target -- see backlog #18/LA-14.
        // ADDS a SECOND, dedicated pair farther from the kfe axis (x58 vs
        // x44) rather than moving/removing the x44 pair, which stays the
        // tunnel-exit strain relief it always was (LA-4/#31). Geometry:
        // the loop's worst-case span is dominated by the TIBIA-side
        // anchor's radius from the kfe axis (this part's own origin) --
        // moving the femur's fixed x84 anchor barely moves the worst-case
        // number (law-of-cosines cross term), so all of the improvement
        // budget went here. x58 still sits on the full-width blade taper
        // (union of the pocket slab's own rounded cap + the blade hull,
        // POCKET_END_X=40 -> TIP_R=16.05 tapering to r=9 at x=112): real
        // half-width at x58 is ~14.2mm, far more than the >=6.6mm the
        // Ø3.2/spacing-10 pair needs, and the new holes sit >=6.4mm
        // center-to-center from the existing x62 single hole (>3.2mm edge
        // clearance, no merge). MEASURED (check_fit.py --cable, this
        // review): worst-case KNEE span 39.2mm (kfe118, old x44 pair only)
        // -> ~51.6mm (kfe118, x58 pair) -- see cable_checks() for the exact
        // swept table. Still short of the 80mm target (moving the tibia
        // anchor much farther starts trading against "the loop should stay
        // near the knee crossing", not just wall material) -- best
        // achievable via anchor relocation alone; the fold-before-zip
        // discipline (cable_clip.scad, README "Free-loop length") still
        // applies for the remaining shortfall.
        zip_pair_neg(58, 0, SLAB_Z0 - 1, 40);
        for (zx = [62, 84])
            translate([zx, 0, SLAB_Z0 - 1]) cylinder(d = 3.2, h = 40);

        // toe_v2 key pockets: ring sectors about the post, mid-band only —
        // the shoe's tabs snap in; pocket walls key the tread rotation
        for (s = [-1, 1])
            translate([TIBIA_LEN, 0, TAB_Z0 + TAB_THK/2 - KEY_ZH/2])
                linear_extrude(KEY_ZH) polygon(concat(
                    [for (a = [-KEY_HW : 2 : KEY_HW])
                     [(SEAT_R + 1)*cos(BAND_CTR + s*KEY_OFF + a),
                      (SEAT_R + 1)*sin(BAND_CTR + s*KEY_OFF + a)]],
                    [for (a = [KEY_HW : -2 : -KEY_HW])
                     [KEY_R0*cos(BAND_CTR + s*KEY_OFF + a),
                      KEY_R0*sin(BAND_CTR + s*KEY_OFF + a)]]));

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
