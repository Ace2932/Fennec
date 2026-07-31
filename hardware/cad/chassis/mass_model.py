#!/usr/bin/env python3
"""ABSOLUTE CoM mass model (2026-07-07) — grounds the battery-rebalance decision
the head re-arch deferred. Itemized: every significant mass x its centroid in
the TRUNK frame (x0 = hip-grid center, +x FRONT). Symmetric masses (4 legs +
12 servos, placed front/rear at ±141) CANCEL in fore-aft, so only the
ASYMMETRIC masses move the CoM. Printed masses = STL solid volume x density x
infill-factor (rough); big masses are spec/caliper.

Run: ../../../.venv/bin/python mass_model.py
"""
PA,PET,TPU = 1.20, 1.25, 1.20          # g/cm3
INF = 0.60                              # ~40% infill + walls -> ~0.6 of solid
# name: (grams, x_centroid_mm, note)
ITEMS = [
    # --- asymmetric (these set the fore-aft CoM) ---
    ('L2 LiDAR',        230, 126.5, 'spec, optical x126.5'),
    ('D456 camera',     110, 155.0, 'spec, body centroid'),
    ('head (PA6-CF)',   49.6*PA*INF, 120, 'STL 49.6cm3 x1.2 x0.6'),
    ('neck_bracket',    14.0*PA*INF, 128, 'STL 14cm3'),
    ('Jetson+case',     350, -7.0, 'Orin Nano + official case, ctr x-7'),
    ('riser_bay',       103*PET*INF, 0, 'STL 103cm3 PETG, ~centered'),
    ('floor_plate',     40, 0, 'thin plate, centered'),
    ('jetson_cradle',   25, -7, 'cradle under the case'),
    ('power PCB stack', 150, -3.5, 'mezzanine, ctr x-3.5'),
    ('trunk shell',     180, 0, 'stock frame, ~centered'),
    ('battery pack',    510, 0.0, 'BENCH: slide fore/aft to trim'),
    # --- symmetric: 4 legs + 12 servos + wiring + hardware, net fore-aft ~0
    #     (front/rear placements CANCEL in x; only sets the total/denominator) ---
    ('12x STS3215 servos (sym)', 12*60, 0, '60 g each'),
    ('leg PA structure x4 (sym)', 4*150, 0, 'coax+femur+tibia+arm ~150 g/leg'),
    ('2x shoulders + plates (sym)', 2*130, 0, ''),
    ('wiring harness (sym)', 350, 0, '24 servo leads + power + bus'),
    ('fasteners/heatsets/wheels/misc (sym)', 250, 0, ''),
]
M = sum(m for _,m,_,_ in ITEMS)
Mx = sum(m*x for _,m,x,_ in ITEMS)
com_x = Mx/M
BASE = 129.6  # #224: feet anchor at the pitch station (haa station minus hip_to_upper_x), since #223
print(f"{'mass (g)':>10} {'x (mm)':>8}  item")
for nm,m,x,note in ITEMS:
    print(f"{m:>10.0f} {x:>8.1f}  {nm:<28} {note}")
print(f"{'-'*10}")
print(f"total {M:>4.0f} g   fore-aft CoM = {com_x:+.1f} mm ({100*com_x/BASE:+.0f}% of the "
      f"±{BASE:.0f} support half-span)")
front = 0.5 + com_x/(2*BASE)
print(f"static load split: FRONT {100*front:.0f}% / REAR {100*(1-front):.0f}%")
print(f"\nBattery trim (510 g pack): to move the CoM by ΔX, shift the pack ΔX·{M:.0f}/510:")
for target in (0, 5):
    need = (com_x - target)
    shift = need*M/510
    edge = -shift - 77.5   # pack rear edge if shifted (pack ±77.5 about its ctr)
    print(f"  -> CoM {target:+d} mm: shift pack {shift:+.0f} mm rearward "
          f"(pack rear edge x{edge:+.0f}; rear hip at x-141 -> "
          f"{'FEASIBLE' if edge>-141 else 'PAST THE REAR HIP — infeasible'})")
print("\nNB rough (printed masses ±30%, centroids ±10mm). Re-run after the head")
print("styling mass (shroud/snout add fwd) + weigh the real parts at Wave 1.")
