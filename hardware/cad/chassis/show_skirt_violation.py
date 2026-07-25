#!/usr/bin/env python3
"""What the FRONT-leg riser-skirt cap actually protects against.

Under the built TRANSLATED knee config (leg_ik.KNEE_FORWARD all-False) the trot
drives the front legs to hfe +59.4 deg, past the +50 deg chassis-gate cap. That
sounds like a collision — it is NOT one at the posture the gait uses.

The +50 cap is a WORST-CASE envelope over the whole haa x kfe grid. The corrected
check_fit crouch sweep puts the front leg's first riser contact at:

    haa   0                     -> no contact anywhere, out to hfe +86
    haa -15, kfe -109           -> first contact hfe +70
    haa -40, kfe -109           -> first contact hfe +55   (the number quoted)

i.e. the +55 figure needs FULL outboard splay AND full knee fold, together. Both
primary gaits run the front legs at haa = 0.00 with kfe ~ -98.8, so they sit in
the clear column. The scalar cap is conservative by construction; the gaits
exceed the SCALAR, not the geometry.

Nothing in the MJX sim can show this — nova.xml carries primitive collision only
(feet + a trunk box), no riser. So draw it against the real meshes check_fit
uses: riser_bay.stl plus the posed leg cloud, at the FRONT-LEFT hip, side view.
Leg points landing INSIDE the riser solid are the actual interference.

  ../../../.venv/bin/python show_skirt_violation.py
"""
import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import check_fit as cf

HFES = [50.0, 55.0, 59.4, 70.0]
ROWS = [
    (0.0, -98.75, "TROT / CRAWL actual posture:  haa 0, kfe -98.8"),
    (-40.0, -109.0, "the cap's worst case:  haa -40 (full splay), kfe -109"),
]


def main():
    cf.LEGPTS = cf.load_leg_parts()
    riser = trimesh.load("riser_bay.stl")
    # FRONT-LEFT hip — the end the corrected gate reports front riser contact on.
    # The haa pivot MUST match the base: check_fit uses +HIP_LAT for an 'R' leg
    # and -HIP_LAT for an 'L' leg, so FL pairs with -HIP_LAT.
    base = dict(cf.coax_to_trunk_bases())["FL"]
    pivot = [cf.HIP_FA, -cf.HIP_LAT, cf.HIP_Z]
    rv = riser.vertices

    fig, axes = plt.subplots(
        len(ROWS), len(HFES),
        figsize=(3.7 * len(HFES), 4.4 * len(ROWS)), sharex=True, sharey=True)

    for r, (haa, kfe, rowlab) in enumerate(ROWS):
        Sx = cf.rot(haa, [1, 0, 0], pivot)
        for c, hfe in enumerate(HFES):
            ax = axes[r][c]
            pts = cf.tf(cf.tf(cf.leg_cloud(hfe, kfe), base), Sx)
            near = pts[(np.abs(pts[:, 0]) < 70) & (np.abs(pts[:, 1]) < 58)]
            inside = riser.contains(near) if len(near) else np.zeros(0, bool)
            n = int(inside.sum())

            ax.scatter(rv[:, 0], rv[:, 2], s=0.6, c="#8a94a6", alpha=0.30, lw=0,
                       label="riser bay (skirt)")
            ax.scatter(pts[:, 0], pts[:, 2], s=1.4, c="#2b6cb0", alpha=0.55, lw=0,
                       label="front leg")
            if n:
                ax.scatter(near[inside, 0], near[inside, 2], s=16, c="#e53e3e",
                           lw=0, label=f"INSIDE riser ({n})")
            ax.set_title(
                f"hfe +{hfe:.1f}    {'clear' if n == 0 else f'{n} pts INSIDE'}",
                fontsize=10, color="#1a202c" if n == 0 else "#c53030")
            if c == 0:
                ax.set_ylabel(f"{rowlab}\ntrunk z (mm)", fontsize=9)
            ax.set_aspect("equal")
            ax.grid(alpha=0.15)
            ax.set_xlabel("trunk x (mm)   +x = HEAD")
            ax.legend(loc="lower left", fontsize=7, framealpha=0.9)

    fig.suptitle(
        "FRONT leg vs riser skirt — the +50 cap is a worst case over haa AND kfe.\n"
        "Top row is where trot/crawl actually run (+59.4 exceeds the SCALAR cap, "
        "not the geometry).", fontsize=12)
    fig.tight_layout()
    fig.savefig("skirt_violation.png", dpi=130)
    print("wrote skirt_violation.png")
    for haa, kfe, _lab in ROWS:
        Sx = cf.rot(haa, [1, 0, 0], pivot)
        for hfe in HFES:
            pts = cf.tf(cf.tf(cf.leg_cloud(hfe, kfe), base), Sx)
            near = pts[(np.abs(pts[:, 0]) < 70) & (np.abs(pts[:, 1]) < 58)]
            n = int(riser.contains(near).sum()) if len(near) else 0
            print(f"  haa {haa:+6.1f}  kfe {kfe:+7.1f}  hfe {hfe:+6.1f} -> "
                  f"{n:4d} pts inside riser")


if __name__ == "__main__":
    main()
