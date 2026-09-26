#!/usr/bin/env bash
# Render an STL (or .scad) to PNG views via OpenSCAD (headless).
# Usage: render_part.sh <input.stl|input.scad> [out_dir]
# Auto-fits camera distance from the STL bounding box (this OpenSCAD build
# ignores --viewall rotation, so distance is computed instead).
set -euo pipefail

OPENSCAD=/opt/homebrew/bin/openscad
in="${1:?usage: render_part.sh <input.stl|.scad> [out_dir]}"
[ -f "$in" ] || { echo "no such file: $in" >&2; exit 1; }
out="${2:-$(dirname "$in")/renders}"
mkdir -p "$out"
name=$(basename "${in%.*}")

scad="$in"; tmp=""; dist=600
case "$in" in
  *.stl|*.STL)
    abs=$(cd "$(dirname "$in")" && pwd)/$(basename "$in")
    tmp="/tmp/renderpart.$$.$RANDOM.scad"
    printf 'import("%s");\n' "$abs" > "$tmp"
    scad="$tmp"
    # distance ~2.6x largest bbox dimension, centered part
    dist=$("$(cd "$(dirname "$0")/../.." && pwd)/.venv/bin/python" - "$abs" <<'PY' 2>/dev/null || echo 600
import sys, trimesh
m = trimesh.load(sys.argv[1])
print(int(max(m.extents) * 2.6) or 600)
PY
)
    ;;
esac

render() { # view-name  gimbal-rot (rotx,roty,rotz)
  "$OPENSCAD" -o "$out/${name}_$1.png" --autocenter --imgsize=900,700 \
    --camera=0,0,0,$2,$dist "$scad" >/dev/null 2>&1 \
    && echo "  $out/${name}_$1.png" || echo "  FAILED $1"
}

echo "Rendering $name (dist=$dist):"
render iso   "55,0,25"
render front "90,0,0"
render top   "0,0,0"

[ -n "$tmp" ] && rm -f "$tmp"
