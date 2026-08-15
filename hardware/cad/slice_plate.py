#!/usr/bin/env python3
"""Slice a plate headlessly, and PROVE the settings that came out are the ones
that went in.

WHY THIS EXISTS AT ALL. Every printed part on this robot is sliced by hand in a
GUI, from a .scad-derived STL, using orientation and settings written in prose
across `docs/checklists/print-batch.md` §2 and the .scad headers. Three things
go wrong there and none of them announce themselves:

  1. A STALE STL. Edit the .scad, forget `build_all.sh`, slice yesterday's
     geometry. `check_stl_fresh.py` (#176) catches this — but only if something
     runs it before the plate, which nothing did.
  2. A MATERIAL CONTRADICTION. `chassis/battery_pocket.scad` says "PRINT:
     PETG-CF"; print-batch §1 (#24) says it stays PA6-CF because it is the belly
     crush guard over the LiPo. Two docs, one part, opposite answers, and the
     slicer takes whatever the human picked that day.
  3. A SETTING THAT SILENTLY DID NOT APPLY. See below — this one is the reason
     the verification step is not optional.

THE TRAP THAT MOTIVATED THE VERIFY STEP (measured 2026-08-01). OrcaSlicer's CLI
does NOT resolve a system preset's `inherits` chain when you hand it a raw
profile json. Only the leaf's own keys apply; everything inherited falls back to
the built-in default. Slicing `lead_notch_grommet.stl` with
`Bambu TPU 95A HF @BBL P1S.json` (7 leaf keys) produced:

    ; filament_settings_id = "Bambu TPU 95A HF @BBL P1S"   <- names TPU
    ; filament_type = PLA                                   <- IS PLA
    ; nozzle_temperature = 200                              <- TPU wants 230

The header NAMES the right filament while the nozzle runs PLA temperatures. TPU
at 200 C underextrudes and jams. Nothing in the slicer's output says "I ignored
your preset" — the one field a human would read to check is the field that was
right. Flattening the chain (71 real keys) fixes it, and `verify_gcode()` below
exists so that fix can never silently regress: the emitted G-code is compared
against the FLATTENED preset, key by key.

    --self-test runs that regression deliberately (raw preset, expect the check
    to FIRE). A guard that has never been seen to fire is not a guard.

THE GATES, in order. Any one of them refuses the plate:

  1. STL freshness (`check_stl_fresh.py`, #176).
  2. Material agreement between the .scad header and the registry — and a
     COUNT of the parts it could not check, because a header that names no
     material is absence of evidence, not agreement.
  3. Orientation, measured: how much flat area actually lands on the bed, and
     how slender the result is. Under 5 mm^2 is an edge, not a face.
  4. Everything asked for is ON one plate — object count matches the request
     and the slicer did not silently split the job (see below).
  5. The emitted G-code matches the flattened presets, key by key.

FOUND BY REVIEWING THIS FILE (2026-08-02) — gate 4 exists because of a real
failure it did not have. Asked for `battery_pocket:9`, OrcaSlicer split the job
across plate_1/2/3 (4 + 4 + 1 objects). This tool read plate_1 only: it printed
"plate total 269.18 g" for what was 4 of 9 parts, wrote a provenance record
claiming qty 9 at those numbers, and handed back one G-code path. Following it
gives you four parts and a record that says nine — silent truncation dressed as
a clean result, which is exactly what the rest of this file exists to prevent.

WHAT THIS DOES NOT DO. It does not send anything to a printer. It does not
invent an orientation: a part whose documented orientation is prose that names a
feature rather than an axis ("horn-seat face down", "crown/pad-down") is
REFUSED, with the prose quoted, rather than sliced in whatever pose the mesh
happens to sit in. Orientation is the one input where a plausible-looking wrong
answer costs a whole print. Parts that are printable but under-documented sit in
UNRESOLVED — refused, counted, and listed with what is missing, rather than
quietly dropped so the coverage line reads well.

Usage:
    python slice_plate.py cable_clip:24
    python slice_plate.py grommet_insert case_slot_grommet lead_notch_grommet:2
    python slice_plate.py --list
    python slice_plate.py --self-test

Requires: OrcaSlicer (ORCA env var overrides the default macOS path), trimesh,
numpy. Run it with the project venv: proj/.venv/bin/python.
"""

from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent

ORCA = pathlib.Path(
    os.environ.get("ORCA", "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer")
)
#: System profile root shipped inside the app bundle. These are the files whose
#: `inherits` chains the CLI will not resolve for you.
PROFILE_ROOT = ORCA.parent.parent / "Resources" / "profiles" / "BBL"
PROFILE_DIRS = ("machine", "process", "filament")

#: The printer. P1S has NO process profiles of its own — it uses the X1C ones
#: (30 of them name a P1S variant in `compatible_printers`); the P1P ones are
#: rejected with "process not compatible with printer".
MACHINE = "Bambu Lab P1S 0.4 nozzle"
PROCESS = "0.20mm Standard @BBL X1C"
#: P1S build volume, mm. Used only to fail early on a plate that cannot fit.
BED_XY = (256.0, 256.0)

#: TWO SEPARATE QUESTIONS, two thresholds. Conflating them is how a gate ends
#: up being loosened to make a legitimate part pass.
#:
#: 1. "Did the documented face actually land on the bed?" — an orientation
#:    error puts the part on an edge or a vertex, which measures under ~1 mm^2
#:    of downward-facing area (case_slot_grommet stood on its long thin edge:
#:    8.3 mm^2 when laid on +X). Every correctly-posed part measured here is
#:    >= 19 mm^2. 5.0 sits in that gap.
MIN_BED_CONTACT_MM2 = 5.0
#: 2. "Will it stay stuck?" — that is not an area question, it is an aspect
#:    ratio: height over the square root of contact area. Measured across the
#:    TPU set: skid_rail 0.09, cable_clip 0.42, lead_notch_grommet 0.71,
#:    grommet_insert 0.83 — and case_slot_grommet 2.53 standing on its thin
#:    edge, which is exactly the part that wants a brim. 1.5 separates them
#:    with room on both sides. Above it, the part must DECLARE brim=True in the
#:    registry; the tool will not quietly add one, because "this part needs a
#:    brim" is a fact about the part that belongs in the source, not a runtime
#:    convenience.
MAX_SLENDERNESS = 1.5
BRIM_WIDTH_MM = 3.0

#: Filament densities, g/cm^3, for the MODELLED per-part mass only. The plate
#: totals in the report come from the G-code, which is the measured number;
#: these are the solid-volume estimate and are labelled as such.
DENSITY = {"TPU 95A": 1.21, "PA6-CF": 1.19, "PETG-CF": 1.29}


class Material:
    """A material as this project prints it: which filament preset, and the
    process overrides from `print-batch.md` §2 that differ from stock."""

    def __init__(self, filament, walls, layer, infill, density_key, abrasive, note=""):
        self.filament = filament
        self.walls = walls
        self.layer = layer
        self.infill = infill
        self.density_key = density_key
        self.abrasive = abrasive
        self.note = note


#: Settings mirror `docs/checklists/print-batch.md` §2 "Slicer spec". Where that
#: table and a .scad header disagree about MATERIAL, this file does not choose —
#: `check_material_agreement()` fails and makes a human choose.
MATERIALS = {
    # TPU: 2 walls / 0.2 / 100% infill, flat, external spool (AMS will not feed it).
    "TPU 95A": Material(
        filament="Bambu TPU 95A HF @BBL P1S",
        walls=2, layer=0.20, infill="100%",
        density_key="TPU 95A", abrasive=False,
        note="external spool — the AMS cannot feed TPU",
    ),
    # PA6-CF: 4 walls / 0.2 / 40% gyroid. DRY 80C/10h before printing (§3).
    "PA6-CF": Material(
        filament="Bambu PA6-CF @BBL X1C",
        walls=4, layer=0.20, infill="40%",
        density_key="PA6-CF", abrasive=True,
        note="DRY 80C/10h first (§3); hardened nozzle — CF is abrasive",
    ),
    # PETG-CF: 3 walls / 0.25 / 20%.
    "PETG-CF": Material(
        filament="Bambu PETG-CF @BBL X1C",
        walls=3, layer=0.25, infill="20%",
        density_key="PETG-CF", abrasive=True,
        note="hardened nozzle — CF is abrasive",
    ),
}


