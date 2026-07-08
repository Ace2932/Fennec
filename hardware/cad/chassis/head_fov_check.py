#!/usr/bin/env python3
"""HEAD sensor-FoV gate (2026-07-07) — the check the plan flagged as needed
before the fennec styling: does the head/ears/bracket (or the robot) block the
L2 360deg ring / down-cone, or intrude the D456 view? Validates the CURRENT
head (STYLE=true ears) + is the gate the styling pass must keep passing.

Sensors (specs; no dims.md entry, noted):
  L2 Unitree 4D: 360deg H x ~90deg V, useful down-edge -45deg (head_study).
    optical center (126.5,0,158) — base z128 + ~30 (drum band, STEP-measured).
  D456: 87deg H x 58deg V, optical axis 27deg DOWN, optical ctr ~(166,0,100)
    (front/lens face). Looks forward-down at the ground.
"""
import numpy as np, trimesh
def box(x0,x1,y0,y1,z0,z1):
    return trimesh.creation.box(extents=[x1-x0,y1-y0,z1-z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]))
def S(m,n=8000): return trimesh.sample.sample_surface(m,n,seed=0)[0]

# occluders near the head (trunk frame)
head=trimesh.load('head.stl'); brk=trimesh.load('neck_bracket.stl')
# ears are separate parts now (head_ear.scad) — include them as occluders
earR=trimesh.load('head_ear.stl'); earL=trimesh.load('head_ear_L.stl')
parts={'head':S(head), 'ears':np.vstack([S(earR,3000),S(earL,3000)]),
       'bracket':S(brk,3000),
       'jetson_case':S(box(-62,48.3,-46.95,46.95,71.9,110.1),4000),
       'front_shoulderL':S(box(109,158,26,59.4,0,80),2000),
       'front_shoulderR':S(box(109,158,-59.4,-26,0,80),2000),
       'riser':S(box(-63.5,63.5,-55,55,29,71.9),3000)}

print("== L2 360deg RING + down-cone ==  optical (126.5,0,158)")
Lc=np.array([126.5,0,158.0]); RNEAR=300.0  # near field that would occlude
def ring(elo,ehi,label):
    az_block={}
    for nm,p in parts.items():
        d=p-Lc; hd=np.hypot(d[:,0],d[:,1])
        elev=np.degrees(np.arctan2(d[:,2],hd)); az=np.degrees(np.arctan2(d[:,1],d[:,0]))%360
        m=(hd<RNEAR)&(elev>=elo)&(elev<ehi)
        for a in az[m]:
            b=int(a//15)*15; az_block.setdefault(b,set()).add(nm)
    clear=sum(1 for b in range(0,360,15) if b not in az_block)
    nonrear=sorted(set(b for b in az_block if b<60 or b>=300 or 60<=b<120 or 240<=b<300))
    print(f"  {label} (elev {elo:+d}..{ehi:+d}): {clear}/24 bins clear. "
          f"blocked: {sorted(az_block)}")
    for b in sorted(az_block):
        print(f"      az {b:3d}-{b+15:3d}: {sorted(az_block[b])}")
    return nonrear
print("  azimuth 0=FWD(+x) 90=LEFT 180=REAR 270=RIGHT")
nr_ring = ring(-10,10, "HORIZONTAL RING")     # the primary 360deg mapping
nr_down = ring(-45,-10, "DOWN-CONE")          # secondary ground view
print(f"  ⚠ HORIZONTAL-ring non-rear blocks: {nr_ring or 'NONE (only rear blocked = intended)'}")
print(f"  (down-cone non-rear blocks {nr_down} = the D456 face-plate below/fwd; "
      f"the D456 itself covers that forward-down ground)")

print("\n== D456 forward view ==  optical ~(166,0,100), axis 27deg down, FoV 87x58")
th=np.radians(27.0)
axis=np.array([np.cos(th),0,-np.sin(th)])          # forward-down
up=np.array([np.sin(th),0,np.cos(th)]); left=np.array([0,1,0])
Cc=np.array([166.0,0,100.0])
for nm,p in parts.items():
    d=p-Cc; fwd=d@axis
    ahead=d[fwd>5]                                  # in front of the lens
    if not len(ahead): print(f"  {nm}: none in front"); continue
    h=np.degrees(np.arctan2(ahead@left, ahead@axis))
    v=np.degrees(np.arctan2(ahead@up,   ahead@axis))
    infov=(np.abs(h)<43.5)&(np.abs(v)<29)
    n=int(infov.sum())
    tag=" <-- INTRUDES the image" if n>20 else ""
    print(f"  {nm}: {n} pts in the 87x58 FoV{tag}")
