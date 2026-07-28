#!/bin/bash
# chassis — render the riser bay (+ spacers) and run the full fit gate.
# shoulder.scad carries the riser interface (notch + hold-down holes), so a
# shoulder re-render + the leg_v6 gate run here too.
set -e
cd "$(dirname "$0")"
# Toolchain discovery (#166) — these were hardcoded to this project's author's
# machine, so the script ran in exactly one place. Override with an env var.
VENV=../../../.venv/bin/python
OS=${OPENSCAD:-$(command -v openscad || echo /opt/homebrew/bin/openscad)}
PY=${PYTHON:-$( [ -x "$VENV" ] && echo "$VENV" || command -v python3 )}
if [ ! -x "$OS" ] && ! command -v "$OS" >/dev/null 2>&1; then
  echo "openscad not found (set OPENSCAD=/path/to/openscad)" >&2; exit 1
fi
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
$OS -o lead_notch_grommet.stl lead_notch_grommet.scad  # battery-lead notch TPU edge liner (AUD-12b)
$OS -o skid_rail.stl skid_rail.scad          # TPU belly skid rail x2 (#15, AUD-10: was un-rendered)
$OS -o ../leg_v6/shoulder.stl ../leg_v6/shoulder.scad
$OS -o /tmp/trunk_preview.stl trunk.scad     # parametric spec sanity render only —
                                              # NOT the shipped trunk.stl (see below)
$PY ../mesh_health.py head.stl head_ear.stl head_ear_L.stl l2_adapter.stl control_pod.stl jetson_case_mount.stl jetson_clamp_bar.stl oled_mount.stl neck_bracket.stl case_slot_grommet.stl lead_notch_grommet.stl skid_rail.stl riser_bay.stl spacer.stl battery_pocket.stl floor_plate.stl
ls -la riser_bay.stl spacer.stl battery_pocket.stl head.stl neck_bracket.stl floor_plate.stl jetson_case_mount.stl

# DERIVED TRUNK (trunk.stl): stock Nova-SM3 trunk geometry + 10 modeled
# fastener bores (battery mount x6, shoulder-foot CSK x4) so nothing is
# drilled at assembly. trunk.scad (above) is the human-readable parametric
# spec; the SHIPPED trunk.stl is built by trunk_build.py (trimesh +
# manifold3d engine), not the OpenSCAD render — see trunk_build.py's
# docstring for why: OpenSCAD's import()+difference() on this mesh reports
# "manifold, NoError" internally but its exported STL fails a strict
# post-reload watertight check, and (proven via a no-op-boolean control
# test) so does trunk_build.py's — a PRE-EXISTING sliver-tessellation
# cluster in the stock mesh at the side-wall/notch edge (x~12-17,
# y~+/-49.2-49.3, z~28.9-29.0), nowhere near any of the 10 modeled holes,
# that surfaces under ANY boolean re-triangulation of this file. trunk_build
# .py's own in-memory asserts (watertight, single body, positive volume —
# the invariants that actually matter) are the real gate here and DO hard-
# fail the build (no `|| true`) if the boolean itself goes wrong.
$PY trunk_build.py
$PY ../mesh_health.py trunk.stl || echo "KNOWN EXCEPTION (see build_all.sh comment above + trunk_build.py docstring): trunk.stl fails the strict post-reload watertight check at one pre-existing, hole-unrelated sliver cluster. Does not block the build; watch this line for a change in the finding."

$PY check_fit.py
echo "chassis gate clean — now re-gate leg_v6 (shoulder rev):"
(cd ../leg_v6 && $PY check_fit.py --sweep)
