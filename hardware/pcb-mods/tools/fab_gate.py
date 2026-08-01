#!/usr/bin/env python3
"""
fab_gate.py - one-shot fab-readiness GATE for the NOVA v6 two-board set.

Complements board_health.py (single-board deep dump). This is the GO / NO-GO
gate across BOTH boards at once, plus the cross-board + freshness checks that
board_health can't see on its own.

  - gerber freshness   : shipped gerbers must MATCH the board, by content
  - DRC live (not .rpt) : a stale -drc.rpt hid 11 live violations (orphan R7)
  - cross-board J20     : mezzanine pin map must match 1:1 or the boards can't talk
  - DNP roster          : asserted against EXPECTED_DNP, not merely printed
  - single-pad nets     : a dangling output (V7V5_ARM pre-J14) = stranded rail

Run with KiCad's bundled python so `pcbnew` imports:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      tools/fab_gate.py [pcb-mods-dir]

Exit code 0 = GO (no hard failures). Non-zero = NO-GO.

-------------------------------------------------------------------------------
AUDIT 2026-07-31 - this gate could previously say GO having measured nothing.
Five defects, all the same class: the check ran and printed, but computed
something *adjacent* to the claim it made. See [[green-but-uncovered]] v10.

  1. DRC/ERC fail-open + cross-contamination. Reports went to a FIXED
     /tmp/_fg_drc.rpt that was never deleted, and run_cli's error return was
     discarded. kicad-cli failing -> no file -> empty text -> "0 hard, 0
     unconnected" -> OK. Failing on board 2 -> board 2 graded on board 1's
     report. (board_health.py, older, does os.remove its report first. This
     file, newer and trusted more, dropped the guard.)
     FIXED: per-call TemporaryDirectory; return code checked; the report must
     exist, must name THIS board in its header, and must carry the
     end-of-report marker. Anything else is FAIL, never OK.
  2. Gerber freshness compared MTIME, not content - meaningless after any
     clone/checkout, where both mtimes are checkout timestamps in arbitrary
     order. Demonstrated 2026-07-31: byte-identical trees reported STALE in one
     checkout and fresh in another.
     FIXED: regenerate gerbers + drill and compare content, with generation
     timestamps normalised out.
  3. DNP roster was printed, never asserted - always OK.
     FIXED: asserted against EXPECTED_DNP below.
  4. Single-pad nets were WARN, so the stranded-rail bug this check exists for
     would not have blocked GO.  FIXED: FAIL unless explicitly allowlisted.
  5. ERC regex miss -> e = -1, tested with `> 0` -> OK. Fail-open on any
     output-format change.  FIXED: unparseable == FAIL.

Each of the five has a planted-failure test in tools/test_fab_gate.py - the fix
is not trusted until the check has been SEEN going red. Run it after touching
anything in here.
-------------------------------------------------------------------------------
"""
import sys, os, glob, subprocess, re, tempfile, zipfile

