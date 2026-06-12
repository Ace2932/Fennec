#!/usr/bin/env bash
# Render all screw-lock leg parts to STL alongside the .scad files.
# Mirrors leg_v5/build_all.sh. ~1 s per part.
set -euo pipefail
cd "$(dirname "$0")"

render() { echo "→ $2"; openscad -o "$2" "$1" >/dev/null 2>&1; }

render coax.scad          coax_L.stl
render coax_R.scad        coax_R.stl
render femur.scad         femur_L.stl
render femur_R.scad       femur_R.stl
render femur_cover.scad   femur_cover_L.stl
render femur_cover_R.scad femur_cover_R.stl
render tibia.scad         tibia_L.stl
render tibia_R.scad       tibia_R.stl

echo "done — 8 STLs"
