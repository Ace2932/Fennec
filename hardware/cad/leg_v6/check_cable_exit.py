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
The kernel is the plug's cross-section held in ONE orientation (wide axis across
the tunnel, thin axis vertical). A real plug can enter nose-first and pivot, so a
part failing this gate is not necessarily unassemblable -- the pre-2026-08-05
femur failed it and Aiden did get a lead through, with a file and pliers. Read a
FAIL as "this needs force", which is its own defect on a part that gets serviced.

It also says nothing about the plug's LENGTH: a long housing may still foul on a
corner the cross-section clears.
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

# Servo lead connector head MEASURED 2026-08-05: 9.8 x 4.6 mm.
#
# The kernel is the PLUG'S ACTUAL CROSS-SECTION, not a sphere. A sphere of the
# thin axis (r=2.3) was the first version and it is BLIND TO WIDTH: it passes a
# 5 mm groove, which cannot admit a 9.8 mm plug. That is the same "runs, reports
# success, does not cover what it claims" failure this gate exists to catch, so
# it is fixed rather than documented.
#
# Orientation: the plug travels along x with its WIDE axis across the tunnel
# (19 mm wide, 5.9 mm tall) and its thin axis vertical -- the only way it fits.
CONN_W = 9.8    # y, across the tunnel
CONN_H = 4.6    # z, the thin axis
CONN_L = 4.6    # x. NOT the housing length -- the smallest footprint the plug
                # can present along the travel direction when pivoted nose-down.
                # It must be non-zero: a purely 2D y-z kernel passes a 3 mm-long
                # downward slot, which is how the x40 groove and main's femur
                # (2.4 mm slot) slipped through the second version of this gate.
STEP = 1.0

# seed: a point known to sit inside the tunnel, in the part's own frame.
# block_x: cells with x below this are the servo bay -- not a legal exit.
# escape_z: a plane unambiguously outside the part.
# Parts that use sts_pocket_neg but are deliberately NOT flood-checked, each with
# the reason. Anything using the shared pocket must appear here or in PARTS --
# see _assert_coverage(). Silently skipping a part is the failure this whole gate
# exists to catch, so it is made impossible rather than discouraged.
EXCLUDED = {
    "coax": "its pocket is rotated so the tunnel points at the part's own BOTTOM "
            "face and runs past it (tunnel to z-42.4, part bottom z-38.4) -- it "
            "breaks out by construction, no groove involved. VERIFIED 2026-08-05: "
            "walls present at y8/12/20, channel at y16, and a straight-down probe "
            "from (0,16.85,-35) reaches outside. The flood machinery below is "
            "x-axis-specific (block_x) and would need a per-part bay axis to run "
            "here, which is not worth it for a tunnel with no floor to block it.",
}

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


def _passable(mesh, box, step, w=CONN_W, h=CONN_H, l=CONN_L):
    """Air cells that can host the plug: l in x, w in y, h in z."""
    (x0, x1), (y0, y1), (z0, z1) = box
    xs = np.arange(x0, x1 + step, step)
    ys = np.arange(y0, y1 + step, step)
    zs = np.arange(z0, z1 + step, step)
    pts = np.array([[x, y, z] for x in xs for y in ys for z in zs])
    air = (~mesh.contains(pts)).reshape(len(xs), len(ys), len(zs))
    # anisotropic kernel: half-extents of the plug in y and z. x is left free --
    # the plug is long in the travel direction and the flood handles that.
    ni = int(np.floor((l / 2) / step))
    nj = int(np.floor((w / 2) / step))
    nk = int(np.floor((h / 2) / step))
    offs = [(i, j, k)
            for i in range(-ni, ni + 1)
            for j in range(-nj, nj + 1)
            for k in range(-nk, nk + 1)]
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


def patency(mesh, cfg, step=STEP):
    xs, ys, zs, ok = _passable(mesh, cfg["box"], step)
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


def _assert_coverage(here):
    """Every user of the shared pocket must be checked or explicitly excluded."""
    users = set()
    for f in pathlib.Path(here).glob("*.scad"):
        if f.name == "leg_v6_common.scad":
            continue
        if "sts_pocket_neg" in f.read_text():
            users.add(f.stem.replace("_L", ""))
    covered = {k.replace("_R", "").replace("_L", "") for k in PARTS}
    unaccounted = users - covered - set(EXCLUDED)
    if unaccounted:
        raise SystemExit(
            f"FAIL: {', '.join(sorted(unaccounted))} use(s) sts_pocket_neg and its cable "
            f"tunnel is neither checked nor listed in EXCLUDED. A part can inherit the "
            f"shared tunnel and never get an exit -- that is the bug this gate exists for. "
            f"Add it to PARTS with a tunnel seed, or to EXCLUDED with a reason.")
    print(f"   coverage: {len(covered)} checked, {len(EXCLUDED)} excluded-with-reason, "
          f"0 unaccounted (of {len(users)} parts using sts_pocket_neg)")


def main(argv):
    cad_contains.install()   # #195 -- reproducible containment
    _assert_coverage(os.path.dirname(os.path.abspath(__file__)))
    here = os.path.dirname(os.path.abspath(__file__))
    targets = argv[1:] or sorted(PARTS)
    bad = 0
    print(f"-- cable-exit patency ({CONN_W} x {CONN_H} mm connector head, flood fill from inside the tunnel) --")
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
            print(f"   OK    {key}: a {CONN_W} x {CONN_H} head can reach the outside ({n} cells)")
        else:
            print(f"   FAIL  {key}: NO EXIT for a {CONN_W} x {CONN_H} head — {n} cells of passable "
                  f"void, none reaching outside. The servo lead cannot leave the part "
                  f"without force.")
            bad = 1
    print("\n" + ("FAIL: a cable tunnel has no connector-sized exit"
                  if bad else "OK: every cable tunnel admits the connector to the outside"))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
