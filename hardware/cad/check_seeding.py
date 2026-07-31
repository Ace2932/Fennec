#!/usr/bin/env python3
"""Every CI-run CAD gate that calls contains() must seed it (#195, #229).

WHY THIS EXISTS
---------------
The #195 determinism fix was applied to leg_v6/check_fit.py in 2026-07 and to
nothing else. It was found missing from chassis/check_fit.py on 2026-07-31, and
missing again from servo_orientation_gate.py, check_shoe.py and hfe_envelope.py
in the review of that fix. Three rounds of "propagate it by hand", three rounds
of missing sites. That is not a memory problem to try harder at -- it is a
convention with no enforcement, so this enforces it.

Same failure family as #226 (a mask copied past the argument that justified it)
and #47 (a dead window left in place beside its replacement). See
~/claude-memory/patterns/fixed-the-instance-not-the-convention.md.

WHAT IT CHECKS
--------------
Gate entrypoints are DISCOVERED, not listed: parsed out of build_all.sh and the
workflow YAMLs, so the set cannot go stale the way a hand-maintained list would
(that would just move the propagation problem into this file). For each
discovered entrypoint, if its source calls `.contains(` then it must also
reference cad_contains, or route through a helper that does.

HONEST LIMIT: this is a STATIC check on source text. It proves the seeding is
wired in, not that install() executes on every path -- a gate could import
cad_contains and never call install(). It catches the failure that actually
keeps happening (a new gate that never heard of #195), not every possible one.
Runtime proof lives in install() itself, which asserts the patch took and
prints `contains() seeding ACTIVE` into the job log.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent.parent

# a file is "seeded" if it names the shared module, or leg_v6/check_fit's own
# pre-existing private wrapper (migrating that one is tracked separately)
SEEDED_MARKERS = ('cad_contains', '_contains_seeded')

# Studies and one-off probes are deliberately out of scope: they are read by a
# human who is looking at the number, not by CI deciding whether to ship a part.
# Anything CI runs is in scope automatically by virtue of being discovered.


def discover_entrypoints():
    """Every *.py under hardware/cad that CI runs, directly OR indirectly.

    The indirect half matters and was missed on the first cut of this file:
    hfe_envelope.py appears in no workflow line at all, because CI runs
    check_generated_fresh.py, which re-runs it as a PRODUCER to regenerate
    rom_envelope_table.py. A discovery that only reads workflow command lines
    would have declared it out of scope -- the same blind spot this gate exists
    to close, one level up. Producers are therefore taken from
    check_generated_fresh's own ARTIFACTS table, imported rather than
    re-transcribed so it cannot drift.
    """
    found = set()
    sh = HERE / 'leg_v6' / 'build_all.sh'
    if sh.exists():
        for m in re.finditer(r'([A-Za-z0-9_./]+\.py)', sh.read_text()):
            found.add(m.group(1))
    wf = PROJ / '.github' / 'workflows'
    if wf.is_dir():
        for y in wf.glob('*.yml'):
            for m in re.finditer(r'python[^\n]*?([A-Za-z0-9_./]+\.py)', y.read_text()):
                found.add(m.group(1))
    # indirect: generated-artifact producers, from the real table
    sys.path.insert(0, str(HERE))
    try:
        import check_generated_fresh as cgf
        for _artifact, producer in cgf.ARTIFACTS:
            found.add(pathlib.Path(producer).name)
    except Exception as e:                                  # pragma: no cover
        print(f'FAIL: could not read check_generated_fresh.ARTIFACTS ({e}) -- '
              f'indirect producers would go unchecked, so this gate refuses to '
              f'report a pass it cannot back up')
        raise SystemExit(1)
    # resolve to real files under hardware/cad
    out = {}
    for name in found:
        base = pathlib.Path(name).name
        for cand in HERE.rglob(base):
            if cand.is_file():
                out[cand.relative_to(HERE).as_posix()] = cand
    return out


def main() -> int:
    entry = discover_entrypoints()
    if not entry:
        print('FAIL: discovered no gate entrypoints -- the parser is broken, '
              'which would make this check silently vacuous')
        return 1

    print(f'-- contains() seeding gate (#195/#229): {len(entry)} CI entrypoints '
          f'discovered --')
    bad = []
    me = pathlib.Path(__file__).resolve()
    for rel, path in sorted(entry.items()):
        if path.resolve() == me:
            # Wiring this into the workflow made its own regex discover it, and
            # it then matched BOTH its own search strings: it "calls contains()"
            # because the literal '.contains(' appears in the matcher below, and
            # it is "seeded" because it names cad_contains in its messages. Both
            # true of the text, neither true of the behaviour -- a fabricated OK
            # about itself, which is the exact reading error this gate exists to
            # catch. Exclude it rather than let it pad the pass count.
            continue
        src = path.read_text()
        if '.contains(' not in src:
            print(f'   n/a   {rel}: does not call contains()')
            continue
        if any(mark in src for mark in SEEDED_MARKERS):
            print(f'   OK    {rel}: seeded')
        else:
            bad.append(rel)
            print(f'   UNSEEDED {rel}: calls contains() but never references '
                  f'cad_contains -- its verdicts can differ between processes')

    if bad:
        print(f'FAIL: {len(bad)} CI gate(s) call contains() unseeded: '
              f'{", ".join(bad)}. Add `import cad_contains` and call '
              f'cad_contains.install() at the top of the entrypoint. See #195.')
        return 1
    print('   all CI gates that use contains() are seeded')
    return 0


if __name__ == '__main__':
    sys.exit(main())