class Part:
    """One printable STL.

    `down` is the model-frame face that goes on the bed, as an axis: "+Y" means
    "rotate until the +Y face is down". `None` means the mesh is already in its
    print pose (documented "flat", and the bed-contact measurement confirms it).
    `None` is a claim that gets checked; a prose orientation that names a
    FEATURE rather than an axis is not a claim this file can check, so it is
    stored as `manual` and refused with the prose quoted.
    """

    def __init__(self, stl, material, down=None, manual=None, supports="none",
                 doc="", scad=None, brim=False, infill=None):
        self.stl = stl
        self.material = material
        self.down = down
        self.manual = manual
        self.supports = supports
        self.doc = doc
        self.scad = scad
        self.brim = brim
        #: Per-part infill override. print-batch §2 carries exactly one
        #: ("tibia 25% — stress audit SF 35"); without this field the tool would
        #: quietly print it at the material default of 40%, which is the class of
        #: divergence the whole file exists to prevent.
        self.infill = infill


def _leg(p):
    return f"leg_v6/{p}"


def _chassis(p):
    return f"chassis/{p}"


#: THE REGISTRY. Every entry's `doc` is quoted from the part's own .scad header
#: or from print-batch §2 — not paraphrased, so a drift between this table and
#: the source is visible by reading. `scad` names the file whose `Print:` line
#: is checked against `material` at run time.
PARTS = {
    # ---- TPU 95A ---------------------------------------------------------
    "cable_clip": Part(
        _leg("cable_clip.stl"), "TPU 95A", down=None, scad=_leg("cable_clip.scad"),
        doc="Print: TPU 95A, flat (base down), 100% infill",
    ),
    "grommet_insert": Part(
        _leg("grommet_insert.stl"), "TPU 95A", down=None, scad=_leg("grommet_insert.scad"),
        doc="Print: TPU 95A flange-down, 100% infill",
    ),
    "knee_bumper": Part(
        _leg("knee_bumper.stl"), "TPU 95A",
        manual="U-opening-UP. Measured: no dominant flat face (-Z 381, +X 200, -X 199 mm^2) "
               "— it is a curved wrap, so the metric cannot pick for you. All 5 are already "
               "printed, so this is not blocking anything",
        scad=_leg("knee_bumper.scad"),
        doc="print-batch §2: knee_bumper U-opening-UP — names the feature, not an axis",
    ),
    "skid_rail": Part(
        _chassis("skid_rail.stl"), "TPU 95A", down=None, scad=_chassis("skid_rail.scad"),
        doc="Print: TPU 95A, flat on the key face, 100% infill",
    ),
    # MEASURED 2026-08-01, and the reason this tool paid for itself on its first
    # run. The .scad says "either flat face down", and the mesh's own pose stands
    # it on the 54 x 3.8 mm EDGE: 11.1 mm tall, 19.2 mm^2 of contact,
    # slenderness 2.53. Laying it on +Y gives 156.6 mm^2, 3.8 mm tall,
    # slenderness 0.30 — same part, 8x the grip and a third of the height.
    # All six faces measured: -Z 19.2 | +Z 43.2 | +Y 156.6 | -Y 64.8 | +-X 8.3.
    "case_slot_grommet": Part(
        _chassis("case_slot_grommet.stl"), "TPU 95A", down="+Y",
        scad=_chassis("case_slot_grommet.scad"),
        doc="Print: TPU 95A, flat (either flat face down, no supports), 100% infill "
            "— '+Y' is which 'either', measured: 156.6 mm^2 vs 19.2 as modelled",
    ),
    "lead_notch_grommet": Part(
        _chassis("lead_notch_grommet.stl"), "TPU 95A", down=None,
        scad=_chassis("lead_notch_grommet.scad"),
        doc="print-batch §2 TPU row: clips/rails/grommet flat",
    ),
    # ---- PA6-CF ----------------------------------------------------------
    # brim=True is measured, not habitual: 46.2 mm tall on 356.9 mm^2 of contact
    # is slenderness 2.44, the second-worst on the leg. The documented +Y pose is
    # NOT the flattest face (-Z gives 1162 mm^2, s=1.60) and is not being
    # second-guessed here — it is chosen for the load path and yoke-bridge
    # support access. Adhesion is a separate problem and a brim is its answer.
    "coax_R": Part(
        _leg("coax_R.stl"), "PA6-CF", down="+Y", supports="normal", brim=True,
        scad=_leg("coax.scad"),
        doc="Print: PA6-CF, rear face (+Y) down; supports under the yoke bridge span.",
    ),
    "coax_L": Part(
        _leg("coax_L.stl"), "PA6-CF", down="+Y", supports="normal", brim=True,
        scad=_leg("coax.scad"),
        doc="Print: PA6-CF, rear face (+Y) down; supports under the yoke bridge span.",
    ),
    # supports="normal" ADDED 2026-08-03, third instance of the same defaulted-field
    # bug (femur_R and femur_L were the first two). MEASURED in the +X-down pose:
    # 374.3 mm^2 of bed contact against 732.4 mm^2 of downward-facing area above the
    # bed, of which 664.5 mm^2 is under 45deg and genuinely needs support -- a shelf
    # of 619.5 mm^2 sitting only 0.5-2.0 mm up, plus 112.8 mm^2 at z 4.35-5.95.
    # Nearly twice as much overhang as bed contact.
    #
    # Cause, same as femur: coax_hfe_block.scad's header names the orientation
    # ("MATING FACE (x=SPLIT_X) DOWN") and says nothing about supports, so this
    # entry omitted supports= and took the default. Caught by Aiden looking at the
    # plate preview, not by any gate -- "none" is a legal value, so an omission and
    # a decision remain indistinguishable in this field.
    "coax_hfe_block": Part(
        _leg("coax_hfe_block.stl"), "PA6-CF", down="+X", supports="normal",
        scad=_leg("coax_hfe_block.scad"),
        doc="Print: PA6-CF, MATING FACE (x=SPLIT_X) DOWN; supports under the "
            "0.5-2.0mm shelf (665 mm^2 of sub-45deg overhang).",
    ),
    # -X, NOT +X. coax_hfe_block_L.scad is `mirror([1,0,0]) coax_hfe_block_R()`,
    # so the mating face lands on the opposite side — the same trap LA-3 records
    # for femur_L / tibia_L ("the Z-mirror flips which face is flat"). This entry
    # was first written as +X by copying the R part, and the bed-contact check
    # caught it: +X gives 54.4 mm^2 (s=2.14), -X gives 366.4 mm^2 (s=0.83) on the
    # same mesh. Copying an orientation across a mirror is the bug, every time.
    "coax_hfe_block_L": Part(
        _leg("coax_hfe_block_L.stl"), "PA6-CF", down="-X", supports="normal",
        scad=_leg("coax_hfe_block_L.scad"),
        doc="Print: PA6-CF, MATING FACE (x=SPLIT_X) DOWN — mirrored to -X on this part",
    ),
    # supports="normal" ADDED 2026-08-03. This entry had no supports= argument at
    # all, so it silently defaulted to "none" -- and femur has 555 mm^2 of FLAT
    # downward-facing area sitting 4.40 mm above the bed (x -15.9..14.8,
    # y -16.0..15.9), cantilevered off the SUB_X0/SUB_X1 ramp with nothing
    # anchoring its far end. It would have drooped.
    #
    # The requirement was never absent, only unwritten: #49 is literally
    # "femur: underside ramp-fill to cut support area -39% (#24/LA-6, partial)",
    # and femur.scad says the ramp "closes MOST of the old float, but NOT all of
    # it". Every OTHER leg part states its support need in its .scad header
    # (tibia "support pillars under the blade slab", coax "supports under the
    # yoke bridge span", shoulder "tree supports under the flange span") and got
    # the right value here. femur's header is silent, so the default won.
    #
    # "none" being a legal value is why no gate caught it: an omission and a
    # decision are indistinguishable in this field. If that recurs, make
    # supports= REQUIRED rather than defaulted.
    "femur_R": Part(
        _leg("femur_R.stl"), "PA6-CF", down=None, supports="normal",
        scad=_leg("femur.scad"),
        doc="Print: PA6-CF, flat on the -Z face; supports under the servo-pocket "
            "end, which floats 4.4 mm (SUB_X0=17 ramp).",
    ),
    # +Z, and the measurement says so rather than the prose: femur_R's documented
    # -Z face is 2772.5 mm^2, and on femur_L the SAME area appears at +Z
    # (2772 mm^2). An equal-area flat face on the opposite side is exactly what
    # LA-3's "180 deg about X" means, so this is the R pose mirrored, confirmed
    # numerically instead of assumed.
    "femur_L": Part(
        _leg("femur_L.stl"), "PA6-CF", down="+Z", supports="normal",
        scad=_leg("femur_L.scad"),
        doc="PRINT (LA-3): the Z-mirror flips which face is flat. Do NOT reuse the R orientation. "
            "+Z measured 2772 mm^2 = femur_R's -Z face.",
    ),
    # brim=True: 58.4 mm tall on 534 mm^2 = slenderness 2.53, the worst on the
    # leg, and -Z is already the best face available (no better pose to move to).
    "tibia_R": Part(
        _leg("tibia_R.stl"), "PA6-CF", down=None, supports="normal", brim=True, infill="25%",
        scad=_leg("tibia.scad"),
        doc="Print: PA6-CF, tab face (-Z) down; support pillars under the blade slab.",
    ),
    # Same mirror logic, and this one carries the receipt LA-3 warned about:
    # tibia_L at +Z is 534 mm^2 — identical to tibia_R's documented -Z face —
    # while tibia_L at -Z collapses to 41 mm^2 (slenderness 9.08), which is
    # LA-3's "lands on two ~25.4 mm^2 islands, tip-over risk" measured directly.
    # brim for the same reason tibia_R has one (58 mm tall, s=2.53).
    "tibia_L": Part(
        _leg("tibia_L.stl"), "PA6-CF", down="+Z", supports="normal", brim=True, infill="25%",
        scad=_leg("tibia_L.scad"),
        doc="PRINT (LA-3): the Z-mirror flips which face is flat; reusing the R pose gives "
            "41 mm^2 of contact instead of 534.",
    ),
    # "z0" IS an axis, so this one is derivable after all: the z=0 face down is
    # the as-modelled pose. Both large faces are flat (-Z 1528, +Z 1730 mm^2), so
    # the measurement alone could not choose — the .scad naming z0 is what picks
    # it, and the 1528 mm^2 confirms the named face is real.
    "knee_arm": Part(
        _leg("knee_arm.stl"), "PA6-CF", down=None, scad=_leg("knee_arm.scad"),
        doc="PRINT: PA6-CF, UNDERSIDE (horn-seat face, z0) DOWN",
    ),
    "strap": Part(
        _leg("strap.stl"), "PA6-CF", down=None, scad=_leg("strap.scad"),
        doc="PRINT: PA6-CF (in the leg batch) or PETG-CF, FLAT (2.5 plate on the bed)",
    ),
    "shoulder": Part(
        _leg("shoulder.stl"), "PA6-CF", down="+Z",
        # RESOLVED #259 (2026-07-31): the .scad header now reads "**+Z FACE DOWN** (deck top
        # on the bed)", so the prose this entry was refusing on no longer exists. Re-measured
        # 2026-08-03: +Z 7880 mm^2 / s0.90 against +X 856, +Y 772, -Z 358, -Y 64 (a knife
        # edge) -- 9.2x the runner-up, and the functionally right face too: +Z is DECK_Z1,
        # the surface shoulder_plate bolts flat against and all 8 plate heat-sets press into.
        # This entry stayed MANUAL for three days after the .scad was fixed, which is the
        # give-away shape: the resolution landed in one of the two files that had to agree.
        supports="tree", scad=_leg("shoulder.scad"),
        doc="Print: PA6-CF, rear face down; tree supports under the flange span. "
            "REAR end only since #377 — the front is `shoulder_sw1`.",
    ),
    "shoulder_sw1": Part(
        _leg("shoulder_sw1.stl"), "PA6-CF", down="+Z",
        # #377 (2026-08-15): the FRONT shoulder, identical to `shoulder` plus the
        # SW1 Contura panel hole. Same orientation and supports — the cutout is a
        # vertical slot in a wall that is already vertical in print space, so it
        # bridges nothing and needs no support of its own. Two parts, one .scad.
        supports="tree", scad=_leg("shoulder_sw1.scad"),
        doc="Print: PA6-CF, rear face down; tree supports under the flange span. "
            "FRONT end (carries SW1). Coupon-test the snap fit before this 165 g "
            "print — Carling says TEST CUT HOLE IN ACTUAL MATERIAL, and SW1_FIT "
            "in shoulder.scad is the knob for it.",
    ),
    "shoulder_plate": Part(
        _leg("shoulder_plate.stl"), "PA6-CF", down="+Y",
        # RESOLVED #253/#258: "back face" IS +Y -- the .scad's own FACE_Y1 = 21.75 is the bed
        # face. Re-measured 2026-08-03: +Y 1617 mm^2 / s0.49, next +Z 504, then +X/-X 74.
        # NB "back face down" was itself a correction of "horn-seat-down" (knee_arm's
        # doctrine copied onto a part whose flange sits 15.75 mm below that plane, so it
        # physically cannot rest there).
        scad=_leg("shoulder_plate.scad"),
        doc="Print: PA6-CF, back face DOWN (perfect seat on the horn face, knee_arm doctrine)",
    ),
    "shoulder_plate_L": Part(
        _leg("shoulder_plate_L.stl"), "PA6-CF", down="+Y",
        # RESOLVED #253/#258, and this pair does NOT swap: +Y 1610 mm^2 vs the R's 1617 --
        # the SAME face, because shoulder_plate_L is an X-mirror of a body that never crosses
        # x=0, making it a pure translation. Only coax_hfe_block and the Z-mirrored
        # femur_L/tibia_L actually flip. Never carry an orientation across a mirror on
        # assumption; measure the part in front of you.
        scad=_leg("shoulder_plate_L.scad"),
        doc="Print: PA6-CF, back face DOWN",
    ),
    "jetson_clamp_bar": Part(
        _chassis("jetson_clamp_bar.stl"), "PA6-CF", down=None,
        scad=_chassis("jetson_clamp_bar.scad"),
        doc="PRINT: PA6-CF, flat, ~4 g. print 2",
    ),
    "l2_adapter": Part(
        _chassis("l2_adapter.stl"), "PA6-CF", down=None, scad=_chassis("l2_adapter.scad"),
        doc="PRINT: PA6-CF or PETG-CF, FLAT (bottom on the bed), ~6 g",
    ),
    # "base-down" resolves to the as-modelled pose on the numbers: -Z is
    # 1647 mm^2 against 256 for the next-best face, a 6.4x margin. A wrong guess
    # here would not be subtle — it would land on 256 mm^2 or less and the
    # adhesion check would say so.
    "neck_bracket": Part(
        _chassis("neck_bracket.stl"), "PA6-CF", down=None,
        scad=_chassis("neck_bracket.scad"),
        doc="PRINT: base-down (deck face on the bed); the wall + gussets rise. PA6-CF.",
    ),
    "head": Part(
        _chassis("head.stl"), "PA6-CF",
        manual="CROWN/PAD-DOWN + tree supports. Measured: there is no good face — the best "
               "is +Z at 420 mm^2 and slenderness 2.37, every other face worse. Whatever "
               "pose is chosen, it needs a brim",
        supports="tree", scad=_chassis("head.scad"),
        doc="print-batch §2: head CROWN/PAD-DOWN, tree supports under the tilted-face + cheek overhangs",
    ),
    # supports="normal" 2026-08-03, found by the new overhang_checks(). MEASURED in
    # the declared FLOOR-DOWN pose: 639 mm^2 prints over air, ALL of it in the
    # z 25..40 band of a 38.8mm-tall part, spanning x -43..45 / y +-29.6 -- i.e. the
    # TOP FLANGE added by the battery-mount redesign.
    # ⚠️ This CONTRADICTS print-batch.md §2, which says battery_pocket prints
    # "FLOOR-DOWN opening-up, zero supports". That line predates the top-flange
    # redesign; the flange is what overhangs. Flagged for review rather than
    # silently trusted -- but 639 mm^2 floating 34.8mm will not print unsupported,
    # so the measurement wins over the stale prose.
    "battery_pocket": Part(
        _chassis("battery_pocket.stl"), "PA6-CF", supports="normal", down=None,
        scad=_chassis("battery_pocket.scad"),
        doc="print-batch §1 (#24): stays PA6-CF (belly crush guard over the LiPo). "
            "FLOOR-DOWN, opening-up, zero supports. NOTE: the .scad header still says PETG-CF.",
    ),
    # ---- PETG-CF ---------------------------------------------------------
    # "the flat TOP deck on the bed" — top face down is +Z, and +Z measures
    # 13384 mm^2 against 4967 for the next, so the prose and the geometry agree.
    "riser_bay": Part(
        _chassis("riser_bay.stl"), "PETG-CF", down="+Z",
        scad=_chassis("riser_bay.scad"),
        doc="PRINT: PETG-CF, DECK-FACE-DOWN (the flat top deck on the bed) — zero supports.",
    ),
    "floor_plate": Part(
        _chassis("floor_plate.stl"), "PETG-CF", down=None, scad=_chassis("floor_plate.scad"),
        doc="print-batch §2: floor_plate flat (zero supports)",
    ),
    # As neck_bracket: -Z 667 mm^2 vs 116 for the next-best, 5.7x.
    #
    # MATERIAL CORRECTED 2026-08-07 (#184): this was PETG-CF here while
    # jetson_case_mount.scad's own header already said PA6-CF (buried on a
    # continuation line, so this file's check_material_agreement() never saw
    # it either — the parser only reads the opening "Print:" line). Same shape
    # as the battery_pocket correction above: two files, one part, opposite
    # answers, resolved toward the part's own dated decision rather than
    # picked here. PA6-CF also matches jetson_clamp_bar.scad, which shares
    # this part's 250-510g case-retention load path and IS PA6-CF.
    "jetson_case_mount": Part(
        _chassis("jetson_case_mount.stl"), "PA6-CF", down=None,
        scad=_chassis("jetson_case_mount.scad"),
        doc="PRINT: PA6-CF, base-down (deck face on the bed); uprights rise (no overhangs now).",
    ),
    # Sits FLAT on the rear shoulder's deck, on the four M3x3.8 heat-set bores
    # shoulder.scad cuts for the FRONT shoulder's neck bracket and the REAR one
    # never uses. EVERY feature hangs off one face (the legs), so bezel-top-down
    # points all of them up and the unsupported area measures 0.0 mm^2. The
    # insert bosses were DELETED to keep it that way -- see the .scad header.
    "oled_tray": Part(
        _chassis("oled_tray.stl"), "PETG-CF", down="+Z",
        scad=_chassis("oled_tray.scad"),
        doc="PRINT: PETG-CF, BEZEL-FACE-DOWN (+Z on the bed) — the four legs are the "
            "only raised feature and they print upward, no supports.",
    ),
    "control_pod": Part(
        _chassis("control_pod.stl"), "PETG-CF",
        manual="COLUMN-FACE-DOWN — names the feature. Measured: +Z 1648 mm^2 (s0.91) "
               "dominates; next is -X 356 (s2.10)",
        supports="normal", scad=_chassis("control_pod.scad"),
        doc="PRINT: PETG-CF (or PA6-CF), COLUMN-FACE-DOWN; light supports under the deck + OLED overhangs",
    ),
}

