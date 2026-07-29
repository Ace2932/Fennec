#!/usr/bin/env python3
"""Is every committed PYTHON-built artifact what its producer actually makes?

WHY. check_stl_fresh.py (#176) closed this hole for OpenSCAD products: it
re-renders each .scad named in a build_all.sh and compares geometry. By
construction it cannot see the artifacts built by Python. `trunk.stl` is in its
SKIP set by name ("not an OpenSCAD product"); `robot_viewer.html` is not an STL
at all and appears in no build_all.sh. Those were the two tracked generated
artifacts with nothing checking them.

That is not hypothetical. gen_viewer.py crashed on a part retired 2026-07-10
(#41) and stayed broken for 18 days. Nobody noticed, because the committed
robot_viewer.html kept opening fine — showing 2026-07-11 geometry while 25
chassis/leg_v6 STLs changed underneath it. A committed artifact is evidence its
producer ran ONCE, not that it still can.

METHOD. Run the producer, compare what it makes against what is committed, put
the committed bytes back. The original is restored in a finally block, so an
interrupted run cannot leave a half-regenerated artifact in the tree.

BYTE vs CONTENT. Both producers are deterministic here — trunk_build.py and
gen_viewer.py each reproduce their artifact byte for byte on this toolchain. But
trimesh's STL loader merges vertices, so a version bump can legitimately shift
the output without any design change. So this compares CONTENT and reports
byte-identity when it happens, exactly as check_stl_fresh.py does:

  *.stl   geometry (volume / bbox / sampled surface), tolerances reused from
          check_stl_fresh so both gates agree on what "same shape" means
  *.html  the embedded DATA blob — non-geometry fields structurally, and each
          base64 Float32 mesh payload as decoded coordinates

The HTML numbers need a tolerance for a reason worth recording: DATA carries
transform matrices built from trig, and libm's last bit or two differs between
platforms. The first CI run of this gate failed on exactly that — a false STALE
caused by sin(x) on Linux vs on the dev Mac, with no artifact drift at all. Numbers
compare within 1e-9, orders of magnitude below any real change.

Usage:
    python check_generated_fresh.py
"""

from __future__ import annotations

import base64
import json
import math
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_stl_fresh import compare as compare_stl  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

#: (committed artifact, producer script). The producer runs with cwd set to its
#: own directory, which is how both write to the right place.
ARTIFACTS = [
    (HERE / "chassis" / "trunk.stl", HERE / "chassis" / "trunk_build.py"),
    (HERE / "viewer" / "robot_viewer.html", HERE / "gen_viewer.py"),
]

#: mm. Decoded viewer coordinates are float32 millimetres; a real geometry
#: change moves them by orders of magnitude more than float32 round-trip noise.
VIEWER_ABS_TOL = 1e-3


def regenerate(artifact: pathlib.Path, script: pathlib.Path) -> bytes:
    """Run the producer, return what it wrote, and restore the committed file.

    Restoring in `finally` matters: this gate runs against a real working tree,
    and a crash mid-run must not leave the artifact rewritten.
    """
    original = artifact.read_bytes()
    try:
        r = subprocess.run([sys.executable, str(script)],
                           cwd=str(script.parent),
                           capture_output=True, text=True)
        if r.returncode != 0:
            tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
            raise RuntimeError(f"{script.name} exited {r.returncode}: {tail}")
        return artifact.read_bytes()
    finally:
        artifact.write_bytes(original)


def _matching_brace(s: str, start: int) -> int:
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces in viewer DATA")


def viewer_data(html: str) -> dict:
    """The DATA object gen_viewer.py substitutes into the page."""
    marker = html.index("const D=")
    start = html.index("{", marker)
    return json.loads(html[start:_matching_brace(html, start) + 1])


def _soup(b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.float32).reshape(-1, 3)


def _close(a, b, path=""):
    """Structural compare that tolerates last-ULP float drift.

    DATA carries transform matrices built from trig (R(-22, ...) and friends),
    and libm differs in the last bit or two between platforms. Comparing the
    decoded JSON exactly made this gate fail in CI on nothing but the difference
    between sin(x) on Linux and on the dev Mac — a false STALE, which is the
    failure mode that gets a gate switched off. Numbers therefore compare with a
    tolerance far below any real geometry change; everything else is exact.

    Returns (ok, path-to-first-difference).
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b, path
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9), path
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False, f"{path or '<root>'} (keys)"
        for k in sorted(a):
            ok, where = _close(a[k], b[k], f"{path}.{k}" if path else k)
            if not ok:
                return False, where
        return True, path
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False, f"{path}[length {len(a)} -> {len(b)}]"
        for i, (x, y) in enumerate(zip(a, b)):
            ok, where = _close(x, y, f"{path}[{i}]")
            if not ok:
                return False, where
        return True, path
    return a == b, path


def compare_viewer(committed: bytes, fresh: bytes):
    if committed == fresh:
        return True, "byte-identical"
    a, b = viewer_data(committed.decode()), viewer_data(fresh.decode())
    ageo, bgeo = a.pop("geo", {}), b.pop("geo", {})

    # Both halves always run: a stale viewer usually differs in BOTH the part
    # list and the meshes, and reporting only the first found sends you looking
    # at half the problem.
    issues = []

    ok_data, where = _close(a, b)
    if not ok_data:
        issues.append(f"DATA differs at {where}")

    detail = ""
    if set(ageo) != set(bgeo):
        added = sorted(set(bgeo) - set(ageo))
        gone = sorted(set(ageo) - set(bgeo))
        issues.append(f"mesh set changed (added {added}, removed {gone})")
    else:
        worst, worst_key = 0.0, None
        for k in sorted(ageo):
            pa, pb = _soup(ageo[k]), _soup(bgeo[k])
            if pa.shape != pb.shape:
                issues.append(f"{k}: triangle count {pa.shape[0] // 3} -> "
                              f"{pb.shape[0] // 3}")
                continue
            d = float(np.abs(pa - pb).max()) if pa.size else 0.0
            if d > worst:
                worst, worst_key = d, k
        if worst > VIEWER_ABS_TOL:
            issues.append(f"max coord delta {worst:.6f}mm (worst: {worst_key})")
        detail = f"{len(ageo)} meshes, max coord delta {worst:.6f}mm"

    return (not issues), ("; ".join(issues) if issues else detail)


def check(artifact: pathlib.Path, script: pathlib.Path) -> bool:
    rel = artifact.relative_to(HERE)
    try:
        fresh = regenerate(artifact, script)
    except RuntimeError as exc:
        print(f"   ERR   {rel}: {exc}")
        return False

    committed = artifact.read_bytes()
    if artifact.suffix == ".html":
        ok, detail = compare_viewer(committed, fresh)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            fresh_path = pathlib.Path(tmp) / artifact.name
            fresh_path.write_bytes(fresh)
            ok, detail = compare_stl(artifact, fresh_path)
    print(f"   {'OK   ' if ok else 'STALE'} {str(rel):32s} {detail}")
    return ok


def main() -> int:
    print("-- python-built artifacts")
    bad = sum(not check(a, s) for a, s in ARTIFACTS)
    print()
    if bad:
        print(f"FAIL: {bad} artifact(s) do not match their producer — rerun it "
              f"and commit the result")
    else:
        print("OK: every committed python-built artifact matches its producer")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
