"""print-batch.md's SUPPORTS table still matches slice_plate.py's registry.

WHY THIS EXISTS. The registry is the authority on supports and orientation, but
hand-slicing in Bambu Studio never opens it — so the list has to be reproduced in
the checklist a human actually reads before printing. A hand-copied table of a
registry drifts, and this one proved it before it ever landed:

  PR #273 (2026-08-06) added the table by hand, claiming "12 parts need supports;
  16 must have them OFF". By the time it was reviewed the registry said 12/17,
  because `oled_tray` was registered on 2026-08-10. The table was stale between
  being written and being merged.

Getting supports wrong is not cosmetic in either direction: OFF where they are
needed droops or fails the print (battery_pocket: 639 mm² over air at a 34.8 mm
drop), and ON where they are not traps material inside the part.

So the table is GENERATED (`hardware/cad/gen_supports_table.py`) and this test
asserts the file still equals what the generator would write.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[4]
GEN = REPO / "hardware/cad/gen_supports_table.py"
DOC = REPO / "docs/checklists/print-batch.md"


def _load_gen():
    sys.path.insert(0, str(GEN.parent))
    import importlib
    mod = importlib.import_module("gen_supports_table")
    importlib.reload(mod)
    return mod


def test_sources_exist():
    assert GEN.is_file(), f"generator missing at {GEN}"
    assert DOC.is_file(), f"print-batch.md missing at {DOC}"


def test_table_is_present_at_all():
    """Guard on the guard: an absent block would make the comparison vacuous."""
    text = DOC.read_text()
    assert "GENERATED BLOCK: supports-table" in text, (
        "the supports block is gone from print-batch.md — the comparison below "
        "would pass trivially on a document with no table in it"
    )
    assert text.count("END GENERATED BLOCK: supports-table") == 1


def test_table_matches_the_registry():
    mod = _load_gen()
    want = mod.render()
    text = DOC.read_text()
    start = text.find("### 2a-0.")
    end = text.find(mod.END, start)
    assert start >= 0 and end >= 0, "block markers not found"
    got = text[start:end + len(mod.END)]
    assert got == want, (
        "print-batch.md's SUPPORTS table no longer matches slice_plate.py.\n\n"
        "Run:  python hardware/cad/gen_supports_table.py\n\n"
        "This is not pedantry — the table is what a human reads at the printer, "
        "and the registry is what the gates enforce. PR #273's hand-written "
        "version was already stale by one part before it merged."
    )


def test_generator_check_mode_agrees():
    """--check must reach the same verdict as the comparison above."""
    r = subprocess.run([sys.executable, str(GEN), "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, f"--check reports stale:\n{r.stdout}{r.stderr}"


def test_every_registered_part_appears():
    """Counts in the prose must equal the registry, not just the rows."""
    mod = _load_gen()
    sp = mod.sp
    text = DOC.read_text()
    for name in sp.PARTS:
        assert f"`{name}`" in text, (
            f"{name} is registered in slice_plate.py but absent from the "
            "supports table — exactly the drift this file exists to catch"
        )
