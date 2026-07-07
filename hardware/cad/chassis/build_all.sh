#!/bin/bash
# chassis — render the riser bay (+ spacers) and run the full fit gate.
# shoulder.scad carries the riser interface (notch + hold-down holes), so a
# shoulder re-render + the leg_v6 gate run here too.
set -e
cd "$(dirname "$0")"
OS=/opt/homebrew/bin/openscad
$OS -o riser_bay.stl riser_bay.scad
$OS -o spacer.stl spacer.scad
$OS -o battery_pocket.stl battery_pocket.scad
$OS -o head.stl head.scad          # integrated D456 face + L2 crown
                                   # (retired: l2_mast.scad + d456_head.scad)
$OS -o floor_plate.stl floor_plate.scad
$OS -o jetson_case_mount.stl jetson_case_mount.scad
$OS -o ../leg_v6/shoulder.stl ../leg_v6/shoulder.scad
../../../.venv/bin/python ../mesh_health.py head.stl
ls -la riser_bay.stl spacer.stl battery_pocket.stl head.stl floor_plate.stl jetson_case_mount.stl
../../../.venv/bin/python check_fit.py
echo "chassis gate clean — now re-gate leg_v6 (shoulder rev):"
(cd ../leg_v6 && ../../../.venv/bin/python check_fit.py --sweep)
