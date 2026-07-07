// =============================================================================
// V6 TIBIA BLADE PAD (TPU 95A — print 5: 4 legs + spare)
// =============================================================================
// Backlog #15 extension (user call 2026-07-06): E-stop limp = collapse by
// design; as the knees fold the tibia BLADE BOTTOM (-Z, the flat print
// face) leads into the ground alongside the belly rails. 3-thick TPU pad
// over the blade underside takes that strike (and rock hits in deep
// crouch) instead of bare PA6-CF edge.
//
// Mount: two ribbed plugs press into the blade's LEGACY zip holes at
// x 62 / 84 (O3.2 vertical through-holes — the final cable routing uses
// the femur x84 + tibia x44 anchors, these two are unused) + CA dab.
// Sacrificial, replaceable. Same part fits L and R (symmetric in y),
// and both knee configs (X-config = software, hardware identical).
//
// Gate: leg_v6 check_fit knee-fold sweep re-run WITH the pad — the kfe
// mech stop is the tibia flank vs the femur fork throat, and the pad
// adds 3 to the blade underside. Pad points ride the tibia transform.
//
// Print: TPU 95A flat (pad face down), 100% infill, ~3 g.

$fn = 32;
EPS = 0.05;

PAD_X0 = 55;  PAD_X1 = 92;    // spans both plug holes (62 / 84)
PAD_W  = 16;                   // blade width there is 21.9..27.5
PAD_T  = 3.0;
SLAB_Z0 = -22.2;               // blade bottom plane (tibia frame)
PLUG_X = [62, 84];
PLUG_L = 8;                    // into the O3.2 through-holes
CHAMF  = 2.5;

module tibia_pad() {
    union() {
        // pad body, sled-chamfered ends (tibia frame: sits below the blade)
        hull() {
            translate([PAD_X0 + CHAMF, -PAD_W/2, SLAB_Z0 - PAD_T])
                cube([PAD_X1 - PAD_X0 - 2*CHAMF, PAD_W, EPS]);
            translate([PAD_X0, -PAD_W/2, SLAB_Z0 - EPS])
                cube([PAD_X1 - PAD_X0, PAD_W, EPS]);
        }
        // ribbed press plugs up into the blade holes
        for (px = PLUG_X)
            translate([px, 0, SLAB_Z0 - EPS]) {
                cylinder(d = 3.3, h = PLUG_L);
                for (rz = [2.5, 5.0])   // grip ribs (squish into O3.2)
                    translate([0, 0, rz]) cylinder(d = 3.7, h = 0.8);
            }
    }
}

tibia_pad();
