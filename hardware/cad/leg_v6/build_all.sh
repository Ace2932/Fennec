#!/bin/bash
# leg_v6 — render all 6 leg STLs (R + L of coax/femur/tibia)
set -e
cd "$(dirname "$0")"
OS=/opt/homebrew/bin/openscad
$OS -o knee_arm.stl knee_arm.scad
for p in femur tibia coax; do
  $OS -o ${p}_R.stl ${p}.scad
  $OS -o ${p}_L.stl ${p}_L.scad
done
ls -la *_R.stl *_L.stl
../../../.venv/bin/python check_fit.py
