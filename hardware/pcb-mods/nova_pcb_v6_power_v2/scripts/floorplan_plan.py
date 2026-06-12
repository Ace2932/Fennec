#!/usr/bin/env python3
# bucks-free planner v4 -- REAL pad geometry + unified cross-layer pad clearance (mini-DRC).
# Key fixes over v3: read actual pads from footprints (caps origin-at-pad1, L1 real pads),
# B-side parts placed TRANSLATE-ONLY at native rotation (matches applier set_xy + KiCad flip),
# unified pad-vs-pad clearance for any pads sharing a copper layer (THT=both faces, SMD=its face).
import re, math
BRD="/Users/afox/codebases/NOVA/proj/hardware/pcb-mods/nova_pcb_v6_power/nova_pcb_v6_power.kicad_pcb"
TERM="/Users/afox/codebases/NOVA/proj/hardware/pcb-mods/nova_pcb_v6_power/nova_v6.pretty/Buck_Offboard_Terminal_2xXT30.kicad_mod"
BX0,BY0,BX1,BY1=84,51,196,141
EDGE=0.5; CLR=0.3; HOLE=0.3; SR=4.6
STAND=[(103,63),(177,63),(103,129),(177,129)]
def blocks(text,head):
    i=0
    while True:
        j=text.find(head,i)
        if j<0:return
        d=0;k=j
        while k<len(text):
            c=text[k]
            if c=='(':d+=1
            elif c==')':
                d-=1
                if d==0:break
            k+=1
        yield text[j:k+1];i=k+1
def ref(b):
    m=re.search(r'\(property "Reference" "([^"]+)"',b);return m.group(1) if m else "?"
def fp_at(b):
    m=re.search(r'\(at ([\d.\-]+) ([\d.\-]+)(?: ([\d.\-]+))?\)',b)
    return float(m.group(1)),float(m.group(2)),float(m.group(3) or 0)
def pads(b):  # list of (px,py,w,h,drill_or_None, is_tht) in footprint-local PRE-rotation frame
    out=[]
    for g in blocks(b,"(pad "):
        m=re.search(r'\(at ([\d.\-]+) ([\d.\-]+)',g)
        sz=re.search(r'\(size ([\d.\-]+) ([\d.\-]+)\)',g)
        dr=re.search(r'\(drill ([\d.\-]+)',g)
        tht='thru_hole' in g
        if m and sz:out.append((float(m.group(1)),float(m.group(2)),float(sz.group(1)),float(sz.group(2)),float(dr.group(1)) if dr else None,tht))
    return out
def crtyd(b):
    pts=[]
    for head in ("(fp_line","(fp_rect","(fp_poly"):
        for g in blocks(b,head):
            if 'CrtYd' not in g:continue
            for m in re.finditer(r'\((?:start|end|xy|mid) ([\d.\-]+) ([\d.\-]+)\)',g):
                pts.append((float(m.group(1)),float(m.group(2))))
    for g in blocks(b,"(fp_circle"):              # circle -> center +/- radius corners
        if 'CrtYd' not in g:continue
        c=re.search(r'\(center ([\d.\-]+) ([\d.\-]+)\)',g);e=re.search(r'\(end ([\d.\-]+) ([\d.\-]+)\)',g)
        if c and e:
            cx,cy=float(c.group(1)),float(c.group(2));r=math.hypot(float(e.group(1))-cx,float(e.group(2))-cy)
            pts+=[(cx-r,cy-r),(cx-r,cy+r),(cx+r,cy-r),(cx+r,cy+r)]
    return pts
def rot(px,py,deg):
    a=math.radians(deg);ca,sa=math.cos(a),math.sin(a)
    return (px*ca+py*sa, -px*sa+py*ca)   # KiCad convention (matches observed C1 (5,0)@90 -> (0,-5))
# --- load board geometry ---
sb=open(BRD).read()
PADL={}; CRT={}; NATROT={}
for b in blocks(sb,"\t(footprint "):
    r=ref(b); PADL[r]=pads(b); CRT[r]=crtyd(b); NATROT[r]=fp_at(b)[2]
# terminal overrides U1-U5 (built at rot0)
tb=next(blocks(open(TERM).read(),"(footprint "))
TPAD=pads(tb); TCRT=crtyd(tb)
for u in ['U1','U2','U3','U4','U5']:
    PADL[u]=TPAD; CRT[u]=TCRT; NATROT[u]=0
# --- placement: ref -> (cx,cy, rot, face). F=target rot, B=NATIVE rot (translate-only) ---
PLACE={}
F=[('J1',90,72,90),('J3',90,89,90),('J4',90,105,90),('J5',90,121,90),
   ('J6',191,69,90),('J7',191,85,90),('J8',191,101,90),('J12',191,117,90),('J13',191,133,90),
   ('SW1',113,57,0),('SW2',164,57,0),('M1',140,55,0),('J2',150,56,0),('Q1',127,57,0),
   ('U9',112,77,0),('U10',140,77,0),('U11',168,77,0),
   ('U1',102,97,0),('U2',120,97,0),('U3',138,97,0),('U4',156,97,0),('U5',174,97,0)]
for r,x,y,rt in F:PLACE[r]=(x,y,rt,'F')
# fixed THT J20 (on board, pierces both faces) -- include as obstacle at its real pose
jx,jy,jr=fp_at(next(b for b in blocks(sb,"\t(footprint ") if ref(b)=="J20"))
PLACE['J20']=(jx,jy,jr,'F')
def apads(r,cx,cy,rt,face):  # abs pads: (ax,ay,w,h,drill,layerset)
    out=[]
    for px,py,w,h,dr,tht in PADL.get(r,[]):
        rx,ry=rot(px,py,rt)
        if rt in (90,270):w,h=h,w
        lay={'F','B'} if tht else ({'F'} if face=='F' else {'B'})
        out.append((cx+rx,cy+ry,w,h,dr,lay))
    return out
