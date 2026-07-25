#!/usr/bin/env python3
"""Measure the FRONT/REAR hfe contact envelope as a function of (haa, kfe).

WHY: the chassis ROM has been carried as a single scalar — "hfe toward-trunk fold
+50 deg" — but the constraint is genuinely 3-dimensional. The corrected crouch
sweep (check_fit.py, rear placement fixed 2026-07-25) shows the front leg's first
riser contact moving with posture:

    haa   0                 no contact anywhere, out to hfe +86
    haa -15, kfe -109       first contact +70
    haa -40, kfe -109       first contact +55     <- the number the scalar came from

so +50 is a worst-case over the WHOLE haa x kfe grid. Both primary gaits run the
front legs at haa 0 / kfe ~-98.8 and are geometrically clear at +59.4, yet they
fail a scalar +50 check. Shrinking the gaits to satisfy a worst-case scalar would
cost real stride for no clearance.

This emits the actual boundary so within_limits can be posture-aware. For each
leg END and each (haa, kfe) cell it finds the widest CONTACT-FREE hfe interval,
tested against every chassis target the crouch sweep uses (riser, battery pocket,
pack, skid rails, head).

Output is a Python table for nova_locomotion/kinematics/rom_envelope.py.

  ../../../.venv/bin/python hfe_envelope.py            # writes rom_envelope_table.py
"""
import numpy as np
import trimesh

import check_fit as cf

# CANONICAL: + = OUTBOARD, - = inboard. FINE near the inboard belly-pack edge:
# the bound collapses hard once the leg rolls under the pack (inboard >15, which
# the separate haa cap already forbids), so a coarse 10-deg grid there drags a
# collapsed neighbour into every conservative bracket just inside the cap.
HAAS = [-40, -30, -20, -15, -12, -10, -8, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
KFES = [-109, -90, -70, -50, -25, 0]
HFE_LO, HFE_HI = -95.0, 95.0
COARSE = 2.5                              # deg, scan step
FINE_ITERS = 5                            # bisection refinement -> ~0.08 deg


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


def clear(label, base, pivot, tgts, haa, hfe, kfe):
    """True if the posed leg touches NOTHING.

    `haa` is CANONICAL (outboard-positive, the leg_ik frame). check_fit's own
    haa is inboard-positive for an L-leg placement (`inboard = haa` there), i.e.
    the negation — so negate on the way into cf.rot. Sanity check: canonical
    +40 (full outboard splay) must land on the documented ~+50 front worst case.
    """
    Sx = cf.rot(-haa, [1, 0, 0], pivot)
    p = cf.tf(cf.tf(cf.leg_cloud(hfe, kfe), base), Sx)
    for _name, mesh, filt in tgts:
        sub = p[filt(p)]
        if len(sub) and mesh.contains(sub).any():
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
    cf.LEGPTS = cf.load_leg_parts()
    tgts = targets()
    bases = dict(cf.coax_to_trunk_bases())
    rows = {}
    for end, label in (("FRONT", "FL"), ("REAR", "RL")):
        base = bases[label]
        # pivot must match the base: check_fit uses +HIP_LAT for 'R', -HIP_LAT for 'L'
        pivot = [cf.HIP_FA if label[0] == "F" else -cf.HIP_FA,
                 -cf.HIP_LAT, cf.HIP_Z]
        print(f"\n== {end} ({label}) ==   hfe contact-free interval, degrees")
        print("   kfe \\ haa " + "".join(f"{h:>14d}" for h in HAAS))
        for kfe in KFES:
            cells = []
            for haa in HAAS:
                lo = edge(label, base, pivot, tgts, haa, kfe, -1)
                hi = edge(label, base, pivot, tgts, haa, kfe, +1)
                cells.append((lo, hi))
                rows[(end, haa, kfe)] = (lo, hi)
            print(f"   {kfe:>6d}    " +
                  "".join(f"  [{lo:+6.1f},{hi:+6.1f}]" for lo, hi in cells))

    with open("rom_envelope_table.py", "w") as f:
        f.write('"""GENERATED by hardware/cad/chassis/hfe_envelope.py — do not edit.\n\n'
                'Contact-free hfe interval (degrees, canonical frame) per leg END and\n'
                '(haa, kfe) cell. haa is CANONICAL: POSITIVE = OUTBOARD splay.\n'
                'Measured against riser_bay / battery_pocket / pack /\n'
                'skid rails / head with the corrected (unmirrored) rear hip placement.\n'
                '"""\n')
        f.write(f"HAAS = {HAAS!r}\nKFES = {KFES!r}\n")
        f.write("ENVELOPE = {\n")
        for end in ("FRONT", "REAR"):
            f.write(f'    "{end}": {{\n')
            for kfe in KFES:
                vals = [rows[(end, h, kfe)] for h in HAAS]
                f.write(f"        {kfe}: {[(round(a,1), round(b,1)) for a,b in vals]!r},\n")
            f.write("    },\n")
        f.write("}\n")
    print("\nwrote rom_envelope_table.py")


if __name__ == "__main__":
    main()
