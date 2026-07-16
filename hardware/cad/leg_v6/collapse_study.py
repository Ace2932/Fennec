#!/usr/bin/env python3
"""COLLAPSE / limp-fold study (2026-07-07) — where does the leg touch ground?
Motivated by the tibia_pad catch: the pad sat on the LATERAL blade face
(normal world +Y), so it never led into the ground on a vertical collapse.
tibia_pad.scad was RETIRED 2026-07-07 (misplaced — see its header) and its
STL was never built/gated; this script previously hard-referenced the
missing tibia_pad.stl and could not run. Fixed 2026-07-16 (housekeeping
review): the pad is dropped from the part stack entirely (the tibia mesh
itself is the real lowest-blade geometry for this analysis; a patched run
with the pad substituted back in beforehand confirmed the conclusions below
are unchanged — sit-pose haa40/hfe+50/kfe-109 clears the skid rail by 22mm,
knee closest approach +42mm).
This asks, per-part, what is the LOWEST world-z geometry across the fold ROM,
and where the belly rails (trunk z -42.2) sit relative to it.
Run: ../../../.venv/bin/python collapse_study.py"""
import numpy as np, trimesh
T = trimesh.transformations.translation_matrix
def rot(d, ax, p=None): return trimesh.transformations.rotation_matrix(np.radians(d), ax, p)
NOVA='/Users/afox/codebases/NOVA'; LEG=f'{NOVA}/proj/hardware/cad/leg_v6'
HIP_FA,HIP_LAT,HIP_Z=141.2,39.05,38.05
RAIL_Z=-42.2   # belly skid-rail bottom (world/trunk z), the designed drop-catch

def load():
    P={}
    P['coax']=trimesh.load(f'{LEG}/coax_R.stl')
    s=trimesh.load(f'{NOVA}/feetech_servo_models/converted_stl/servo.stl'); s.apply_translation([-12.5,0,0]); P['servo']=s
    P['femur']=trimesh.load(f'{LEG}/femur_R.stl')
    a=trimesh.load(f'{LEG}/knee_arm.stl'); a.apply_transform(T([59,0,17.75])); P['arm']=a  # rev 3: 17.2->17.75
    P['tibia']=trimesh.load(f'{LEG}/tibia_R.stl')
    # tibia_pad RETIRED 2026-07-07 (misplaced on the lateral blade face, never
    # built/gated — see tibia_pad.scad header) — dropped from the stack; the
    # tibia mesh above is the real lowest-blade geometry for this study.
    sh=trimesh.load(f'{NOVA}/original_body_files/SM3_Foot.stl'); sh.apply_transform(T([129,0,-30.5])@rot(54,[0,0,1])@T([0,-7.0,0])); P['foot']=sh
    return {k:np.asarray(trimesh.sample.sample_surface(v,3000,seed=0)[0]) for k,v in P.items()}

PTS=load()
MIR=np.eye(4);MIR[1,1]=-1
S2T=np.array([[0,1,0,HIP_FA],[1,0,0,0],[0,0,1,HIP_Z],[0,0,0,1.0]])
W=S2T@T([HIP_LAT,0,0])@MIR     # FR world placement
coax_pose=rot(-90,[0,1,0])@rot(90,[1,0,0])
M_f0=T([33.8,11.6,-9.5])@rot(180,[0,0,1])@rot(90,[0,1,0])

def tf(p,M): return (M@np.c_[p,np.ones(len(p))].T).T[:,:3]

def leg_parts(hfe,kfe):
    S=rot(hfe,[1,0,0],[33.8,11.6,-9.5]); Mtib=S@M_f0@T([106.9,0,0])@rot(kfe,[0,0,1])
    return {
      'coax': tf(PTS['coax'], W),
      'femur':tf(PTS['femur'],W@S@M_f0),
      'tibia':tf(PTS['tibia'],W@Mtib),
      'foot': tf(PTS['foot'], W@Mtib),
    }

print("== collapse fold sweep (FR leg, haa=0). Lowest world-z per part; "
      "global lowest part flagged. Rail bottom z=-42.2 ==\n")
print(f"{'hfe':>4}{'kfe':>5} | {'coax':>7}{'femur':>7}{'tibia':>7}{'foot':>7} | lowest")
# stance ~ hfe40 kfe80; fold = kfe -> -109 (limp buckle), hfe swings
rows=[]
for hfe in (40,0,-50,50):
    for kfe in (109,55,0,-55,-109):
        P=leg_parts(hfe,kfe)
        lows={k:v[:,2].min() for k,v in P.items()}
        who=min(lows,key=lows.get)
        rows.append((hfe,kfe,lows,who))
        print(f"{hfe:>4}{kfe:>5} | "+"".join(f"{lows[k]:7.0f}" for k in ('coax','femur','tibia','foot'))
              +f" | {who} ({lows[who]:.0f})")
