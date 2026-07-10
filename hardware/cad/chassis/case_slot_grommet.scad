// =============================================================================
// CASE_SLOT GROMMET — TPU edge liner, riser -Y cable drop (print: TPU 95A)
// =============================================================================
// #41 retired jetson_cowl.scad: right-angle plug adapters now turn each
// Jetson cable DOWN at the port so it drops straight through the riser's
// existing -Y CASE_SLOT (riser_bay.scad) into the bay -- no cowl needed.
// That leaves the slot's cable-bearing edge as bare printed PA6, chafing
// the DC-barrel/RJ45/USB-C bundle on every vibration cycle. This is a TPU
// U-channel liner modeled on leg_v6/grommet_insert.scad (#30: slit liner,
// rounded lips both faces, wraps a bare edge) -- adapted from a closed
// bore to a straight OPEN edge, because CASE_SLOT is a long-thin THROUGH
// SLOT in a 4mm deck plate, not a round hole in a wall.
//
// ---- CASE_SLOT geometry (riser_bay.scad, read 2026-07-10) ------------------
// CASE_SLOT = [-30, 30, -51.5, -47]  (x0,x1,y0,y1), trunk frame. DECK_T=4.0,
// DECK_BOT=67.9, DECK_TOP=71.9 (riser_bay.scad consts). Documented as the
// case -Y-flank cable drop, "long+thin", sitting in the ~4.8mm channel
// between the Jetson case footprint (y-46.95) and the riser skirt inner
// (y-51.8). This liner targets the documented -Y OUTER edge, y0 = -51.5
// (the far edge from the case, where a cable dropping past the -y flank
// naturally bows as it falls away from the case body -- matches this
// file's own strain-relief tab placement and the task's explicit "at
// minimum the -Y outer edge the bundle rests against" fallback).
//
// *** FLAG — riser_bay.scad CASE_SLOT cut does NOT match its own docs ***
// riser_bay.scad line ~194 calls `rounded_slot(CASE_SLOT..., 4)` -- a
// hull-of-4-corner-circles with r=4. That r requires the short (y) span
// to be >= 2*r = 8mm; CASE_SLOT's y-span is only 4.5mm. The corner circles
// invert past each other and the hull blows WAY out past the nominal
// bounds. Verified by direct mesh inspection of the built riser_bay.stl
// (2026-07-10): the actual cut spans y approx -55.0..-43.5 (11.5mm, not
// 4.5mm) x -30..30 -- it reaches the deck plate's own -y outer edge
// (OUT_Y=55) and eats well under the Jetson case footprint (case -y edge
// -46.95). jetson_case_mount.scad's own comment ("-Y tie-rail ... OUTBOARD
// of the CASE_SLOT (y-52..-55, over the skirt)") independently corroborates
// the blown-out extent -- a previous pass routed AROUND this bug rather
// than fixing it. NOT fixed here (out of this task's scope: this file
// only adds the new grommet part, per the brief). Recommended follow-up:
// riser_bay.scad line 194, drop r from 4 to <= 2.0 (half the 4.5mm y-span,
// e.g. r=2) so the cut actually matches CASE_SLOT's documented bounds --
// a clean -Y edge is a PRE-REQUISITE for this liner to seat as designed.
// Until that lands, the liner in the CURRENT riser_bay.stl has nothing
// crisp to clip onto over most of its length (open air out to the skirt).
//
// ---- design: straight edge liner, not a closed-bore grommet ----------------
// A full-perimeter ring (grommet_insert.scad's approach) would eat a
// wall's worth of clearance on all 4 sides of an already-narrow 4.5mm
// channel -- not enough room left for 3 real cables. Instead this is a
// hook-profile edge liner that clips onto ONLY the -Y outer edge (spine
// caps the raw PA6 corner, ONE leg grips the deck's BOTTOM/bay face) --
// same shape family as door/panel edge trim, but ASYMMETRIC (see below).
//
// *** SECOND FLAG — no room for a top (case-side) leg ***
// A symmetric two-leg design (grip caps on both the deck's top AND
// bottom faces, like grommet_insert.scad's two lips) was the first pass
// here, but jetson_case_mount.scad's -Y tie-rail
// (`translate([CX0, -53.35, DECK]) cube([..., 1.35, 3])`, i.e. y
// -53.35..-52, z 71.9..74.9, running the tie rail's full x length) sits
// DIRECTLY on top of the deck at this same (x,y) footprint. ANY liner
// material proud of the deck's TOP face (z>71.9) in that y-band collides
// with the tie rail -- confirmed by direct dimension check (a symmetric
// design's top leg landed z 71.1..72.95, 1.05mm into the tie rail's
// 71.9..74.9 band). There is no slack to shrink a top leg into: the tie
// rail starts only 0.5mm past the documented edge (EDGE_Y=-51.5 vs tie
// rail y0=-52). So this liner is BOTTOM-LEG-ONLY: the spine still rounds
// the top (case-side) transition (its profile reaches to within 0.05mm
// of the true deck top, z<=DECK_TOP), just without an additional cap
// riding proud on the top surface. Retention is the spine's interference
// fit (GAP undersized vs DECK_T) plus the bottom leg -- lighter grip than
// a two-sided clip, adequate for a TPU part carrying no load of its own
// (cable weight only; tension is meant to be taken by the strain-relief
// tab, not the liner's friction fit). Checked in check_fit.py case 12b.
//
// Rounded spine (hull of X-axis corner cylinders, same idiom as
// riser_bay.scad's rounded_slot(), just swept along X instead of Z, and
// only rounded on the cable-facing +y side -- see spine_round() below)
// means the cable meets a TPU radius instead of the printed corner on
// BOTH the case-side entry and the bay-side exit. Open (no full wrap) =
// press-installs onto the edge directly, no threading/slitting required
// -- and it barely narrows the passage (spine protrudes SPINE_FWD ~1.0mm
// into the 4.5mm channel, leaving ~3.5mm clear for the bundle running
// single-file along the slot's 54mm liner length).
//
// Strain relief: a zip-pair tab (O3.4 x2, 10mm spacing -- matches
// leg_v6/cable_clip.scad's established anchor idiom) hangs off the
// bottom leg into the bay, so the bundle gets zip-tied to the GROMMET
// right where it enters the bay, not left to hang off the port plugs.
//
// Fit: GAP = DECK_T - 0.1 = 3.9 (light interference on the 4.0mm deck
// edge -- TPU 95A flexes on; kept small since there's no top leg to help
// hold it on, so the fit shouldn't need excessive install force either).
// LEG_REACH = 4.0 onto the bottom deck face for grip.
//
// Print: TPU 95A, flat (either flat face down, no supports), 100% infill,
// ~1 g (lighter than the original two-leg pass since the top leg is gone).
// Trunk-frame placement (this part IS built in trunk-frame world coords,
// like riser_bay.scad -- open both STLs together to check the fit
// visually): x centered 0 (CASE_SLOT x-center), spans x +/-27.
//
// Fit gate: chassis/check_fit.py case 12b (added alongside this file).
// build_all.sh renders + mesh_health.py-checks it.

