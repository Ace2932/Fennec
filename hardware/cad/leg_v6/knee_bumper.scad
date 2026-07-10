// =============================================================================
// V6 KNEE BUMPER (TPU 95A) — collapse strike guard, backlog #15 "B"
// =============================================================================
// Replaces the RETIRED tibia_pad (which sat on the LATERAL MID-blade face and
// never led into the ground). collapse_study.py + strike-trace 2026-07-07:
// on a hard-power-loss limp fold the LOW knee-region contact is the TIBIA's
// KNEE-END pocket block, on its LATERAL faces (world-down when the block lies
// on its side). The y-side depends on fold direction, so this wraps BOTH ±Y
// faces. Complements "A" (controlled-limp sit on soft faults, firmware).
//
// MOUNTS ON THE TIBIA (rides the kfe rotation → always guards the knee end).
// Tibia frame: +X toward the foot, kfe axis Z@origin. Knee pocket block =
// x -16.05..56.05, y ±16.05 (SLAB_W 32.1 = 2*(CASE_HW 12.4 + CLR_POCKET 0.45
// + WALL 3.2), verified against tibia.scad/leg_v6_common.scad 2026-07-10 —
// BW below was a stale copy of tibia.scad's OLD SLAB_W comment (31.7); the
// real computed value is 32.1, see CR-8 #5), z -22.2..14.7 (SLAB_Z0..SLAB_Z1).
// The joint fork/disc grip the block at x<~15 (metal-on-metal, self-guarding);
// the EXPOSED lateral faces at x~15..40 are what this caps.
//
// GRIP: a U-channel that wraps UNDER the blade bottom (z-22.2) and hugs both
// ±Y faces — squeeze-fit on the 31.7 width + a CA dab (sacrificial, pop-off
// replaceable, same practice as skid_rail). Slides up from below over the
// block bottom. Sled-chamfered so the wrap-under doesn't catch on collapse.
// COVERAGE (honest): caps the EXPOSED knee-block lateral faces x15..40. The
// strike concentrates a bit further back (x-16..12, the joint zone) but the
// femur FORK grips the tibia there (metal-on-metal, self-guarding) and leaves
// no room for a tibia-side pad — so this covers the exposed forward case wall,
// the fork covers the rear. Combined with A (the sit lands on the outboard
// face, which the arms cover). Partial by necessity, not by oversight.
// GATE (both green, exit 0): leg_v6 knee-fold sweep — clears the femur fork
// through ±109° (only the 118° MECH STOP HITs, as designed; v1's full-width
// wrap-under fouled the fork at x15..23/z-25 and was pulled fwd to x24). +
// chassis crouch (bumper vs battery/riser clean). Print: TPU 95A, U opening up.

$fn = 32;
EPS = 0.05;

BW   = 32.1;            // knee-block width (y) = SLAB_W (corrected 2026-07-10,
                        //   see header note — was stale 31.7)
BZ0  = -22.2;          // block bottom (SLAB_Z0)
BZ1  = 14.7;           // block top (SLAB_Z1)
X0   = 15;  X1 = 40;    // ARM span along the tibia (exposed knee-block strike face)
XB0  = 24;             // BASE (wrap-under) start — kept FWD of x15..23, the
                       //   fold-collision zone (gate: the base dipped z-25..-23
                       //   into the femur fork there at kfe ±109). Arms (z>=-22)
                       //   clear the fold; only the wrap-under fouled.
WALL = 3.0;            // TPU wall on each lateral face
BASE = 2.0;            // wrap-under thickness below the blade bottom
ZTOP = 11;            // arms rise to z11 (clear of the strap bosses @z14.7)
CH   = 3.0;            // sled chamfer on the wrap-under leading/outer edges
SQUEEZE = 0.3;         // CR-8 #3: TOTAL inner-span interference (~0.15/side)
                       //   for the TPU 95A squeeze-fit over the rigid tibia
                       //   block — was 0 (arms sat flush at exact BW, no clamp
                       //   force). TPU stretches on install and grips; backed
                       //   up by the CA dab (part header). Only the GRIP arms
                       //   are squeezed; the wrap-under base is an outer hook,
                       //   not a mating face, so it stays at the nominal BW.
LEAD = 3;              // AUD-5 (2026-07-10): install lead-in. The bracket
                       //   slides UP FROM BELOW onto the tibia block (part
                       //   header), so the arm TOP (z near ZTOP) is the
                       //   MOUTH — the leading edge that first rides onto the
                       //   block — while the wrap-under (bottom) seats last.
                       //   Eases the SQUEEZE interference from fit_hy (full
                       //   grip) to hy (~0 interference) over the last LEAD mm
                       //   of arm travel, so install force ramps in instead of
                       //   hitting full interference at first contact. Seated
                       //   grip below (z < ZTOP-LEAD) is untouched.

module knee_bumper() {
    hy = BW / 2;                       // 16.05, the nominal ±Y block face plane
    fit_hy = hy - SQUEEZE / 2;         // 15.90, the squeezed ARM inner-face plane
    relief = hy - fit_hy;              // 0.15, the eased-to amount at the mouth
    union() {
        // wrap-under base (below the blade bottom) — FRONT only (x24..40),
        // clear of the fold-collision zone; provides the bottom grip hook.
        // Top raised +1.5 INTO the arm zone so it fuses to both arms (one body).
        hull() {
            translate([XB0 + CH, -(hy + WALL), BZ0 - BASE])
                cube([X1 - XB0 - 2 * CH, 2 * (hy + WALL), EPS]);
            translate([XB0, -(hy + WALL - CH), BZ0 + 1.5])
                cube([X1 - XB0, 2 * (hy + WALL - CH), EPS]);
        }
        // two side arms on the ±Y faces (full strike span x15..40) — squeezed
        // fit_hy inward of the nominal block face (SQUEEZE interference),
        // with the AUD-5 lead-in taper cut from the inner face at the mouth
        // (the arm top, the last LEAD mm of z).
        for (sy = [-1, 1])
            difference() {
                translate([X0, sy * fit_hy - (sy < 0 ? WALL : 0), BZ0])
                    cube([X1 - X0, WALL, ZTOP - BZ0]);
                // lead-in cut: tapers from 0 relief (z = ZTOP-LEAD, matches
                // the seated inner face exactly) to full relief (z = ZTOP,
                // inner face eased out to the nominal hy plane)
                hull() {
                    translate([X0 - EPS, sy * fit_hy - (sy < 0 ? EPS : 0),
                               ZTOP - LEAD])
                        cube([X1 - X0 + 2 * EPS, EPS, EPS]);
                    translate([X0 - EPS, sy * fit_hy - (sy < 0 ? relief : 0),
                               ZTOP - EPS])
                        cube([X1 - X0 + 2 * EPS, relief, 2 * EPS]);
                }
            }
    }
}

knee_bumper();
