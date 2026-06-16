// DEMO: a bracket that bolts to an STS3215 horn (verified 14mm BCD M2.5 pattern)
// and offers 2× M3 heat-set bosses to mount something. Proves the lib + the
// author->render->measure design loop. Composed entirely from nova_cad_lib.
use <../lib/nova_cad_lib.scad>;
$fn=64;
plate_d = 34; plate_t = 4;
difference() {
  union() {
    cylinder(d=plate_d, h=plate_t);                 // base plate
    // 2 heat-set bosses (M3) on top, ±10mm in X
    for (x=[-10,10]) translate([x,0,plate_t]) heatset_boss("M3");
  }
  translate([0,0,-EPS]) {
    // center horn-disc relief (so the splined horn clears)
    cylinder(d=STS_HORN_RELIEF_D, h=plate_t+2*EPS);
    // 4× M2.5 horn screw holes on the verified 14mm BCD
    sts_horn_holes("M2.5", plate_t+2);
  }
}
