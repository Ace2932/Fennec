#!/usr/bin/env python3
"""stl_measure.py — pure-Python STL bounding-box / dimension reader (no deps).

Handles binary + ASCII STL. Prints per-file bbox (X/Y/Z extents in mm),
center, and triangle count. Built for the NovaSM3 leg geometry-extraction
(B2): get real part dimensions for the URDF/locomotion link lengths without
trimesh/numpy-stl (which aren't installable offline here).

  python3 stl_measure.py part1.stl part2.stl ...
  python3 stl_measure.py path/to/dir   # all *.stl under dir
"""
import sys, os, struct, glob


def _read_binary(data):
    n = struct.unpack_from("<I", data, 80)[0]
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    off = 84
    for _ in range(n):
        # skip 3 normal floats, read 3 vertices (9 floats), skip 2-byte attr
        for v in range(3):
            base = off + 12 + v * 12
            x, y, z = struct.unpack_from("<fff", data, base)
            for i, c in enumerate((x, y, z)):
                if c < mn[i]: mn[i] = c
                if c > mx[i]: mx[i] = c
        off += 50
    return mn, mx, n


def _read_ascii(text):
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            _, x, y, z = s.split()[:4]
            for i, c in enumerate((float(x), float(y), float(z))):
                if c < mn[i]: mn[i] = c
                if c > mx[i]: mx[i] = c
        elif s.startswith("facet"):
            n += 1
    return mn, mx, n


def measure(path):
    with open(path, "rb") as f:
        data = f.read()
    is_ascii = data[:5].lower() == b"solid" and b"facet" in data[:512].lower()
    mn, mx, n = _read_ascii(data.decode("ascii", "ignore")) if is_ascii else _read_binary(data)
    dim = [mx[i] - mn[i] for i in range(3)]
    ctr = [(mx[i] + mn[i]) / 2 for i in range(3)]
    return mn, mx, dim, ctr, n


def main():
    args = sys.argv[1:] or ["."]
    files = []
    for a in args:
        files += glob.glob(os.path.join(a, "**", "*.stl"), recursive=True) if os.path.isdir(a) else [a]
    for p in sorted(set(files)):
        try:
            mn, mx, dim, ctr, n = measure(p)
            print(f"{os.path.basename(p)}  ({n} tris)")
            print(f"  size XYZ: {dim[0]:.2f} x {dim[1]:.2f} x {dim[2]:.2f} mm")
            print(f"  X[{mn[0]:.2f},{mx[0]:.2f}] Y[{mn[1]:.2f},{mx[1]:.2f}] Z[{mn[2]:.2f},{mx[2]:.2f}]  center({ctr[0]:.1f},{ctr[1]:.1f},{ctr[2]:.1f})")
        except Exception as e:
            print(f"{p}: ERROR {e}")


if __name__ == "__main__":
    main()
