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
$OS -o strap.stl strap.scad                # PA6-CF/PETG-CF servo retention plate (AUD-10)
                                           # (#184: said "TPU servo strap" — wrong.
                                           #  strap.scad specifies PA6-CF or PETG-CF,
                                           #  2.5mm plate, ~100% infill. It is a rigid
                                           #  zip-tied retainer, not an elastic strap.)
$OS -o grommet_insert.stl grommet_insert.scad  # TPU flange grommet liner (#30, AUD-10)
# (toe_profile.scad is a reference profile, empty top-level object -- not rendered)
$OS -o shoulder.stl shoulder.scad              # REAR end — plain
$OS -o shoulder_sw1.stl shoulder_sw1.scad      # FRONT end — + SW1 panel hole (#377)
$OS -o shoulder_plate.stl shoulder_plate.scad
$OS -o shoulder_plate_L.stl shoulder_plate_L.scad
$OS -o coax_hfe_block.stl coax_hfe_block.scad        # #226 option C: bolt-on OUTBOARD HFE arm
$OS -o coax_hfe_block_L.stl coax_hfe_block_L.scad
for p in femur tibia coax; do
  $OS -o ${p}_R.stl ${p}.scad
  $OS -o ${p}_L.stl ${p}_L.scad
done
ls -la *_R.stl *_L.stl
$PY ../mesh_health.py *_R.stl *_L.stl knee_arm.stl knee_bumper.stl shoulder.stl shoulder_plate.stl shoulder_plate_L.stl cable_clip.stl strap.stl grommet_insert.stl coax_hfe_block.stl coax_hfe_block_L.stl
$PY check_fit.py --sweep
$PY check_shoe.py
# Can the servo lead actually LEAVE the part? sts_pocket_neg's cable tunnel is
# SHARED, but the groove that lets it reach daylight is cut per-part -- so a
# part can inherit the tunnel and never get an exit. tibia.scad did exactly
# that and shipped a blind pocket; cable_checks() could not see it because it
# measures the loop SPAN BETWEEN ANCHORS and assumes the cable reaches them.
$PY check_cable_exit.py
# Proves the hfe/kfe servos still seat only ONE way round. This is what backs
# the derived hfe/kfe servo signs in nova_ops/safety_envelope/derived_signs.py:
# loosen an arm relief and the flipped servo starts fitting, which silently
# removes the evidence those signs rest on. Runs on the STLs rendered above.
$PY servo_orientation_gate.py
