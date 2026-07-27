// =============================================================================
// NovaSM3 Leg V6 — functional STS3215 leg, designed for assembly   (rev 2)
// =============================================================================
// rev 2 (2026-07-02): pocket + joint rebuilt against the FULL servo model
// (feetech_servo_models/converted_stl/servo.stl, from STS3215_03a v1.step).
// The earlier "case mount square" was a misread — those holes belong to the
// horn/wheel discs. Real case anatomy (spline-relative, shaft = +Z):
//   case box     x -35.2..+10.2, y ±12.4, z -15.5..+14.7
//   top rear cap ridge to z 17.4 (x -34.8..-28.5, y ±7)
//   OUTPUT HORN  Ø20 x ~3.05, z 14.7..17.75, 4x M2.5 on Ø14 BCD ±45° + center
//   BOTTOM WHEEL Ø20 x ~2.15, z -17.75..-15.6, same screw pattern (standard!)
//   rev 3 (2026-07-10): disc-to-disc CALIPERED on the bare servo = 35.5mm
//   (tip-to-tip incl. protrusions = 39.1). The mesh-derived 34.9mm gap
//   (17.2 top / -17.7 bottom) was 0.6mm too narrow — arms wouldn't seat
//   flat. HORN_Z1/WHEEL_Z0 (the yoke SEAT planes, not the case/pocket
//   envelope) moved outward to ±17.75, split symmetrically about the
//   shaft (Z=0) so no joint axis moves — only the two seat planes do.
//   Driven-side retention screw (Ø5.4, ~1.5mm proud) and idler-side
//   plastic boss (Ø6, ~1-2mm proud) now get real center reliefs instead
//   of a Ø3.4 through-hole that couldn't clear either.
//   connector BAY: rear-bottom drops to z -19.4 over case x < -5.3; the two
//     3-pin sockets sit mid-body facing the rear
//   4x CASE-SCREW COLUMNS (Ø2 self-tap, heads at bottom): the REAL mounting
//     — replace with longer M2 screws through the pocket floor:
//     (-8.3, ±10.2) and (-32.8, ±10.25)
//
// Joint pattern (SO-ARM-style, bolted BOTH sides):
//   * driven yoke TOP arm bolts the horn (underside contacts horn face 17.75)
//   * driven yoke BOTTOM arm carries a Ø19 boss up through the pocket
//     floor's Ø21.5 window (WHEEL_WIN_D) and BOLTS THE WHEEL
//     (face WHEEL_Z0 -17.75, rev 3)
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
HORN_Z0   = 14.7;   HORN_Z1 = 17.75;     // output horn disc faces. HORN_Z1 =
                                          // yoke SEAT plane, CALIPERED (rev 3):
                                          // disc-to-disc 35.5 split symmetric
                                          // about the shaft (Z=0) -> ±17.75.
                                          // HORN_Z0 (case-side face) unmoved.
HORN_OD   = 20.0;
HORN_BCD  = 14.0;                        // 4x M2.5 at ±45° + center (both discs)
WHEEL_Z0  = -17.75; WHEEL_Z1 = -15.6;    // bottom wheel faces. WHEEL_Z0 = yoke
                                          // SEAT plane, same rev-3 caliper fix.
WHEEL_OD  = 20.0;
COL_PTS   = [[-8.3, 10.2], [-8.3, -10.2], [-32.8, 10.25], [-32.8, -10.25]];

