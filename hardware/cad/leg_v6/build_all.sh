#!/bin/bash
# leg_v6 — render all 6 leg STLs (R + L of coax/femur/tibia)
set -e
cd "$(dirname "$0")"
# Toolchain discovery (#166) — these were hardcoded to this project's author's
# machine (/opt/homebrew/bin/openscad and ../../../.venv/bin/python), so the
# script ran in exactly one place. Override either with an env var.
VENV=../../../.venv/bin/python
OS=${OPENSCAD:-$(command -v openscad || echo /opt/homebrew/bin/openscad)}
PY=${PYTHON:-$( [ -x "$VENV" ] && echo "$VENV" || command -v python3 )}
if [ ! -x "$OS" ] && ! command -v "$OS" >/dev/null 2>&1; then
  echo "openscad not found (set OPENSCAD=/path/to/openscad)" >&2; exit 1
fi
$OS -o knee_arm.stl knee_arm.scad
$OS -o knee_bumper.stl knee_bumper.scad   # TPU collapse guard (backlog #15 B)
$OS -o cable_clip.stl cable_clip.scad      # TPU cable clip (#18, AUD-10: was un-rendered)
$OS -o strap.stl strap.scad                # TPU servo strap (AUD-10)
$OS -o grommet_insert.stl grommet_insert.scad  # TPU flange grommet liner (#30, AUD-10)
# (toe_profile.scad is a reference profile, empty top-level object -- not rendered)
$OS -o shoulder.stl shoulder.scad
$OS -o shoulder_plate.stl shoulder_plate.scad
$OS -o shoulder_plate_L.stl shoulder_plate_L.scad
$OS -o coax_hfe_plate.stl coax_hfe_plate.scad        # #53 fix: bolt-on inboard HFE arm
$OS -o coax_hfe_plate_L.stl coax_hfe_plate_L.scad
for p in femur tibia coax; do
  $OS -o ${p}_R.stl ${p}.scad
  $OS -o ${p}_L.stl ${p}_L.scad
done
ls -la *_R.stl *_L.stl
$PY ../mesh_health.py *_R.stl *_L.stl knee_arm.stl knee_bumper.stl shoulder.stl shoulder_plate.stl shoulder_plate_L.stl cable_clip.stl strap.stl grommet_insert.stl coax_hfe_plate.stl coax_hfe_plate_L.stl
$PY check_fit.py --sweep
$PY check_shoe.py
# Proves the hfe/kfe servos still seat only ONE way round. This is what backs
# the derived hfe/kfe servo signs in nova_ops/safety_envelope/derived_signs.py:
# loosen an arm relief and the flipped servo starts fitting, which silently
# removes the evidence those signs rest on. Runs on the STLs rendered above.
$PY servo_orientation_gate.py
