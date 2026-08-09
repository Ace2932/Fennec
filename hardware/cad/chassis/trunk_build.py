#!/usr/bin/env python3
"""Build trunk.stl — the DERIVED trunk (stock Nova-SM3 geometry, PRINTED
fastener holes). See trunk.scad for the full per-hole documentation/sourcing
(BATT_*/FOOT_XY constants there are the source of truth this script mirrors).

WHY trimesh, not OpenSCAD: trunk.scad's `import()+difference()` renders fast
(~0.15s) and OpenSCAD's own CGAL check reports "manifold, NoError" -- but the
exported STL is NOT watertight under trimesh's stricter edge-manifold check
(mesh_health.py): 8 degenerate near-zero-area sliver triangles appear at the
side-wall-top notch edge (x~13-16, y~+/-49.27, z~28.97) -- nowhere near any
of the 10 modeled holes (battery holes at bx +/-40/0, foot holes at
+/-59.5/+/-42). This is OpenSCAD's Nef-polyhedron -> STL re-triangulation
touching the WHOLE mesh during any boolean, a known fragility on complex
imported meshes (12446 stock faces, genus 152). Falling back to the plan's
documented alternative: boolean the ORIGINAL watertight mesh directly via
trimesh + the manifold3d engine (built for guaranteed-manifold output on
manifold input), which is confirmed installed in .venv. Run:
  ../../../.venv/bin/python trunk_build.py
"""
import pathlib
import re
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cad_assets import asset  # noqa: E402  (path insert must come first)

# The stock trunk, already vendored for the URDF at nova_description/meshes.
# chassis/check_fit.py imports this module, so the absolute path this replaces
# pinned the whole chassis gate to one machine (#166).
TRUNK_STL = str(asset('SM3_Frame_ChassisTrunk.stl'))
OUT = 'trunk.stl'

# ---- SET 1: battery mount, 6x M3 clearance through the floor ----------
# battery_pocket.scad BOSS_X=[-40,0,40], BOSS_Y=27.5, M3_CLEAR=3.4.
# AUD-11 fix, 2026-07-10 (was 26.5): the old axis put the nut-trap bore
# flush on the cavity wall's outer face -- a 0.0mm breach into the LiPo
# bay. Moved +1.0 outboard to seal a >=1.5mm wall for the new heat-set
# mount; this bore must keep tracking BOSS_Y 1:1.
BATT_BOSS_X = [-35, 0, 40]   # #68 fix 2026-07-12: -x col -40->-35 (== floor_plate BAT_X + battery_pocket BOSS_X)
BATT_BOSS_Y = 27.5
BATT_CLEAR_D = 3.4
BATT_BORE_Z0 = -2
BATT_BORE_H = 8

# ---- SET 2: shoulder flange-foot CSK, 4x M3x14 through the floor ------
# leg_v6/shoulder.scad FOOT_BOLT_X=42, FOOT_BOLT_Y=-81.7 (shoulder-local),
# transformed via the front/rear S2T placements (check_fit.py) ->
# trunk (x=+/-59.5, y=+/-42).
FOOT_XY = [(59.5, 42), (59.5, -42), (-59.5, 42), (-59.5, -42)]
FOOT_CLEAR_D = 3.4
FOOT_CSK_D = 6.0   # 6.4 -> 6.0 (#301/#321); MUST match trunk.scad, asserted below
FOOT_CSK_H = (FOOT_CSK_D - FOOT_CLEAR_D) / 2  # 1.3mm at 90deg
FOOT_BORE_H = 8

# SET 3 (shoulder-flange end-wall clearance) is ALREADY STOCK -- see
# trunk.scad's header comment + measure_trunk.py + check_fit.py's new
# alignment gate. Nothing to cut here.