// ---- ANTI-ROTATION RIBS (2026-07-07, servo_pocket_analysis.py) ----------------
// The joint torque is reacted about the output axis (Z). With the walls at the
// full 0.45 slip fit, ALL of it rides the 4 M2 self-tap screws in the SERVO's
// own plastic -> cyclic loosening/back-out over trot life (the real weakness,
// not a static one; the femur has NO strap so it depends on this entirely).
// FIX: crush ribs on the ±Y case flats reduce the rotational slop 0.45 -> 0.1
// and take the torque as WALL BEARING (SF ~570 at 12V stall) so the screws see
// only axial retention. Ribs stand PROUD 0.35 -> 0.1 nominal clearance = FREE
// drop-in preserved (contact only under load); the thin tip crushes to take up
// print tolerance. 2 x-stations near the case ends (max arm, bidirectional),
// clear of the screw columns (-8.3/-32.8), the bay (z<-15.5) + wheel window.
ANTIROT_X     = [-30, -12];   ANTIROT_Z = [-13, 13];
ANTIROT_PROUD = 0.35;         ANTIROT_BASE = 1.4;
// LEAD-IN (2026-07-16): the servo case enters the open pocket TOP (+Z, see
// sts_pocket_neg's "open top" comment) and seats DOWN toward the floor
// (-Z, bay/case-column side) -- so the rib's FIRST contact as the case
// drops in is its +Z end (ANTIROT_Z[1] = 13, only 1.7mm below the CASE_TOP
// rim). Full 0.35 interference right at that mouth would gouge/gall the
// case on entry (drop-in assembly needs a soft touchdown, not a scrape).
// Ramp the last ANTIROT_LEADIN mm of the +Z end from ~0 interference (flush
// with the void wall, hw) down to the full crush profile at
// ANTIROT_Z[1]-ANTIROT_LEADIN; the -Z (floor) end is untouched (case seats
// there last, already at full engagement, no lead-in needed).
ANTIROT_LEADIN = 2.5;
// The taper's mouth-end profile can't be a truly zero-area polygon (apex
// exactly ON the base line) -- OpenSCAD silently drops a degenerate/zero-
// area polygon's linear_extrude, which collapsed the hull() to just the
// full-interference slice in testing (no taper at all, confirmed by
// scratch-render + ray-cast probe). ANTIROT_MOUTH_PROUD is a tiny residual
// interference (not a real design dimension) that only exists to keep the
// polygon non-degenerate; functionally it IS ~0.
ANTIROT_MOUTH_PROUD = 0.02;

// ---- fits / hardware ---------------------------------------------------------
CLR_POCKET = 0.45;   // DROP-IN slip fit. NOT the 0.30 press calibration
                     // (parametric-servo-fit.md — that's for v5-style
                     // carved pockets). Location comes from the 4 column
                     // screws (O2 in O2.3 = +/-0.15), walls only guide;
                     // 0.25 was tighter than the calibrated press = servo
                     // would not drop in.
CLR_HORN   = 0.15;
M2_CLEAR   = 2.3;    // case-column replacement screws (M2 self-tap)
M25_CLEAR  = 2.9;    // horn / wheel disc screws
M3_CLEAR   = 3.4;    // general M3 clearance (knee_arm/shoulder_plate mounting
                     // screws). NOT the horn/wheel center relief any more —
                     // see HORN_CTR_D / WHEEL_CTR_D below (rev 3).
HORN_CTR_D    = 6.5;  // driven-side center counterbore: clears the horn's
                       // own retention screw head, Ø5.4 x ~1.5mm proud
                       // (MEASURED). Was Ø3.4/M3_CLEAR — too narrow.
HORN_CTR_DEEP = 2.5;   // counterbore depth from the seat face (screw head
                       // 1.5 proud + margin; arm is 4mm thick, so 1.5mm of
                       // solid material remains above the pocket).
WHEEL_CTR_D    = 9.5;  // idler-side center relief: clears the wheel's raised
                        // center HUB. FIX 2026-07-13: real hub = Ø8.8 x ~1.0mm
                        // proud (CALIPERED off the physical servo — thin disc
                        // 2.1mm, hub region 3.1mm, hub OD 8.8). The old Ø7.0
                        // assumed a Ø6 boss (wrong) and BOTTOMED the Ø8.8 hub —
                        // the idler wheel wouldn't seat (first-article catch).
                        // Ø9.5 = 8.8 + 0.7 clearance (room for PA6-CF shrink);
                        // relief r4.75 keeps ~0.8mm wall to the r7 BCD holes.
                        // The idler has NO retention screw — boss clearance only.
