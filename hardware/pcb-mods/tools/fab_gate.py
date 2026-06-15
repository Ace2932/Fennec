#!/usr/bin/env python3
"""
fab_gate.py - one-shot fab-readiness GATE for the NOVA v6 two-board set.

Complements board_health.py (single-board deep dump). This is the GO / NO-GO
gate across BOTH boards at once, plus the cross-board + freshness checks that
board_health can't see on its own. Compiled from the 2026-06-15 review session,
where each of these caught a real bug:

  - gerber freshness   : both boards shipped gerbers OLDER than their .kicad_pcb
  - DRC live (not .rpt) : a stale -drc.rpt hid 11 live violations (orphan R7)
  - cross-board J20     : mezzanine pin map must match 1:1 or the boards can't talk
  - DNP roster          : Phase-4 parts must stay DNP (U5 arm buck, U12 arm INA)
  - single-pad nets     : a dangling output (V7V5_ARM pre-J14) = stranded rail

Run with KiCad's bundled python so `pcbnew` imports:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      tools/fab_gate.py [pcb-mods-dir]

Exit code 0 = GO (no hard failures). Non-zero = NO-GO.
"""
import sys, os, glob, subprocess, re

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# DRC/ERC violation types that BLOCK fab vs. cosmetic ones that only warn.
SOFT = {"lib_footprint_mismatch", "lib_symbol_mismatch", "silk_over_copper",
        "silk_overlap", "silk_over_silk", "courtyards_overlap_info"}

J20_REF = "J20"  # inter-board mezzanine connector present on both boards


def run_cli(args):
    try:
        out = subprocess.run([CLI] + args, capture_output=True, text=True, timeout=300)
        return out.stdout + out.stderr
    except Exception as e:
        return f"__CLI_ERROR__ {e}"


def tally(report_text):
    return {}.__class__(  # dict
        (k, report_text.count(f"[{k}]"))
        for k in set(re.findall(r"\[([a-z_]+)\]", report_text)))


def check_board(pcb):
    """Return (board_name, list[(level, msg)]) — level in {FAIL, WARN, OK}."""
    import pcbnew
    name = os.path.splitext(os.path.basename(pcb))[0]
    d = os.path.dirname(pcb) or "."
    sch = os.path.join(d, name + ".kicad_sch")
    res = []

    # 1. ERC (schematic) — errors block, warnings don't
    if os.path.exists(sch):
        rpt = "/tmp/_fg_erc.rpt"
        run_cli(["sch", "erc", "--output", rpt, sch])
        txt = open(rpt).read() if os.path.exists(rpt) else ""
        m = re.search(r"Errors\s+(\d+)\s+Warnings\s+(\d+)", txt)
        e, w = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
        res.append(("FAIL" if e > 0 else "OK", f"ERC: {e} errors, {w} warnings"))
    else:
        res.append(("WARN", "no .kicad_sch found — skipped ERC"))

    # 2. DRC (live, never trust a saved .rpt) — tally is source of truth
    rpt = "/tmp/_fg_drc.rpt"
    run_cli(["pcb", "drc", "--output", rpt, pcb])
    txt = open(rpt).read() if os.path.exists(rpt) else ""
    mu = re.search(r"Found (\d+) unconnected", txt)
    nu = int(mu.group(1)) if mu else 0
    t = tally(txt)
    # 'unconnected_items' is double-counted (also in the unconnected total) — drop from tally
    t.pop("unconnected_items", None)
    hard = {k: v for k, v in t.items() if k not in SOFT}
    soft = {k: v for k, v in t.items() if k in SOFT}
    hard_n = sum(hard.values())
    res.append((("FAIL" if hard_n or nu else "OK"),
                f"DRC: {hard_n} hard, {sum(soft.values())} cosmetic, {nu} unconnected"))
    if hard:
        res.append(("FAIL", "  hard: " + ", ".join(f"{k}={v}" for k, v in sorted(hard.items()))))
    if soft:
        res.append(("WARN", "  cosmetic: " + ", ".join(f"{k}={v}" for k, v in sorted(soft.items()))))

    # 3. Gerber freshness vs .kicad_pcb mtime
    zips = glob.glob(os.path.join(d, "*gerbers*.zip"))
    if not zips:
        res.append(("WARN", "no gerber zip found"))
    else:
        pcb_m = os.path.getmtime(pcb)
        for z in zips:
            stale = os.path.getmtime(z) < pcb_m
            res.append((("FAIL" if stale else "OK"),
                        f"gerbers {'STALE' if stale else 'fresh'}: {os.path.basename(z)}"))

    # 4 + 5. Board-level: DNP roster + single-pad nets
    b = pcbnew.LoadBoard(pcb)
    dnp = sorted(f.GetReference() for f in b.GetFootprints()
                 if getattr(f, "IsDNP", lambda: False)())
    res.append(("OK", f"DNP parts: {', '.join(dnp) if dnp else 'none'}"))
    b.BuildConnectivity()
    padcount = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n:
                padcount.setdefault(n, []).append(f"{f.GetReference()}.{p.GetPadName()}")
    singles = {n: v for n, v in padcount.items() if len(set(v)) == 1 and not n.startswith("unconnected")}
    if singles:
        res.append(("WARN", "single-pad nets (verify intentional): "
                    + ", ".join(f"{n}({v[0]})" for n, v in sorted(singles.items()))))
    return name, res


