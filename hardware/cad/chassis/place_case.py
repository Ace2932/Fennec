#!/usr/bin/env python3
"""Jetson official-case PLACEMENT STUDY (gates the whole repackaging).

Computes the case world AABB for the CHOSEN placement + clearances to every
neighbour. Decision context (caliper data 2026-07-07, dimensions.md 7748bd3):

  * Case = 110.3 (X, long) x 93.9 (Y) x 38.2 (Z), CALIPERED (the ref mesh is
    ~1.2mm oversize at 110.5x95.2x38.5; design uses calipered, mesh only for
    render/preview). PORT face = the 93.9-wide END; heatsink on the opposite
    end. The PORT END faces REARWARD (-x) toward the rear cable exit; the
    heatsink end faces +x (front).
  * The rear shoulder flange is a HARD WALL at x=-63.5 (shoulder mesh min-x
    through the whole deck z-band) -> the deck CANNOT be extended rearward
    (brief option (a) literal is blocked). The shoulder CENTER NOTCH (y+-26,
    open above z57.55) is the only rearward aperture -> case rear ports exit
    into it + a deck slot right under the port end. Case rear = -62.0
    (1.5 to the wall) needs RIGHT-ANGLE plugs (RJ45/barrel/USB) - flagged.
  * The case (110.3) cannot coexist with the old center-front mast (flange
    x38 / shaft x44): rear-pinned front = +48.3 overlaps it. RESOLUTION:
    keep the L2 where it is (mast plate CTR=53.5, L2 optical position
    UNCHANGED) but COMPACT the mast BASE into the front strip x51.3..63.0
    (11.7 deep, 3.0 to the case) and lift the L2 plate to z113.4 so it
    cantilevers over the case top (110.1) with 3.3 clearance. The L2 CoM
    sits ~over the base (CTR 53.5 vs base ctr 57) so the static cantilever
    moment is tiny; dynamic loads on 4x M3 are far inside proof load.

Run: ../../../.venv/bin/python place_case.py   (from chassis/)
"""
import numpy as np
import trimesh

NOVA = '/Users/afox/codebases/NOVA'

# ---- chosen placement (calipered case) ---------------------------------------
CASE_L, CASE_W, CASE_H = 110.3, 93.9, 38.2
CASE_REAR = -62.0                          # 1.5 from the rear shoulder wall
CASE_CY = 0.0
CASE_BOTTOM_Z = 71.9                       # sits on the deck top
CASE = dict(x=(CASE_REAR, CASE_REAR + CASE_L),
            y=(CASE_CY - CASE_W / 2, CASE_CY + CASE_W / 2),
            z=(CASE_BOTTOM_Z, CASE_BOTTOM_Z + CASE_H))

# ---- neighbours (trunk frame) ------------------------------------------------
DECK_TOP = 71.9
MAST_FRONT = 51.3                 # compact mast flange/shaft front wall
MAST_REAR = 63.0
L2_PLATE_Z0 = 113.4              # raised from 110.4 to clear the case top
REAR_SHOULDER_X = -63.5          # hard wall (probe)
D456_STEM_X = 63.45
DECK_Y = 55.0
SMA = [(57.0, 40.0), (57.0, -40.0)]


def main():
    x0, x1 = CASE['x']; y0, y1 = CASE['y']; z0, z1 = CASE['z']
    print('CASE world AABB (calipered 110.3 x 93.9 x 38.2, port end -x):')
    print(f'  x [{x0:+.2f}, {x1:+.2f}]  (len {x1-x0:.2f})')
    print(f'  y [{y0:+.2f}, {y1:+.2f}]  (len {y1-y0:.2f})')
    print(f'  z [{z0:+.2f}, {z1:+.2f}]  (len {z1-z0:.2f})')
    # cross-check vs the oversize ref mesh centred the same way
    m = trimesh.load(f'{NOVA}/proj/hardware/cad/chassis/jetson_case_ref.stl')
    bc = (m.bounds[0] + m.bounds[1]) / 2
    cx = (x0 + x1) / 2
    m.apply_translation([cx - bc[0], CASE_CY - bc[1], CASE_BOTTOM_Z - m.bounds[0][2]])
    ml, mh = m.bounds
    print(f'  (ref mesh AABB, ~1.2 oversize: x[{ml[0]:.1f},{mh[0]:.1f}] '
          f'y[{ml[1]:.1f},{mh[1]:.1f}] z[{ml[2]:.1f},{mh[2]:.1f}])')
    print()

    ok = True

    def clr(name, val, need=3.0):
        nonlocal ok
        good = val >= need
        ok &= good
        tag = 'OK  ' if good else ('near' if val >= -0.6 else 'FAIL')
        print(f'  [{tag}] {name}: {val:+.2f} mm  (need >= {need})')

    print('CLEARANCES:')
    clr('front edge -> mast flange front (x51.3)', MAST_FRONT - x1)
    clr('rear edge  -> rear shoulder wall (x-63.5)', x0 - REAR_SHOULDER_X,
        need=1.0)
    clr('+y edge -> deck edge (y55)', DECK_Y - y1, need=1.0)
    clr('-y edge -> deck edge (y-55)', DECK_Y + y0, need=1.0)
    clr('front edge -> D456 stem (x63.45)', D456_STEM_X - x1)
    clr('front edge -> shoulder deck-ext fin (x63.5)', 63.5 - x1)
    clr('top -> L2 plate bottom (z113.4)', L2_PLATE_Z0 - z1)
    for (sx, sy) in SMA:
        dx = max(sx - x1, x0 - sx, 0)
        dy = max(sy - y1, y0 - sy, 0)
        gap = (dx**2 + dy**2) ** 0.5 - 3.25          # Ø6.5 bulkhead
        clr(f'SMA post ({sx:+.0f},{sy:+.0f}) edge', gap, need=1.0)
    clr('bottom -> mezzanine stack top (z64, deck between)', z0 - 64.0,
        need=0.0)
    print()
    print('  free deck after the case:')
    print(f'    FRONT strip x[{x1:.1f}, 63.35]  ({63.35-x1:.1f} deep) -> mast + SMA')
    print(f'    +/-y strips y[{y1:.1f}, 55]  ({55-y1:.1f} deep, too narrow for Ø6.5)')
    print(f'    REAR: no strip (port end 1.5 off the shoulder wall)')
    print()
    print('VERDICT:', 'FEASIBLE — build.' if ok else 'BLOCKED — report back.')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