WHEEL_CTR_DEEP = 2.5;   // relief depth from the wheel-seat face (boss face);
                        // clears the ~1.0mm-proud hub with margin
HEATSET_D  = 4.0;    // Ruthex M3 insert BORE — insert OD is 4.6, bore must
                     // be 4.0 (tolerance audit). Referenced by femur +
                     // shoulder but NEVER DEFINED until 2026-07-06: OpenSCAD
                     // warned and silently dropped every heat-set bore, so
                     // femur_?.stl + shoulder.stl on disk had NO insert
                     // bores (chassis-lane catch; STLs rebuilt).
HEATSET_L  = 6.2;    // bore depth: 5.7 insert + 0.5 seat
WALL       = 3.2;
FLOOR      = 2.5;    // NOMINAL seat-to-exterior (FLOOR_TOP->FLOOR_BOT). #67
                     // (2026-07-12): the connector-bay void cuts 0.375 BELOW
                     // FLOOR_TOP (to z-20.075, forced by the servo connector
                     // clearance), so the REAL case-screw floor is 2.125mm
                     // (measured, all 3 pockets). SF still >1 (servo_pocket_
                     // analysis.py). Do NOT change this value -- it's live
                     // geometry (FLOOR_BOT, wheel window, YOKE_BOT_IN).
FLOOR_TOP  = BAY_BOT - 0.3;              // -19.7 bay seat plane
FLOOR_BOT  = FLOOR_TOP - FLOOR;          // -22.2
ARM_THK    = 4.0;
WHEEL_WIN_D  = 21.5;                     // floor window (wheel Ø20 + boss Ø19 clear)
WHEEL_BOSS_D = 19.0;                     // yoke bottom-arm boss through it
// yoke arm planes (contact, bolted):
YOKE_TOP_IN = HORN_Z1;                   // 17.75  top-arm underside ON horn
                                          // (rev 3: was 17.2 -- see HORN_Z1)
YOKE_BOT_IN = FLOOR_BOT - 0.4;           // -22.6 bottom-arm plate top (0.4: PA6-CF shrink robustness)
                                          // NOTE: NOT the wheel seat -- that's
                                          // WHEEL_Z0, reached by the boss.
                                          // YOKE_BOT_IN is unaffected by the
                                          // rev-3 gap fix (only the boss
                                          // lengthens to reach WHEEL_Z0).

// =============================================================================
// MODULES — SPLINE AXIS = Z THROUGH ORIGIN. Case body extends toward -X.
// Callers rotate/translate the whole set.
// =============================================================================

