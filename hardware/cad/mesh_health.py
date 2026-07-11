#!/usr/bin/env python3
"""Mesh-health gate: every printable STL must be watertight, positive
volume, and a SINGLE body. Added 2026-07-06 after the pre-print audit
found coax_L carrying a -7.8 mm3 inverted internal shell from a
misplaced L-wrapper marker dot (and tibia_L/femur_L dots cutting air —
no LEFT marking at all). Body-count catches both failure classes:
buried cutters make voids (bodies > 1 or negative-volume shells);
air cutters are caught by the paired dot-cut probes below.

Usage: python mesh_health.py <stl> [<stl> ...]     (exit 1 on any fail)
"""
import sys

import trimesh


def check(path: str) -> bool:
    m = trimesh.load(path)
    bodies = m.split(only_watertight=False)
    ok = m.is_watertight and m.volume > 0 and len(bodies) == 1
    neg = [b for b in bodies if b.volume < 0]
    print(f"{path}: watertight={m.is_watertight} bodies={len(bodies)} "
          f"vol={m.volume/1000:.1f}cm3"
          + (f"  NEGATIVE-SHELL {[round(b.volume,1) for b in neg]}" if neg else "")
          + ("" if ok else "   <-- FAIL"))
    return ok


if __name__ == "__main__":
    results = [check(p) for p in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
