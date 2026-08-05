// =============================================================================
// V6 Coax HFE BLOCK — removable OUTBOARD bearing arm (#226 option C, 2026-07-31)
// =============================================================================
// REPLACES coax_hfe_plate.scad, which is retired. That cap could never be
// installed: MEASURED blocked in all six axes against the seated femur AND
// against a bare coax, in the #67 revision AND the pre-#7-fix one, while its
// seated pose was itself legitimate (boolean intersection with the coax =
// 0.0 mm3). A valid final position with no path to it — a ship in a bottle.
// Aiden's printed coax refused it on the bench ("doesn't really slide in"),
// which is not a tolerance problem: no path exists at any tolerance.
// check_fit.removable_member_checks() now gates that whole class.
//
// WHY THE REMOVABLE MEMBER MOVED OUTBOARD. The inboard side has 3.15mm of slot
// and 0.5mm to the HAA servo; the outboard side has ~8mm of material and open
// air past x=62.4. The cap was on the cramped side, and its fasteners could not
// be driven (0.8-4.5mm of driver run against the 15-20mm needed). Inverting
// which arm is removable puts the serviced member where the access is, and
// opens the +X AXIAL insertion path for the femur — coax.scad's own #53 header
// recorded "+X blocked by the integral outboard arm", so making that arm
// removable is exactly what unblocks it. MEASURED: femur withdraws +X with 0
// points over t=2..50mm.
//
// WHY A TENON AND NOT BOLTS IN TENSION. This joint's binding case is FATIGUE,
// not the 400 N static couple: coax.scad records the arm-to-bridge junction as
// "the only member on the robot under SF 15" (~14 MPa at the 4-thick root under
// a 20 N lateral/turning foot load, fatigue SF ~1.9 per stride, halved to ~6MPa
// by the gusset this part now carries). Any bridge-level interface sits ~22mm
// above the boss, so the 133 N cyclic axial load becomes ~2.95 N.m at the joint
// = ~490 N per bolt on a 10mm face — past M3 heat-set pull-out in wet PA6-CF.
// A concentric spigot would shorten the lever, but MEASURED there is no room:
// the femur occupies r 10..16 at the boss station, leaving no free annulus.
//
// So the tenon reacts the moment in BEARING over its own length (2.95 N.m /
// 12.05mm = 245 N on ~92 mm2 = 2.7 MPa) and the 2x M3 drop to retention
// (cyclic 133/2 = 66 N each vs ~175-245 N wet pull-out -> SF 2.6-3.7). That is
// the same move #7-fix made for the cap — shape key carries, bolt retains —
// including its hard-won corollary: the key must be CLOSED in BOTH directions,
// because a compression-only key cannot react peel. This tenon is shrunk
// CLR_TENON off y0/y1/z0/z1 and flush only at the mating plane.
//
// Geometry proof + negative control: hfe_block_study.py.
//
// FASTENERS: 2x M3x16 SHCS into 2x SLIM M3 HEAT-SETS (4.0mm OD x 6.0 long),
// NOT the 4.6mm OD insert used everywhere else on this robot.
//
// WHY A DIFFERENT INSERT HERE (2026-08-02). The insert has to TRAVEL ~10mm down
// the mortise to reach its bore at the blind end, and that slot was 4.00mm tall
// (MEASURED, every station, both bolt axes) against a 4.6mm insert. It could
// not be delivered: a valid seat with no path to it -- the same failure that
// retired the inboard cap on this joint. Every gate was green, because the
// heat-set gate casts a RAY to prove the bore is reachable and a ray has no
// diameter. insert_path_checks() now sweeps the insert's actual DIAMETER.
// Growing the slot to 5.0 for the 4.6 insert leaves the mortise roof at 1.50mm
// -- exactly MIN_SECTION_MM, no margin -- and more forces GROW_Z1 up, which
// coax.scad records as HITTING THE SHOULDER at haa -40. A slimmer, longer
// insert is the cheaper trade: pull-out goes as pi*D*L, so 4.0x6.0 = 75mm2
// against 4.6x5.7 = 82mm2 (92%), for a 0.4mm slot growth instead of 1.0, and
// the roof stays 2.10mm. MORT_Z1 is therefore 13.9 (4.4mm slot), shared from
// leg_v6_common.scad so this file and coax.scad cannot disagree about it.
//
// SCREW LENGTH, re-derived off the meshes: head seat (c'bore floor) x=57.0,
// coax face x=46.35, bore 3.5 x 6.5 deep so its bottom is x=39.85 => 17.15mm of
// usable span. M3x16 lands 5.35mm into the 6.0 insert and stops 1.15mm clear of
// the bottom. (The line here used to say M3x22, and said MEASURED: it was --
// at #234, when MORT_X0 was 43.8. #235 moved it to 46.4, the insert rides on
// that constant, and nothing re-measured. M3x22 bottoms out 5.2mm early in a
// BLIND pocket, so the head never seats: no preload, and torquing it jacks the
// block off the mortise or strips the insert.) fastener_span_checks() now
// derives all of this from the meshes. See docs/fastener-schedule.md.
//
// Plus 4x M2.5x8 wheel screws (unchanged geometry, wheel_couple_neg) -- those
// moved here from coax.scad with the boss.
//
// OPEN, worth a look before the first structural print: the root doubler that
// came across with the arm was sized for the arm-to-BRIDGE junction, which no
// longer exists on this part -- the block's root is now the tenon. Its two M3
// head counterbores also pass through it. The doubler is almost certainly
// still useful (it stiffens the arm carrying the boss) but its ORIGINAL
// justification no longer applies, so it should be re-derived rather than
// inherited.
//
// Print: PA6-CF, MATING FACE (x=SPLIT_X) DOWN — the tenon and boss then rise
// as the only overhangs and the bearing faces land on the bed. Same material
// and settings as the coax (4 walls / 40% / 0.2).
include <leg_v6_common.scad>