# tibia-specific: when tibia is low, is it the flat face or an edge? report the
# lowest tibia point's LOCAL coords (the retired pad's comparison print is
# dropped along with the pad itself, see the module-docstring note above).
print("\n-- deepest-fold pose kfe-109: what's the tibia's lowest point? --")
S=rot(0,[1,0,0],[33.8,11.6,-9.5]); Mtib=S@M_f0@T([106.9,0,0])@rot(-109,[0,0,1])
tw=tf(PTS['tibia'],W@Mtib)
i=tw[:,2].argmin()
# back to tibia-local for the lowest world point
Minv=np.linalg.inv(W@Mtib); loc=(Minv@np.r_[tw[i],1])[:3]
print(f"  tibia lowest world z={tw[i,2]:.0f} at world {tw[i].round(0)}  (tibia-local {loc.round(0)})")
print(f"  rail bottom z={RAIL_Z}")

print("\n== SPLAYED collapse (haa outboard) — does the lateral face rotate "
      "down + the pad become the contact? ==\n")
def leg_parts_haa(hfe,kfe,haa):
    S=rot(hfe,[1,0,0],[33.8,11.6,-9.5]); Mtib=S@M_f0@T([106.9,0,0])@rot(kfe,[0,0,1])
    # haa about the fore-aft axis through the hip (outboard = away from centerline)
    Sx=rot(haa,[1,0,0],[HIP_FA,HIP_LAT,HIP_Z])
    def tp(p,M): return tf(tf(p,M),Sx)
    return {
      'femur':tp(PTS['femur'],W@S@M_f0),
      'tibia':tp(PTS['tibia'],W@Mtib),
      'foot': tp(PTS['foot'], W@Mtib),
    }
print(f"{'hfe':>4}{'kfe':>5}{'haa':>5} | {'femur':>7}{'tibia':>7}{'foot':>7} | lowest")
for haa in (25,40):
    for hfe in (40,0):
        for kfe in (55,0,-55,-109):
            P=leg_parts_haa(hfe,kfe,haa)
            lows={k:v[:,2].min() for k,v in P.items()}
            who=min(lows,key=lows.get)
            print(f"{hfe:>4}{kfe:>5}{haa:>5} | "+"".join(f"{lows[k]:7.0f}" for k in ('femur','tibia','foot'))
                  +f" | {who}")

print("\n== controlled-limp SIT-POSE search (A): find splay+fold where every "
      "leg part clears the rail line z>=-42.2 (body settles on the rails) ==\n")
RAIL=-42.2
def knee_world(hfe,kfe,haa):
    S=rot(hfe,[1,0,0],[33.8,11.6,-9.5]); Mtib=S@M_f0@T([106.9,0,0])@rot(kfe,[0,0,1])
    Sx=rot(haa,[1,0,0],[HIP_FA,HIP_LAT,HIP_Z])
    knee=(Sx@W@Mtib@np.array([0,0,0,1]))[:3]   # tibia origin = knee joint
    return knee
best=[]
for haa in (30,40):
    for hfe in (30,40,50):
        for kfe in (-70,-90,-109):
            P=leg_parts_haa(hfe,kfe,haa)
            lows={k:v[:,2].min() for k,v in P.items()}
            gmin=min(lows.values()); who=min(lows,key=lows.get)
            clr=gmin-RAIL
            k=knee_world(hfe,kfe,haa)
            tag="CLEARS" if clr>=0 else "below "
            best.append((clr,haa,hfe,kfe,who,gmin,k))
            print(f"haa{haa} hfe{hfe:+d} kfe{kfe:+d} | lowest={who} z{gmin:6.0f} "
                  f"({tag} rail by {clr:+.0f}) | knee@z{k[2]:.0f}")
best.sort(reverse=True)
c,haa,hfe,kfe,who,gmin,k=best[0]
print(f"\n-- BEST sit pose: haa {haa} (outboard), hfe {hfe:+d}, kfe {kfe:+d} --")
print(f"   leg lowest part = {who} at z{gmin:.0f} -> clears the rail (-42.2) by "
      f"{c:.0f} mm; body settles on the belly rails.")
print(f"   knee joint sits at world z{k[2]:.0f}, {k[2]-RAIL:+.0f} vs the rail "
      f"= the closest approach -> the KNEE-OUTER bumper (B) protects a dynamic "
      f"knee strike as the leg folds through this.")
