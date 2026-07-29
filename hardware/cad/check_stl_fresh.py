#!/usr/bin/env python3
"""Is every committed STL what its .scad actually produces? (#176)

WHY. The CAD gates check the COMMITTED STLs, which is the right thing to check
— that is what gets printed. But it leaves a hole: edit a .scad, forget to run
build_all.sh, and the gates happily certify the OLD geometry while the source
says something else. Nothing anywhere notices.

WHY NOT THE OBVIOUS CHECK. "if a .scad changed in this PR, its .stl must have
changed too" is unsatisfiable: renders are deterministic, so a comment-only
edit produces a byte-identical STL and the check could never be satisfied. It
also needs the scad->stl mapping, which is not 1:1 (femur.scad -> femur_R.stl,
toe_profile.scad -> nothing). That mapping already exists, in machine-readable
form, inside build_all.sh — so it is parsed from there rather than retyped.

BYTE vs GEOMETRY. On one toolchain OpenSCAD is byte-reproducible: measured, all
11 leg_v6 parts re-render byte-identical to what is committed. Across versions
it will not be, so this compares GEOMETRY (volume, bounds, sampled surface
distance) and reports the deltas. Byte-identity is reported when it happens
because it is the strongest possible answer, but it is not required.

Usage:
    python check_stl_fresh.py [dir ...]      # default: leg_v6 + chassis
    OPENSCAD=/path/to/openscad python check_stl_fresh.py
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_DIRS = [HERE / "leg_v6", HERE / "chassis"]

#: Geometry tolerances. Generous on purpose for the first CI run — the point of
#: this pass is to LEARN the real cross-version spread, then tighten. A stale
#: STL is a geometry change, which is orders of magnitude larger than
#: tessellation noise.
VOL_REL_TOL = 1e-3          # 0.1% of volume
BBOX_ABS_TOL = 0.01         # mm
#: mm, p99 of sampled point-to-surface distance. DERIVED FROM MEASUREMENT, not
#: chosen: across OpenSCAD 2021.01 (CI) vs 2026.04.26 (dev Mac), 32 of 33 parts
#: sit at <=0.0006mm and knee_bumper — a hull()-based curved part, where CGAL
#: and Manifold tessellate differently — sits at 0.0754mm. 0.10 clears that with
#: room while staying 6x below the 0.605mm the negative control produces
#: (cable_clip L 18->19). Tighten it if the toolchains are ever unified.
SURF_ABS_TOL = 0.10
SURF_SAMPLES = 4000

#: Built by trunk_build.py (trimesh + manifold3d), NOT by OpenSCAD — see that
#: file's docstring. Rendering trunk.scad gives a preview, not the shipped part.
SKIP = {"trunk.stl"}


def openscad() -> str:
    return (os.environ.get("OPENSCAD")
            or shutil.which("openscad")
            or "/opt/homebrew/bin/openscad")


def render_pairs(build_all: pathlib.Path):
    """(stl, scad) pairs from a build_all.sh, expanding its one for-loop.

    Parsed rather than retyped so a new part cannot be added to the build and
    silently skipped here.
    """
    text = build_all.read_text()
    pairs = []
    loop_vars = []
    for m in re.finditer(r"for\s+(\w+)\s+in\s+([^;]+);\s*do", text):
        loop_vars.append((m.group(1), m.group(2).split()))
    for m in re.finditer(r"\$OS\s+-o\s+(\S+)\s+(\S+)", text):
        stl, scad = m.group(1), m.group(2)
        if "${" in stl or "${" in scad:
            for var, values in loop_vars:
                if "${" + var + "}" in stl or "${" + var + "}" in scad:
                    for v in values:
                        pairs.append((stl.replace("${" + var + "}", v),
                                      scad.replace("${" + var + "}", v)))
            continue
        pairs.append((stl, scad))
    return pairs


def compare(committed: pathlib.Path, fresh: pathlib.Path):
    """Geometric comparison. Returns (ok, detail)."""
    if committed.read_bytes() == fresh.read_bytes():
        return True, "byte-identical"
    a, b = trimesh.load(committed), trimesh.load(fresh)
    va, vb = abs(a.volume), abs(b.volume)
    vol_rel = abs(va - vb) / max(va, 1e-9)
    bbox = float(np.abs(np.asarray(a.bounds) - np.asarray(b.bounds)).max())
    pa, _ = trimesh.sample.sample_surface(a, SURF_SAMPLES, seed=0)
    d = np.abs(trimesh.proximity.signed_distance(b, pa))
    surf_max = float(d.max())
    # p99, not max. The first CI run (OpenSCAD 2021.01 there vs 2026.04.26 on
    # the dev Mac) put 30 of 33 parts at <=0.0006mm and three at 0.14-0.99mm —
    # and all three had volume AND bbox identical to four decimals. A local
    # surface deviation with no change in volume or extent is a few facets
    # placed differently by a different boolean engine, not a geometry change,
    # and max is precisely the statistic a handful of facets can dominate.
    surf_p99 = float(np.percentile(d, 99))
    ok = (vol_rel <= VOL_REL_TOL and bbox <= BBOX_ABS_TOL
          and surf_p99 <= SURF_ABS_TOL)
    return ok, (f"vol {vol_rel * 100:.4f}%  bbox {bbox:.4f}mm  "
                f"surf p99 {surf_p99:.4f}mm  max {surf_max:.4f}mm")


def check_dir(d: pathlib.Path) -> int:
    build_all = d / "build_all.sh"
    if not build_all.exists():
        print(f"-- {d.name}: no build_all.sh, skipped")
        return 0
    bad = 0
    print(f"-- {d.name}")
    with tempfile.TemporaryDirectory() as tmp:
        for stl, scad in render_pairs(build_all):
            if os.path.isabs(stl):
                # build_all.sh renders trunk.scad to /tmp deliberately: it is a
                # parametric SPEC sanity render, not the shipped trunk.stl
                # (which trunk_build.py produces). An absolute target is never
                # a committed part.
                print(f"   SKIP  {stl} (rendered outside the repo on purpose)")
                continue
            stl_p = (d / stl).resolve()
            scad_p = (d / scad).resolve()
            if stl_p.name in SKIP:
                print(f"   SKIP  {stl_p.name} (not an OpenSCAD product)")
                continue
            if not scad_p.exists():
                continue
            if not stl_p.exists():
                print(f"   MISS  {stl_p.name}: committed STL absent")
                bad += 1
                continue
            fresh = pathlib.Path(tmp) / stl_p.name
            r = subprocess.run([openscad(), "-o", str(fresh), str(scad_p)],
                               capture_output=True, text=True, cwd=str(d))
            if r.returncode != 0 or not fresh.exists():
                print(f"   ERR   {stl_p.name}: render failed "
                      f"({r.stderr.strip().splitlines()[-1:] or ''})")
                bad += 1
                continue
            ok, detail = compare(stl_p, fresh)
            print(f"   {'OK   ' if ok else 'STALE'} {stl_p.name:26s} {detail}")
            if not ok:
                bad += 1
    return bad


def main() -> int:
    dirs = [pathlib.Path(a).resolve() for a in sys.argv[1:]] or DEFAULT_DIRS
    if not shutil.which(openscad()) and not os.path.exists(openscad()):
        print(f"openscad not found ({openscad()}); set OPENSCAD=", file=sys.stderr)
        return 2
    bad = sum(check_dir(d) for d in dirs)
    print()
    if bad:
        print(f"FAIL: {bad} STL(s) do not match their .scad — run build_all.sh")
    else:
        print("OK: every committed STL matches its .scad")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