def abox(r,cx,cy,rt):
    pts=CRT.get(r,[]) or [(-1,-1),(1,1)]
    cs=[]
    for px,py in pts:
        rx,ry=rot(px,py,rt);cs.append((cx+rx,cy+ry))
    return (min(c[0] for c in cs),min(c[1] for c in cs),max(c[0] for c in cs),max(c[1] for c in cs))
def pad_conflict(pA,pB):  # both abs pad tuples
    ax,ay,aw,ah,adr,al=pA; bx,by,bw,bh,bdr,bl=pB
    if not (al & bl):return None            # no shared copper layer
    # copper: axis-aligned bbox overlap test w/ clearance (conservative)
    if abs(ax-bx) < (aw+bw)/2+CLR and abs(ay-by) < (ah+bh)/2+CLR:
        # hole-to-hole if both drilled
        if adr and bdr:
            d=math.hypot(ax-bx,ay-by)
            if d < adr/2+bdr/2+HOLE:return 'HOLE'
        return 'CU'
    if adr and bdr:
        d=math.hypot(ax-bx,ay-by)
        if d < adr/2+bdr/2+HOLE:return 'HOLE'
    return None
# --- greedy place B-side: caps (THT) then SMD ---
CAPS=['C1','C2','C3','C4','C5','C6']
SMD=['L1','U8','Q2']+[f'R{i}' for i in range(2,13)]
COURT=0.4
def cyd_overlap(a,b):  # axis-aligned courtyard bbox overlap w/ gap
    ax0,ay0,ax1,ay1=a;bx0,by0,bx1,by1=b
    return bx0<ax1+COURT and ax0<bx1+COURT and by0<ay1+COURT and ay0<by1+COURT
def part_ok(r,cx,cy,face,extra):
    rt=NATROT[r]
    bb=abox(r,cx,cy,rt)
    x0,y0,x1,y1=bb
    if min(x0-BX0,BX1-x1,y0-BY0,BY1-y1)<EDGE:return False
    for sx,sy in STAND:
        if math.hypot(sx-min(max(sx,x0),x1),sy-min(max(sy,y0),y1))<SR:return False
    me=apads(r,cx,cy,rt,face)
    for orr,opose in {**PLACE,**extra}.items():
        ocx,ocy,ort,oface=opose
        if oface==face and cyd_overlap(bb,abox(orr,ocx,ocy,ort)):return False  # same-face body clash
        for pa in me:
            for pb in apads(orr,ocx,ocy,ort,oface):
                if pad_conflict(pa,pb):return False
    return True
placed={}
# scan region: lower band y112..116 for caps (clear of terminal pads @y102 and standoffs/J20)
capspots=[(x,y) for y in (112,116) for x in range(90,184,1)]
for r in CAPS:
    for cx,cy in capspots:
        if part_ok(r,cx,cy,'B',{k:(placed[k][0],placed[k][1],NATROT[k],'B') for k in placed}):
            placed[r]=(cx,cy,NATROT[r],'B');break
    else:print(f"  !! cap {r} unplaced")
for r in placed:PLACE[r]=placed[r]
# scan rear strip for SMD (below caps, dodge J20/standoffs). L1 biggest -> first.
smdplaced={}
smdspots=[(x,y) for y in (133,136,130) for x in range(90,184,1)]
for r in SMD:
    for cx,cy in smdspots:
        if part_ok(r,cx,cy,'B',{k:(smdplaced[k][0],smdplaced[k][1],NATROT[k],'B') for k in smdplaced}):
            smdplaced[r]=(cx,cy,NATROT[r],'B');break
    else:print(f"  !! smd {r} unplaced")
for r in smdplaced:PLACE[r]=smdplaced[r]
# --- full verify (unified) ---
refs=list(PLACE);viol=[]
APAD={r:apads(r,*PLACE[r]) for r in refs}
BOX={r:abox(r,PLACE[r][0],PLACE[r][1],PLACE[r][2]) for r in refs}
for r in refs:
    x0,y0,x1,y1=BOX[r]
    if min(x0-BX0,BX1-x1,y0-BY0,BY1-y1)<EDGE:viol.append(f"EDGE {r} {min(x0-BX0,BX1-x1,y0-BY0,BY1-y1):+.2f}")
    for sx,sy in STAND:
        d=math.hypot(sx-min(max(sx,x0),x1),sy-min(max(sy,y0),y1))
        if d<SR:viol.append(f"STBY {r} d={d:.2f}@({sx},{sy})")
for i in range(len(refs)):
    for j in range(i+1,len(refs)):
        a,b=refs[i],refs[j]
        if PLACE[a][3]==PLACE[b][3] and cyd_overlap(BOX[a],BOX[b]):viol.append(f"CYD {a}<->{b}")
        for pa in APAD[a]:
            for pb in APAD[b]:
                c=pad_conflict(pa,pb)
                if c:viol.append(f"{c} {a}<->{b}");break
            else:continue
            break
print("caps:",{r:tuple(round(v,1) for v in placed[r][:2]) for r in placed})
print("smd :",{r:tuple(round(v,1) for v in smdplaced[r][:2]) for r in smdplaced})
print(f"CLR={CLR} HOLE={HOLE} SR={SR}")
for v in viol[:50]:print("  "+v)
print("\nRESULT:","PASS" if not viol else f"FAIL ({len(viol)})")
