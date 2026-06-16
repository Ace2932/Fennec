// nova_cad_lib.scad — verified NovaSM3 parametric design library (OpenSCAD).
//
// Reusable modules with the project's REAL, verified dimensions (from
// hardware/cad/dimensions.md + parametric-servo-fit.md + patterns.md), so any
// new/edited part automatically matches the current design: STS3215 mounts,
// heat-set insert bosses, M-screw holes, 688ZZ bearing seats, connector cutouts.
//
// Usage:  use <.../lib/nova_cad_lib.scad>;  then call the modules.
// Tuned for Bambu P1S + PA6-CF. $fn set by caller (default 64 below).
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
BEARING_OD = 16.05; BEARING_ID = 8.0; BEARING_H = 5.0;

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

// clearance through-hole for a screw, length L (centered on Z, drilled -Z..)
module screw_hole(size="M3", L=20) {
  d = _scr(size)[0];
  translate([0,0,-L/2]) cylinder(d=d, h=L);
}

// counterbored clearance hole (socket-head), head pocket on +Z
module screw_counterbore(size="M3", L=20) {
  p=_scr(size);
  screw_hole(size,L);
  translate([0,0,-EPS]) cylinder(d=p[4], h=p[5]+EPS);
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