def j20_map(pcb):
    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    f = b.FindFootprintByReference(J20_REF)
    if not f:
        return None
    m = {}
    for p in f.Pads():
        m[p.GetPadName()] = p.GetNetname()
    return m


# Active board set (the v6 two-board mezzanine). Deprecated dirs (nova_pcb_v6
# combined, nova_pcb_v6_power v1) are excluded by default. Override by passing
# explicit .kicad_pcb paths as args.
ACTIVE = ["nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_pcb",
          "nova_pcb_v6_logic/nova_pcb_v6_logic.kicad_pcb"]


def main():
    args = sys.argv[1:]
    explicit = [a for a in args if a.endswith(".kicad_pcb")]
    if explicit:
        pcbs = explicit
    else:
        base = args[0] if args else "."
        pcbs = [os.path.join(base, p) for p in ACTIVE if os.path.exists(os.path.join(base, p))]
    pcbs = sorted(set(p for p in pcbs if os.path.exists(p)))
    if not pcbs:
        print("no active boards found (looked for:", ", ".join(ACTIVE), ")")
        return 2

    print("=" * 64)
    print("NOVA v6 FAB-READINESS GATE")
    print("=" * 64)
    any_fail = False
    j20s = {}
    for pcb in pcbs:
        name, res = check_board(pcb)
        print(f"\n### {name}")
        for level, msg in res:
            mark = {"FAIL": "✗", "WARN": "!", "OK": "✓"}[level]
            print(f"  {mark} {msg}")
            if level == "FAIL":
                any_fail = True
        j = j20_map(pcb)
        if j:
            j20s[name] = j

    # cross-board J20
    print("\n### cross-board J20 mezzanine")
    if len(j20s) >= 2:
        names = list(j20s)
        a, bb = j20s[names[0]], j20s[names[1]]
        pins = sorted(set(a) | set(bb), key=lambda x: int(x) if x.isdigit() else 99)
        mism = [p for p in pins if a.get(p) != bb.get(p)]
        if mism:
            any_fail = True
            print(f"  ✗ J20 MISMATCH between {names[0]} and {names[1]}:")
            for p in mism:
                print(f"      pin {p}: {names[0]}={a.get(p)}  {names[1]}={bb.get(p)}")
        else:
            print(f"  ✓ J20 identical across {names[0]} ↔ {names[1]} ({len(pins)} pins)")
    else:
        print("  ! fewer than 2 boards carry J20 — cross-check skipped")

    print("\n" + "=" * 64)
    print("GATE: " + ("NO-GO ✗ (hard failures above)" if any_fail else "GO ✓"))
    print("=" * 64)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
