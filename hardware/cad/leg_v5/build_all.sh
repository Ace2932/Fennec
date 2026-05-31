#!/bin/bash
# Build all V5 STLs from OpenSCAD source.
# Uses original NovaSM3 STL shape + cuts STS3215 cavity inside.

set -e
cd "$(dirname "$0")"

OPENSCAD="${OPENSCAD:-/opt/homebrew/bin/openscad}"

# Per part: L uses LeftXxx.stl, R uses RightXxx.stl
# Shoulder is front/rear-symmetric (single variant)

echo "Building shoulder..."
"$OPENSCAD" -o "shoulder.stl" "shoulder.scad"

for part in coax femur tibia; do
    echo "Building ${part}_L (Left)..."
    "$OPENSCAD" -o "${part}_L.stl" "${part}.scad"
    echo "Building ${part}_R (Right)..."
    "$OPENSCAD" -o "${part}_R.stl" "${part}_R.scad"
done

echo
echo "Done. Outputs:"
ls -la *.stl 2>/dev/null