#: STLs that are NOT printable parts: imported reference geometry, used for fit
#: checks and never sent to a bed.
#:
#: CORRECTED 2026-08-02 after review. The first version of this set also held
#: `oled_mount` (DELETED 2026-08-10, #35 — the OLED moved to `oled_tray`,
#: flat on the rear shoulder deck), `spacer`, `trunk`, `head_ear` and
#: `head_ear_L` — five parts
#: that ARE printed (oled_mount.scad: "PRINT: PETG/PA6-CF, foot-down, ~5 g";
#: spacer.scad: "4 needed + spares (print 8)"). They were in the exclusion list
#: for one reason: it made `--list`'s coverage line read "covers every STL".
#: That is the project's own green-but-uncovered pattern, committed by the tool
#: written to catch it. They now live in UNRESOLVED, which is refused and
#: counted, so the gap is visible instead of absorbed.
NOT_PRINTED = {
    "chassis/d456_ref.stl", "chassis/jetson_case_ref.stl", "chassis/l2_ref.stl",
    "chassis/power_board_model.stl",
}

#: Printable parts that CANNOT be sliced yet because something they need is not
#: recorded anywhere — not because the tool is missing a feature. Refused, and
#: reported by `--list`, so the set stays a visible to-do rather than a silent
#: omission. Each value says exactly what is missing and where it would go.
UNRESOLVED = {
    "spacer": (
        "chassis/spacer.stl",
        "no material recorded anywhere — the .scad header specifies M3x14, "
        "engagement and height but never says what to print it in, and "
        "print-batch §2 has no row for it. 8 are needed (4 + spares)."),
    "trunk": (
        "chassis/trunk.stl",
        "built by trunk_build.py (trimesh + manifold3d), NOT by OpenSCAD, so "
        "check_stl_fresh.py SKIPs it and gate 1 cannot cover this plate. "
        "Material/orientation for a part this size also need a decision that no "
        "doc records."),
    "head_ear": (
        "chassis/head_ear.stl",
        "material is deliberately OUTSIDE the three modelled here: print-batch "
        "§1 says plain PETG or ASA, NOT a CF filament, because the ear is a "
        "2.4/5 GHz antenna mast and carbon fibre detunes it (#32). Add a "
        "non-CF entry to MATERIALS first. Orientation is also yawed (EAR_YAW +45)."),
    "head_ear_L": (
        "chassis/head_ear_L.stl",
        "as head_ear — non-CF material (#32) and a yawed pose."),
}