// Mirrors coax.scad's constants byte-for-byte — `include` does not share
// variables across files, same convention every part in this set follows.
FEMUR_MID   = 33.8;
HFE_Y       = 11.6;
HFE_Z       = -9.5;
ARM_THK     = 4.0;
ARM_HALF_YZ = 16;
BRIDGE_Z0   = 7.4;
ARM_OUT_X0  = FEMUR_MID - YOKE_BOT_IN;   // 56.2
ARM_OUT_X1  = ARM_OUT_X0 + ARM_THK;      // 60.2
SPLIT_X     = ARM_OUT_X0;
BOSS_X0     = FEMUR_MID - WHEEL_Z0;      // 51.55

// MORT_*/CLR_TENON/BOLT_* come from leg_v6_common.scad (hoisted 2026-08-02).
// They used to be declared HERE as well as in coax.scad; the tenon below is
// built from them, so a mortise change in one file and not the other produced
// a tenon that rattles in its slot with no error anywhere.
M3_CLEAR_D = 3.4;
SHCS_HEAD_D = 6.0;
SHCS_HEAD_H = 3.2;

module arm_plate(x0, x1) {
    hull() {
        translate([x0, HFE_Y, HFE_Z]) rotate([0, 90, 0])
            cylinder(r = ARM_HALF_YZ, h = x1 - x0);
        translate([x0, HFE_Y - ARM_HALF_YZ, BRIDGE_Z0])
            cube([x1 - x0, 2*ARM_HALF_YZ, 13.4 - BRIDGE_Z0]);
    }
}

module coax_hfe_block_R() {
    difference() {
        union() {
            // the outboard arm itself
            arm_plate(ARM_OUT_X0, ARM_OUT_X1);
            // ROOT DOUBLER (backlog #26) — travels with the arm it stiffens
            hull() {
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, 0])
                    cube([2, 2*ARM_HALF_YZ, 13.4]);
                translate([ARM_OUT_X1 - EPS, HFE_Y - ARM_HALF_YZ, -1.5])
                    cube([0.5, 2*ARM_HALF_YZ, 14.9]);
            }
            // wheel boss reaching inboard to the femur wheel face
            translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
                wheel_boss_pos();
            // TENON — shrunk on y0/y1/z0/z1 (closed both ways in Z), flush at
            // the mating plane. This is the member that carries the moment.
            // two prongs, matching the coax's rib-split mortise (see that
            // file: the rib halves the floor's bending span, 119 -> ~22 MPa)
            for (yy = [[MORT_Y0, MORT_RIB_Y0], [MORT_RIB_Y1, MORT_Y1]])
                translate([MORT_X0 + CLR_TENON, yy[0] + CLR_TENON,
                           MORT_Z0 + CLR_TENON])
                    cube([SPLIT_X - MORT_X0 - CLR_TENON,
                          (yy[1] - yy[0]) - 2*CLR_TENON,
                          (MORT_Z1 - MORT_Z0) - 2*CLR_TENON]);
        }

        // wheel-screw couple through the boss + arm (unchanged geometry — this
        // is the femur idler side, it just lives on a separate part now)
        translate([FEMUR_MID, HFE_Y, HFE_Z]) rotate([0, -90, 0])
            wheel_couple_neg();

        // 2x M3 retention: clearance through the tenon + head counterbore
        // opening on the OUTBOARD face, driven from +X open air.
        for (by = BOLT_YS) {
            translate([MORT_X0, by, BOLT_Z]) rotate([0, 90, 0])
                cylinder(d = M3_CLEAR_D, h = ARM_OUT_X1 + 3 - MORT_X0);
            translate([ARM_OUT_X1 - SHCS_HEAD_H, by, BOLT_Z]) rotate([0, 90, 0])
                cylinder(d = SHCS_HEAD_D, h = SHCS_HEAD_H + 3);
        }

        // side marker: 1 dot = RIGHT (the _L wrapper adds a 2nd, 3mm away in z)
        // ON THE GUSSET'S OUTBOARD FACE (x=62.3), not the arm's. Two earlier
        // sites failed the depth gate at 0.00mm: y+10/z-12 sat at r=15.6
        // against a 16 rim so the dimple spilled off the edge, and y+8/z-8
        // landed on a WHEEL-SCREW COUNTERBORE, which had already recessed the
        // face -- probed flat, so the dot cut air. This face measures flat at
        // 62.30 across a +-1.4mm neighbourhood. Cut starts outside so it
        // breaks the surface.
        translate([62.3 + 0.4, HFE_Y + 8, 6.0]) rotate([0, -90, 0])
            cylinder(d = 3, h = 1.2);
    }
}

coax_hfe_block_R();