$fn = 32;
EPS = 0.05;

// ---- source consts (riser_bay.scad / jetson_case_mount.scad — keep in sync) -
DECK_T   = 4.0;
DECK_BOT = 67.9;
DECK_TOP = 71.9;
EDGE_Y   = -51.5;     // CASE_SLOT[2], the documented -Y outer edge (intended
                       // geometry — see FLAG above re: the current riser cut)
SLOT_LEN = 60;         // CASE_SLOT[1] - CASE_SLOT[0]
TIE_RAIL_Y0 = -53.35; TIE_RAIL_Y1 = -52; TIE_RAIL_Z0 = DECK_TOP;  // jetson_case_mount.scad

// ---- liner geometry -----------------------------------------------------------
LINER_LEN  = 54;        // inset 3mm off each end — sits on the straight run,
                        // clear of the slot's own rounded corners
GAP        = DECK_T - 0.1;   // 3.9 — light interference grip on the deck edge
LEG_T      = 1.2;       // leg wall thickness (matches grommet_insert.scad FLG_T)
// *** THIRD FLAG — deck margin caps LEG_REACH at 3.5, not a round number ***
// The deck plate itself (riser_bay.scad OUT_Y=55) ends at y=-55 -- only
// 3.5mm past the documented edge (EDGE_Y=-51.5). A first pass used
// LEG_REACH=4.0, which hung the leg 0.5mm off the edge of the deck plate
// itself (caught by comparing this file's own bounds against OUT_Y, not
// by mesh_health -- that only checks THIS part's own watertightness, not
// its fit against the riser). 3.0 leaves 0.5mm margin.
LEG_REACH  = 3.0;       // leg reach onto the deck face, away from the passage
SPINE_BACK = 0.3;       // spine's flat core reaches this far onto the
                        // material side (-y), overlapping the leg
SPINE_FWD  = 1.0;       // spine protrusion into the cable passage (+y) —
                        // rounds the raw edge without eating much clearance
