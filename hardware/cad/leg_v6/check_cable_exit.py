#!/usr/bin/env python3
"""CABLE-EXIT PATENCY GATE — can the servo lead actually LEAVE the part?

WHY THIS EXISTS
---------------
sts_pocket_neg cuts a cable tunnel (19 wide x 5.9 tall, floor z-19.80) into
every part that houses an STS3215. It is SHARED geometry, but the groove that
lets the tunnel reach daylight is cut per-part -- so a part can inherit the
tunnel and never get an exit.

That is exactly what happened. tibia.scad had no groove at all: its tunnel was
a BLIND POCKET, walled on four sides, open only back into the servo bay. The
KFE servo's cable could not leave the part. Found on the bench 2026-08-05.

NOTHING CAUGHT IT, and the reason matters. check_fit.py's cable_checks()
measures the knee-loop SPAN BETWEEN ANCHORS and assumes the cable can reach
them; the tibia's own zip anchors are commented "flank the tunnel exit", which
reads as confirmation that an exit exists. main's cad-gates ran green on the
broken part.

WHAT THIS GATE ASSERTS
----------------------
Starting from a point INSIDE the tunnel, a sphere of CONNECTOR_R can travel to
the outside world without going back through the servo bay.

Three details, each of which a naive version gets wrong -- all three were hit
while writing this, so they are recorded rather than rediscovered:

1. CLEARANCE-AWARE, not "any air". A first version flood-filled raw air and
   PASSED on the known-broken tibia: the void escapes through the O3.2 zip-tie
   bores. A zip bore is not a cable route. The flood therefore runs on an
   ERODED grid -- a cell is passable only if a CONNECTOR_R ball fits.

2. THE BAY IS BLOCKED. The servo pocket is open-topped, so raw air from the
   tunnel trivially reaches outside by going up through the pocket mouth and
   around the part. That is the "fold it under the servo and around" workaround,
   not the designed route, and it pinches the lead under a servo that is
   supposed to drop in on 0.45 mm clearance. Cells on the bay side of the
   throat are excluded.

3. THE BOX MUST EXTEND WELL PAST THE SKIN. Erosion blanks cells near the grid
   boundary, so a box that stops just under the part erodes away the very open
   air the cable escapes into, and the gate fails on a good part.

WHAT IT DOES NOT PROVE
----------------------
A sphere is a conservative proxy. The real connector is a prism that can enter
nose-first and pivot, so a part failing this gate is not necessarily
unassemblable -- the pre-2026-08-05 femur failed it and Aiden did get a lead
through, with a file and pliers. Read a FAIL as "this needs force", which is
its own defect on a part that must be serviced.
"""
import os
import pathlib
import sys
from collections import deque

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cad_contains  # noqa: E402  (#195 -- installed in main(); contains() is
                     # nondeterministic unseeded, and this gate is ALL contains())

# Servo lead connector head MEASURED 2026-08-05: 9.8 x 4.6 mm. The thin axis is
# what has to clear, so the passage must admit a sphere of that diameter.
CONNECTOR_R = 2.3
STEP = 1.0

# seed: a point known to sit inside the tunnel, in the part's own frame.
# block_x: cells with x below this are the servo bay -- not a legal exit.
# escape_z: a plane unambiguously outside the part.
PARTS = {
    "femur_R": dict(seed=(37.0, 0.0, -16.85), box=((34, 64), (-15, 15), (-38, -12)),
                    block_x=35.0, escape_z=-32.0),
    "femur_L": dict(seed=(37.0, 0.0, -16.85), box=((34, 64), (-15, 15), (-38, -12)),
                    block_x=35.0, escape_z=-32.0),
    "tibia_R": dict(seed=(38.0, 0.0, -16.85), box=((34, 64), (-15, 15), (-34, -12)),
                    block_x=35.0, escape_z=-28.0),
    "tibia_L": dict(seed=(38.0, 0.0, -16.85), box=((34, 64), (-15, 15), (-34, -12)),
                    block_x=35.0, escape_z=-28.0),
}