// Pocket NEGATIVE: subtract from a solid. Open top (+Z), bay-seat floor,
// wheel window, 4x case-column screw holes (countersunk at FLOOR_BOT),
// rear cable tunnel out the -X end wall.
// Anti-rotation ribs: solid triangular ridges LEFT on the ±Y pocket walls by
// subtracting them from the void (so the part material fills them). Base on the
// wall (y = ±(CASE_HW+CLR_POCKET)), apex PROUD inward toward the case flat.
module antirot_ribs() {
    hw = CASE_HW + CLR_POCKET;                 // 12.85 = void wall plane
    z_full_top = ANTIROT_Z[1] - ANTIROT_LEADIN;  // 10.5: full-crush zone stops
                                                   // here; mouth-ward of it is
                                                   // the lead-in taper only.
    for (rx = ANTIROT_X, sy = [-1, 1]) {
        // full-interference body (UNCHANGED cross-section: base/proud as
        // before, just shortened by ANTIROT_LEADIN at the +Z mouth end so
        // the taper below can occupy that span) -- SF 573 wall-bearing calc
        // depends on this profile, do not resize it.
        translate([rx, 0, (ANTIROT_Z[0] + z_full_top) / 2])
            linear_extrude(z_full_top - ANTIROT_Z[0], center = true)
                polygon([[-ANTIROT_BASE / 2, sy * hw],
                         [ ANTIROT_BASE / 2, sy * hw],
                         [0, sy * (hw - ANTIROT_PROUD)]]);
        // lead-in taper: hull() from the full-crush profile at z_full_top
        // down to a FLUSH (zero-interference, apex = base = hw) profile at
        // the mouth (ANTIROT_Z[1]) -- a linear ramp in crush depth over the
        // last ANTIROT_LEADIN mm of insertion travel, so the case's flat
        // wall meets ~0 interference on first touch and only crushes the
        // full 0.35 -> 0.1 once it's past the mouth and running true.
        hull() {
            translate([rx, 0, z_full_top])
                linear_extrude(EPS, center = true)
                    polygon([[-ANTIROT_BASE / 2, sy * hw],
                             [ ANTIROT_BASE / 2, sy * hw],
                             [0, sy * (hw - ANTIROT_PROUD)]]);
            translate([rx, 0, ANTIROT_Z[1]])
                linear_extrude(EPS, center = true)
                    polygon([[-ANTIROT_BASE / 2, sy * hw],
                             [ ANTIROT_BASE / 2, sy * hw],
                             [0, sy * (hw - ANTIROT_MOUTH_PROUD)]]);  // ~0
                                                        // interference (see
                                                        // ANTIROT_MOUTH_PROUD)
        }
    }
}

module sts_pocket_neg(extra_top = 30) {
    c = CLR_POCKET;
  difference() {
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
    antirot_ribs();     // leave the ±Y anti-rotation ribs as part material
  }
}

// Front-platform POSITIVE: raises the floor to seat the case's front bottom
// face (-15.5) outboard of the bay, ringing the wheel window. Union AFTER
// the main solid, BEFORE subtracting sts_pocket_neg (the pocket void stops
// at CASE_BOT so the platform survives; the wheel window re-cuts it).
module pocket_platform_pos() {
    difference() {
        intersection() {
            translate([BAY_X1, -(CASE_HW + CLR_POCKET), FLOOR_TOP - EPS])
                cube([CASE_X1 - BAY_X1 + CLR_POCKET + WALL,
                      2*(CASE_HW + CLR_POCKET),
                      CASE_BOT - 0.1 - FLOOR_TOP]);
            // corners rounded to r16.1 about the joint axis: the platform
            // corners at r18.6 grazed the mating part's bridge (sweep-gate
            // find); the servo case corner itself is r16.05, so nothing is
            // lost seating-wise
            translate([0, 0, FLOOR_BOT - 2])
                cylinder(r = 16.1, h = CASE_BOT - FLOOR_BOT + 4);
        }
        translate([0, 0, FLOOR_BOT - 1]) cylinder(d = WHEEL_WIN_D, h = 30);
    }
}

// Horn coupling NEGATIVE for a yoke TOP arm spanning z [YOKE_TOP_IN,
// YOKE_TOP_IN+ARM_THK]: shallow Ø20 locating recess + 4x M2.5 BCD + a center
// counterbore (rev 3) that clears the horn's own proud retention screw head
// (Ø5.4, ~1.5mm proud, MEASURED) — was a Ø3.4 hole, too narrow to clear it.
// ctr_deep overrides HORN_CTR_DEEP for callers whose backing material behind
// the counterbore is thinner than the generic ARM_THK slab assumes (LA-7,
// 2026-07-11: coax.scad's inboard arm backs onto the HAA pocket cavity, not
// a full ARM_THK of solid — see coax.scad's horn_couple_neg() call). Only
// coax.scad calls this module, so the default (HORN_CTR_DEEP, unchanged)
// leaves every other geometry-generation path byte-identical.
module horn_couple_neg(ctr_deep = HORN_CTR_DEEP) {
    translate([0, 0, YOKE_TOP_IN - EPS]) {
        cylinder(d = HORN_OD + 2*CLR_HORN, h = 0.4 + EPS);   // locating recess
        for (a = [45 : 90 : 315])
            rotate([0, 0, a]) translate([HORN_BCD/2, 0, 0])
                cylinder(d = M25_CLEAR, h = ARM_THK + 2*EPS);
        cylinder(d = HORN_CTR_D, h = ctr_deep + EPS);   // blind counterbore
    }
}