# ---------------------------------------------------------------------------
# preset flattening
# ---------------------------------------------------------------------------

def _profile_index():
    idx = {}
    for d in PROFILE_DIRS:
        for f in glob.glob(str(PROFILE_ROOT / d / "*.json")):
            try:
                j = json.load(open(f))
            except Exception:
                continue
            if j.get("name"):
                idx[j["name"]] = f
    return idx


def flatten_preset(name, idx=None, seen=None):
    """Resolve a system preset's `inherits` chain into one standalone dict.

    The CLI does not do this. See the module docstring for what that costs.
    """
    idx = idx if idx is not None else _profile_index()
    seen = seen or []
    if name in seen:
        raise SystemExit(f"inherits cycle: {seen + [name]}")
    path = idx.get(name)
    if not path:
        raise SystemExit(f"unknown preset: {name!r}")
    leaf = json.load(open(path))
    parent = leaf.get("inherits")
    merged = flatten_preset(parent, idx, seen + [name]) if parent else {}
    merged.update(leaf)
    merged.pop("inherits", None)
    return merged


def _scalar(v):
    """Preset values are often 1-element lists (`"nozzle_temperature": ["230"]`)
    while the G-code header prints the scalar. Normalise both sides."""
    if isinstance(v, list):
        return str(v[0]) if v else ""
    return str(v)


