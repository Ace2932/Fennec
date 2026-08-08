// =============================================================================
// LEAD-NOTCH GROMMET — TPU edge liner, shoulder battery-lead notch (print: TPU 95A)
// =============================================================================
// PRINT: TPU 95A, flat, zero supports, 100% infill — as case_slot_grommet.scad
//   and the rest of the TPU liner family. (#184: this used to be only the
//   parenthetical "(print: TPU 95A)" on the title line above, lowercase and
//   mid-line, which is not a header a PRINT:-line parser can find.)
// AUD-12b (2026-07-10): leg_v6/shoulder.scad's battery-lead notch (flange
// bottom center, x +/-10, z -38.1..-26 — REAR end: pack->MRBF leads; FRONT
// end, same part: D456 right-angle USB-C) was a zero-radius 90deg through-cut
// in abrasive PA6-CF, with leads running unsupported from the belly pack
// (trunk x~-78) into it. shoulder.scad now chamfers all 4 nominal edges at
// both flange mouths (lead_notch()/notch_bevel()); this part is the TPU liner
// that rides that chamfer, same "raw edge -> TPU radius" job as
// chassis/case_slot_grommet.scad, ported here.
//
// ---- notch geometry (leg_v6/shoulder.scad, read 2026-07-10 — keep in sync) --
// Built in the SAME shoulder-LOCAL frame as shoulder.scad itself (not trunk
// world coords) — open both STLs together to check the fit, same practice as
// case_slot_grommet.scad opening against riser_bay.stl in ITS frame.
// FLANGE_Y0=-77.7, FLANGE_Y1=-73.7 (4mm flange thickness, the wall this
// liner clips onto). NOTCH_X0/X1 = +/-10 (20mm nominal width). NOTCH_TOP =
// -26 — the ONLY genuine material edge the leads chafe on: the notch is
// OPEN at the BOTTOM (the flange's own solid stops dead at z=-38, 0.1mm
// short of the notch cut's z0=-38.1 — that -0.1 is the standard EPS-overcut
// idiom, not a deliberate 4th edge) and the left/right ends (x=+/-10) are
// the slot's own end corners — same "protect the flat run, not the rounded
// corners" call case_slot_grommet.scad makes with its own LINER_LEN inset.
//
// ---- axis mapping vs case_slot_grommet.scad (ported pattern) ---------------
// case_slot_grommet's SLOT LENGTH axis (X) <-> this part's NOTCH WIDTH axis
// (X) — same LINER_LEN-inset-from-the-full-span idiom (18 of 20mm here,
// span "~18mm inset from the 20mm" per the fix brief — EXACT match).
// case_slot_grommet's WALL-THICKNESS/grip axis (Z, DECK_T=4mm) <-> this
// part's flange-thickness axis (Y, FLANGE_T=4mm) — same GAP=T-0.1=3.9
// light-interference idiom ("GAP~=3.9 for a 4mm flange" per the fix brief —
// EXACT match). case_slot_grommet's OPEN-EDGE axis (Y, EDGE_Y) <-> this
// part's OPEN-EDGE axis (Z, NOTCH_TOP) — the rounded_prism() helper below is
// case_slot_grommet's, copied verbatim (it's already axis-generic: it just
// places cylinders at the 2nd/3rd args it's given).
//
// ---- design: spine (rounds the top edge, BOTH flange mouths — leads may
// bend over either face depending on routing) + ONE retention lip -----------
// case_slot_grommet ended up BOTTOM-LEG-ONLY after finding a two-leg design
// fights a neighboring part; this notch has no such neighbor, but the SAME
// "bottom-leg [i.e. one-sided] clip is enough" call applies here for a
// simpler reason: the notch's own "bottom" is open air (see above), so
// there's no flat face there to clip onto at all — the one real analog of
// case_slot_grommet's leg (a flat plate pressed flush against solid
// material just past the open edge) is a plate against the flange's
// EXTERIOR (Y1) face, hooking over the top edge into the solid flange
// material that continues above the notch (z>NOTCH_TOP). Retention is
// secondary to the GAP interference fit anyway — the lead bundle itself is
// strap-retained, same call as case_slot_grommet's zip-tie tab (no tab
// needed here — nothing this liner carries pulls axially on it).
// No slit: like case_slot_grommet, this is an OPEN profile (never wraps a
// full loop around the bundle) — press-installs onto the chamfered top edge
// directly, no threading required, so there's nothing to slit.
//
// Fit gate: chassis/build_all.sh renders + mesh_health.py-checks this file
// (watertight + single body). Not a check_fit.py case (no automated seat
// gate — the shoulder-local frame + shoulder's own gate coverage make a
// dedicated case low value here; verified by direct measurement instead,
// see the FIX B report).

