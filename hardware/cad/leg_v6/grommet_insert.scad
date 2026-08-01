// =============================================================================
// V6 GROMMET INSERT (TPU 95A — print 6: 4 grommets + spares)
// =============================================================================
// Integration audit 2026-07-06: the shoulder-flange cable grommets
// (O12, 2 per shoulder at (+/-32, z -26)) are bare printed PA6-CF
// holes, and the LEG cables move through them with every haa swing —
// sharp printed edge + ~1e5 flex cycles/hr chews insulation. This TPU
// liner press-fits the hole: rounded flange lips both jobs (bend
// radius + chafe). Axial slit lets it wrap an already-routed bundle.
//
// Fit: barrel OD 12.2 (0.2 press in O12, TPU squish), bore O9 (bundle
// ~O5 + spur + slack), length 4.2 = flange 4.0 + squeeze; retaining
// flange O15 x 1.2 on the OUTER (leg) face where the bend lives; inner
// end 45-chamfered to pull through. Clearances on the flange face
// checked: D456 pads end x 23, feet start x 38 -> O15 at x 32 clears
// both by 1.5+.
//
// Print: TPU 95A flange-down, 100% infill, ~1 g.
//
// LA-25 (2026-07-11) FIRST-ARTICLE CHECK: BARREL_OD 12.2 into a nominal
// Ø12 hole is only 0.2mm diametral interference -- likely inside FDM/TPU
// dimensional noise -- AND the axial SLIT (see below) turns the press-fit
// into a split/spring ring, so retention depends on spring-back rather
// than a clean interference fit (undiscussed until now). Before trusting
// this on the full batch: press one into a printed Ø12 hole, tug-test
// retention, and if it's loose/spins free, grow BARREL_OD (adjust here)
// rather than reprinting the flange hole. See print-batch.md.
//
// ---- LA-25 SHARPENED 2026-08-01: it is not a tolerance problem ----------
// The note above is true and it buries the lede. Work the split-ring
// geometry and the original 12.2 cannot grip at ANY print accuracy:
//
//   SLIT = 2.0mm of arc removed.
//   Closing the slit completely shrinks the barrel diameter by
//       SLIT/pi = 2.0/pi = 0.637mm.
//   Design interference into a nominal O12 hole = 12.2 - 12.0 = 0.200mm.
//
// So the ring swallows the entire interference by closing 0.20mm of its
// 2.0mm gap, and still has ~1.8mm of gap left. It never reaches hoop
// compression -- the barrel wall is never strained against the hole. The
// only restoring force is the C-section's BENDING stiffness in Shore-95A
// TPU, which is an order of magnitude below hoop.
//
//   ==> Hoop engagement begins at BARREL_OD > 12.0 + SLIT/pi = 12.637.
//
// A perfect printer and a perfect O12 hole still give a part that spins.
// That is why "grow BARREL_OD a bit if loose" was the wrong instruction:
// it points at 12.3-12.4, which is still inside the dead band. Any fix
// has to CLEAR 12.637, not creep toward it.
//
// DEFAULT MOVED 12.2 -> 12.7 on that analysis (smallest value in the
// engaged regime). Still a hypothesis for the press test, not a result --
// just past the threshold, grip is bending-plus-a-little-hoop and may
// prove weak. A 3-rung ladder was rendered 2026-08-01 to settle it in ONE
// sitting rather than a print/test/edit loop (TPU spool changeover is the
// expensive step here, not the ~0.5g of filament):
//
//   openscad -D BARREL_OD=12.2 -o ladder_12.2.stl grommet_insert.scad
//   openscad -D BARREL_OD=12.7 ...        <- this file's default
//   openscad -D BARREL_OD=13.2 ...        <- clear margin, 0.56mm real
//                                            squeeze after slit closure
//
// 12.2 is the NEGATIVE CONTROL, and print it: it should spin free. If it
// grips, this analysis is wrong and 12.7/13.2 are oversized.
//
// BORE stays 9.0 on every rung, so bundle clearance is unaffected -- only
// the wall thickens (1.60 / 1.85 / 2.10mm). FLG_OD is untouched, so the
// x=32 flange-face clearances in the block above still hold.
//
// The press test needs a printed PA6-CF O12 hole and there are no
// first-article prints yet (STATUS.md). Cheapest unblock is a scrap
// coupon with a few O12 holes in the wave-1 PA6-CF job -- then LA-25
// clears without test-fitting into a real shoulder.

$fn = 64;
EPS = 0.05;

BARREL_OD = 12.7;   // 12.2 -> 12.7 on 2026-08-01, see LA-25 block above.
                    // Hoop engagement threshold is 12.0 + SLIT/pi = 12.637;
                    // anything at or below that is a slit that just closes.
                    // Pending the press test — do NOT read this as verified.
BORE = 9.0;
BARREL_L = 4.2;
FLG_OD = 15.0;
FLG_T = 1.2;
SLIT = 2.0;

module grommet_insert() {
    difference() {
        union() {
            // flange with a rounded lip (torus-ish via rotate_extrude)
            rotate_extrude() translate([FLG_OD/2 - FLG_T, FLG_T, 0])
                circle(r = FLG_T);
            cylinder(d = FLG_OD - 0.4, h = FLG_T);
            // barrel
            translate([0, 0, FLG_T - EPS])
                cylinder(d = BARREL_OD, h = BARREL_L + EPS);
            // entry chamfer nose (pull-through)
            translate([0, 0, FLG_T + BARREL_L - EPS])
                cylinder(d1 = BARREL_OD, d2 = BORE + 0.8, h = 1.2);
        }
        // bore with rounded exit at the flange side
        translate([0, 0, -EPS])
            cylinder(d = BORE, h = FLG_T + BARREL_L + 1.2 + 2*EPS);
        translate([0, 0, -EPS])
            cylinder(d1 = BORE + 2.4, d2 = BORE, h = 1.4);
        // axial slit — wrap over a routed bundle
        translate([-SLIT/2, 0, -1])
            cube([SLIT, FLG_OD, FLG_T + BARREL_L + 3]);
    }
}

grommet_insert();