# ---------------------------------------------------------------------------
# orientation
# ---------------------------------------------------------------------------

#: Rotation that brings the named model-frame face onto the bed. Derived, not
#: tabulated by hand: Ry(+90) maps +X to -Z, Rx(-90) maps +Y to -Z, etc.
_DOWN_ROT = {
    "+X": (90, [0, 1, 0]),
    "-X": (-90, [0, 1, 0]),
    "+Y": (-90, [1, 0, 0]),
    "-Y": (90, [1, 0, 0]),
    "+Z": (180, [1, 0, 0]),
    "-Z": None,
}


def orient(mesh, down):
    """Rotate `mesh` so face `down` is on the bed, then drop it onto z=0."""
    m = mesh.copy()
    if down not in _DOWN_ROT:
        raise SystemExit(f"unknown down-face {down!r}; expected one of {sorted(_DOWN_ROT)}")
    rot = _DOWN_ROT[down]
    if rot:
        ang, axis = rot
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), axis))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m


def bed_contact_mm2(mesh, band=0.05):
    """Area of downward-facing triangles resting in the bottom `band` mm.

    This is the measurement that turns "documented flat" into a checked claim.
    A part that lands on a curve, a corner, or two little islands reports a
    number near zero here even though the STL loads and slices perfectly.
    """
    normals = mesh.face_normals
    centroids = mesh.triangles_center
    flat_down = normals[:, 2] < -0.999
    on_bed = centroids[:, 2] < band
    return float(mesh.area_faces[flat_down & on_bed].sum())


def slenderness(mesh):
    """height / sqrt(bed contact). Dimensionless, so it compares a 0.24 g
    grommet with a 130 mm rail. See MAX_SLENDERNESS for the measured spread."""
    c = bed_contact_mm2(mesh)
    if c <= 0:
        return float("inf")
    return float((mesh.bounds[1][2] - mesh.bounds[0][2]) / c ** 0.5)


def face_report(mesh):
    """Every axis-aligned face-down option, measured.

    Printed when an orientation check fails, because "that pose is wrong" is
    only half an answer — the useful half is which pose is right, with the
    number that says so.
    """
    rows = []
    for d in ("-Z", "+Z", "+Y", "-Y", "+X", "-X"):
        om = orient(mesh, d)
        ext = om.bounds[1] - om.bounds[0]
        rows.append((d, bed_contact_mm2(om), float(ext[2]), slenderness(om)))
    return sorted(rows, key=lambda r: r[3])


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

#: WORD BOUNDARIES ARE LOad-BEARING. Without them `PLA` matches inside "plate"
#: and `ASA` inside any word containing it — and "plate" appears in plenty of
#: print headers ("plate on the bed"). The unbounded version returned PLA for
#: `// PRINT: plate flat on the bed`, which would have this gate reporting a
#: contradiction that does not exist, or agreeing with one that does.
_SCAD_MATERIAL = re.compile(r"\b(TPU\s*95A|PA6-CF|PETG-CF|PET-CF|PLA|ABS|ASA)\b", re.I)
_SCAD_USE = re.compile(r"^\s*use\s*<([^>]+)>")


def scad_material(scad_path, _depth=0):
    """The material named on the .scad's own `Print:` / `PRINT:` header line.

    Returns None when nothing in the chain names one. Only the FIRST material
    token is taken: headers like "PA6-CF or PETG-CF" state a preference order,
    and the preference is what the registry should agree with.

    FOLLOWS `use <...>` ONCE. The mirrored parts (`femur_L.scad`,
    `tibia_L.scad`, `coax_hfe_block_L.scad`, `shoulder_plate_L.scad`) are three
    lines that mirror the R geometry and never restate the material — so before
    this, the agreement gate silently skipped every left-hand part on the robot.
    A gate that quietly covers half of what it names is the failure mode this
    file is supposed to be about.
    """
    p = REPO / "hardware" / "cad" / scad_path
    if not p.exists():
        return None
    text = p.read_text()
    for line in text.splitlines()[:120]:
        if re.match(r"^//\s*PRINT\b|^//\s*Print:", line):
            m = _SCAD_MATERIAL.search(line)
            if m:
                t = m.group(1).upper().replace(" ", "")
                return {"TPU95A": "TPU 95A"}.get(t, t)
    if _depth == 0:
        for line in text.splitlines()[:60]:
            u = _SCAD_USE.match(line)
            if u:
                got = scad_material(str(pathlib.Path(scad_path).parent / u.group(1)), 1)
                if got:
                    return got
    return None


def check_material_agreement(parts):
    """Compare each part's .scad header against the registry.

    Returns (mismatches, unchecked). `battery_pocket` is why the first list
    exists — it really did have two answers in two files (#24 moved it to
    PA6-CF for LiPo puncture resistance; the .scad header still said PETG-CF).

    The SECOND list is why this function does not just return failures: a part
    whose header names no material is not agreement, it is absence of evidence,
    and reporting it as a pass is how a gate ends up covering less than its name
    claims. The caller prints the count.
    """
    bad, unchecked = [], []
    for name, part in parts:
        declared = scad_material(part.scad) if part.scad else None
        if declared is None:
            unchecked.append(name)
        elif declared != part.material:
            bad.append((name, part.scad, declared, part.material))
    return bad, unchecked


def check_fresh(dirs):
    """Run the STL-freshness gate (#176) over the directories in play.

    Slicing a stale STL is the one failure this whole file cannot detect on its
    own: the geometry loads, orients, slices and verifies perfectly — it is just
    not what the source says any more.
    """
    cmd = [sys.executable, str(HERE / "check_stl_fresh.py")] + [str(HERE / d) for d in sorted(dirs)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-3:]


# ---------------------------------------------------------------------------
# slice + verify
# ---------------------------------------------------------------------------

def slice_plate(stls, mat, supports, outdir, raw_filament=False, brim=False):
    """Invoke the slicer. Returns (gcode_path, argv, flattened presets)."""
    idx = _profile_index()
    machine = flatten_preset(MACHINE, idx)
    process = flatten_preset(PROCESS, idx)
    filament = flatten_preset(mat.filament, idx)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="slice_presets_"))
    if raw_filament:
        # --self-test only: hand the CLI the UNFLATTENED leaf, which is what
        # silently produced PLA settings under a TPU name.
        fil_path = pathlib.Path(idx[mat.filament])
    else:
        fil_path = tmp / "filament.json"
        fil_path.write_text(json.dumps(filament, indent=1))
    mach_path = tmp / "machine.json"
    proc_path = tmp / "process.json"
    mach_path.write_text(json.dumps(machine, indent=1))
    proc_path.write_text(json.dumps(process, indent=1))

    argv = [
        str(ORCA),
        "--load-settings", f"{mach_path};{proc_path}",
        "--load-filaments", str(fil_path),
        "--slice", "0",
        "--ensure-on-bed",
        "--arrange", "1",
        "--layer-height", str(mat.layer),
        "--wall-loops", str(mat.walls),
        "--sparse-infill-density", mat.infill,
        "--outputdir", str(outdir),
    ]
    if supports != "none":
        argv += ["--enable-support", "--support-type",
                 "tree(auto)" if supports == "tree" else "normal(auto)"]
    if brim:
        argv += ["--brim-type", "outer_only", "--brim-width", str(BRIM_WIDTH_MM)]
    argv += [str(s) for s in stls]

    r = subprocess.run(argv, capture_output=True, text=True)
    gcode = outdir / "plate_1.gcode"
    if r.returncode != 0 or not gcode.exists():
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        raise SystemExit("slicer failed:\n  " + "\n  ".join(tail))
    return gcode, argv, {"machine": machine, "process": process, "filament": filament}


