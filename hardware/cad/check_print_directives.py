#!/usr/bin/env python3
"""Does every registered part's .scad state a material CI can check? (#184)

WHY THIS EXISTS. slice_plate.py's PARTS registry has always been the
authoritative material + orientation source, but nothing enforced that a human
opening the .scad could see the same answer — 16 parts (79% of build mass)
carried it only in the registry, or as stress-analysis prose the registry's own
`scad_material()` parser could not find. The `strap` part went further: its
.scad said one material, `build_all.sh`'s comment said another, and nothing
caught the disagreement until a human read both files side by side. The same
shape recurred with `jetson_case_mount` (found closing this issue): its .scad
said PA6-CF, the registry said PETG-CF, and `scad_material()` missed the
disagreement anyway because the material sat on a continuation line instead of
the line the parser reads.

`check_material_agreement()` in slice_plate.py already computes exactly this —
but only when a human runs an actual slice. This file runs that same check as
a CI gate, so a PR that edits a .scad header without ever slicing anything
still gets caught.

WHAT IT CHECKS. For every part in slice_plate.py's PARTS registry:
  1. Its `scad=` file has a `// PRINT:` / `// Print:` line naming a known
     material (TPU 95A / PA6-CF / PETG-CF / ...). Absence is refused, not
     silently skipped the way `--list`'s coverage line does.
  2. That material matches the registry's `material` field, byte for byte
     after normalisation.

Both checks reuse `slice_plate.scad_material()` and `check_material_agreement()`
directly — the parsing rules (including the `use <...>` mirror fallback) live
in exactly one place, not copied here to drift out of sync with it.

WHAT IT DOES NOT CHECK. `UNRESOLVED` parts (trunk, head_ear, head_ear_L) are
deliberately out of scope: they are refused by slice_plate.py itself, for
reasons recorded there, and are not guessed at here either — see each file's
own "OPEN ITEM (#184)" header note instead. Nor are `RETIRED` parts (spacer),
for a different reason: the robot no longer has them, so there is no material
decision to be right about.

⚠️ Both of those lists are RETYPED here and nothing enforces the copy. `spacer`
sat in this sentence under UNRESOLVED after it had moved to RETIRED, in the
same change that moved it — caught by review, not by a gate. If a third
category appears, or a part moves between them, this line goes stale silently.

Usage:
    python check_print_directives.py
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from slice_plate import PARTS, check_material_agreement  # noqa: E402


def main() -> int:
    parts = sorted(PARTS.items())
    bad, unchecked = check_material_agreement(parts)

    print(f"-- print directives: {len(parts)} registered parts --")
    fail = False

    if unchecked:
        fail = True
        print(f"\nNO MATERIAL NAMED — {len(unchecked)} part(s)' .scad has no "
              f"'PRINT:' / 'Print:' line a known material can be read from:")
        for name in unchecked:
            print(f"  {name}: {PARTS[name].scad}")

    if bad:
        fail = True
        print(f"\nMATERIAL CONTRADICTION — {len(bad)} part(s) where the .scad "
              f"and the registry disagree:")
        for name, scad, declared, want in bad:
            print(f"  {name}: {scad} says {declared}, registry says {want}")

    if fail:
        print("\nFAIL: fix the .scad header (or the registry, if the .scad is "
              "right) so both agree — see slice_plate.py's PARTS doc= fields "
              "for the wording convention.")
        return 1

    print(f"OK: every registered part's .scad names a material, and it "
          f"matches slice_plate.py's registry ({len(parts)}/{len(parts)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