// Wheel coupling for a yoke BOTTOM arm whose plate spans
// z [YOKE_BOT_IN-ARM_THK, YOKE_BOT_IN]: POSITIVE boss reaching the wheel
// face through the floor window + NEGATIVE screws w/ head counterbores.
module wheel_boss_pos() {
    translate([0, 0, YOKE_BOT_IN - EPS]) {
        cylinder(d = WHEEL_BOSS_D, h = WHEEL_Z0 - YOKE_BOT_IN + EPS);
        // NOTE: no radial locating feature is POSSIBLE here (boss Ø19 must
        // stay under the wheel's Ø20 inside the Ø21.5 window) — the joint's
        // radial location comes from the 5 screws (Ø2.9 clear on M2.5,
        // ±0.2). Flat-on-flat clamp only.
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
        // #51 (2026-07-11): NO center screw hole on the wheel/idler side —
        // the idler has no retention screw (rev 3), so a center M25_CLEAR
        // through-cut here was PHANTOM: an open daylight hole through the
        // flat-on-flat wheel clamp face + a debris path into the C-box (the
        // same defect LA-5 removed from shoulder.scad's standalone cut, but it
        // was still latent in this SHARED module -> coax HFE + femur KFE wheels).
        // Removed. The wheel's proud center boss is cleared by the blind
        // idler-boss relief below (WHEEL_CTR_D Ø9.5 x WHEEL_CTR_DEEP, widened
        // from Ø7 by the 2026-07-13 hub caliper fix), which does NOT go
        // through. The 4 BCD screws above are the real fasteners.
    }
    // idler-boss relief (rev 3): the wheel side has NO retention screw —
    // instead a black plastic boss (Ø6, ~1-2mm proud, MEASURED) sits proud
    // of the wheel face. Blind counterbore from the wheel-seat face
    // (WHEEL_Z0 = the yoke boss's own top/contact face) clears it.
    translate([0, 0, WHEEL_Z0 - WHEEL_CTR_DEEP])
        cylinder(d = WHEEL_CTR_D, h = WHEEL_CTR_DEEP + EPS);
}

// Pocket side-wall VENT window NEGATIVE (CR-6, 2026-07-09): rounded-end
// (stadium) slot punched fully through BOTH ±Y pocket side walls at once.
// Width w along X from x0, height h along Z (centered at z_ctr), full
// pass-through along Y from y0 to y1. Corner radius = h/2 (a true stadium
// profile) so there is NO sharp corner anywhere on the cut — the FDM
// crack-initiation risk of the old raw cube() (0 fillet, 4 reentrant
// vertical corners) is eliminated outright, not just reduced to the 1.5mm
// minimum. Keep h small (<=5mm) so the residual top/bottom wall strips
// retain enough section modulus — see femur.scad / tibia.scad for the SF
// calc this geometry is sized against.
module vent_window_neg(x0, w, z_ctr, h, y0, y1) {
    r  = h / 2;
    yd = y1 - y0;
    hull()
        for (xc = [x0 + r, x0 + w - r])
            translate([xc, y0, z_ctr])
                rotate([-90, 0, 0])
                    cylinder(r = r, h = yd);
}