_GCODE_KV = re.compile(r"^;\s*([a-z0-9_]+)\s*=\s*(.*)$")


def gcode_settings(path):
    out = {}
    for line in path.read_text(errors="ignore").splitlines():
        m = _GCODE_KV.match(line)
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


def verify_gcode(gc, mat, presets, brim=False, supports="none"):
    """Compare what the slicer EMITTED against what the presets SAID.

    The expectations are derived from the flattened presets and the overrides
    actually passed — nothing is hardcoded here, so this stays true when a
    preset changes. Returns a list of (key, expected, got) mismatches; empty
    means the plate is what was asked for.
    """
    want = {
        "filament_type": _scalar(presets["filament"].get("filament_type")),
        "nozzle_temperature": _scalar(presets["filament"].get("nozzle_temperature")),
        "hot_plate_temp": _scalar(presets["filament"].get("hot_plate_temp")),
        "printer_model": _scalar(presets["machine"].get("printer_model")),
        "layer_height": str(mat.layer),
        "wall_loops": str(mat.walls),
        "sparse_infill_density": mat.infill,
    }
    # Requested-only: verifying "no brim" or "no supports" would compare against
    # whatever the process profile defaults to, which is not this tool's claim.
    if brim:
        want["brim_type"] = "outer_only"
        want["brim_width"] = str(BRIM_WIDTH_MM)
    if supports != "none":
        want["enable_support"] = "1"
        want["support_type"] = "tree(auto)" if supports == "tree" else "normal(auto)"
    bad = []
    for k, exp in want.items():
        got = gc.get(k)
        if got is None:
            bad.append((k, exp, "<absent from G-code>"))
        elif not _same_value(exp, got):
            bad.append((k, exp, got))
    return bad


def _same_value(exp, got):
    """Compare a preset value with a G-code value.

    Numeric when both sides are numbers — the slicer prints `brim_width = 3`
    for a requested `3.0`, and a string compare would fail an identical
    setting. Everything else compares as text, so `PLA` vs `TPU` still fails
    loudly, which is the whole point.
    """
    a, b = exp.strip().strip('"'), got.strip().strip('"')
    if a.endswith("%") or b.endswith("%"):
        a, b = a.rstrip("%"), b.rstrip("%")
    try:
        return abs(float(a) - float(b)) < 1e-9
    except ValueError:
        return a == b


def gcode_object_count(path):
    """How many distinct objects the slicer actually put on this plate.

    Counts unique `; start printing object, unique label id: N` markers — NOT
    occurrences, which repeat once per layer (776 lines for 4 objects on the
    plate that exposed this).
    """
    txt = pathlib.Path(path).read_text(errors="ignore")
    return len(set(re.findall(r"start printing object, unique label id:\s*(\d+)", txt)))


def gcode_totals(gc, path):
    txt = path.read_text(errors="ignore")
    grams = re.search(r"total filament used \[g\]\s*=\s*([\d.]+)", txt) or \
        re.search(r"filament used \[g\]\s*=\s*([\d.]+)", txt)
    t = re.search(r"total estimated time:\s*([^\n;]+)", txt)
    model_t = re.search(r"model printing time:\s*([^;\n]+)", txt)
    return (float(grams.group(1)) if grams else None,
            (t.group(1).strip() if t else None),
            (model_t.group(1).strip() if model_t else None))


def slicer_version():
    """`--help`'s banner, not its first line — the first line is a boost log
    stamp, which is what the record captured before this was fixed."""
    out = subprocess.run([str(ORCA), "--help"], capture_output=True, text=True).stdout
    m = re.search(r"(OrcaSlicer|BambuStudio)[- ]([0-9][0-9.]*)", out)
    return f"{m.group(1)} {m.group(2)}" if m else "unknown"


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def git_head():
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() or "unknown"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_spec(spec):
    name, _, qty = spec.partition(":")
    return name, int(qty) if qty else 1


def cmd_list():
    print(f"{'part':22s} {'material':9s} {'orientation':38s} supports")
    for name in sorted(PARTS):
        p = PARTS[name]
        o = f"MANUAL — {p.manual}" if p.manual else (p.down or "as modelled")
        print(f"{name:22s} {p.material:9s} {o[:38]:38s} {p.supports}")

    print("\nUNRESOLVED — printable, refused, and why (this is a to-do list):")
    for name in sorted(UNRESOLVED):
        why = UNRESOLVED[name][1]
        print(f"  {name}:")
        for chunk in (why[i:i + 74] for i in range(0, len(why), 74)):
            print(f"      {chunk}")

    seen = {p.stl for p in PARTS.values()} | {v[0] for v in UNRESOLVED.values()}
    everything = {f"{d}/{os.path.basename(f)}"
                  for d in ("leg_v6", "chassis")
                  for f in glob.glob(str(HERE / d / "*.stl"))}
    missing = everything - seen - NOT_PRINTED
    print()
    if missing:
        print("NOT IN REGISTRY (and not marked reference-only):")
        for m in sorted(missing):
            print("  ", m)

    # Coverage is stated as three numbers, not one adjective. "covers
    # everything" was true only because five printable parts had been moved
    # into the exclusion list, which is the failure this line now refuses to
    # hide.
    _, unchecked = check_material_agreement([(n, p) for n, p in PARTS.items()])
    manual = [n for n, p in PARTS.items() if p.manual]
    print(f"{len(PARTS)} registered ({len(manual)} refused for prose orientation), "
          f"{len(UNRESOLVED)} unresolved, {len(NOT_PRINTED)} reference-only, "
          f"{len(missing)} unaccounted.")
    print(f"material gate covers {len(PARTS) - len(unchecked)}/{len(PARTS)}; "
          f"no material named in the .scad of: {', '.join(sorted(unchecked)) or 'none'}")
    return 0


def cmd_self_test(outdir):
    """Negative control: prove verify_gcode() actually FIRES.

    Slices a real part with the raw, unflattened filament preset — the exact
    condition that produced TPU-named/PLA-behaving G-code. If the verification
    comes back clean, the guard is decorative and this exits non-zero.
    """
    part = PARTS["lead_notch_grommet"]
    mat = MATERIALS[part.material]
    mesh = trimesh.load(HERE / part.stl, force="mesh")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="selftest_"))
    oriented = tmp / "part.stl"
    orient(mesh, part.down or "-Z").export(oriented)

    print("self-test: slicing with the RAW (unflattened) filament preset ...")
    gcode, _, presets = slice_plate([oriented], mat, "none", tmp, raw_filament=True)
    bad = verify_gcode(gcode_settings(gcode), mat, presets)
    if not bad:
        print("FAIL: raw preset sliced clean — verify_gcode() did not fire, "
              "so it is not protecting anything.")
        return 1
    print("PASS: guard fired on the known-bad input:")
    for k, exp, got in bad:
        print(f"    {k}: preset says {exp!r}, G-code says {got!r}")
    print("  (this is the failure that ships TPU at PLA temperatures)")
    return 0


