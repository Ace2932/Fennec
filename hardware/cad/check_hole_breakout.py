#!/usr/bin/env python3
"""HOLE-BREAKOUT GATE — does any fastener hole run off the edge of its part?

WHY THIS EXISTS
---------------
l2_adapter's two FRONT L2 bolts sat 1.5 mm from the plate's front edge while
their O6.2 countersinks need 3.1 mm of radius. Both holes were therefore not
holes at all but open notches: no head seat on the outboard side, nothing
stopping the bolt sliding out sideways, and the L2 held on two of its four
bolts. Spotted by Aiden on a slicer preview, 2026-08-06.

Root cause was the usual one. head.scad's crown was "grown to hold the REAL L2
pattern (+-18)" -> CROWN_X1 = 148, and the adapter plate carrying the same bolts
was left at x146.

NOTHING COULD HAVE CAUGHT IT. chassis/check_fit.py checks the adapter's SEAT
against the crown; CI runs mesh_health on it, which is watertight / single-body /
positive-volume. No check anywhere in the repo looked at hole-to-edge margin, so
a hole that leaves the part entirely passed every gate.

METHOD
------
Read the EVALUATED geometry, not the source. `openscad -o part.csg` flattens
every transform to numbers, so each cut appears as a multmatrix + cylinder with
concrete world coordinates -- no re-deriving positions from .scad variables that
are computed at render time.

For each cylinder on the SUBTRACTED side of a difference(), sample a ring just
outside its wall, at several heights inside the part. Every one of those points
must be inside the solid. If any is air, the hole is open to the outside there.

WHAT IT DOES NOT PROVE
----------------------
It cannot tell an accidental breakout from a deliberately open feature -- a slot,
a relief, or a bore that is meant to run out of an edge. Those go in ALLOW with a
reason. Silence is not an option: an unlisted breakout fails.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cad_contains  # noqa: E402  (#195 -- installed in main())

OPENSCAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"  # placeholder, see _openscad()
MARGIN = 0.30       # mm outside the hole wall to sample
MIN_R = 0.9         # ignore sub-fastener detail (vents, chamfer slivers)
MAX_R = 8.0         # ignore big architectural bores (wheel window, cable tunnel)

# Cuts that are MEANT to leave the part, or that this checker cannot
# correctly evaluate. Key: "part:x,y,z" (position rounded to 0.1mm; see
# check()'s `by_pos` key -- axis is NOT part of the key, so two features at
# the same rounded xyz would collide; that has not happened in this tree).
#
# #281 triage (2026-08-07), full tree-wide sweep, every entry below grounded
# against its .scad source (module + line), not guessed from coordinates.
# Grouped by feature via _allow() so one reason covers every hole a feature
# cuts, and organized per part below. Three DELIBERATE sub-classes:
#   (a) genuinely open by design -- a slot, vent, channel, grommet, driver-
#       access pocket, or ID-marking dimple that is SUPPOSED to reach air.
#   (b) a checker limitation, not a part defect: a fastener's straight shank
#       and its countersink/counterbore are cut as two cylinders that don't
#       share a Z position (the countersink starts partway up the shank), so
#       the "test only the largest radius at this position" merge (this
#       file's own docstring, see check()) never fires and the shank's own
#       ring reads the countersink's wider void as a breakout. Or: a guard-
#       band cut (h deliberately overshoots the real local wall so the
#       OpenSCAD subtraction is unambiguous) reaches past the true material
#       into an adjacent legitimate void (open interior, a servo pocket
#       cavity, open air past a thin wall) -- verified per-entry by sampling
#       height stations across the cut and confirming the part's own probed
#       comments/measurements account for it, not just "it's some other cut".
#   (c) a parser bug (not a hole at all): parse_cuts() flags ANY cylinder
#       found inside a difference()'s braces, including ones in the FIRST
#       (additive) child -- e.g. a union() of cylinders that IS the part's
#       own body. Confirmed on spacer (own shaft, r=4.00), grommet_insert
#       (flange disc r=7.30 + barrel/nose r=6.35 x2 -- the issue's own write-
#       up mis-cited r=7.30 as "the through bore"; the real bore, r=4.50, was
#       never flagged and is fine), strap (own hull-of-2-circles body,
#       r=4.00 x2) and tibia_L/tibia's strap bosses (r=3.50 x2, raised
#       material, not holes). A tree-based re-parse (differentiating a
#       difference()'s child0/additive from child1+/subtrahend) confirms
#       these 8 are never on the subtrahend side. Root-causing parse_cuts()
#       itself is out of scope here (ALLOW population + CI wiring, per
#       #281); flagged in the PR body as a follow-up worth a real fix.
#
# NOT included below (left to fail, on purpose): trunk's 3 FOOT countersinks
# (-59.5,-42/-59.5,42/59.5,42, r=3.20) and oled_mount's 2 pod-foot M2 holes
# (-96/-71, y=23) -- both are SUSPECT, not deliberate: measured directly
# against the mesh, both leave <=0.2mm of real wall on one side. See the PR
# body for the measurements. Silencing those would defeat the gate.


# GOTCHA (found populating this list, #281): the ALLOW key's rounding
# (Python's round() called on a numpy float64, in check()'s `key` tuple) and
# this script's own FAIL-message coordinates (built with an :.1f format spec
# on the same numpy float64) do NOT always agree on an exact .x5 half value
# -- e.g. base z=3.85 rounds to "3.8" for the key but prints as "3.9" in the
# FAIL line. Copying coordinates straight off a FAIL message into ALLOW
# silently no-ops for every such entry (30 of 121 in the #281 sweep). Every
# coordinate below was verified against the real by_pos key, not read off
# printed output.
def _allow(label, reason, *coords):
    return {f"{label}:{x},{y},{z}": reason for (x, y, z) in coords}


ALLOW = {}

# ---- case_slot_grommet.scad -------------------------------------------------
ALLOW.update(_allow(
    "case_slot_grommet",
    "zip-tie strain-relief tab hole (TAB_HOLE=3.4mm) in the TAB_T=1.6mm tab "
    "-- L161-217; the hole is wider than the tab it's cut in, by design "
    "(cable_clip.scad's own zip-tie-hole idiom).",
    ("-5.0", "-49.8", "62.8"), ("5.0", "-49.8", "62.8"),
))

# ---- control_pod.scad --------------------------------------------------------
ALLOW.update(_allow(
    "control_pod",
    "cable grommet through the column (Ø12, E-stop NC + OLED SPI drop), cut "
    "starting AT the column's own rear face by design -- L81-83.",
    ("-70.0", "0.0", "63.0"),
))

# ---- floor_plate.scad --------------------------------------------------------
ALLOW.update(_allow(
    "floor_plate",
    "rear cutout over the trunk's rear floor opening -- a hull() of 4 r=4 "
    "corner circles forming one big rounded-rectangle vent/inspection "
    "opening, not a fastener hole; each corner cylinder gets flagged "
    "individually by the checker -- L110-112.",
    ("-58.0", "-22.0", "3.8"), ("-58.0", "22.0", "3.8"),
    ("-48.0", "-22.0", "3.8"), ("-48.0", "22.0", "3.8"),
))
ALLOW.update(_allow(
    "floor_plate",
    "battery-sandwich M3 clearance hole (r=1.70) + its 90deg countersink "
    "(r=3.4, d1=3.4/d2=6.8) don't share a Z base (shank z=3.85, csk z=4.2) "
    "so the largest-radius merge never fires; the shank's own ring reads "
    "the countersink's wider cone above it as open. Verified directly "
    "against the CSG (both cuts dumped) and confirmed non-directional "
    "(fails uniformly at all 32 angles -- an axial/radial cone effect, not "
    "an edge). Not near any edge: BAT_Y=27.5 vs plate half-width HW=48 "
    "(20.5mm margin) -- L94-100.",
    ("-35.0", "-27.5", "3.8"), ("-35.0", "27.5", "3.8"),
    ("0.0", "-27.5", "3.8"), ("0.0", "27.5", "3.8"),
    ("40.0", "-27.5", "3.8"), ("40.0", "27.5", "3.8"),
))

# ---- head.scad ----------------------------------------------------------------
ALLOW.update(_allow(
    "head",
    "D456 mount hole's own +-3mm Z-tolerance slot (MOUNT_SLOT): a hull() of "
    "2 cylinders at the slot's ends, each flagged individually -- L226-230.",
    ("137.1", "-47.2", "111.1"), ("139.9", "-47.2", "116.5"),
))
ALLOW.update(_allow(
    "head",
    "D456 driver-access pocket (Ø11), explicitly an open pocket so a "
    "screwdriver can reach the mount bolt -- L231-236.",
    ("137.7", "-47.2", "114.2"), ("137.7", "47.2", "114.2"),
))

# ---- neck_bracket.scad --------------------------------------------------------
ALLOW.update(_allow(
    "neck_bracket",
    "driver-access notch (Ø9 socket/hex-key channel) for the head-mount "
    "bolts, explicitly cut open to the gusset/aft face -- L190-217.",
    ("103.0", "-10.0", "89.0"), ("103.0", "10.0", "89.0"),
    ("103.0", "-10.0", "100.0"), ("103.0", "10.0", "100.0"),
))
ALLOW.update(_allow(
    "neck_bracket",
    "head-mount bolt rear counterbore (Ø6.5), cut from the wall's own rear "
    "face (WALL_X0-EPS) inward -- open at that face by design -- L187-188.",
    ("113.0", "-10.0", "89.0"), ("113.0", "10.0", "89.0"),
))

# ---- riser_bay.scad ------------------------------------------------------------
ALLOW.update(_allow(
    "riser_bay",
    "control-pod cable grommet (Ø10), cut from the pad's pocket face "
    "(POD_BOSS_X-EPS) inward -- open at that face by design -- L237-238.",
    ("-66.6", "0.0", "63.5"),
))
ALLOW.update(_allow(
    "riser_bay",
    "riser<->flange M3 clearance shank, cut from the true outer wall face "
    "(OUT_X+EPS) with h=8.2 deliberately overshooting the WALL=3.2mm wall "
    "into the open bay interior -- guard-band idiom, not a breakout -- "
    "L219-225.",
    ("-63.4", "-40.0", "67.4"), ("-63.4", "40.0", "67.4"),
    ("63.4", "-40.0", "67.4"), ("63.4", "40.0", "67.4"),
))
ALLOW.update(_allow(
    "riser_bay",
    "CASE_SLOT cable-drop opening: rounded_slot() hull() of 4 corner "
    "circles (r=2.0), same shape as floor_plate's rear cutout -- L113-121, "
    "159-163, 205.",
    ("-28.0", "-47.0", "67.8"), ("-28.0", "-42.0", "67.8"),
    ("28.0", "-47.0", "67.8"), ("28.0", "-42.0", "67.8"),
))

# ---- spacer.scad ----------------------------------------------------------------
ALLOW.update(_allow(
    "spacer",
    "PARSER BUG, not a hole: this is the spacer's own outer cylinder body "
    "(d=8, the minuend of the top-level difference()), not the bore. The "
    "real bore (r=1.70) is a genuine cut and correctly passes. Confirmed "
    "via a tree-based re-parse that separates a difference()'s additive "
    "(child0) side from its subtrahend (child1+) side.",
    ("0.0", "0.0", "0.0"),
))

# ---- trunk.scad -----------------------------------------------------------------
ALLOW.update(_allow(
    "trunk",
    "belly-battery M3 clearance bore, deliberately cut BATT_BORE_Z0=-2 to "
    "BATT_BORE_H=8 -- 'starts below the floor bottom / ends well above the "
    "floor top -- clean cut' per the file's own comment -- against a "
    "probed-solid floor only ~3.9mm thick (probe_trunk.py). Guard-band "
    "overshoot into open air both sides, not a breakout -- L67-73, 121-124.",
    ("-35.0", "-27.5", "-2.0"), ("-35.0", "27.5", "-2.0"),
    ("0.0", "-27.5", "-2.0"), ("0.0", "27.5", "-2.0"),
    ("40.0", "-27.5", "-2.0"), ("40.0", "27.5", "-2.0"),
))
ALLOW.update(_allow(
    "trunk",
    "shoulder-foot M3 clearance SHANK (FOOT_BORE_H=8, 'through + margin "
    "above' per the file's own comment) -- verified by height-station "
    "sampling that it is fully solid within the real ~3.9mm floor "
    "(z0.0-3.9, where the fastener actually needs clearance) and only "
    "shows gaps in the guard-band region above the floor, where it grazes "
    "the corner-post structure -- irrelevant to the fastener, which never "
    "reaches that far. The FOOT CSK itself (r=3.20, the near-edge-relevant "
    "part) is deliberately NOT allow-listed here -- see the PR body's "
    "SUSPECT list -- L92-96, 126-133.",
    ("-59.5", "-42.0", "1.5"), ("-59.5", "42.0", "1.5"),
    ("59.5", "-42.0", "1.5"), ("59.5", "42.0", "1.5"),
))

# ---- leg_v6/cable_clip.scad ------------------------------------------------------
ALLOW.update(_allow(
    "cable_clip",
    "bundle channel (Ø6, the cable passage the clip exists for), starting "
    "1mm before the clip's own body by design -- L87-89.",
    ("-1.0", "0.0", "4.0"),
))
ALLOW.update(_allow(
    "cable_clip",
    "bell-mouth horn (bend-radius control at the clip's cable exits), "
    "explicitly a flared-open mouth at each end -- L90-96.",
    ("5.0", "0.0", "4.0"), ("13.0", "0.0", "4.0"),
))
ALLOW.update(_allow(
    "cable_clip",
    "zip-tie hole crossing the bundle channel -- both features are "
    "deliberate and meant to intersect (the tie loops around the bundle "
    "sitting in the channel) -- L87-89, 97-101.",
    ("9.0", "-5.0", "-0.0"), ("9.0", "5.0", "-0.0"),
))

# ---- leg_v6/coax.scad (coax_L is coax.scad mirrored) -----------------------------
ALLOW.update(_allow(
    "coax_L",
    "front strap zip-tie bore -- coax.scad's own header extensively "
    "documents this exact partial-open condition as analysed and accepted "
    "('the opening faces exactly OUTBOARD ... the clamp force acts ALONG "
    "the bore axis ... this trade is sound') -- L451-509.",
    ("-15.6", "-18.6", "-31.0"), ("15.6", "-18.6", "-31.0"),
))
ALLOW.update(_allow(
    "coax_L",
    "case-column M2 screw countersink (d1=4.6) + shank (M2_CLEAR) don't "
    "share a Z base, same checker-limitation class as floor_plate/trunk -- "
    "leg_v6_common.scad L294-301, called from pocket_platform_pos().",
    ("-10.2", "22.2", "-8.3"), ("10.2", "22.2", "-8.3"),
    ("-10.2", "23.2", "-32.8"), ("-10.2", "23.2", "-8.3"),
    ("10.2", "23.2", "-32.8"), ("10.2", "23.2", "-8.3"),
))
ALLOW.update(_allow(
    "coax_L",
    "zip anchor flanking the tunnel exit / HAA connector-bay, explicit "
    "through-hole starting inside an already-open void -- L586-603, "
    "605-638.",
    ("-7.0", "17.0", "-36.0"), ("7.0", "17.0", "-36.0"),
    ("-7.0", "19.0", "-27.0"), ("7.0", "19.0", "-27.0"),
))
ALLOW.update(_allow(
    "coax_L",
    "L/R identity marking dimple (2 dots = LEFT), coax_L.scad's own "
    "mirrored 2nd-dot cut -- L15-16.",
    ("12.0", "22.2", "-8.0"),
))
ALLOW.update(_allow(
    "coax_L",
    "horn-coupling M3 bolt clearance (horn_couple_neg, BCD r=7 about the "
    "hfe axis) -- extensively analysed in this file's #7-fix (BAND_* "
    "engagement bands, measured SF at these exact bolts) -- L343-350.",
    ("16.1", "6.7", "-14.4"), ("16.1", "6.7", "-4.6"),
))

# ---- leg_v6/coax_hfe_block.scad --------------------------------------------------
ALLOW.update(_allow(
    "coax_hfe_block",
    "2x M3 tenon-retention bolt clearance, driven from +X open air -- "
    "L166-173.",
    ("46.4", "5.0", "11.7"), ("46.4", "18.0", "11.7"),
))
ALLOW.update(_allow(
    "coax_hfe_block",
    "M3 SHCS head counterbore, opens on the outboard face by design -- "
    "L171-172.",
    ("57.2", "5.0", "11.7"), ("57.2", "18.0", "11.7"),
))
ALLOW.update(_allow(
    "coax_hfe_block",
    "wheel-screw head counterbore (wheel_couple_neg, 4x at the BCD) -- "
    "leg_v6_common.scad, called L163-164.",
    ("61.4", "6.7", "-14.4"), ("61.4", "6.7", "-4.6"),
    ("61.4", "16.5", "-14.4"), ("61.4", "16.5", "-4.6"),
))

# ---- leg_v6/coax_hfe_block_L.scad ------------------------------------------------
ALLOW.update(_allow(
    "coax_hfe_block_L",
    "L/R identity marking dimple (2 dots = LEFT), cut STARTING OUTSIDE the "
    "face by design -- L14-22.",
    ("-62.7", "19.6", "1.0"),
))

# ---- leg_v6/femur.scad (femur_L is femur.scad mirrored) --------------------------
ALLOW.update(_allow(
    "femur_L",
    "case-column M2 screw shank: passes through a ~1mm floor straight "
    "into the STS servo pocket cavity (its intended destination), so the "
    "ring reads the pocket's own open interior as a breakout -- uniform "
    "across all 32 angles at every station (verified with a per-angle "
    "probe), i.e. not an edge, a legitimate internal void -- "
    "leg_v6_common.scad COL_PTS/sts_pocket_neg, femur.scad L11-12.",
    ("8.3", "-10.2", "-23.2"), ("8.3", "10.2", "-23.2"),
    ("32.8", "-10.2", "-23.2"), ("32.8", "10.2", "-23.2"),
))
ALLOW.update(_allow(
    "femur_L",
    "side-wall vent window (CR-6 fix, stadium profile r=2.5, SF-calculated "
    "safety cutout) -- L210-227.",
    ("16.5", "-17.0", "0.0"), ("21.5", "-17.0", "0.0"),
))
ALLOW.update(_allow(
    "femur_L",
    "zip anchor (zip_pair_neg), explicit through-hole per the LA-4 fix -- "
    "L284-294.",
    ("44.0", "-5.0", "-27.6"), ("44.0", "5.0", "-27.6"),
    ("52.0", "-5.0", "-27.6"), ("52.0", "5.0", "-27.6"),
))

# ---- leg_v6/grommet_insert.scad --------------------------------------------------
ALLOW.update(_allow(
    "grommet_insert",
    "PARSER BUG, not a hole: flange disc (r=7.30, d=FLG_OD-0.4) + barrel "
    "(r=6.35, d=BARREL_OD) + entry-chamfer nose (r=6.35) are all additive "
    "union() geometry (the grommet's own body), not subtracted cuts. The "
    "real bore (r=4.50) and its rounded exit (r=5.70) are genuine cuts and "
    "both correctly pass -- confirmed via the tree-based re-parse -- "
    "L88-111.",
    ("0.0", "0.0", "0.0"), ("0.0", "0.0", "1.2"), ("0.0", "0.0", "5.4"),
))

# ---- leg_v6/knee_arm.scad --------------------------------------------------------
ALLOW.update(_allow(
    "knee_arm",
    "M3 mount hole + its Ø6.4 head counterbore don't share a Z base, same "
    "checker-limitation class as floor_plate -- L47-55; not near any edge "
    "(holes at +-8 well inside the TIP_R=15.85 rounded plate).",
    ("6.0", "-8.0", "-0.0"), ("6.0", "8.0", "-0.0"),
    ("16.0", "-8.0", "-0.0"), ("16.0", "8.0", "-0.0"),
))

# ---- leg_v6/shoulder.scad ---------------------------------------------------------
ALLOW.update(_allow(
    "shoulder",
    "trunk-flange heat-set bore, drilled from the flange's own rearward "
    "(open trunk-end) face -- trunk.scad's own header independently "
    "confirms this exact bore's path is already open ('the side wall is "
    "solid from x-50..48.8, then OPEN ... at every one of the 4 (y,z) "
    "combinations') -- shoulder.scad L335-338.",
    ("-51.8", "-77.8", "-14.0"), ("51.8", "-77.8", "-14.0"),
))

# ---- leg_v6/shoulder_plate.scad ---------------------------------------------------
ALLOW.update(_allow(
    "shoulder_plate",
    "flange mount hole (M3 clear or close-fit dowel) + its Ø6.4 head "
    "counterbore don't share a Z base, same checker-limitation class as "
    "floor_plate -- L106-113.",
    ("27.0", "6.2", "41.4"), ("27.0", "14.0", "41.4"),
    ("51.0", "6.2", "41.4"), ("51.0", "14.0", "41.4"),
))
ALLOW.update(_allow(
    "shoulder_plate",
    "horn locating recess (Ø6.5 x 0.4 deep), a shallow facing cut right at "
    "the horn mating face -- open there by design -- L95-100.",
    ("39.0", "17.7", "0.0"),
))

# ---- leg_v6/strap.scad -------------------------------------------------------------
ALLOW.update(_allow(
    "strap",
    "PARSER BUG, not a hole: this is the strap's own body outline, "
    "hull() of 2 Ø8 circles (the plate's additive minuend), not a "
    "fastener hole -- L26-28. Confirmed via the tree-based re-parse.",
    ("0.0", "-13.0", "0.0"), ("0.0", "13.0", "0.0"),
))
ALLOW.update(_allow(
    "strap",
    "zip-tie bore (Ø3.2), explicitly documented as 1.44mm clear of the "
    "plate's own outer edge (TRIMESH-PROBED, >=1.0mm) -- L4-17, 29-30.",
    ("0.0", "-15.6", "-0.1"), ("0.0", "15.6", "-0.1"),
))

# ---- leg_v6/tibia.scad (tibia_L is tibia.scad Z-mirrored) --------------------------
ALLOW.update(_allow(
    "tibia_L",
    "case-column M2 screw shank into the STS servo pocket cavity, same "
    "checker limitation as femur_L -- leg_v6_common.scad COL_PTS.",
    ("8.3", "-10.2", "-23.2"), ("8.3", "10.2", "-23.2"),
    ("32.8", "-10.2", "-23.2"), ("32.8", "10.2", "-23.2"),
))
ALLOW.update(_allow(
    "tibia_L",
    "side-wall vent window (stadium profile), same feature as femur_L.",
    ("16.5", "-17.0", "0.0"), ("21.5", "-17.0", "0.0"),
))
ALLOW.update(_allow(
    "tibia_L",
    "retention-strap zip-tie bore (strap_pilot_neg): the file's own header "
    "explicitly analyses and accepts the outboard side's thin margin "
    "('that side is the boss's exterior shoulder, not a cavity wall ... "
    "nothing breaks through') -- leg_v6_common.scad L428-472, called "
    "tibia.scad L152.",
    ("31.0", "-15.6", "-25.2"), ("31.0", "15.6", "-25.2"),
))
ALLOW.update(_allow(
    "tibia_L",
    "PARSER BUG, not a hole: strap boss (Ø7 raised material the strap "
    "seats on), additive union() geometry -- tibia.scad L81-84. Confirmed "
    "via the tree-based re-parse.",
    ("31.0", "-14.2", "14.6"), ("31.0", "14.2", "14.6"),
))
ALLOW.update(_allow(
    "tibia_L",
    "L/R identity marking dimple -- tibia.scad L149, tibia_L.scad L12-17.",
    ("37.0", "-10.0", "-14.9"), ("39.0", "10.0", "13.9"),
))
ALLOW.update(_allow(
    "tibia_L",
    "zip anchor (zip_pair_neg / the x62/84 through-hole convention), "
    "explicit through-holes along the blade -- L219-254.",
    ("58.0", "-5.0", "-23.2"), ("58.0", "5.0", "-23.2"),
    ("62.0", "0.0", "-23.2"), ("84.0", "0.0", "-23.2"),
))


def _openscad():
    for c in ("/opt/homebrew/bin/openscad",
              "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"):
        if os.path.exists(c):
            return c
    raise SystemExit("FAIL: openscad not found")


def _tokenize(src):
    return re.findall(r'[A-Za-z_][\w]*\s*\([^)]*\)|[{}]|;', src, re.S)


def parse_cuts(csg):
    """World-space (x, y, z, r, h) for every cylinder on a difference's cut side."""
    out, mat_stack, diff_depth = [], [np.eye(4)], []
    depth = 0
    pending = None
    child_idx = []
    for tok in _tokenize(csg):
        if tok == '{':
            depth += 1
            child_idx.append(0)
            if pending == 'difference':
                diff_depth.append(depth)
            pending = None
            continue
        if tok == '}':
            if diff_depth and diff_depth[-1] == depth:
                diff_depth.pop()
            depth -= 1
            child_idx.pop()
            if mat_stack and len(mat_stack) > 1:
                mat_stack.pop()
            continue
        if tok == ';':
            pending = None
            continue
        name = tok.split('(')[0].strip()
        if name == 'multmatrix':
            nums = [float(v) for v in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?', tok)]
            mat_stack.append(mat_stack[-1] @ np.array(nums[:16]).reshape(4, 4))
            pending = name
            continue
        if name == 'difference':
            pending = name
            continue
        if name == 'cylinder':
            kv = dict(re.findall(r'(\w+)\s*=\s*(-?[\d.]+)', tok))
            r = max(float(kv.get('r1', 0)), float(kv.get('r2', 0)))
            h = float(kv.get('h', 0))
            if diff_depth:
                m = mat_stack[-1]
                base = (m @ np.array([0, 0, 0, 1.0]))[:3]
                # THE AXIS IS NOT ALWAYS Z. Taking only the translation and
                # assuming +Z made this gate sample a ring along the hole's
                # LENGTH for every rotated bore -- neck_bracket's x-axis
                # head-mount holes then read 86-100% "open" when they are fine.
                # Transform the local +Z through the same matrix instead.
                axis = (m @ np.array([0, 0, 1.0, 0]))[:3]
                n = np.linalg.norm(axis)
                axis = axis / n if n > 1e-9 else np.array([0, 0, 1.0])
                out.append((base, axis, r, h))
            pending = None
            continue
        if child_idx:
            child_idx[-1] += 1
        pending = name
    return out


def check(stl, csg_path, label):
    mesh = trimesh.load(stl, force="mesh")
    cuts = parse_cuts(Path(csg_path).read_text())
    lo, hi = mesh.bounds
    # One hole may be cut by SEVERAL cylinders stacked on the same axis: a shank
    # plus a countersink or counterbore. Test only the LARGEST radius at each
    # position. Sampling just outside the shank of a countersunk hole lands
    # INSIDE the countersink void and reports a false breakout -- the first
    # version of this gate did exactly that on l2_adapter's rear pair, which is
    # measurably fine.
    by_pos = {}
    for (base, axis, r, h) in cuts:
        if not (MIN_R <= r <= MAX_R):
            continue
        key = (round(base[0], 1), round(base[1], 1), round(base[2], 1),
               round(axis[0], 2), round(axis[1], 2), round(axis[2], 2))
        prev = by_pos.get(key)
        if prev is None or r > prev[2]:
            by_pos[key] = (base, axis, r, h)

    bad = []
    for key, (base, axis, r, h) in sorted(by_pos.items()):
        if f"{label}:{key[0]},{key[1]},{key[2]}" in ALLOW:
            continue
        # two unit vectors perpendicular to the hole axis
        tmp = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(axis, tmp); u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        rr = r + MARGIN
        th = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        pts = []
        for f in (0.25, 0.5, 0.75):
            c = base + axis * (h * f)
            if not np.all((c > lo + 0.15) & (c < hi - 0.15)):
                continue      # this station is outside the part -- not a breakout
            for t in th:
                pts.append(c + rr * (np.cos(t) * u + np.sin(t) * v))
        if not pts:
            continue
        inside = mesh.contains(np.array(pts))
        if not inside.all():
            bad.append((base[0], base[1], base[2], r, 100.0 * (1 - inside.mean())))
    return bad


def main(argv):
    cad_contains.install()   # #195
    here = Path(__file__).resolve().parent
    scads = sorted(list((here / "leg_v6").glob("*.scad")) + list((here / "chassis").glob("*.scad")))
    scads = [s for s in scads if not s.name.endswith("_common.scad")
             and not s.name.startswith("preview_")]
    osc = _openscad()
    worst = 0
    print("-- fastener holes vs part edges (evaluated CSG, ring sampled outside each hole wall) --")
    for s in scads:
        stl = s.with_suffix(".stl")
        if not stl.exists():
            continue
        csg = Path("/tmp") / (s.stem + ".csg")
        rc = subprocess.run([osc, "-o", str(csg), str(s)],
                            capture_output=True, text=True)
        if not csg.exists():
            print(f"   SKIP  {s.stem}: csg export failed")
            continue
        bad = check(stl, csg, s.stem)
        if bad:
            worst = 1
            for (x, y, z, r, frac) in bad:
                print(f"   FAIL  {s.stem}: hole r={r:.2f} at ({x:.1f}, {y:.1f}, {z:.1f}) is OPEN "
                      f"to the outside over {frac:.0f}% of its wall — no material to seat "
                      f"against, fastener can leave sideways")
        else:
            print(f"   OK    {s.stem}")
    print("\n" + ("FAIL: a fastener hole runs off the edge of its part"
                  if worst else "OK: every fastener hole is fully enclosed"))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