$fn = 32;
EPS = 0.05;

// ---- source consts (leg_v6/shoulder.scad — keep in sync) --------------------
FLANGE_Y0 = -77.7;  FLANGE_Y1 = -73.7;    // 4mm flange thickness
FLANGE_T  = FLANGE_Y1 - FLANGE_Y0;         // 4.0
NOTCH_TOP = -26;                           // the one real material edge

// ---- liner geometry (ported from chassis/case_slot_grommet.scad) -----------
LINER_LEN = 18;                    // x +/-9 — inset 1mm off the 20mm notch
                                    // each side, clear of the end corners
GAP       = FLANGE_T - 0.1;        // 3.9 — light interference on the 4mm flange
Y0        = FLANGE_Y0 + (FLANGE_T - GAP) / 2;   // grip band, centered in the flange
Y1        = FLANGE_Y1 - (FLANGE_T - GAP) / 2;

SPINE_BACK = 0.3;    // core embeds this far past the top edge (z>NOTCH_TOP,
                      // real solid flange material) — light interference,
                      // same role as case_slot_grommet's SPINE_BACK
SPINE_FWD  = 1.1;     // spine protrusion down into the passage (z<NOTCH_TOP)
                       // — rounds the raw edge without eating much of the
                       // ~10mm clear height left under it
CAP_R      = 0.5;      // spine corner-rounding radius (passage side only)

LEG_T      = 1.3;       // retention lip thickness
LEG_REACH  = 4.0;        // lip reaches this far above NOTCH_TOP into the
                          // solid flange material at the exterior (Y1) face
                          // — "whatever solid backs the notch"

assert(CAP_R <= (Y1 - Y0) / 2, "CAP_R too big for the flange grip band");
assert(CAP_R <= (SPINE_FWD + 0.2) / 2, "CAP_R too big for the spine's z-span");

module xcyl(r, len) {
    rotate([0, 90, 0]) cylinder(r = r, h = len, center = true);
}

// rounded prism swept along X — case_slot_grommet.scad's rounded_prism(),
// copied verbatim (hull of 4 corner cylinders; exact-bounds only if
// r <= half of both spans, asserted at the call sites above).
module rounded_prism(len, y0, y1, z0, z1, r) {
    hull()
        for (py = [y0 + r, y1 - r], pz = [z0 + r, z1 - r])
            translate([0, py, pz]) xcyl(r, len);
}

module lead_notch_grommet() {
    union() {
        // spine flat core: full flange grip band (Y0..Y1), embeds
        // SPINE_BACK past the top edge into real flange material (square
        // corners there — never exposed to the cable) down to just short of
        // the rounded cap below (overlap for a clean union, same idiom as
        // case_slot_grommet's core/cap overlap).
        translate([-LINER_LEN / 2, Y0, NOTCH_TOP - 0.2])
            cube([LINER_LEN, Y1 - Y0, SPINE_BACK + 0.2]);
        // rounded cap: protrudes into the passage (z<NOTCH_TOP), rounded on
        // the exposed tip — this is what the cable actually rides.
        rounded_prism(LINER_LEN, Y0, Y1, NOTCH_TOP - SPINE_FWD,
                     NOTCH_TOP + 0.2, CAP_R);
        // retention lip: flat plate flush against the flange's EXTERIOR
        // (Y1) face, hooking over the top edge into the solid flange
        // material above it (z>NOTCH_TOP) — generous overlap into the
        // spine/cap for a clean single-body union.
        translate([-LINER_LEN / 2, Y1 - 0.6, NOTCH_TOP - 0.3])
            cube([LINER_LEN, (FLANGE_Y1 + LEG_T) - (Y1 - 0.6),
                  LEG_REACH + 0.3]);
    }
}

lead_notch_grommet();
