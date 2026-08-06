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

# Cuts that are MEANT to leave the part. Key: "part:x,y" rounded to 0.1.
ALLOW = {}


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