def _passable(mesh, box, step, rad):
    """Air cells with `rad` of clearance in every direction."""
    (x0, x1), (y0, y1), (z0, z1) = box
    xs = np.arange(x0, x1 + step, step)
    ys = np.arange(y0, y1 + step, step)
    zs = np.arange(z0, z1 + step, step)
    pts = np.array([[x, y, z] for x in xs for y in ys for z in zs])
    air = (~mesh.contains(pts)).reshape(len(xs), len(ys), len(zs))
    n = int(np.ceil(rad / step))
    offs = [(i, j, k)
            for i in range(-n, n + 1) for j in range(-n, n + 1) for k in range(-n, n + 1)
            if (i * step) ** 2 + (j * step) ** 2 + (k * step) ** 2 <= rad * rad]
    ok = air.copy()
    for i, j, k in offs:
        sh = np.roll(np.roll(np.roll(air, i, 0), j, 1), k, 2)
        # np.roll wraps; blank the wrapped faces so clearance is never claimed
        # from the far side of the grid.
        if i > 0: sh[:i, :, :] = False
        elif i < 0: sh[i:, :, :] = False
        if j > 0: sh[:, :j, :] = False
        elif j < 0: sh[:, j:, :] = False
        if k > 0: sh[:, :, :k] = False
        elif k < 0: sh[:, :, k:] = False
        ok &= sh
    return xs, ys, zs, ok


def patency(mesh, cfg, rad=CONNECTOR_R, step=STEP):
    xs, ys, zs, ok = _passable(mesh, cfg["box"], step, rad)
    si = (int(np.abs(xs - cfg["seed"][0]).argmin()),
          int(np.abs(ys - cfg["seed"][1]).argmin()),
          int(np.abs(zs - cfg["seed"][2]).argmin()))
    if not ok[si]:
        return None, 0
    seen = np.zeros_like(ok)
    seen[si] = True
    q = deque([si])
    escaped = False
    n = 0
    while q:
        i, j, k = q.popleft()
        n += 1
        if zs[k] <= cfg["escape_z"]:
            escaped = True
        for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b, c = i + di, j + dj, k + dk
            if not (0 <= a < ok.shape[0] and 0 <= b < ok.shape[1] and 0 <= c < ok.shape[2]):
                continue
            if xs[a] < cfg["block_x"]:
                continue
            if ok[a, b, c] and not seen[a, b, c]:
                seen[a, b, c] = True
                q.append((a, b, c))
    return escaped, n


def main(argv):
    cad_contains.install()   # #195 -- reproducible containment
    here = os.path.dirname(os.path.abspath(__file__))
    targets = argv[1:] or sorted(PARTS)
    bad = 0
    print(f"-- cable-exit patency (O{2*CONNECTOR_R:.1f} connector head, flood fill from inside the tunnel) --")
    for t in targets:
        stl = t if os.path.exists(t) else os.path.join(here, t + ".stl")
        key = os.path.basename(stl).replace(".stl", "")
        cfg = PARTS.get(key)
        if cfg is None:
            print(f"   SKIP  {key}: no tunnel seed defined")
            continue
        mesh = trimesh.load(stl, force="mesh")
        esc, n = patency(mesh, cfg)
        if esc is None:
            print(f"   FAIL  {key}: seed is inside solid — the tunnel is not where this gate expects it")
            bad = 1
        elif esc:
            print(f"   OK    {key}: a O{2*CONNECTOR_R:.1f} head can reach the outside ({n} cells)")
        else:
            print(f"   FAIL  {key}: NO EXIT for a O{2*CONNECTOR_R:.1f} head — {n} cells of passable "
                  f"void, none reaching outside. The servo lead cannot leave the part "
                  f"without force.")
            bad = 1
    print("\n" + ("FAIL: a cable tunnel has no connector-sized exit"
                  if bad else "OK: every cable tunnel admits the connector to the outside"))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
