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

$fn = 64;
EPS = 0.05;

BARREL_OD = 12.2;
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
