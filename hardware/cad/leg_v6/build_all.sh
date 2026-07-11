#!/bin/bash
# leg_v6 — render all 6 leg STLs (R + L of coax/femur/tibia)
set -e
cd "$(dirname "$0")"
OS=/opt/homebrew/bin/openscad
$OS -o knee_arm.stl knee_arm.scad
$OS -o knee_bumper.stl knee_bumper.scad   # TPU collapse guard (backlog #15 B)
$OS -o cable_clip.stl cable_clip.scad      # TPU cable clip (#18, AUD-10: was un-rendered)
$OS -o strap.stl strap.scad                # TPU servo strap (AUD-10)
$OS -o grommet_insert.stl grommet_insert.scad  # TPU flange grommet liner (#30, AUD-10)
# (toe_profile.scad is a reference profile, empty top-level object -- not rendered)
$OS -o shoulder.stl shoulder.scad
$OS -o shoulder_plate.stl shoulder_plate.scad
$OS -o shoulder_plate_L.stl shoulder_plate_L.scad
for p in femur tibia coax; do
  $OS -o ${p}_R.stl ${p}.scad
  $OS -o ${p}_L.stl ${p}_L.scad
done
ls -la *_R.stl *_L.stl
../../../.venv/bin/python ../mesh_health.py *_R.stl *_L.stl knee_arm.stl knee_bumper.stl shoulder.stl shoulder_plate.stl shoulder_plate_L.stl cable_clip.stl strap.stl grommet_insert.stl
../../../.venv/bin/python check_fit.py --sweep
../../../.venv/bin/python check_shoe.py
