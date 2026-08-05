#!/usr/bin/env python3
"""NECK-BRACKET stress audit (2026-07-07) — closes the "not stress-audited for
infill" flag. The bracket cantilevers the head off the front-shoulder deck; it
takes the head's forward-tipping moment via the rear mount wall + the 4 deck
bolts. PA6-CF 151 MPa dry (Bambu TDS; Z-layers x0.6 — but the wall/base bend
IN-PLANE, no Z knockdown)."""
UTS=151.0
# head mass + CoM (trunk frame): L2 230@x126.5, D456 110@x155, struct 50@x120
mL2,mCam,mStr = 230,110,50; Mh=mL2+mCam+mStr
com_x=(mL2*126.5+mCam*155+mStr*120)/Mh
print(f"head mass {Mh} g, CoM x{com_x:.0f}. STATIC weight {Mh*9.81e-3:.1f} N -> "
      f"trivial moment. Design case = a FACEPLANT impact (the mast 'unbounded' case;")
print("the nylon head->bracket breakaway is the ultimate limit — see #2).")
# ⚠ GEOMETRY REFRESHED 2026-08-05. This block had been carrying bolts x110/148
# (centroid 129, span 38) — two revisions stale. neck_bracket.scad's BOLT_XY is
# x117 and x146 since the NO-DRILL fix (2026-07-10) moved the front pair off the
# shoulder's thin rear-wall rib: centroid 131.5, span 29. The shorter span RAISES
# the base-bolt force ~23% (a shorter couple reacting the same moment), so the
# stale numbers were optimistic exactly where it mattered.
for F in (60, 100, 150):        # impact N at the head FRONT (x172)
    arm_base = 172 - 131.5     # to the base-bolt centroid (BOLT_XY x117/x146)
    M = F*arm_base              # N·mm
    # base-bolt couple over the 29mm fore-aft span, 2 bolts/side
    Fb = M/29/2
    # rear mount wall bending: 32 wide (y±16) x 8 thick section
    Z = 32*8**2/6               # mm3
    sig = M/Z
    print(f"  F={F:3d} N: M={M/1000:.1f} N·m | wall bend {sig:.1f} MPa (SF {UTS/sig:.0f}) "
          f"| base bolt {Fb:.0f} N (~{Fb/5:.0f} MPa bearing, SF {UTS/(Fb/5):.0f})")
print("\n⚠ THE BASE-BOLT NUMBER ABOVE IS THE WRONG MODEL, not just a stale value.")
print("  This line used to read 'nyloc on the 6.5 deck'. The NO-DRILL fix")
print("  (2026-07-10) replaced the nuts with M3x3.8 BRASS HEAT-SETS pressed into")
print("  the shoulder deck, so the limit is no longer bolt bearing against a nut")
print("  — it is INSERT PULL-OUT from PA6-CF, a different and weaker mode. The")
print("  Fb/5 bearing estimate does not capture it. A real check is pi*D*L pull-")
print("  out area on a 4.6 OD x 3.8 insert, against the same 2.1 (wet) / 3.0")
print("  (dry) N/mm2 figures check_fit.py uses for the leg inserts. NOT DERIVED")
print("  HERE — do not quote this SF for the deck bolts until it is.")
print("\nVERDICT: at a 100 N faceplant SF ~12 in bending — the 8 mm wall + base")
print("plate carry it at the PERIMETER (4 walls), so 40% infill is adequate")
print("(matches the leg spec). Set: 4 walls / 40% / gyroid. ⚠ VIBRATION/resonance")
print("(the L2-scan concern, plan item 3) is a STIFFNESS problem, NOT strength —")
print("needs a physical/modal check on the first print, not captured here.")
