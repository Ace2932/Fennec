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

## Backfill records (2026-09-05)

The 19 `backfill-<part>.json` files predate `slice_plate.py` recording anything
for these parts — they exist to answer "which revision is this bench part?" for
parts that were already printed before this directory had a writer. They are
**hand-authored**, not written by `slice_plate.py`: built by hashing every STL
export sitting in `~/Downloads` against every git revision of the matching repo
path, then cross-checking that against print-batch.md / STATUS.md / memory for
what was actually printed and when.

Key set (from `backfill-cable_clip.json`): `part`, `printed`, `backfilled`,
`repo_path`, `material`, `settings`, `source`, `status`, `downloads_exports`,
`notes` — a different, smaller set than the `slice_plate.py` schema above, and
filed as `backfill-<part>.json` rather than `{git_head}-{stem}.json`.

`printed` is `true` only where there is cited evidence the part was actually
printed — a ✅ line in `docs/checklists/print-batch.md`, or a STATUS.md /
BUILD_PLAN / memory line saying so. A Downloads export alone is not evidence:
it proves a slice or export happened, not a print (see `backfill-grommet_insert.json`,
corrected 2026-09-05 — the only evidence had been its own Downloads export,
while print-batch.md:82 still showed it unprinted). Everywhere the evidence is
export-only, `printed` is `null`, with a `printed_evidence` field explaining why.
