// =============================================================================
// *** RETIRED 2026-07-10 — SUPERSEDED BY RIGHT-ANGLE PLUG ADAPTERS (#41) ***
// This −Y cable cowl existed ONLY to shield STRAIGHT plugs exiting the
// Jetson's −Y (robot-right) ports (barrel V12_JET, USB-A, USB-C, RJ45) that
// stuck out ~13-25mm past the tight flank channel — a snag + side-fall
// crush risk, cantilevering ~19mm past the riser −y edge. RESOLUTION
// (backlog #41): ~$6-15 right-angle plug adapters at each port turn the
// cable DOWN at the port instead of sideways, so it drops straight through
// the riser's existing −Y CASE_SLOT (x-30..30, y-51.5..-47 — unchanged,
// still built by riser_bay.scad, see #38) with zero −Y protrusion. The
// cowl's protection role is gone; the CASE_SLOT relocation it depended on
// stays.
// Kept in place (not deleted) for its reused knowledge — impact-wall/
// end-wall geometry, the M2-into-upright bolt pattern, the counterbore
// idiom for a short M2x10 in a thick wall — NOT built (removed from
// build_all.sh) and NOT gated (removed from check_fit.py case 12). See
// docs/improvement-backlog.md #41 (this retirement) + #38 (cowl's origin,
// CASE_SLOT still active).
// =============================================================================
// JETSON -Y CABLE COWL — bolt-on flank shield for STRAIGHT port plugs (#38)
// =============================================================================
// The Jetson ports face -Y (robot RIGHT). With no right-angle plugs, STRAIGHT
// plugs stick out ~13-25mm (barrel 13 / USB-C 20 / USB-A 22 / RJ45 25) — past
// the tight flank channel, so on a right-side fall the ground would CRUSH them.
// This cowl is an outer IMPACT WALL (y-74) + 2 end walls that bolt to the
// cradle's -y uprights + a floor shelf: a -y fall hits the wall, not the plugs.
// Open TOP + open +Y (toward the case) so you plug the cables in with the cowl
// OFF, then bolt it on. The floor guides the cables inboard to the deck edge
// (y-55) -> the riser CASE_SLOT -> the bay.
//
// SEPARATE part (not fused to the cradle) so the assembly order works: cradle
//   down -> case in -> PLUG the -y cables (full access) -> drop this cowl on +
//   2x M3 from the -y (outer) side into the cradle -y uprights (COWL_BOLT_Z
//   heat-sets, pressed from the upright -y faces). -> then the 4 case clamps.
// Frame: TRUNK/world (matches jetson_case_mount — keep the shared consts in sync).
// Depth: inner wall face y-72 clears USB-A/C plugs (~y-69); RJ45 (~y-72, dev-
//   only) reaches the wall / pokes the open top. Cantilevers ~19 past the riser
//   -y edge (y-55) — mid-body, verified clear of the legs.
// PRINT: PA6-CF (impact part), OUTER-WALL-DOWN or end-down; ~8g. print 1.

$fn = 48; EPS = 0.05; M2_CLEAR = 2.3;   // bolts to the -y uprights with M2 (fastener audit)

// ---- shared with jetson_case_mount (KEEP IN SYNC) ----
FRONT_PXC = 47.3; REAR_PXC = -59.0;   // -y upright x centres
POST_YC = 50.35; POST_W = 6;          // upright y centre + size
DECK = 71.9; COWL_BOLT_Z = 85;        // deck top + cowl bolt z

// ---- cowl geometry ----
COWL_YI = -72; COWL_YO = -74;         // impact wall: inner y-72, outer y-74
COWL_Z1 = 102;                        // wall top (covers ports z72..101; kept
                                      // BELOW the clamp seats z102.8 so the -y
                                      // clamp discs don't clip the cowl top)
UP_FACE = -POST_YC - POST_W / 2;      // -y upright -y face = -53.35 (end-wall root)

module jetson_cowl() {
    difference() {
        union() {
            // outer IMPACT wall (spans between the -y uprights)
            translate([REAR_PXC, COWL_YO, DECK])
                cube([FRONT_PXC - REAR_PXC, COWL_YI - COWL_YO, COWL_Z1 - DECK]);
            // 2 end walls: outer wall -> the -y upright -y faces (bolt roots)
            for (px = [REAR_PXC, FRONT_PXC])
                translate([px - POST_W / 2, COWL_YO, DECK])
                    cube([POST_W, UP_FACE - COWL_YO, COWL_Z1 - DECK]);
            // floor shelf: catches cables, bridges to the deck edge (y-55)
            translate([REAR_PXC, COWL_YI, DECK])
                cube([FRONT_PXC - REAR_PXC, -55 - COWL_YI, 2]);
        }
        // 2x M2 bolt into the upright -y-face inserts. The end wall is ~20mm
        // thick, so COUNTERBORE from the outer face (Ø5.5) to leave a short
        // M2x10 bolt (head recessed, reached with a long 1.5mm hex key) — not a
        // silly M2x25. Clearance for the last stretch into the upright.
        for (px = [REAR_PXC, FRONT_PXC]) {
            translate([px, COWL_YO - EPS, COWL_BOLT_Z]) rotate([-90, 0, 0])
                cylinder(d = 5.5, h = (UP_FACE - COWL_YO) - 6);      // head counterbore
            translate([px, COWL_YO - EPS, COWL_BOLT_Z]) rotate([-90, 0, 0])
                cylinder(d = M2_CLEAR, h = UP_FACE - COWL_YO + 2 * EPS);  // M2 shank
        }
    }
}

// RETIRED — not called. See banner above.
// jetson_cowl();
