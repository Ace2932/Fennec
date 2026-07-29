#!/usr/bin/env python3
"""ChassisTrunk mesh survey — the measurement pass that unblocked the riser
(2026-07-06). Rerun after any change to the stock-shell mesh reference:
  ../../../.venv/bin/python measure_trunk.py

Prints the mate table recorded in ../dimensions.md §11. Method: vertex-plane
clustering + top/side ray casting (trimesh). The trunk is NOT a tub:
floor slab + two side walls + four corner wedge ramps; ends are OPEN
(closed at assembly by the v6 shoulder flanges).
"""
import pathlib
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cad_assets import asset  # noqa: E402  (path insert must come first)

TRUNK = str(asset('SM3_Frame_ChassisTrunk.stl'))


def clusters(vals, tol=0.05, minc=30):
    s = np.sort(vals)
    out, start = [], 0
    for i in range(1, len(s) + 1):
        if i == len(s) or s[i] - s[i - 1] > tol:
            if i - start >= minc:
                out.append((round(float(s[start:i].mean()), 2), i - start))
            start = i
    return out


def main():
    m = trimesh.load(TRUNK)
    v = m.vertices
    print('bounds:', np.round(m.bounds, 2).tolist(),
          'watertight:', m.is_watertight)

    wall = v[(np.abs(v[:, 1]) > 48.5) & (np.abs(v[:, 1]) < 55)
             & (v[:, 2] > 27) & (v[:, 2] < 30)]
    print('side wall top z:', round(float(wall[:, 2].max()), 2))
    yp = [c for c, n in clusters(v[:, 1], minc=200)]
    print('side wall faces y:', [y for y in yp if abs(abs(y) - 52) < 4])

    top = v[v[:, 2] > 46.8]
    for sx in (1, -1):
        for sy in (1, -1):
            c = top[(np.sign(top[:, 0]) == sx) & (np.sign(top[:, 1]) == sy)]
            print(f'wedge plateau ({sx:+d}x,{sy:+d}y): '
                  f'x {c[:, 0].min():.2f}..{c[:, 0].max():.2f}  '
                  f'y {c[:, 1].min():.2f}..{c[:, 1].max():.2f}  '
                  f'z top {c[:, 2].max():.2f}')

    # wedge windows (stock cover hook slots): ray scan from +x
    step = 0.1
    for ys0, ys1 in [(30, 40), (-40, -30)]:
        us = np.arange(ys0, ys1, step)
        vs = np.arange(40, 47, step)
        U, V = np.meshgrid(us, vs)
        o = np.column_stack([np.full(U.size, 70.), U.ravel(), V.ravel()])
        d = np.tile([-1., 0, 0], (len(o), 1))
        _, ir, _ = m.ray.intersects_location(o, d, multiple_hits=False)
        hit = np.zeros(U.size, bool)
        hit[ir] = True
        ii = np.where(~hit)[0]
        yv, zv = U.ravel()[ii], V.ravel()[ii]
        inner = ((yv > ys0 + 0.3) & (yv < ys1 - 0.3)
                 & (zv > 40.3) & (zv < 46.7))
        if inner.any():
            print(f'wedge window y[{ys0},{ys1}]: '
                  f'ctr y {yv[inner].mean():.2f} z {zv[inner].mean():.2f}  '
                  f'span {yv[inner].max() - yv[inner].min() + step:.1f} x '
                  f'{zv[inner].max() - zv[inner].min() + step:.1f}')

    ring = v[(np.abs(np.abs(v[:, 1]) - 51.75) < 2) & (v[:, 0] > 55)
             & (v[:, 2] > 3) & (v[:, 2] < 7)]
    print('shoulder bolt bore (front, low): y',
          round(float(np.abs(ring[:, 1]).mean()), 2),
          'z', round(float(ring[:, 2].mean()), 2),
          'depth x', round(float(ring[:, 0].min()), 1), '..63.5')


if __name__ == '__main__':
    main()