// Zip-tie anchor NEGATIVE: Ø3.2 through-hole pair, spacing 10, for
// strain-relieving the cable bundle (daisy link + VCC spur) at tunnel
// exits and along runs. Axis along Z at (x0, y0), full depth h from z0.
module zip_pair_neg(x0, y0 = 0, z0 = -30, h = 60, spacing = 10) {
    for (s = [-1, 1])
        translate([x0, y0 + s*spacing/2, z0]) cylinder(d = 3.2, h = h);
}

// Retention-strap ZIP-TIE bores (CONVERTED 2026-07-16, owner decision --
// was 2x Ø2.05 self-tap pilots into the side-wall rims). The self-tap
// pilot centered on wall_y (14.25) measured only 0.374mm of wall to the
// servo cavity (CASE_HW+CLR_POCKET = 12.85 void wall, TRIMESH-PROBED
// against tibia_R.stl) -- too thin for any insert or nut, and self-
// tapping into filament is banned project-wide (see leg_v6/README.md +
// nova-proj/feedback-no-self-tap-into-filament.md). All of that pilot's
// margin sat on the WRONG side: 2.474mm remained outboard (pilot edge to
// the raised Ø7 boss's own OD) vs 0.374mm inboard (pilot edge to the
// pocket wall). The strap is BACKUP-ONLY retention (anti-rotation ribs
// carry the servo torque -- see those ribs' own notes above) so a zip
// tie is mechanically sufficient once it isn't drilled through the thin
// side: a straight Ø3.2 through-bore (zip_pair_neg's own diameter,
// standard 2.5mm zip tie) sized for a tie to loop strap-end -> through
// the boss -> back, cinching the strap flush.
// ZIP_Y_OUT shifts the bore's Y center OUTBOARD off wall_y by a fixed
// amount (not a caller param -- x0/wall_y/rim_z keep their ORIGINAL
// meaning and this module keeps its ORIGINAL name/signature so
// tibia.scad's one call site, strap_pilot_neg(31, 14.25, SLAB_Z1+3.2),
// needs no edit) so the bore's INBOARD edge clears the servo-cavity wall
// by >=1.0mm instead of 0.374mm. TRIMESH-PROBED at wall_y+1.35 (=15.60):
// inboard wall to the pocket void = 1.15mm, matching strap.scad's own
// slot wall (1.44mm, see strap.scad) -- both comfortably >=1.0mm. The
// bore's OUTBOARD edge sits close to the boss's own Ø7 OD (~0.55mm
// remaining) -- thin, but that side is the boss's exterior shoulder, not
// a cavity wall, so it isn't the safety-critical direction; nothing
// breaks through.
// Depth: a self-tap pilot could be blind (h=8, from rim_z-8 to rim_z);
// a zip tie can't -- it must be feedable end-to-end (matches this file's
// own zip_pair_neg()/LA-21 through-hole convention). Top just clears the
// boss (rim_z, as originally); bottom runs to FLOOR_BOT-3, past the
// tibia's real underside at this X (TRIMESH-PROBED: solid the whole
// column at x0=31 down to ~FLOOR_BOT, air just past it).
// NOTE: coax.scad has its OWN separate strap-pilot cut (~line 286-289,
// NOT this shared module) that still drills the old Ø2.05 self-tap
// pilot -- it does not call strap_pilot_neg() and is therefore now
// INCONSISTENT with this zip-tie conversion. Left untouched here
// (coax.scad is a concurrent agent's file); flagged as a follow-up.
ZIP_BORE_D = 3.2;    // matches zip_pair_neg's cable-tie bore diameter
ZIP_Y_OUT  = 1.35;   // outboard shift applied to wall_y (14.25 -> 15.60)
module strap_pilot_neg(x0 = 31, wall_y = 14.25, rim_z = CASE_TOP) {
    z0 = FLOOR_BOT - 3;
    for (sy = [-1, 1])
        translate([x0, sy*(wall_y + ZIP_Y_OUT), z0])
            cylinder(d = ZIP_BORE_D, h = (rim_z + EPS) - z0);
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
