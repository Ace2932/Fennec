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
$OS -o head.stl head.scad          # fwd head (D456 face + L2 crown)
$OS -o head_ear.stl head_ear.scad          # fennec ear / antenna mast (R)
$OS -o head_ear_L.stl head_ear_L.scad      # ear (L mirror)
$OS -o l2_adapter.stl l2_adapter.scad      # L2 accessible-mount plate
$OS -o control_pod.stl control_pod.scad    # rear-top E-stop + OLED pod
$OS -o neck_bracket.stl neck_bracket.scad   # front-shoulder-deck adapter
$OS -o floor_plate.stl floor_plate.scad
$OS -o jetson_case_mount.stl jetson_case_mount.scad
$OS -o jetson_clamp_bar.stl jetson_clamp_bar.scad  # case hold-down bar (x2, #44)
$OS -o oled_mount.stl oled_mount.scad          # OLED bracket (split off pod, #40)
$OS -o case_slot_grommet.stl case_slot_grommet.scad  # -Y CASE_SLOT TPU edge liner (#41 follow-up)
$OS -o skid_rail.stl skid_rail.scad          # TPU belly skid rail x2 (#15, AUD-10: was un-rendered)
$OS -o ../leg_v6/shoulder.stl ../leg_v6/shoulder.scad
../../../.venv/bin/python ../mesh_health.py head.stl head_ear.stl head_ear_L.stl l2_adapter.stl control_pod.stl jetson_case_mount.stl jetson_clamp_bar.stl oled_mount.stl neck_bracket.stl case_slot_grommet.stl skid_rail.stl
ls -la riser_bay.stl spacer.stl battery_pocket.stl head.stl neck_bracket.stl floor_plate.stl jetson_case_mount.stl
../../../.venv/bin/python check_fit.py
echo "chassis gate clean — now re-gate leg_v6 (shoulder rev):"
(cd ../leg_v6 && ../../../.venv/bin/python check_fit.py --sweep)
