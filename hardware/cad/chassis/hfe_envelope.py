#!/usr/bin/env python3
"""Measure the FRONT/REAR hfe contact envelope as a function of (haa, kfe).

FRAMES: `hfe` is swept inside cf.leg_cloud(), i.e. LEG-LOCAL (coax frame), where
+hfe means "fold toward the trunk" for whichever leg it is placed on. The rear
hip is the front placement YAWED 180 deg about Z (check_fit.coax_to_trunk_bases),
so toward-the-trunk is REARWARD at the front and FORWARD at the rear, while
canonical/URDF +hfe is uniformly rearward on all four. The table is emitted
LEG-LOCAL and the CONSUMER converts (nova_ops.rom_envelope._to_canonical):

    canonical_front = ( lo, hi)      canonical_rear = (-hi, -lo)

Exactly ONE side may do that. Do NOT negate here as well -- a double negation
puts the rear bound back on the wrong side, permitting the folds that reach the
riser. Regenerated 2026-07-26 against the corrected placement with the real
servo.stl; the FRONT rows reproduce the previous table bit-for-bit, which is
what validates the run.

Output is a Python table for nova_locomotion/kinematics/rom_envelope.py.

  ../../../.venv/bin/python hfe_envelope.py            # writes rom_envelope_table.py
"""
import pathlib

import numpy as np
import trimesh

import check_fit as cf
import cad_contains   # (#195 -- installed in main(); path set up by check_fit)

