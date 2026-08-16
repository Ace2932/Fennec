// SW1 fit-test coupon — four allowances, one print.
// =============================================================================
// #377 (2026-08-16). Print this BEFORE shoulder_sw1. It exists to answer one
// question: what does SW1_FIT need to be for the Contura's wings to grip a
// printed 4mm PA6-CF panel?
//
// Four slots, labelled in hundredths of a mm per side:
//
//     0        nominal — the datasheet hole, 21.08 x 36.83
//     10       +0.10 / side
//     20       +0.20 / side
//     30       +0.30 / side
//
// Geometry comes from shoulder.scad's own SW1_* constants, so the coupon
// cannot drift from the part it is qualifying.
//
// PRINT: PA6-CF, **+Z FACE DOWN** — same as shoulder / shoulder_sw1, and this
// is not optional. The whole value of the coupon is that it reproduces the
// ~21mm BRIDGE that closes each slot, on the rim the wings grip. Laid flat
// there is no bridge, every hole comes out clean, and the test says nothing
// about the real part. Same material, same profile, same nozzle as the real
// print — a coupon run with different settings qualifies different settings.
// It stands on its own foot; a brim is worth it at 140mm of first layer.
//
// HOW TO READ IT
//   1. Push the switch into each slot in turn, starting at 0.
//   2. The right one goes in with a firm push and CLICKS, and does not fall out
//      when the coupon is held vertically and tapped.
//   3. Too tight = it will not seat, or the wings never clear the rear face.
//      Too loose = it seats but rocks, or pushes back out under thumb pressure.
//   4. Set SW1_FIT in shoulder.scad to the winning value and re-render
//      shoulder_sw1. If TWO adjacent slots both hold, take the SMALLER — the
//      wings want to be working.
//
// Also worth doing while it is in your hand: check the bridged rim. It is the
// edge at the top of each slot as printed. If it has drooped enough to narrow
// the opening, that is the defect the flat-printed coupon would have hidden,
// and it is a slicer problem (bridge flow / cooling), not a SW1_FIT one.

$fn = 64;
use <shoulder.scad>

sw1_coupon();
