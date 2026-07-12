// LEFT coax HFE cap = X-mirror of the right (same convention as
// coax_L.scad / shoulder_plate_L.scad).
$fn = 64;
use <coax_hfe_plate.scad>
// side marker: 2 dots = LEFT. Base (RIGHT) dot sits on the mid-band body's
// Y-facing low-y wall (x=14.1, y=STUB_MIDY0+CLR-EPS=7.15, z=-8.0), cut
// direction +Y (into the 20mm-deep mid-band block); mirror([1,0,0]) only
// flips X, so on this LEFT part that same dot lands at world x=-14.1, same
// y/z, same +Y cut direction -- comes along for free via
// `mirror(...) coax_hfe_plate_R()` below, no separate handling needed.
// 2nd dot: SAME wall (x=-14.1 mirrored, y=7.15), offset in z (z=-11.0,
// 3mm from the base dot's -8.0 -- clears both dots' own d=2 (r=1) radius
// plus a real reference-probe margin, both still within the mid-band's
// z=[-12.8,-6.0] span) so 1-vs-2 dots reads unambiguously and the fit
// gate's own reference-point probes (check_fit.py's FASTENER_GROUPS) don't
// cross-contaminate between the two dimples. Cut direction unchanged (+Y
// is not affected by an X-mirror).
difference() {
    mirror([1, 0, 0]) coax_hfe_plate_R();
    translate([-14.1, 7.15, -11.0]) rotate([-90, 0, 0]) cylinder(d = 2, h = 0.8);
}