# CANONICAL: + = OUTBOARD, - = inboard. FINE near the inboard belly-pack edge:
# the bound collapses hard once the leg rolls under the pack (inboard >15, which
# the separate haa cap already forbids), so a coarse 10-deg grid there drags a
# collapsed neighbour into every conservative bracket just inside the cap.
#
# REFINED AGAIN 2026-07-28 (#181). The band above was still too coarse across
# two transitions, and conservative bracketing projects a step back across the
# WHOLE span between samples, so a 2-deg gap with a 43-deg step behaves like a
# cliff 2 deg wide. Measured on the previous grid (FL, worst over kfe):
#
#     haa -12 -> -10  ( 2 deg apart):  +43.3 deg step
#     haa  -5 ->   0  ( 5 deg apart):   +9.6 deg step
#
# The second one is load-bearing: the trot peaks at +59.4 deg fold and only
# fits because it commands haa EXACTLY 0.00 (see trot.py). One thousandth of a
# degree inboard dropped the cap to 56.7 and clipped it. These extra samples
# LOCALISE each crossing -- the steps are real geometry (the leg crossing an
# obstacle edge), so the point is to stop projecting them across degrees of haa
# the leg is actually clear in.
#
# NOT refined below -15: the haa cap forbids it, so those cells are only ever
# reached as a clamped edge bracket and finer sampling there buys nothing.
HAAS = [-40, -30, -20, -15, -12, -11.5, -11, -10.5, -10, -8, -5,
        -4, -3, -2, -1, -0.5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
# S2 (review 2026-07-25): POSITIVE kfe is now swept. It was not, so every
# kfe > 0 query extrapolated from the kfe=0 row — an unvalidated region inside a
# safety gate. solve_side(knee_forward=True) produces positive kfe.
KFES = [-109, -90, -70, -50, -25, 0, 25, 50, 75, 109]
HFE_LO, HFE_HI = -95.0, 95.0
# 0.5 deg, was 2.5. The verifier caught the reason: at 2.5 the scan STEPPED OVER
# a blocked sliver below the returned edge (FL haa-5 kfe-109 reported +57.6 while
# +57.0 was already blocked), so the stored bound was not a contiguous safe
# interval — exactly the granularity half of S4. Proximity is ~1 ms per probe, so
# 5x the steps costs ~3 min for the whole sweep.
COARSE = 0.5                              # deg, scan step
FINE_ITERS = 5                            # bisection refinement -> ~0.08 deg
# ...OF THE SCAN. That 0.08 is NOT the precision of the printed number, and the
# table is printed to 0.1 as if it were. leg_cloud() poses a MONTE-CARLO point
# cloud (load_leg_parts -> sample_surface, 4000-5000 points per part), so
# re-drawing the cloud moves the boundary this bisects toward.
#
# MEASURED 2026-08-06, 150 cells (FL+RR x kfe -109/0/75 x all 25 haa), geometry
# byte-identical, by overriding the seed= that load_leg_parts passes:
#     same seed, two processes  ->   0/150 cells differ   (deterministic; the
#                                    #195 seeding does hold here)
#     four different seeds      -> 142/150 cells differ, max spread 1.36 deg,
#                                  p95 0.89, median 0.31  -- ~17x the 0.08
# A cell can therefore sit ~1.4 deg LOOSER than the geometry, which is the
# unsafe direction. The consumer carries that as nova_ops.rom_envelope
# MARGIN_DEG = 1.5; raising the sample counts here would shrink the scatter as
# 1/sqrt(n) (4x the points to halve it) and is the real fix if the headroom is
# ever needed back.


def targets():
    riser = trimesh.load("riser_bay.stl")
    pocket = trimesh.load("battery_pocket.stl")
    head = trimesh.load("head.stl")
    pack = cf.make_box(-77.5, 77.5, -23.4, 23.4, -35.9, -0.9)
    rails = trimesh.util.concatenate([
        cf.make_box(-55, 75, 9, 21, -42.2, -39.2),
        cf.make_box(-55, 75, -21, -9, -42.2, -39.2)])
    # (name, mesh, spatial prefilter) — same filters as check_fit's crouch sweep
    return [
        ("riser", riser, lambda p: (np.abs(p[:, 0]) < 70) & (np.abs(p[:, 1]) < 58)
         & (p[:, 2] > 25) & (p[:, 2] < 75)),
        ("pocket", pocket, lambda p: (np.abs(p[:, 0]) < 95) & (np.abs(p[:, 1]) < 35)
         & (p[:, 2] > -45) & (p[:, 2] < 5)),
        ("pack", pack, lambda p: (np.abs(p[:, 0]) < 90) & (np.abs(p[:, 1]) < 30)
         & (p[:, 2] > -40) & (p[:, 2] < 1)),
        ("rails", rails, lambda p: (np.abs(p[:, 0]) < 90) & (np.abs(p[:, 1]) < 30)
         & (p[:, 2] > -46) & (p[:, 2] < -35)),
        ("head", head, lambda p: (p[:, 0] > 100) & (p[:, 0] < 146)
         & (np.abs(p[:, 1]) < 40) & (p[:, 2] > 82)),
    ]


# REQUIRED PHYSICAL GAP (issue #146 / S4). The boundary is now "the leg comes
# closer than this to the chassis", not "a sampled point is already inside it".
# 5 mm matches what the project already used implicitly: the published +50 cap
# vs ~+55 measured contact is 5 deg, which at full outboard splay is ~5 mm of
# real gap. Stated in millimetres it means the same thing at EVERY posture --
# the angular version was worth ~5 mm at haa +40 but noticeably more at haa 0.
CLEARANCE_MM = 5.0


def clear(label, base, pivot, tgts, haa, hfe, kfe):
    """True if the posed leg touches NOTHING.

    `haa` is CANONICAL (outboard-positive, the leg_ik frame). check_fit's own
    haa is inboard-positive for an L-leg placement (`inboard = haa` there), i.e.
    the negation — so negate on the way into cf.rot. Sanity check: canonical
    +40 (full outboard splay) must land on the documented ~+50 front worst case.
    """
    # canonical -> check_fit haa. check_fit sets inboard = -haa on an R leg and
    # +haa on an L leg; canonical is OUTBOARD-positive, so haa_cf = -canonical
    # on the LEFT and +canonical on the RIGHT. Derived per leg, because getting
    # it backwards silently mirrors the entire table.
    Sx = cf.rot(haa if label[1] == "R" else -haa, [1, 0, 0], pivot)
    p = cf.tf(cf.tf(cf.leg_cloud(hfe, kfe), base), Sx)
    for _name, mesh, filt in tgts:
        sub = p[filt(p)]
        if not len(sub):
            continue
        if mesh.contains(sub).any():
            return False
        # PROXIMITY, not just intersection (issue #146 / S4). Containment flips
        # only once a SAMPLED point is already inside the solid, which is late
        # twice over: the cloud is sparse, so a tangential graze can register
        # zero points while the surfaces touch; and a 2.5 deg scan step is ~6.5 mm
        # of arc at the tibia flank, wide enough to step over a boss or rib
        # entirely. Requiring a real gap fixes both — a feature is detected from
        # CLEARANCE_MM away rather than only when a sample lands inside it.
        if CLEARANCE_MM > 0.0:
            if mesh.nearest.on_surface(sub)[1].min() < CLEARANCE_MM:
                return False
    return True


def edge(label, base, pivot, tgts, haa, kfe, direction):
    """Scan outward from hfe=0 in `direction` (+1/-1) to the first contact."""
    if not clear(label, base, pivot, tgts, haa, 0.0, kfe):
        return 0.0                                   # even neutral touches
    last_ok = 0.0
    limit = HFE_HI if direction > 0 else HFE_LO
    x = 0.0
    while (x + direction * COARSE) * direction <= abs(limit):
        x += direction * COARSE
        if clear(label, base, pivot, tgts, haa, x, kfe):
            last_ok = x
        else:
            lo, hi = last_ok, x                      # lo clear, hi blocked
            for _ in range(FINE_ITERS):
                mid = 0.5 * (lo + hi)
                if clear(label, base, pivot, tgts, haa, mid, kfe):
                    lo = mid
                else:
                    hi = mid
            return lo
    return last_ok


def main():
    # #195: this is a GENERATED-ARTIFACT PRODUCER, not just a gate -- CI
    # regenerates rom_envelope_table.py from it and compares. A producer whose
    # output can shift run to run turns a freshness check into a coin flip in
    # both directions: false STALE on an untouched tree, and a real staleness
    # masked by a lucky match. Seed before computing anything.
    cad_contains.install()
    # Inputs are loaded by bare name via check_fit (chassis STLs), so this has
    # to run from this directory. chdir HERE rather than at module scope:
    # verify_rom_envelope.py imports this module, and an import that silently
    # changes the caller's cwd is its own bug.
    import os
    os.chdir(pathlib.Path(__file__).resolve().parent)
    cf.LEGPTS = cf.load_leg_parts()
    tgts = targets()
    bases = dict(cf.coax_to_trunk_bases())
    rows = {}
    # S3 (review 2026-07-25): all FOUR legs are swept and stored PER LEG.
    # Previously only FL and RL were, with the right side assumed
    # mirror-identical — an unverified assumption inside a safety gate.
    # check_fit itself sweeps all four.
    for label in ("FL", "FR", "RL", "RR"):
        end = label
        base = bases[label]
        # pivot must match the base: check_fit uses +HIP_LAT for 'R', -HIP_LAT for 'L'
        pivot = [cf.HIP_FA if label[0] == "F" else -cf.HIP_FA,
                 cf.HIP_LAT if label[1] == "R" else -cf.HIP_LAT, cf.HIP_Z]
        print(f"\n== {label} ==   hfe contact-free interval, degrees")
        # `g`, not `d`: the haa grid carries half-degree samples since #181
        print("   kfe \\ haa " + "".join(f"{h:>14g}" for h in HAAS))
        for kfe in KFES:
            cells = []
            for haa in HAAS:
                lo = edge(label, base, pivot, tgts, haa, kfe, -1)
                hi = edge(label, base, pivot, tgts, haa, kfe, +1)
                cells.append((lo, hi))
                rows[(end, haa, kfe)] = (lo, hi)
            print(f"   {kfe:>6d}    " +
                  "".join(f"  [{lo:+6.1f},{hi:+6.1f}]" for lo, hi in cells))

    import io
    f = io.StringIO()
    if True:
        f.write('"""GENERATED by hardware/cad/chassis/hfe_envelope.py — do not edit.\n\n'
                'Contact-free hfe interval (degrees) per leg and (haa, kfe) cell.\n\n'
                'FRAMES — the two axes are NOT in the same frame, read this before use:\n'
                '  haa  is CANONICAL: POSITIVE = OUTBOARD splay, every leg. Outboard is\n'
                '       fixed by which SIDE the leg is on, and the rear yaw does not\n'
                '       change a corner\'s side, so haa needs no per-leg correction.\n'
                '  hfe  is LEG-LOCAL (the coax frame cf.leg_cloud sweeps in), NOT\n'
                '       canonical. +hfe here = fold TOWARD THE TRUNK for whichever leg\n'
                '       it is. The REAR hip is the front placement YAWED 180 deg about Z\n'
                '       (check_fit.coax_to_trunk_bases, fixed 2026-07-26), so toward-the-\n'
                '       trunk is REARWARD at the front and FORWARD at the rear, while\n'
                '       canonical/URDF +hfe is uniformly rearward on all four\n'
                '       (leg.macro.xacro axis 0 1 0). Therefore:\n\n'
                '           canonical_front = ( lo, hi)          # unchanged\n'
                '           canonical_rear  = (-hi, -lo)         # negate AND swap\n\n'
                '       The CONSUMER performs that conversion — nova_ops.rom_envelope\n'
                '       does it in _to_canonical(). Do NOT also negate here on\n'
                '       regeneration: exactly one side may do it, and doing it twice\n'
                '       puts the rear bound back on the wrong side, permitting the\n'
                '       folds that reach the riser.\n\n'
                f'Boundary = the leg comes within {CLEARANCE_MM} mm of the chassis\\n'
                '(proximity, not intersection), so the gap is already included.\n'
                'Measured against riser_bay / battery_pocket / pack / skid rails / head.\n'
                '"""\n')
        f.write(f"CLEARANCE_MM = {CLEARANCE_MM!r}\nHAAS = {HAAS!r}\nKFES = {KFES!r}\n")
        f.write("ENVELOPE = {\n")
        for end in ("FL", "FR", "RL", "RR"):
            f.write(f'    "{end}": {{\n')
            for kfe in KFES:
                vals = [rows[(end, h, kfe)] for h in HAAS]
                f.write(f"        {kfe}: {[(round(a,1), round(b,1)) for a,b in vals]!r},\n")
            f.write("    },\n")
        f.write("}\n")

    # Fan out to BOTH destinations. The nova_ops copy used to be carried by
    # hand: this generator wrote one file, a human moved it, and nothing
    # enforced that they matched (#219). The copy that mattered was the one
    # nobody re-ran — nova_ops reads this envelope for the posture backstop,
    # while the chassis copy only feeds CAD gates.
    #
    # Paths resolve from THIS FILE, not the cwd. The old `open("rom_envelope_
    # table.py", "w")` wrote wherever you happened to be standing, so running
    # this from the repo root silently produced a stray table at the root and
    # left the real ones untouched.
    text = f.getvalue()
    here = pathlib.Path(__file__).resolve().parent
    proj = here.parents[2]
    dests = [
        here / "rom_envelope_table.py",
        proj / "ros2_ws" / "src" / "nova_ops" / "nova_ops" / "rom_envelope_table.py",
    ]
    for d in dests:
        d.write_text(text)
    print("\nwrote " + " + ".join(str(d.relative_to(proj)) for d in dests))


if __name__ == "__main__":
    main()