CAP_R      = 0.5;       // spine corner-rounding radius (passage side only)

Z0 = DECK_BOT + (DECK_T - GAP) / 2;   // 67.95 — bottom of the grip gap
Z1 = DECK_TOP - (DECK_T - GAP) / 2;   // 71.85 — top of the grip gap, <= DECK_TOP
assert(Z1 <= TIE_RAIL_Z0, "liner top must not protrude above the deck (tie-rail clash)");

// spine rounding needs r <= half of the y-span it rounds — this is exactly
// the check riser_bay.scad's CASE_SLOT cut skipped (see the FLAG above);
// assert it here so this file can't repeat that bug.
assert(CAP_R <= (0.1 + SPINE_FWD) / 2, "CAP_R too big for the rounded cap's y-span");
assert(CAP_R <= (Z1 - Z0) / 2, "CAP_R too big for spine z-span (gap)");

// ---- strain-relief tie tab (zip-pair, cable_clip.scad idiom) ---------------
TAB_W    = 12;          // along X — fits the 10mm hole spacing + margin
TAB_DROP = 6;            // hangs this far below the bottom leg, into the bay
TAB_T    = 1.6;          // thicker than the leg — it carries real tension
TAB_HOLE = 3.4;          // zip-tie hole d (matches cable_clip.scad)
TAB_X    = 0;             // centered on the liner length

module xcyl(r, len) {
    rotate([0, 90, 0]) cylinder(r = r, h = len, center = true);
}

// rounded prism swept along X — the riser_bay.scad rounded_slot() idiom
// (hull of 4 corner circles), just built with X-axis cylinders instead of
// Z-axis ones so the extrusion runs the liner's length instead of the
// deck's thickness. Exact-bounds ONLY if r <= half of both spans (assert
// at the call site, not here — this module doesn't know the caller's math).
module rounded_prism(len, y0, y1, z0, z1, r) {
    hull()
        for (py = [y0 + r, y1 - r], pz = [z0 + r, z1 - r])
            translate([0, py, pz]) xcyl(r, len);
}

module case_slot_grommet() {
    union() {
        // spine FLAT CORE: square corners on the leg-facing (-y) side, so
        // it shares an exact rectangular face with the leg below (same
        // idiom every abutting cube in riser_bay.scad already uses) —
        // no rounding to fight there, avoids the corner-pullback trap a
        // uniformly-rounded prism hits right at its own z0/z1 planes
        // (hit this on the first pass: mesh_health caught bodies=3 from
        // the spine's rounded corners not actually reaching the legs).
        translate([-LINER_LEN / 2, EDGE_Y - SPINE_BACK, Z0])
            cube([LINER_LEN, SPINE_BACK + 0.5, Z1 - Z0]);
        // rounded CAP: only the passage-facing (+y) side needs rounding —
        // nothing ever rubs the grip/-y side. Overlaps generously into the
        // flat core above (0.3 overlap comfortably clears CAP_R's worst-
        // case corner pullback at z0/z1).
        rounded_prism(LINER_LEN, EDGE_Y - 0.2, EDGE_Y + SPINE_FWD, Z0, Z1, CAP_R);
        // bottom leg — grips the deck BOTTOM (bay-side) face. Flat
        // rectangular cross-section; its top face sits AT z=Z0 (matching
        // the spine core's bottom exactly) but the two cubes only union
        // cleanly if their Y-ranges actually OVERLAP at that shared
        // plane, not just touch at a single Y value (a leg that stopped
        // exactly at the core's own y0 shared only a zero-area edge —
        // hit this on the second pass, mesh_health caught watertight=False
        // bodies=2). +0.3 y-overlap past the core's y0 fixes it.
        translate([-LINER_LEN / 2, EDGE_Y - LEG_REACH, Z0 - LEG_T])
            cube([LINER_LEN, LEG_REACH - SPINE_BACK + 0.3, LEG_T]);
        // strain-relief tab, hanging off the bottom leg into the bay
        translate([TAB_X - TAB_W / 2, EDGE_Y - LEG_REACH + 2, Z0 - LEG_T - TAB_DROP])
            difference() {
                cube([TAB_W, TAB_T, TAB_DROP + LEG_T]);   // overlaps up into the leg
                for (sx = [-1, 1])
                    translate([TAB_W / 2 + sx * 5, -EPS, TAB_DROP - 4])
                        rotate([-90, 0, 0])
                            cylinder(d = TAB_HOLE, h = TAB_T + 2 * EPS);
            }
    }
}

case_slot_grommet();
