// nova_cad_lib.scad — verified NovaSM3 parametric design library (OpenSCAD).
//
// Reusable modules with the project's REAL, verified dimensions (from
// hardware/cad/dimensions.md + parametric-servo-fit.md + patterns.md), so any
// new/edited part automatically matches the current design: STS3215 mounts,
// heat-set insert bosses, M-screw holes, 688ZZ bearing seats, connector cutouts.
//
// Usage:  include <.../lib/nova_cad_lib.scad>;  then call the modules.
//   IMPORTANT: use `include`, NOT `use`. This file exposes CONSTANTS (EPS,
//   STS_*, BEARING_*, SCREW, ...) which OpenSCAD's `use` does NOT import — only
//   `include` does. The file has no top-level geometry, so include is safe.
// Tuned for Bambu P1S + PA6-CF. Set $fn before the include to override the 64 default.
// ============================================================================
$fn = $fn ? $fn : 64;
EPS = 0.05;

// ---- STS3215 servo (verified) ----------------------------------------------
STS_L = 45.40; STS_W = 24.80; STS_H = 34.30;     // body
STS_SPLINE_X = 12.50;                            // spline offset from body center (long axis)
STS_HORN_BCD = 14.0;                             // horn screw bolt-circle dia
STS_HORN_RELIEF_D = 22.0;                        // horn disc OD + 2mm
// body mount: 4× M2.5, 9.9×9.9 square centered on spline (x=12.5,y=0)
STS_BODYMNT = [[7.55,4.95],[7.55,-4.95],[17.45,4.95],[17.45,-4.95]];

// ---- bearing (688ZZ) -------------------------------------------------------
BEARING_OD = 16.0; BEARING_ID = 8.0; BEARING_H = 5.0;   // RAW 688ZZ; press clr added in bearing_seat

// ---- print clearances (PA6-CF on P1S) --------------------------------------
CLR_BODY = 0.25;     // add to servo-cavity dims (press fit)
CLR_BEARING = 0.05;  // add to bearing OD (press fit)
CLR_SLIP = 0.25;     // free-slip clearance

// ---- screws / heat-set inserts (Ruthex, project default) -------------------
// [clearance_hole_d, insert_bore_d, insert_depth, boss_od, head_d, head_h]
SCREW = [
  ["M2",   [2.4, 3.2, 4.0, 5.5, 4.0, 2.0]],
  ["M2.5", [2.9, 3.6, 5.0, 6.0, 5.0, 2.5]],
  ["M3",   [3.4, 4.0, 5.7, 6.5, 5.5, 3.0]],
];
function _scr(s) = SCREW[search([s], SCREW)[0]][1];

// Clearance through-hole. Convention: part sits on the XY plane (z=0..L); the
// hole is drilled from just below z=0 up THROUGH the top, so pass L = part
// thickness (over-cut handled here). Subtract from the part.
module screw_hole(size="M3", L=20) {
  translate([0,0,-EPS]) cylinder(d=_scr(size)[0], h=L+2*EPS);
}

// counterbored clearance hole (socket head) for a part of thickness L; head
// pocket recessed into the TOP face (z = L-head_h .. L).
module screw_counterbore(size="M3", L=20) {
  p=_scr(size);
  screw_hole(size,L);
  translate([0,0,L-p[5]]) cylinder(d=p[4], h=p[5]+EPS);
}

// heat-set insert boss + bore. Place boss base at Z=0, grows +Z.
module heatset_boss(size="M3", h=0) {
  p=_scr(size); H = h>0 ? h : p[2]+1.5;
  difference() {
    cylinder(d=p[3], h=H);                        // boss
    translate([0,0,H-p[2]]) cylinder(d=p[1], h=p[2]+EPS);  // bore from top
  }
}
// just the insert bore (to subtract from existing solid; bore from +Z face at z)
module heatset_bore(size="M3", from_z=0) {
  p=_scr(size);
  translate([0,0,from_z-p[2]]) cylinder(d=p[1], h=p[2]+EPS);
}

// ---- STS3215 features ------------------------------------------------------
// 4× horn screw holes on the 14mm BCD at ±45°, centered at origin
module sts_horn_holes(size="M2.5", L=12) {
  for (a=[45,135,225,315]) rotate([0,0,a]) translate([STS_HORN_BCD/2,0,0]) screw_hole(size,L);
}
// Composite "bolt TO the horn" pattern: small center clearance for the spline
// boss + 4 BCD screw holes. Subtract from a part whose face sits on the horn
// disc. NOTE: shaft_clr_d must be < BCD (14) so it doesn't eat the screw holes
// (the Ø22 horn *pass-through* relief is a different use — don't combine them).
module sts_horn_mount(size="M2.5", shaft_clr_d=12, L=12) {
  translate([0,0,-EPS]) cylinder(d=shaft_clr_d, h=L+2*EPS);   // through (part z=0..L)
  sts_horn_holes(size, L);
}
// 4× body-mount holes (origin = spline axis), for bolting a bracket to the servo face
module sts_body_mount_holes(size="M2.5", L=12, mirror_y=false)
  for (p=STS_BODYMNT) translate([p[0]-STS_SPLINE_X, (mirror_y?-1:1)*p[1], 0]) screw_hole(size,L);

// servo body cavity (press-fit pocket), centered, long axis = X
module sts_cavity(clr=CLR_BODY)
  translate([0,0,-(STS_H+clr)/2]) cube([STS_L+clr, STS_W+clr, STS_H+clr], center=true) ;

// ---- bearing seat ----------------------------------------------------------
// press-fit 688ZZ pocket, opens +Z, seat floor at z=0
module bearing_seat(through=false, L=30)
  translate([0,0,-EPS]) {
    cylinder(d=BEARING_OD+CLR_BEARING, h=BEARING_H+EPS);
    if (through) translate([0,0,-L]) cylinder(d=BEARING_ID+1, h=L+EPS); // shaft clearance
  }

// ---- connector / panel cutouts (subtract from a panel) ---------------------
module xt30_cutout(L=20) translate([0,0,-L/2]) cube([8.0, 8.0, L], center=true);   // XT30 body+keying slop
module xt60_cutout(L=20) translate([0,0,-L/2]) cube([8.2, 16.2, L], center=true);  // XT60
module estop_22mm(L=20)  translate([0,0,-L/2]) cylinder(d=22.5, h=L);              // 22mm panel e-stop
module m3_panel_mount(L=20) screw_hole("M3", L);
