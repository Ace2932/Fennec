// LEFT head ear = Y-mirror of the right part (head_ear.scad).
// PRINT: as head_ear.scad — plain PETG or ASA, NOT a CF filament (#32: carbon
//   fibre is conductive at 2.4/5 GHz and detunes/absorbs the antenna whip).
//   Same EAR_YAW edge-on orientation, mirrored. UNRESOLVED in slice_plate.py
//   (#184) pending a non-CF entry in MATERIALS — see that file's
//   UNRESOLVED["head_ear_L"] note; not guessed here.
$fn = 32;
use <head_ear.scad>
mirror([0, 1, 0]) head_ear();