#: Unsupported-overhang gate (2026-08-03). WHY: `supports` defaults to "none",
#: so an OMISSION and a DECISION are indistinguishable in that field, and no gate
#: could tell them apart. That defaulted three times in one day -- femur_R,
#: femur_L, coax_hfe_block -- each caught only by a human looking at the plate
#: preview. Making the field REQUIRED was the obvious fix and the wrong one: 16 of
#: 20 entries relied on the default, so it would have forced 16 guesses.
#:
#: Measure it instead. For each part, in its DECLARED orientation, find the
#: downward-facing facets under 45 deg whose ray straight down reaches the bed
#: without hitting part material -- i.e. facets that genuinely print over air.
#:
#: THE FIRST VERSION OF THIS WAS WRONG and is worth recording. It counted every
#: downward facet above the bed, with no ray cast, and flagged four extra parts:
#: knee_arm 287, riser_bay 505, neck_bracket 160, skid_rail 119 mm^2. Ray-casting
#: drops those to 33 / 88 / 9 / 60 -- over-reported by up to 17x, because a
#: downward facet sitting on top of solid material (a bolt-hole ceiling, a 0.5mm
#: step) is not an overhang. knee_arm printed fine with no supports the day
#: before, which is the corroboration. Proximity is not containment; measure the
#: predicate you actually mean.
MIN_DROP_MM = 1.0        #: below this it is first-layer noise, not an overhang
MAX_UNSUPPORTED_MM2 = 150.0
#: 150 sits in a MEASURED gap: the largest correctly-"none" part is riser_bay at
#: 88 mm^2, the smallest part that legitimately declares supports is shoulder at
#: 461. Room on both sides. (battery_pocket lands at 639 while declaring "none" --
#: that is the defect this gate exists to catch, not a reason to move the line.)


def unsupported_area(mesh):
    """(area_mm2, max_drop_mm) of facets that print over air down to the bed."""
    n = mesh.face_normals
    c = mesh.triangles_center
    a = mesh.area_faces
    ang = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
    cand = np.where((n[:, 2] < 0) & (ang < 45) & (c[:, 2] > MIN_DROP_MM))[0]
    if len(cand) == 0:
        return 0.0, 0.0
    org = c[cand] + np.array([0, 0, -1e-3])
    dirs = np.tile([0, 0, -1.0], (len(cand), 1))
    hit = mesh.ray.intersects_any(ray_origins=org, ray_directions=dirs)
    free = cand[~hit]
    if len(free) == 0:
        return 0.0, 0.0
    return float(a[free].sum()), float(c[free][:, 2].max())


