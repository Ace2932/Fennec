#!/usr/bin/env python3
"""SERVO-POCKET structural check (2026-07-07) — the gap load-analysis.md left
("leg-internal pockets sized in the design memo, unchanged"). All 3 leg joints
share sts_pocket_neg + COL_PTS, so one analysis covers haa/hfe/kfe.

Load path: the STS3215 OUTPUT axis = Z. Joint torque is reacted about Z. The
walls are SLIP-FIT (0.45) so they DON'T engage -> the full reaction rides the
4x M2 case screws in tangential shear, transmitted to the pocket FLOOR via the
screw shanks bearing on the M2 clearance holes. (Landing/leg loads bypass this
- they go through the horn/wheel discs + yoke, already SF>100 in load-analysis.)
"""
import numpy as np
COL_PTS = np.array([[-8.3,10.2],[-8.3,-10.2],[-32.8,10.25],[-32.8,-10.25]])
r = np.hypot(COL_PTS[:,0], COL_PTS[:,1])          # radius of each screw from axis
Sr2 = (r**2).sum()
UTS = 151.0                                        # PA6-CF flex, dry (Bambu TDS)
UTS_WET = 75.0
# floor bearing per screw: M2 shank Ø2.0 x 0.725 deep.  #67 fix (2026-07-12):
# the REAL floor is 2.125mm (the connector-bay void cuts to z-20.075, 0.375
# below FLOOR_TOP -- forced by the servo connector clearance, MEASURED all 3
# pockets) and the csk is 1.4 deep -> 2.125-1.4 = 0.725.  Was (floor 2.5 - csk
# 1.1)=1.4, which over-stated the bearing ~2x; SF drops accordingly but stays >1.
A_bear = 2.0 * 0.725                               # 1.45 mm^2 (in-plane, no Z knockdown)
# case-side wall bearing IF anti-rotation engaged (the fix): 2 side flats at
# y=±12.4 over ~45 long x ~10 tall contact
A_wall = 45.0 * 10.0                               # per side, mm^2

def screw_shear(T_Nm):
    T = T_Nm*1000.0                                # N·mm
    return T*r/Sr2                                 # N per screw (∝ radius)

print("STS3215 stall torque: 1.86 N·m @ 7.5V (v1 leg rail); 2.94 N·m @ 12V "
      "(+58% latent SKU option).  operating trot peak ~1.0 N·m (cyclic).\n")
print(f"screw radii from axis: {r.round(1)} mm   (far pair 34.4, near 13.2)\n")
print(f"{'case':<26}{'T(N·m)':>8}{'F_far(N)':>10}{'floorσ(MPa)':>13}{'SF_dry':>8}{'SF_wet':>8}")
for name,T in [('STALL 7.5V (v1)',1.86),('STALL 12V (latent)',2.94),
               ('trot operating (cyc)',1.0)]:
    F=screw_shear(T); Ff=F.max()
    sig=Ff/A_bear
    print(f"{name:<26}{T:>8.2f}{Ff:>10.1f}{sig:>13.1f}{UTS/sig:>8.1f}{UTS_WET/sig:>8.1f}")
print()
print("-- landing 60 N single-leg: does NOT load the pocket screws --")
print("   foot force -> tibia -> KNEE DISCS + yoke boss (Ø19) -> femur.")
print("   load-analysis: wheel-boss shear 0.4 MPa SF≫100; disc bearing SF≫100.")
print("   the pocket screws see ONLY the torque reaction above.\n")
print("== FATIGUE / RETENTION (the real weakness) ==")
Fcyc=screw_shear(1.0).max()
print(f"   trot ~1.0 N·m cyclic -> far screw {Fcyc:.1f} N tangential, "
      f"floor {Fcyc/A_bear:.1f} MPa (≪ PA6-CF endurance ~45 MPa -> FLOOR ok).")
print("   BUT the 4 screws are M2 SELF-TAP into the SERVO's own plastic columns,")
print("   cyclic, with the 0.45 slip-fit + NO anti-rotation. Self-tap-in-plastic")
print("   under 1e5 cyc/hr classically BACKS OUT / wallows -> preload loss ->")
print("   servo rattles in the slip -> accelerating wear. No static SF captures")
print("   this; it is a retention/reliability failure, not a strength one.\n")
print("== ANTI-ROTATION (fix B) — reaction moves to WALL BEARING ==")
for name,T in [('STALL 12V',2.94)]:
    F_wall = T*1000/(2*12.4)                       # couple across 2 side flats @ 12.4
    print(f"   {name}: wall force {F_wall:.0f} N/side over {A_wall:.0f} mm² "
          f"= {F_wall/A_wall:.2f} MPa -> SF {UTS/(F_wall/A_wall):.0f}.")
print("   -> the walls swallow the torque; the 4 screws drop to ~axial-only")
print("   retention (no cyclic tangential load) -> the loosening driver is GONE.")
