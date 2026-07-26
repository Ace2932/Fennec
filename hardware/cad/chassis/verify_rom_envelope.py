#!/usr/bin/env python3
"""Re-verify the SHIPPED posture-gate table against the real meshes (issue #146).

The gate in nova_ops is now the only thing protecting the chassis from a leg
fold (issue #142), and its bounds come from a GENERATED table,
nova_ops/rom_envelope_table.py. Nothing tied that table back to the geometry it
claims to describe: the unit tests check rom_envelope against its own table, so
a bad regeneration — wrong haa sign convention, base/pivot mismatch, stale STLs
— would pass the entire suite silently.

That is not hypothetical. Both of these happened while the table was being
built, and were caught only by noticing the numbers disagreed with check_fit:
  * canonical -> check_fit haa sign inverted (mirrors the whole table)
  * the FL base paired with the FR haa pivot (rotates about the wrong hip)

This script re-tests EVERY cell of the SHIPPED table against live mesh
containment (~4 s). For each sampled (leg, haa, kfe) it asserts:
    just INSIDE the stored bound  -> still contact-free
    just OUTSIDE the stored bound -> actually touches something
The second half is the one that matters: it proves the bound is a real boundary
and not merely a number that happens to be conservative.

Exit 0 = table matches geometry. Exit 1 = drift; regenerate with hfe_envelope.py.

  ../../../.venv/bin/python verify_rom_envelope.py [--quick]
"""
import sys

import numpy as np

import check_fit as cf
import hfe_envelope as H

sys.path.insert(0, "../../../ros2_ws/src/nova_ops")
from nova_ops.rom_envelope_table import ENVELOPE, HAAS, KFES  # noqa: E402

PROBE = 0.6          # deg, how far either side of the stored edge to test
OPEN_EDGE = 94.0     # |bound| >= this means "never contacted in the sweep range"


def sampled_cells(every: int):
    for leg in ENVELOPE:
        for ki, kfe in enumerate(KFES):
            for hi, haa in enumerate(HAAS):
                if (ki * len(HAAS) + hi) % every:
                    continue
                yield leg, haa, kfe, ENVELOPE[leg][kfe][hi]


def main():
    # FULL COVERAGE BY DEFAULT. This was sampled every 7th cell, and the
    # negative control exposed why that is useless for a verifier: corrupting
    # one cell (FL kfe-109 haa+40, +8 deg looser) was NOT caught, because that
    # index simply was not sampled. Full sweep is 680 cells in ~4 s -- there is
    # no reason to sample. --quick exists only for an interactive sanity pass
    # and must NOT be what a gate runs.
    every = 7 if "--quick" in sys.argv else 1
    cf.LEGPTS = cf.load_leg_parts()
    tgts = H.targets()
    bases = dict(cf.coax_to_trunk_bases())

    checked = fails = skipped = 0
    for leg, haa, kfe, (lo, hi) in sampled_cells(every):
        base = bases[leg]
        pivot = [cf.HIP_FA if leg[0] == "F" else -cf.HIP_FA,
                 cf.HIP_LAT if leg[1] == "R" else -cf.HIP_LAT, cf.HIP_Z]
        for edge, direction in ((lo, -1), (hi, +1)):
            if abs(edge) >= OPEN_EDGE:
                skipped += 1        # open edge: nothing to contact, nothing to prove
                continue
            if lo == 0.0 and hi == 0.0:
                skipped += 1        # degenerate cell: hfe_envelope.edge() returns 0
                continue            # when even the NEUTRAL pose is not clear, so
                                    # there is no boundary here to probe either side of
            checked += 1
            inside = H.clear(leg, base, pivot, tgts, haa, edge - direction * PROBE, kfe)
            outside = H.clear(leg, base, pivot, tgts, haa, edge + direction * PROBE, kfe)
            if not inside or outside:
                fails += 1
                why = ("interior NOT clear" if not inside
                       else "beyond the bound is STILL clear -> bound is not the boundary")
                print(f"  DRIFT {leg} haa{haa:+d} kfe{kfe:+d} edge {edge:+.1f}: {why}")

    print(f"\nchecked {checked} live boundary probes across "
          f"{len(list(sampled_cells(every)))} cells ({skipped} open edges skipped)")
    if fails:
        print(f"FAIL — {fails} probes disagree with the shipped table. "
              f"Regenerate: ../../../.venv/bin/python hfe_envelope.py")
        return 1
    print("OK — shipped table matches the meshes it claims to describe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
