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
import numpy as np
import trimesh

TRUNK_STL = ('/Users/afox/codebases/NOVA/original_body_files/'
             'SM3_Frame_ChassisTrunk.stl')
OUT = 'trunk.stl'

# ---- SET 1: battery mount, 6x M3 clearance through the floor ----------
# battery_pocket.scad BOSS_X=[-40,0,40], BOSS_Y=27.5, M3_CLEAR=3.4.
# AUD-11 fix, 2026-07-10 (was 26.5): the old axis put the nut-trap bore
# flush on the cavity wall's outer face -- a 0.0mm breach into the LiPo
# bay. Moved +1.0 outboard to seal a >=1.5mm wall for the new heat-set
# mount; this bore must keep tracking BOSS_Y 1:1.
BATT_BOSS_X = [-40, 0, 40]
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
FOOT_CSK_D = 6.4
FOOT_CSK_H = (FOOT_CSK_D - FOOT_CLEAR_D) / 2  # 1.5mm at 90deg
FOOT_BORE_H = 8

# SET 3 (shoulder-flange end-wall clearance) is ALREADY STOCK -- see
# trunk.scad's header comment + measure_trunk.py + check_fit.py's new
# alignment gate. Nothing to cut here.


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
