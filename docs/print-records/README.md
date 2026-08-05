# Print records

One JSON per sliced plate, written by `hardware/cad/slice_plate.py`.

Each record answers **"which revision is this printed part, and what settings
made it?"** — the question that was previously answered from memory, and
answered wrong at least twice (the printed `shoulder` on the bench is a
pre-chamfer revision; the coax was redesigned under #234/#235/#240 after parts
existed).

A record carries:

- `git_head` — the commit the STLs came from
- per part: `stl_sha256_16`, `scad_sha256_16`, orientation, bed contact
- `verified_gcode_keys` — the settings **read back out of the emitted G-code**,
  not the ones requested. See the module docstring in `slice_plate.py` for why
  those are different things.
- `stl_fresh_verified` — whether `check_stl_fresh.py` passed for that plate
- `gcode_sha256_16` — ties the record to one specific G-code file

**Commit a record when the plate is actually printed.** Records from
experiments and dry runs are noise here: a record that says "sliced" reads as
"printed" six months later, which is the same class of mistake this directory
exists to prevent.