def overhang_checks():
    """Does every part that prints over air actually declare supports?"""
    print('-- unsupported overhang vs declared supports --')
    bad = False
    for name in sorted(PARTS):
        part = PARTS[name]
        if part.manual:
            continue
        mesh = trimesh.load(part.stl, force='mesh', process=False)
        mesh = orient(mesh, part.down) if part.down else mesh.copy()
        if not part.down:
            mesh.apply_translation([0, 0, -mesh.bounds[0][2]])
        area, drop = unsupported_area(mesh)
        if part.supports == "none" and area > MAX_UNSUPPORTED_MM2:
            bad = True
            print(f'FAIL  {name}: {area:.0f} mm^2 prints over air (max drop '
                  f'{drop:.1f} mm) but supports="none". Either declare supports '
                  f'or explain why this face is acceptable.')
        elif area > MAX_UNSUPPORTED_MM2:
            print(f'   OK    {name}: {area:.0f} mm^2 over air (drop {drop:.1f} mm), '
                  f'supports="{part.supports}"')
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("parts", nargs="*", help="part[:qty] ... (see --list)")
    ap.add_argument("--outdir", default=str(HERE / "slices"))
    ap.add_argument("--list", action="store_true", help="registry + coverage, then exit")
    ap.add_argument("--self-test", action="store_true", help="prove the verify step fires")
    ap.add_argument("--no-fresh-check", action="store_true",
                    help="skip the STL freshness gate (the record is stamped UNVERIFIED)")
    ap.add_argument("--no-record", action="store_true", help="do not write a provenance record")
    args = ap.parse_args()

    if args.list:
        rc = cmd_list()
        return 1 if overhang_checks() else (rc or 0)
    if not ORCA.exists():
        raise SystemExit(f"OrcaSlicer not found at {ORCA} (set ORCA=/path/to/binary)")

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if args.self_test:
        return cmd_self_test(outdir)
    if not args.parts:
        ap.error("give at least one part, or --list")

    specs = [parse_spec(s) for s in args.parts]
    blocked = [n for n, _ in specs if n in UNRESOLVED]
    if blocked:
        print("REFUSED — printable, but something it needs is not recorded anywhere:")
        for n in blocked:
            print(f"  {n}: {UNRESOLVED[n][1]}")
        return 2
    unknown = [n for n, _ in specs if n not in PARTS]
    if unknown:
        raise SystemExit(f"not in the registry: {unknown} (try --list)")
    chosen = [(n, PARTS[n], q) for n, q in specs]

    manual = [(n, p.manual, p.doc) for n, p, _ in chosen if p.manual]
    if manual:
        print("REFUSED — orientation is documented as prose, not as an axis:")
        for n, why, doc in manual:
            print(f"  {n}: {why}\n      doc: {doc}")
        print("\nSlicing these at the mesh's own pose would be a guess. Add an axis to\n"
              "the registry (and to the .scad header) once it is measured on the plate.")
        return 2

    mats = {p.material for _, p, _ in chosen}
    if len(mats) > 1:
        raise SystemExit(f"one plate, one filament: asked for {sorted(mats)}")
    mat = MATERIALS[mats.pop()]
    # Infill is a plate-level CLI override, so parts wanting different infills
    # cannot share a plate. Saying so is better than silently printing one of
    # them at the other's density (tibia is 25%, all other PA6-CF is 40%).
    infills = {p.infill or mat.infill for _, p, _ in chosen}
    if len(infills) > 1:
        raise SystemExit(
            f"one plate, one infill: asked for {sorted(infills)} — "
            f"print-batch §2 gives tibia its own 25% (stress audit SF 35)")
    mat = copy.copy(mat)
    mat.infill = infills.pop()
    sups = {p.supports for _, p, _ in chosen}
    if len(sups) > 1:
        raise SystemExit(f"mixed support settings on one plate: {sorted(sups)}")
    supports = sups.pop()

    # --- gate 1: the STLs are what their .scad says ------------------------
    fresh_ok, fresh_tail = True, ["skipped"]
    if not args.no_fresh_check:
        dirs = {p.stl.split("/")[0] for _, p, _ in chosen}
        fresh_ok, fresh_tail = check_fresh(dirs)
        if not fresh_ok:
            print("STL FRESHNESS GATE FAILED — refusing to slice:")
            for line in fresh_tail:
                print("   ", line)
            print("Run hardware/cad/leg_v6/build_all.sh (or the chassis build) first.")
            return 3

    # --- gate 2: nobody disagrees about the material -----------------------
    bad_mat, unchecked_mat = check_material_agreement([(n, p) for n, p, _ in chosen])
    if bad_mat:
        print("MATERIAL CONTRADICTION — the .scad header and the registry disagree:")
        for n, scad, declared, want in bad_mat:
            print(f"  {n}: {scad} says {declared}, registry says {want}")
        print("Fix the source of truth, do not pick one here.")
        return 4
    if unchecked_mat:
        # Not a failure — an honest statement of what gate 2 did NOT cover on
        # this plate. Silence here would read as "material agreed".
        print(f"NOTE: material unchecked for {len(unchecked_mat)} part(s) — their .scad "
              f"header names no material: {', '.join(unchecked_mat)}")

    # --- orient, and CHECK the orientation ---------------------------------
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="slice_models_"))
    loaded, contacts, slenders = [], {}, {}
    for name, part, qty in chosen:
        mesh = trimesh.load(HERE / part.stl, force="mesh")
        om = orient(mesh, part.down or "-Z")
        area = bed_contact_mm2(om)
        slim = slenderness(om)
        contacts[name], slenders[name] = area, slim

        if area < MIN_BED_CONTACT_MM2:
            print(f"ORIENTATION CHECK FAILED — {name}: only {area:.1f} mm^2 of flat face "
                  f"lands on the bed (need >= {MIN_BED_CONTACT_MM2:.0f}). That is an "
                  f"edge or a corner, not a face.")
            print(f"  documented as: {part.doc}")
            print("\n  every face measured, best first:")
            print(f"    {'down':>5s} {'contact mm^2':>13s} {'height mm':>10s} {'slenderness':>12s}")
            for d, c, h, s in face_report(mesh):
                print(f"    {d:>5s} {c:>13.1f} {h:>10.1f} {s:>12.2f}")
            return 5

        if slim > MAX_SLENDERNESS and not part.brim:
            print(f"ADHESION CHECK FAILED — {name}: slenderness {slim:.2f} "
                  f"(> {MAX_SLENDERNESS}) on {area:.1f} mm^2 of contact, "
                  f"{om.bounds[1][2] - om.bounds[0][2]:.1f} mm tall.")
            print(f"  documented as: {part.doc}")
            print("\n  Either set brim=True on this part in the registry, or pick a better\n"
                  "  face — every option measured, best first:")
            print(f"    {'down':>5s} {'contact mm^2':>13s} {'height mm':>10s} {'slenderness':>12s}")
            for d, c, h, s in face_report(mesh):
                print(f"    {d:>5s} {c:>13.1f} {h:>10.1f} {s:>12.2f}")
            return 5
        fx, fy = (om.bounds[1] - om.bounds[0])[:2]
        if fx > BED_XY[0] or fy > BED_XY[1]:
            raise SystemExit(f"{name} footprint {fx:.0f}x{fy:.0f} exceeds the P1S bed")
        p = tmp / f"{name}.stl"
        om.export(p)
        loaded.append((name, part, qty, p, om))

    stls, clones = [], []
    for name, part, qty, p, _ in loaded:
        stls.append(p)
        clones.append(str(qty))
    argv_extra = ["--clone-objects", ",".join(clones)] if any(c != "1" for c in clones) else []

    # --- slice -------------------------------------------------------------
    # plate_*.gcode only — this is the tool's own output namespace. The first
    # version wiped every *.gcode in --outdir, which is somebody else's file if
    # --outdir is ever pointed somewhere shared.
    for f in outdir.glob("plate_*.gcode"):
        f.unlink()
    # Brim is a plate-level setting: if any part on the plate declared one, the
    # plate gets one. Erring toward the brim is the cheap direction.
    brim = any(p.brim for _, p, _ in chosen)
    gcode, argv, presets = slice_plate(stls, mat, supports, outdir, brim=brim)
    if argv_extra:  # re-slice with clones once the single-copy plate is known good
        argv = argv[:-len(stls)] + argv_extra + [str(s) for s in stls]
        r = subprocess.run(argv, capture_output=True, text=True)
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
            raise SystemExit("slicer failed on the cloned plate:\n  " + "\n  ".join(tail))

    # --- gate 3: everything asked for is ON THE PLATE ----------------------
    # FOUND BY REVIEW 2026-08-02, and it is the failure this tool would most
    # have deserved. Asked for `battery_pocket:9`, the slicer silently split the
    # job across plate_1/2/3 (4 + 4 + 1 objects) and this code read plate_1
    # only: it reported "plate total 269.18 g" for what is 4 of 9 parts, wrote a
    # provenance record claiming qty 9 at those numbers, and printed one G-code
    # path. Following it gives you four parts and a record that says nine.
    plates = sorted(outdir.glob("plate_*.gcode"))
    want_objects = sum(q for _, _, q in chosen)
    if len(plates) > 1:
        print(f"DOES NOT FIT ONE PLATE — the slicer produced {len(plates)} plates:")
        for f in plates:
            print(f"  {f.name}: {gcode_object_count(f)} objects")
        print(f"\nAsked for {want_objects} object(s). A 'plate' is the unit this tool "
              f"records and\nverifies, so it will not hand back the first one as if it "
              f"were the job.\nSplit the request into plates that fit.")
        return 7
    got_objects = gcode_object_count(gcode)
    if got_objects != want_objects:
        print(f"OBJECT COUNT MISMATCH — asked for {want_objects}, the G-code contains "
              f"{got_objects}.")
        print("  Something was dropped or duplicated between the request and the plate.")
        return 7

    # --- gate 4: the G-code is what the presets said -----------------------
    gc = gcode_settings(gcode)
    bad = verify_gcode(gc, mat, presets, brim=brim, supports=supports)
    if bad:
        print("SETTINGS VERIFICATION FAILED — the G-code is not what the presets say:")
        for k, exp, got in bad:
            print(f"  {k}: expected {exp!r}, G-code has {got!r}")
        print("\nThis is the failure mode this tool exists for: the header can NAME the\n"
              "right filament while the nozzle runs another material's temperature.")
        return 6

    grams, est, model_t = gcode_totals(gc, gcode)

    # --- report ------------------------------------------------------------
    print(f"\nPLATE  {mat.filament}  |  {mat.walls} walls / {mat.layer} mm / {mat.infill}"
          f"  |  supports: {supports}")
    print(f"       nozzle {gc.get('nozzle_temperature')} C, bed {gc.get('hot_plate_temp')} C, "
          f"{gc.get('printer_model')}")
    if mat.note:
        print(f"       note: {mat.note}")
    print()
    print(f"{'part':22s} {'qty':>4s} {'solid g ea':>11s} {'bed contact':>12s} {'slend':>6s}  orientation")
    rho = DENSITY[mat.density_key]
    for name, part, qty, p, om in loaded:
        modelled = om.volume / 1000.0 * rho
        print(f"{name:22s} {qty:>4d} {modelled:>11.2f} {contacts[name]:>10.0f} mm^2 "
              f"{slenders[name]:>6.2f}  {part.down or 'as modelled'}"
              f"{'  +brim' if part.brim else ''}")
    print()
    print(f"  plate total (from G-code): {grams} g   model time {model_t}   total est {est}")
    print(f"  ('solid g ea' is mesh volume x {rho} g/cm^3 — the SOLID part. The plate total is")
    print(f"   the slicer's, at {mat.infill} infill, and is the number to trust.)")
    print(f"  gcode: {gcode}")
    print(f"  STL freshness gate: {'PASSED' if fresh_ok else 'SKIPPED — record marked UNVERIFIED'}")
    if mat.abrasive:
        print("  ⚠️  abrasive filament — hardened nozzle required")

    # --- provenance --------------------------------------------------------
    if not args.no_record:
        rec = {
            "git_head": git_head(),
            "stl_fresh_verified": bool(fresh_ok and not args.no_fresh_check),
            "slicer": slicer_version(),
            "machine": MACHINE, "process": PROCESS, "filament": mat.filament,
            "overrides": {"layer_height": mat.layer, "wall_loops": mat.walls,
                          "sparse_infill_density": mat.infill, "supports": supports,
                          "brim": brim},
            "verified_gcode_keys": {k: gc.get(k) for k in
                                    ("filament_type", "nozzle_temperature", "hot_plate_temp",
                                     "layer_height", "wall_loops", "sparse_infill_density",
                                     "printer_model")},
            "plate_grams": grams, "estimated_time": est,
            "parts": [{"name": n, "qty": q, "stl": p.stl,
                       "stl_sha256_16": sha256(HERE / p.stl),
                       "scad_sha256_16": sha256(REPO / "hardware" / "cad" / p.scad) if p.scad else None,
                       "bed_contact_mm2": round(contacts[n], 1),
                       "orientation": p.down or "as modelled"}
                      for n, p, q, _, _ in loaded],
            "gcode_sha256_16": sha256(gcode),
        }
        recdir = REPO / "docs" / "print-records"
        recdir.mkdir(parents=True, exist_ok=True)
        stem = "-".join(n for n, _, _, _, _ in loaded)[:60]
        out = recdir / f"{rec['git_head']}-{stem}.json"
        out.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"  record: {out.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
