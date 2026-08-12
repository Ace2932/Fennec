#!/usr/bin/env python3
"""Regenerate the SUPPORTS table in docs/checklists/print-batch.md.

WHY THIS EXISTS. `slice_plate.py`'s registry is the authority on supports and
orientation, but hand-slicing in Bambu Studio never consults it, so the list has
to be reproduced where a human reads it before printing. A hand-copied table of a
registry drifts — the first attempt (PR #273) drifted between being written and
being merged: it claimed "12 ON / 16 OFF" and by merge time the registry said
12/17, because `oled_tray` landed in between.

So: generate it, and gate it. `test_supports_table_matches_registry.py` calls
`render()` and requires the file to match byte-for-byte.

    python hardware/cad/gen_supports_table.py          # rewrite the block
    python hardware/cad/gen_supports_table.py --check   # exit 1 if stale
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slice_plate as sp  # noqa: E402

DOC = HERE.parent.parent / "docs/checklists/print-batch.md"
START = "<!-- GENERATED BLOCK: supports-table."
END = "<!-- END GENERATED BLOCK: supports-table -->"


def _orient(p) -> str:
    if p.down:
        return p.down
    if p.manual:
        return p.manual.split("--")[0].strip()[:38]
    return "as modelled"


def render() -> str:
    on = sorted(n for n, p in sp.PARTS.items() if p.supports != "none")
    off = sorted(n for n, p in sp.PARTS.items() if p.supports == "none")
    L = [
        "### 2a-0. 🔴 SUPPORTS — the whole list, in one place",
        "",
        START,
        "     `test_supports_table_matches_registry.py` regenerates and compares this.",
        "     Regenerate: python hardware/cad/gen_supports_table.py -->",
        "",
        "`hardware/cad/slice_plate.py`'s registry is **the authority**. Hand-slicing in Bambu",
        "Studio never consults it, so it is reproduced here — and a test keeps the two in sync,",
        "because the first version of this table drifted between being written and being merged.",
        "",
        f"**{len(on)} parts need supports; {len(off)} must have them OFF.** "
        "Check before every print.",
        "",
        "**SUPPORTS ON:**",
        "",
        "| part | supports | material | orientation |",
        "|---|---|---|---|",
    ]
    for n in on:
        p = sp.PARTS[n]
        L.append(f"| `{n}` | {p.supports} | {p.material} | {_orient(p)} |")
    L += ["", "**SUPPORTS OFF** (`none`) — turning them on traps material:", "",
          "| part | material | orientation |", "|---|---|---|"]
    for n in off:
        p = sp.PARTS[n]
        L.append(f"| `{n}` | {p.material} | {_orient(p)} |")
    L += ["", END]
    return "\n".join(L)


def _splice(doc_text: str, block: str) -> str:
    head = doc_text.find("### 2a-0.")
    if head < 0:
        raise SystemExit("anchor '### 2a-0.' not found in print-batch.md")
    tail = doc_text.find(END, head)
    if tail < 0:
        raise SystemExit("END marker not found — refusing to guess the block extent")
    return doc_text[:head] + block + doc_text[tail + len(END):]


def main(argv):
    text = DOC.read_text()
    want = _splice(text, render())
    if "--check" in argv:
        if text != want:
            print("STALE: print-batch.md's supports table no longer matches "
                  "slice_plate.py. Run: python hardware/cad/gen_supports_table.py")
            return 1
        print("OK: supports table matches the registry")
        return 0
    DOC.write_text(want)
    print(f"rewrote the supports block in {DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
