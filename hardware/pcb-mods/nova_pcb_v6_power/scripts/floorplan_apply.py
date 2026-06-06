#!/usr/bin/env python3
"""Apply the validated bucks-free floorplan (positions only) to the power board.

RUN ORDER (idiomatic, GUI-correct):
  1. In pcbnew run F8 (Update PCB from Schematic) so U1-U5 carry the
     Buck_Offboard_Terminal_2xXT30 footprint (pulled from the library, not
     hand-built). Close pcbnew.
  2. python3 floorplan_apply.py <board.kicad_pcb>     # this script -- sets (at x y rot)
  3. Reopen pcbnew, select the B.Cu set (printed below), press F to flip them
     to B.Cu in place (KiCad mirrors correctly; XY preserved). Run DRC.

This script does POSITIONS ONLY. It does NOT flip and does NOT rebuild
footprints -- both of those are done correctly by KiCad itself (F8 + F).
Validated by /tmp rehearsal: DRC-clean except 3 pre-existing INA226-internal
holes_co_located + benign silk/mask. Planner = floorplan_plan.py.
"""
import re, sys, os, shutil

# ref -> (x, y, rot).  Footprint ORIGIN coordinates (planner local-bbox frame).
PLACE_F = {  # F.Cu low-profile THT
 'J1':(90,72,90),'J3':(90,89,90),'J4':(90,105,90),'J5':(90,121,90),
 'J6':(191,69,90),'J7':(191,85,90),'J8':(191,101,90),'J12':(191,117,90),'J13':(191,133,90),
 'SW1':(113,57,0),'SW2':(164,57,0),'M1':(140,55,0),'J2':(150,56,0),'Q1':(127,57,0),
 'U9':(112,77,0),'U10':(140,77,0),'U11':(168,77,0),
 'U1':(102,97,0),'U2':(120,97,0),'U3':(138,97,0),'U4':(156,97,0),'U5':(174,97,0),
}
PLACE_B = {  # position on F.Cu here; FLIP to B.Cu in pcbnew (step 3). rot = native.
 'C1':(94,112,90),'C2':(108,112,90),'C3':(122,112,90),'C4':(136,112,90),
 'C5':(150,112,90),'C6':(163,112,90),
 'L1':(115,133,90),'U8':(90,133,90),'Q2':(95,133,90),
 'R2':(98,133,90),'R3':(123,133,90),'R4':(125,133,90),'R5':(127,133,90),'R6':(129,133,90),
 'R7':(131,133,90),'R8':(133,133,90),'R9':(135,133,90),'R10':(137,133,90),'R11':(139,133,90),
 'R12':(141,133,90),
}
# J20 (interboard) is FIXED -- never moved.

def blocks(text, head):
    i = 0
    while True:
        j = text.find(head, i)
        if j < 0: return
        d = 0; k = j
        while k < len(text):
            c = text[k]
            if c == '(': d += 1
            elif c == ')':
                d -= 1
                if d == 0: break
            k += 1
        yield (j, k+1, text[j:k+1]); i = k+1

def ref(b):
    m = re.search(r'\(property "Reference" "([^"]+)"', b); return m.group(1) if m else None

def fp_name(b):
    m = re.search(r'\(footprint "([^"]+)"', b); return m.group(1) if m else ""

def set_at(b, x, y, rot):
    return re.sub(r'\(at [\d.\-]+ [\d.\-]+(?: [\d.\-]+)?\)', f'(at {x} {y} {rot})', b, count=1)

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: floorplan_apply.py <board.kicad_pcb>")
    brd = sys.argv[1]
    d = os.path.dirname(os.path.abspath(brd))
    if any(f.endswith('.lck') for f in os.listdir(d)):
        sys.exit("ABORT: a .lck file exists -- close pcbnew before running.")
    s = open(brd).read()
    # GUARD: U1-U5 must already be the terminal footprint (i.e. F8 was run).
    for u in ('U1','U2','U3','U4','U5'):
        b = next((t for _,_,t in blocks(s, "\t(footprint ") if ref(t) == u), None)
        if b is None: sys.exit(f"ABORT: {u} not found.")
        if 'Terminal' not in fp_name(b):
            sys.exit(f"ABORT: {u} footprint is '{fp_name(b)}', not the terminal. "
                     f"Run F8 (Update PCB from Schematic) first.")
    shutil.copyfile(brd, brd + ".prefloorplan.bak")
    PLACE = {**PLACE_F, **PLACE_B}
    out = s; done = []; miss = []
    for r, (x, y, rot) in PLACE.items():
        for j, k, b in blocks(out, "\t(footprint "):
            if ref(b) == r:
                out = out[:j] + set_at(b, x, y, rot) + out[k:]; done.append(r); break
        else:
            miss.append(r)
    open(brd, "w").write(out)
    print(f"placed {len(done)}/{len(PLACE)}; backup -> {os.path.basename(brd)}.prefloorplan.bak")
    if miss: print("MISSING (not on board):", miss)
    print("\nNEXT (pcbnew): select these and press F to flip to B.Cu, then run DRC:")
    print("  " + " ".join(PLACE_B))

if __name__ == "__main__":
    main()
