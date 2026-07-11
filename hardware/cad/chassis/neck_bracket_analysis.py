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
for F in (60, 100, 150):        # impact N at the head FRONT (x172)
    arm_base = 172 - 129        # to the base-bolt centroid x129 (bolts x110/148)
    M = F*arm_base              # N·mm
    # base-bolt couple over the 38mm fore-aft span, 2 bolts/side
    Fb = M/38/2
    # rear mount wall bending: 32 wide (y±16) x 8 thick section
    Z = 32*8**2/6               # mm3
    sig = M/Z
    print(f"  F={F:3d} N: M={M/1000:.1f} N·m | wall bend {sig:.1f} MPa (SF {UTS/sig:.0f}) "
          f"| base bolt {Fb:.0f} N (nyloc on the 6.5 deck, ~{Fb/5:.0f} MPa, SF {UTS/(Fb/5):.0f})")
print("\nVERDICT: at a 100 N faceplant SF ~12 in bending — the 8 mm wall + base")
print("plate carry it at the PERIMETER (4 walls), so 40% infill is adequate")
print("(matches the leg spec). Set: 4 walls / 40% / gyroid. ⚠ VIBRATION/resonance")
print("(the L2-scan concern, plan item 3) is a STIFFNESS problem, NOT strength —")
print("needs a physical/modal check on the first print, not captured here.")