CLI = os.environ.get(
    "KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

# DRC/ERC violation types that BLOCK fab vs. cosmetic ones that only warn.
SOFT = {"lib_footprint_mismatch", "lib_symbol_mismatch", "silk_over_copper",
        "silk_overlap", "silk_over_silk", "courtyards_overlap_info"}

J20_REF = "J20"  # inter-board mezzanine connector present on both boards

# Asserted, not printed. Keyed by board file stem.
#   U5  = arm buck station, Phase-4, genuinely DNP (no arm exists yet).
#   U12 is deliberately NOT listed. The 4th INA226 was reassigned to the L2 rail
#   at 0x45 on 2026-06-30 and the firmware publishes it (-D NOVA_INA226_L2,
#   /power_rails[9..11]), so it must be POPULATED. The board file still carries a
#   stale DNP flag on it, and this assertion is what surfaces that.
EXPECTED_DNP = {
    "nova_pcb_v6_power_v2": {"U5"},
    "nova_pcb_v6_logic": set(),
}

# Single-pad nets that are intentional. Empty set => any single-pad net blocks.
ALLOWED_SINGLE_PAD_NETS = {
    "nova_pcb_v6_power_v2": set(),
    "nova_pcb_v6_logic": set(),
}

# Lines that legitimately differ between two exports of the SAME board.
TS_NOISE = re.compile(r"CreationDate|Created by KiCad|DRILL file \{")


def run_cli(args):
    """Return (ok, combined_output). ok=False on nonzero exit OR exception.

    The old version returned only text and callers discarded it, so a failed
    invocation was indistinguishable from a clean run.
    """
    try:
        p = subprocess.run([CLI] + args, capture_output=True, text=True,
                           timeout=600)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return False, f"__CLI_ERROR__ {type(e).__name__}: {e}"


def get_report(kind, path):
    """Run erc/drc into a PRIVATE temp dir. Return (text, err).

    text is None on any failure. A fresh TemporaryDirectory per call makes it
    structurally impossible to read a previous board's report.
    """
    sub = ["sch", "erc"] if kind == "erc" else ["pcb", "drc"]
    with tempfile.TemporaryDirectory() as td:
        rpt = os.path.join(td, f"{kind}.rpt")
        ok, out = run_cli(sub + ["--output", rpt, path])
        if not ok:
            return None, f"{kind} run failed: {out.strip()[:160]}"
        if not os.path.exists(rpt):
            return None, f"{kind}: no report produced"
        with open(rpt, encoding="utf-8", errors="replace") as fh:
            return fh.read(), ""


def parse_drc(txt, board_file):
    """Return dict, or None meaning 'could not verify' -> FAIL, never OK.

    Also asserts the report is FOR THIS BOARD and is complete: a second,
    independent guard against grading one board on another's report.
    """
    if not txt:
        return None
    if os.path.basename(board_file) not in txt.split("\n")[0]:
        return None                       # header names a different board
    if "** End of Report **" not in txt:
        return None                       # truncated / partially written
    mv = re.search(r"Found (\d+) DRC violations", txt)
    mu = re.search(r"Found (\d+) unconnected pads", txt)
    mf = re.search(r"Found (\d+) Footprint errors", txt)
    if not (mv and mu):
        return None
    tally = {}
    for k in re.findall(r"\[([a-z_]+)\]", txt):
        tally[k] = tally.get(k, 0) + 1
    tally.pop("unconnected_items", None)  # double-counted in the unconnected total
    return {
        "violations": int(mv.group(1)),
        "unconnected": int(mu.group(1)),
        "footprint_errors": int(mf.group(1)) if mf else 0,
        "hard": {k: v for k, v in tally.items() if k not in SOFT},
        "soft": {k: v for k, v in tally.items() if k in SOFT},
    }


def parse_erc(txt):
    """Return (errors, warnings) or None. None == FAIL (was: -1 -> 'OK')."""
    if not txt:
        return None
    m = re.search(r"ERC messages:\s*\d+\s+Errors\s+(\d+)\s+Warnings\s+(\d+)", txt)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def norm_gerber(text):
    """Strip only the lines that differ between two exports of one board."""
    return "\n".join(l for l in text.splitlines() if not TS_NOISE.search(l))


def compare_gbrjob(shipped_text, fresh_text):
    """.gbrjob needs a semantic compare, and here is the justification.

    It is a MANIFEST: its FilesAttributes list reflects which layers that
    particular export selected, not what the board contains. A default
    regeneration includes layers the original export did not (Adhesive, User_*),
    so a byte compare reports a difference that says nothing about the artwork.

    So: every file the SHIPPED job describes must still be described
    identically. Extra entries in the fresh job are ignored; a changed or
    vanished description is not. This is deliberately narrow -- the copper,
    mask, silk and drill files are still compared byte-for-byte above.

    Returns (ok, reason).
    """
    import json
    try:
        a = json.loads(shipped_text)
        b = json.loads(fresh_text)
    except Exception as e:
        return False, f"gbrjob not parseable: {e}"
    def strip_dates(o):
        # CreationDate appears in BOTH Header and GeneralSpecs, and they carry
        # different values. Popping only the one you thought of leaves the
        # compare failing for a reason that has nothing to do with the artwork.
        if isinstance(o, dict):
            return {k: strip_dates(v) for k, v in o.items() if k != "CreationDate"}
        if isinstance(o, list):
            return [strip_dates(v) for v in o]
        return o

    a, b = strip_dates(a), strip_dates(b)
    fa = {e.get("Path"): e for e in a.pop("FilesAttributes", []) or []}
    fb = {e.get("Path"): e for e in b.pop("FilesAttributes", []) or []}
    if a != b:
        return False, "gbrjob specs differ (not just the file list)"
    for path, ent in sorted(fa.items()):
        if path not in fb:
            return False, f"gbrjob: shipped file {path} is no longer produced"
        if fb[path] != ent:
            return False, f"gbrjob: {path} description changed"
    return True, ""


def check_gerbers(pcb, zip_path):
    """Compare shipped gerbers to a fresh export BY CONTENT. (level, msg)."""
    with tempfile.TemporaryDirectory() as td:
        ok1, o1 = run_cli(["pcb", "export", "gerbers", "--output", td, pcb])
        ok2, o2 = run_cli(["pcb", "export", "drill", "--excellon-separate-th",
                           "--output", td + os.sep, pcb])
        if not (ok1 and ok2):
            return "FAIL", ("gerber regen FAILED, cannot verify: "
                            + (o1 + o2).strip()[:140].replace("\n", " "))
        try:
            with zipfile.ZipFile(zip_path) as zf:
                shipped = {os.path.basename(n): zf.read(n)
                           for n in zf.namelist() if not n.endswith("/")}
        except Exception as e:
            return "FAIL", f"cannot read {os.path.basename(zip_path)}: {e}"
        if not shipped:
            return "FAIL", f"{os.path.basename(zip_path)} is empty"
        missing, differ = [], []
        for fname, data in sorted(shipped.items()):
            fresh = os.path.join(td, fname)
            if not os.path.exists(fresh):
                missing.append(fname)
                continue
            with open(fresh, encoding="utf-8", errors="replace") as fh:
                fresh_text = fh.read()
            ship_text = data.decode("utf-8", "replace")
            if fname.endswith(".gbrjob"):
                ok_job, why = compare_gbrjob(ship_text, fresh_text)
                if not ok_job:
                    differ.append(f"{fname} ({why})")
            elif norm_gerber(fresh_text) != norm_gerber(ship_text):
                differ.append(fname)
        if differ or missing:
            bits = []
            if differ:
                bits.append("CONTENT DIFFERS: " + ", ".join(differ))
            if missing:
                bits.append("not reproducible: " + ", ".join(missing))
            return "FAIL", "gerbers STALE vs board - " + "; ".join(bits)
        return "OK", (f"gerbers match board content "
                      f"({len(shipped)} files, timestamps ignored)")


def check_dnp(stem, actual):
    """Assert the DNP roster instead of printing it. (level, msg)."""
    exp = EXPECTED_DNP.get(stem)
    actual = set(actual)
    if exp is None:
        return "WARN", (f"DNP {sorted(actual) or '(none)'} - no expected roster "
                        f"for '{stem}', NOT asserted")
    if actual != exp:
        bits = []
        extra = sorted(actual - exp)
        miss = sorted(exp - actual)
        if extra:
            bits.append("marked DNP but expected populated: " + ", ".join(extra))
        if miss:
            bits.append("expected DNP but is populated: " + ", ".join(miss))
        return "FAIL", "DNP roster MISMATCH - " + "; ".join(bits)
    return "OK", f"DNP roster == expected {sorted(exp) or '(none)'}"


def check_single_pad_nets(stem, singles):
    """A dangling output is a stranded rail. Blocks, unless allowlisted."""
    allow = ALLOWED_SINGLE_PAD_NETS.get(stem, set())
    bad = {n: v for n, v in singles.items() if n not in allow}
    if bad:
        return "FAIL", ("single-pad nets (stranded?): "
                        + ", ".join(f"{n}({v})" for n, v in sorted(bad.items())))
    return "OK", f"no unexpected single-pad nets ({len(allow)} allowlisted)"


def check_board(pcb):
    """Return (board_name, list[(level, msg)]) - level in {FAIL, WARN, OK}."""
    import pcbnew
    name = os.path.splitext(os.path.basename(pcb))[0]
    d = os.path.dirname(pcb) or "."
    sch = os.path.join(d, name + ".kicad_sch")
    res = []

    # 1. ERC - unparseable is FAIL, not OK
    if os.path.exists(sch):
        txt, err = get_report("erc", sch)
        parsed = parse_erc(txt)
        if parsed is None:
            res.append(("FAIL", f"ERC: UNVERIFIED - {err or 'could not parse report'}"))
        else:
            e, w = parsed
            res.append(("FAIL" if e > 0 else "OK", f"ERC: {e} errors, {w} warnings"))
    else:
        res.append(("WARN", "no .kicad_sch found - skipped ERC"))

    # 2. DRC (live). Unparseable / wrong board / truncated is FAIL.
    txt, err = get_report("drc", pcb)
    drc = parse_drc(txt, pcb)
    if drc is None:
        res.append(("FAIL", "DRC: UNVERIFIED - "
                    + (err or "unparseable, wrong board, or truncated report")))
    else:
        hard_n = sum(drc["hard"].values())
        bad = hard_n or drc["unconnected"] or drc["footprint_errors"]
        res.append((("FAIL" if bad else "OK"),
                    f"DRC: {hard_n} hard, {sum(drc['soft'].values())} cosmetic, "
                    f"{drc['unconnected']} unconnected, "
                    f"{drc['footprint_errors']} footprint errors"))
        if drc["hard"]:
            res.append(("FAIL", "  hard: " + ", ".join(
                f"{k}={v}" for k, v in sorted(drc["hard"].items()))))
        if drc["soft"]:
            res.append(("WARN", "  cosmetic: " + ", ".join(
                f"{k}={v}" for k, v in sorted(drc["soft"].items()))))

    # 3. Gerber freshness - by CONTENT, not mtime
    zips = glob.glob(os.path.join(d, "*gerbers*.zip"))
    if not zips:
        res.append(("FAIL", "no gerber zip found - nothing to verify"))
    else:
        for z in zips:
            lvl, msg = check_gerbers(pcb, z)
            res.append((lvl, f"{msg}  [{os.path.basename(z)}]"))

    # 4 + 5. DNP roster + single-pad nets - both asserted
    b = pcbnew.LoadBoard(pcb)
    dnp = sorted(f.GetReference() for f in b.GetFootprints()
                 if getattr(f, "IsDNP", lambda: False)())
    res.append(check_dnp(name, dnp))
    b.BuildConnectivity()
    padcount = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n:
                padcount.setdefault(n, []).append(
                    f"{f.GetReference()}.{p.GetPadName()}")
    singles = {n: v[0] for n, v in padcount.items()
               if len(set(v)) == 1 and not n.startswith("unconnected")}
    res.append(check_single_pad_nets(name, singles))
    return name, res


def j20_map(pcb):
    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    f = b.FindFootprintByReference(J20_REF)
    if not f:
        return None
    return {p.GetPadName(): p.GetNetname() for p in f.Pads()}


ACTIVE = ["nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_pcb",
          "nova_pcb_v6_logic/nova_pcb_v6_logic.kicad_pcb"]


def main():
    args = sys.argv[1:]
    explicit = [a for a in args if a.endswith(".kicad_pcb")]
    if explicit:
        pcbs = explicit
    else:
        base = args[0] if args else "."
        pcbs = [os.path.join(base, p) for p in ACTIVE
                if os.path.exists(os.path.join(base, p))]
    pcbs = sorted(set(p for p in pcbs if os.path.exists(p)))
    if not pcbs:
        print("no active boards found (looked for:", ", ".join(ACTIVE), ")")
        return 2

    if not os.path.exists(CLI):
        print(f"x kicad-cli not found at {CLI} - set $KICAD_CLI. "
              f"Refusing to report GO without running DRC/ERC.")
        return 2

    print("=" * 64)
    print("NOVA v6 FAB-READINESS GATE")
    print("=" * 64)
    any_fail = False
    j20s = {}
    marks = {"FAIL": "x", "WARN": "!", "OK": "+"}
    for pcb in pcbs:
        name, res = check_board(pcb)
        print(f"\n### {name}")
        for level, msg in res:
            print(f"  {marks[level]} {msg}")
            if level == "FAIL":
                any_fail = True
        j = j20_map(pcb)
        if j:
            j20s[name] = j

    print("\n### cross-board J20 mezzanine")
    if len(j20s) >= 2:
        names = list(j20s)
        a, bb = j20s[names[0]], j20s[names[1]]
        pins = sorted(set(a) | set(bb), key=lambda x: int(x) if x.isdigit() else 99)
        mism = [p for p in pins if a.get(p) != bb.get(p)]
        if mism:
            any_fail = True
            print(f"  x J20 MISMATCH between {names[0]} and {names[1]}:")
            for p in mism:
                print(f"      pin {p}: {names[0]}={a.get(p)}  {names[1]}={bb.get(p)}")
        else:
            print(f"  + J20 identical across {names[0]} <-> {names[1]} ({len(pins)} pins)")
    else:
        # Was a silent pass. Two boards that cannot talk is a fab-blocking fact.
        any_fail = True
        print("  x fewer than 2 boards carry J20 - cross-check COULD NOT RUN")

    print("\n" + "=" * 64)
    print("GATE: " + ("NO-GO x (hard failures above)" if any_fail else "GO +"))
    print("=" * 64)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
