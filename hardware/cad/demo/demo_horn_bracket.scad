// DEMO: a bracket that bolts to an STS3215 horn (verified 14mm BCD M2.5 pattern)
// and offers 2× M3 heat-set bosses to mount something. Proves the lib + the
// author->render->measure design loop. Composed entirely from nova_cad_lib.
include <../lib/nova_cad_lib.scad>;   // include (not use) — exposes constants
$fn=64;
plate_d = 34; plate_t = 4;
difference() {
  union() {
    cylinder(d=plate_d, h=plate_t);                 // base plate
    // 2 heat-set bosses (M3) on top, ±10mm in X
    for (x=[-10,10]) translate([x,0,plate_t]) heatset_boss("M3");
  }
  // bolt-TO-horn: Ø12 spline clearance (< 14mm BCD) + 4× M2.5 holes on the BCD
  sts_horn_mount("M2.5", shaft_clr_d=12, L=plate_t+2);
}
