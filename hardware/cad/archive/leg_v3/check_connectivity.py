"""
Connectivity validation gate. Run on every exported STL.

Watertight != connected. A mesh of two disconnected closed surfaces is
still watertight, but won't print as a single piece. This script flags
any STL with > 1 connected component.

Usage:
    source /tmp/nova-cadquery-venv/bin/activate
    python check_connectivity.py
"""
import glob
import sys
import trimesh


def main():
    bad = 0
    for stl in sorted(glob.glob("*.stl")):
        # Skip the assembly preview — it's intentionally multi-piece
        if "assembly" in stl:
            continue
        m = trimesh.load(stl, force="mesh")
        parts = m.split(only_watertight=False)
        n = len(parts)
        wt = m.is_watertight
        status = "OK" if (n == 1 and wt) else "FAIL"
        print(f"  [{status}] {stl:35s}  parts={n}  watertight={wt}")
        if n != 1 or not wt:
            bad += 1
    if bad:
        print(f"\n{bad} STL(s) failed validation.")
        sys.exit(1)
    print("\nAll STLs: 1 connected, watertight component.")


if __name__ == "__main__":
    main()