def assert_mirrors_scad():
    """Fail loudly if the constants above have drifted from trunk.scad's.

    WHY THIS EXISTS (#321). The docstring says this script "mirrors" trunk.scad,
    and that mirroring was a HAND COPY that nothing checked:

      * trunk.stl -- the part that gets printed -- is built HERE, in Python.
      * check_hole_breakout.py parses trunk.SCAD to find the holes it tests.
      * check_stl_fresh.py has SKIP = {"trunk.stl"} (trunk.scad renders only a
        preview), so it never compared the two either.

    So the gate could pass on one geometry while the printed part had another.
    That is not hypothetical: taking FOOT_CSK_D 6.4 -> 6.0 in trunk.scad alone
    left trunk.stl BYTE-IDENTICAL while the breakout gate started reporting the
    new r=3.00 hole and went green. A false pass, caught only because the STL
    hash did not move. Two copies of a dimension with no check between them is
    the whole bug; this is the check.

    Regex-matched rather than reading the .scad symbolically: it only has to
    catch a NUMBER changing on one side, and a parser that can be wrong in its
    own right would just move the problem.
    """
    scad = (pathlib.Path(__file__).parent / 'trunk.scad').read_text()
    mirrored = {
        'FOOT_CLEAR_D': FOOT_CLEAR_D,
        'FOOT_CSK_D': FOOT_CSK_D,
        'FOOT_BORE_H': FOOT_BORE_H,
        'BATT_CLEAR_D': BATT_CLEAR_D,
        'BATT_BORE_Z0': BATT_BORE_Z0,
        'BATT_BORE_H': BATT_BORE_H,
        'BATT_BOSS_Y': BATT_BOSS_Y,
    }
    bad = []
    for name, here in mirrored.items():
        hit = re.search(rf'^\s*{name}\s*=\s*(-?[\d.]+)\s*;', scad, re.M)
        if hit is None:
            bad.append(f'{name}: not found in trunk.scad (renamed or removed?)')
        elif abs(float(hit.group(1)) - float(here)) > 1e-9:
            bad.append(f'{name}: trunk.scad has {hit.group(1)}, this file has {here}')
    # FOOT_XY is a list, so compare it as text rather than as one number.
    hit = re.search(r'^\s*FOOT_XY\s*=\s*\[(.+?)\]\s*;', scad, re.M | re.S)
    if hit is None:
        bad.append('FOOT_XY: not found in trunk.scad')
    else:
        nums = [float(v) for v in re.findall(r'-?[\d.]+', hit.group(1))]
        mine = [float(v) for xy in FOOT_XY for v in xy]
        if nums != mine:
            bad.append(f'FOOT_XY: trunk.scad has {nums}, this file has {mine}')
    if bad:
        raise SystemExit(
            'trunk_build.py has DRIFTED from trunk.scad (#321):\n  '
            + '\n  '.join(bad)
            + '\n\ntrunk.stl is built from THIS file, but check_hole_breakout.py'
              ' tests the holes it parses out of trunk.scad. While these two'
              ' disagree, a green gate says nothing about the printed part.'
              ' Fix both, then re-run.')
    print(f'constants mirror trunk.scad: {len(mirrored) + 1} checked, all agree')


def straight_bore(d, z0, h, sections=48):
    return trimesh.creation.cylinder(
        radius=d / 2, height=h, sections=sections,
        transform=trimesh.transformations.translation_matrix([0, 0, z0 + h / 2]))


def csk_bore(r_big, r_small, csk_h, bore_h, sections=48):
    """Revolve a trapezoid profile: 90deg countersink taper r_big->r_small
    over csk_h (mouth at z=0), then a straight bore at r_small for bore_h
    more. Single watertight solid."""
    prof = np.array([
        [0, 0], [r_big, 0], [r_small, csk_h],
        [r_small, csk_h + bore_h], [0, csk_h + bore_h],
    ])
    return trimesh.creation.revolve(prof, sections=sections)


def main():
    assert_mirrors_scad()
    trunk = trimesh.load(TRUNK_STL)
    assert trunk.is_watertight, 'stock trunk mesh is not watertight -- abort'

    tools = []
    for bx in BATT_BOSS_X:
        for sy in (1, -1):
            m = straight_bore(BATT_CLEAR_D, BATT_BORE_Z0, BATT_BORE_H)
            m.apply_translation([bx, sy * BATT_BOSS_Y, 0])
            tools.append(m)

    for (wx, wy) in FOOT_XY:
        m = csk_bore(FOOT_CSK_D / 2, FOOT_CLEAR_D / 2, FOOT_CSK_H, FOOT_BORE_H)
        m.apply_translation([wx, wy, 0])
        tools.append(m)

    print(f'trunk: watertight={trunk.is_watertight} faces={len(trunk.faces)}')
    print(f'subtracting {len(tools)} tool solids (6 battery + 4 foot-CSK)')

    result = trimesh.boolean.difference([trunk] + tools, engine='manifold')
    result.update_faces(result.nondegenerate_faces())
    result.remove_unreferenced_vertices()

    bodies = result.split(only_watertight=False)
    print(f'result: watertight={result.is_watertight} bodies={len(bodies)} '
          f'volume={result.volume / 1000:.1f}cm3 euler={result.euler_number}')
    assert result.is_watertight, 'boolean result is not watertight'
    assert len(bodies) == 1, f'boolean result split into {len(bodies)} bodies'
    assert result.volume > 0

    result.export(OUT)
    print(f'{OUT} written, bounds={np.round(result.bounds, 2).tolist()}')


if __name__ == '__main__':
    main()
