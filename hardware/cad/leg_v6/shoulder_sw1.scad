// FRONT shoulder = the same v6 crossmember, plus the SW1 Contura panel hole.
// =============================================================================
// #377 (2026-08-15). Until now shoulder.scad was "SAME part both ends; print 2"
// and that is now only half true: the FRONT end carries the master power
// switch, the REAR end prints plain from shoulder.scad. Two STLs, one source.
//
// WHY THE SPLIT rather than cutting both ends (which would have kept one part
// and cost nothing in code):
//   * the rear end cannot USE the hole. panel_probe.py qualified 112 placements
//     and every one is at trunk x +108 — the front. Cutting the rear would be a
//     hole that nothing goes in, opening the rear C-box to debris.
//   * a shoulder is ALREADY PRINTED (2026-08-07/08 bench session, 1 of the 2).
//     Leaving the rear plain means that part still conforms EXACTLY to its
//     model — no drift to declare, no reprint wasted. It becomes the rear.
//
// `shoulder.stl` deliberately keeps its name and its plain geometry, so every
// existing consumer keeps loading the part it always loaded. The no-hole part
// is the conservative one for clearance gates, so a consumer that has not been
// taught about the split under-reports free space rather than over-reporting it.
//
// PRINT: identical to shoulder.scad — PA6-CF, +Z FACE DOWN (deck top on the
// bed), tree supports under the flange span. The cutout is a vertical slot in a
// wall that is itself vertical in print space, so it needs no SUPPORT — but it
// is NOT bridging-free, which an earlier draft of this header claimed. See the
// coupon note below: closing the slot costs a ~21mm bridge.
//
// BEFORE COMMITTING THE 165 g PRINT: coupon-test the snap. A 4mm PA6-CF plate
// with this cutout, against the real switch. Carling's drawings say "TEST CUT
// HOLE IN ACTUAL MATERIAL" — the wings assume ABS/PC compliance and CF-filled
// nylon is stiffer. Dial SW1_FIT in shoulder.scad from that coupon.
//
// PRINT THE COUPON IN THIS PART'S ORIENTATION, NOT FLAT. It matters: with the
// deck top on the bed the build runs along -z, so the printer meets the cutout
// at shoulder z +23.4, opens 36.8mm of nothing, and has to CLOSE it again at
// z -13.5 — a ~21mm unsupported BRIDGE, 4mm deep, in a material that bridges
// badly. That bridged edge is one of the four rims the wings grip. A coupon
// printed flat has no bridge at all and would pass while the real part's rim
// droops. (The 1.2mm corner radii help by starting the bridge narrow.)

$fn = 64;
use <shoulder.scad>

shoulder_v6(sw1 = true);
