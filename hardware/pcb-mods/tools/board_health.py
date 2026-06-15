#!/usr/bin/env python3
"""
board_health.py - one-shot pre-fab health report for a KiCad PCB.

Run with the KiCad-bundled python so `pcbnew` is importable:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      tools/board_health.py path/to/board.kicad_pcb

Checks (compiled from the 2026-06-14 NOVA review sessions):
  1. Lock / KiCad-open guard (don't edit a live board)
  2. DRC (errors only) + ERC via kicad-cli
  3. Footprint + value list
  4. Off-board connector pinout dump (board-EXPECTS side of the mating audit)
  5. Zones / planes (net, layer, filled?)
  6. Single-pad ("dangling") nets
  7. Trace width per named net (spot thin power traces / verify planes carry current)

Exit code != 0 if DRC errors, unconnected items, or a hard lock is found.
"""
import sys, os, glob, subprocess, collections

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

def find_board(arg):
    if arg and arg.endswith(".kicad_pcb"):
        return arg
    hits = glob.glob("*.kicad_pcb") + glob.glob("**/*.kicad_pcb", recursive=True)
    hits = [h for h in hits if "-backups" not in h]
    if len(hits) == 1:
        return hits[0]
    print("Specify a .kicad_pcb (found: %s)" % hits); sys.exit(2)

def lock_guard(board):
    d = os.path.dirname(os.path.abspath(board))
    locks = glob.glob(os.path.join(d, "~_autosave*.lck")) + glob.glob(os.path.join(d, "*.lck"))
    running = subprocess.run(["pgrep", "-i", "kicad"], capture_output=True, text=True).stdout.strip()
    if locks or running:
        print("  !! LOCK/KiCad-OPEN: %s%s" % (locks, " (kicad running)" if running else ""))
        print("     Do NOT write this board headless until KiCad is fully closed.")
        return False
    print("  ok - no lock, KiCad not running")
    return True

def run_drc(board):
    r = subprocess.run([CLI, "pcb", "drc", "--severity-error", "--exit-code-violations", board],
                       capture_output=True, text=True)
    out = [l for l in r.stdout.splitlines() if "Found" in l]
    for l in out: print("  " + l.strip())
    return r.returncode == 0

def run_erc(board):
    sch = board.replace(".kicad_pcb", ".kicad_sch")
    if not os.path.exists(sch):
        print("  (no top .kicad_sch next to board - skipped)"); return True
    r = subprocess.run([CLI, "sch", "erc", "--exit-code-violations", sch], capture_output=True, text=True)
    rpt = board.replace(".kicad_pcb", "-erc.rpt")
    if os.path.exists(rpt):
        counts = collections.Counter()
        for line in open(rpt):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                counts[line[:line.index("]")+1]] += 1
        for k, v in sorted(counts.items()): print("  %3d %s" % (v, k))
        os.remove(rpt)
    return r.returncode == 0

def analyze(board):
    import pcbnew
    mm = pcbnew.ToMM
    b = pcbnew.LoadBoard(board)

    print("\n[3] FOOTPRINTS")
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        print("  %-6s %-26s %s" % (fp.GetReference(), fp.GetValue(), fp.GetFPID().GetLibItemName()))

    print("\n[4] OFF-BOARD CONNECTOR PINOUTS (board-expects; verify vs the physical part)")
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        r = fp.GetReference()
        if r[0] in "JS" or "Module" in str(fp.GetFPID().GetLibItemName()) or "Terminal" in str(fp.GetFPID().GetLibItemName()):
            print("  %s [%s]" % (r, fp.GetValue()))
            for pd in sorted(fp.Pads(), key=lambda p: p.GetPadName()):
                print("      %4s = %s" % (pd.GetPadName(), pd.GetNetname().split("/")[-1]))

    print("\n[5] ZONES / PLANES")
    for z in b.Zones():
        print("  %-10s %-8s filled=%s" % (z.GetNetname().split("/")[-1], b.GetLayerName(z.GetLayer()), z.IsFilled()))

    print("\n[6] SINGLE-PAD NETS (potential dangling)")
    net = collections.defaultdict(list)
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            n = pd.GetNetname()
            if n: net[n].append("%s.%s" % (fp.GetReference(), pd.GetPadName()))
    found = False
    for n, ps in sorted(net.items()):
        if len(ps) == 1 and not n.startswith("unconnected"):
            print("  %s: %s" % (n.split("/")[-1], ps)); found = True
    if not found: print("  none")

    print("\n[7] TRACE WIDTH per named net (min/max mm)")
    w = collections.defaultdict(list)
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            w[t.GetNetname().split("/")[-1]].append(mm(t.GetWidth()))
    for n in sorted(w):
        if not n.startswith("Net-") and not n.startswith("unconnected"):
            print("  %-18s %.3f / %.3f  (%d segs)" % (n, min(w[n]), max(w[n]), len(w[n])))

def main():
    board = find_board(sys.argv[1] if len(sys.argv) > 1 else None)
    print("=== board_health: %s ===" % board)
    print("\n[1] LOCK GUARD"); locked_ok = lock_guard(board)
    print("\n[2a] DRC (errors)"); drc_ok = run_drc(board)
    print("\n[2b] ERC"); run_erc(board)
    try:
        analyze(board)
    except ImportError:
        print("\n(pcbnew not importable - run with the KiCad-bundled python for sections 3-7)")
    print("\n=== summary: DRC %s | lock %s ===" % (
        "PASS" if drc_ok else "FAIL", "clear" if locked_ok else "PRESENT"))
    sys.exit(0 if (drc_ok and locked_ok) else 1)

if __name__ == "__main__":
    main()
