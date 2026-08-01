#!/usr/bin/env python3
"""
test_fab_gate.py - planted-failure tests for fab_gate.py.

Every check in fab_gate exists to go RED on a specific defect. A check that has
never been SEEN red is not a check -- that is how all five of the 2026-07-31
audit findings survived: they ran, printed, and were believed.

So each case here PLANTS the defect and asserts the gate catches it. Positive
controls (clean input -> OK) are included too, because a check that fails on
everything is equally useless.

Run with either python3:
  python3 tools/test_fab_gate.py                     # parser/logic cases only
  /Applications/KiCad/.../python3 tools/test_fab_gate.py --with-kicad   # + real gerber regen

Exit 0 = all planted failures were caught.
"""
import os, sys, re, shutil, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fab_gate as fg

HERE = os.path.dirname(os.path.abspath(__file__))
PCBMODS = os.path.dirname(HERE)
LOGIC = os.path.join(PCBMODS, "nova_pcb_v6_logic", "nova_pcb_v6_logic.kicad_pcb")
LOGIC_ZIP = os.path.join(PCBMODS, "nova_pcb_v6_logic",
                         "nova_pcb_v6_logic_gerbers.zip")

RESULTS = []


def case(name, got, want, note=""):
    ok = got == want
    RESULTS.append((ok, name, got, want, note))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got={got!r}\n        want={want!r}")


# Real KiCad output, captured 2026-07-31, used as the "clean" baseline.
DRC_OK = """** Drc report for nova_pcb_v6_logic.kicad_pcb **
** Created on 2026-07-31T20:39:08-0700 **

** Found 7 DRC violations **
[lib_footprint_mismatch]: Footprint doesn't match copy in library
    Local override; severity: warning
** Found 0 unconnected pads **
** Found 0 Footprint errors **
** End of Report **
"""
ERC_OK = " ** ERC messages: 2  Errors 0  Warnings 2\n"


print("\n=== 1. ERC: unparseable must FAIL, not read as 0 errors ===")
print("    (old code: regex miss -> e=-1 -> 'FAIL if e > 0' -> OK)")
case("clean ERC parses", fg.parse_erc(ERC_OK), (0, 2))
case("PLANTED empty report -> None", fg.parse_erc(""), None)
case("PLANTED garbage -> None", fg.parse_erc("kicad-cli: command not found"), None)
case("PLANTED format change -> None",
     fg.parse_erc(" ** ERC summary: 0 problems\n"), None)
case("real errors are seen", fg.parse_erc(
     " ** ERC messages: 5  Errors 3  Warnings 2\n"), (3, 2))

print("\n=== 2. DRC: unparseable / truncated / WRONG BOARD must FAIL ===")
print("    (old code: missing report -> '' -> 0 hard, 0 unconnected -> OK)")
d = fg.parse_drc(DRC_OK, LOGIC)
case("clean DRC parses", d is not None, True)
case("  soft tally counted", (d or {}).get("soft"), {"lib_footprint_mismatch": 1})
case("  hard tally empty", (d or {}).get("hard"), {})
case("PLANTED empty report -> None", fg.parse_drc("", LOGIC), None)
case("PLANTED CLI error text -> None",
     fg.parse_drc("__CLI_ERROR__ FileNotFoundError", LOGIC), None)
case("PLANTED truncated (no end marker) -> None",
     fg.parse_drc(DRC_OK.replace("** End of Report **", ""), LOGIC), None)

print("\n=== 3. DRC cross-contamination: board A's report must not grade board B ===")
print("    (old code: fixed /tmp/_fg_drc.rpt, never deleted, no header check)")
other = os.path.join(PCBMODS, "nova_pcb_v6_power_v2",
                     "nova_pcb_v6_power_v2.kicad_pcb")
case("PLANTED logic report vs power board -> None",
     fg.parse_drc(DRC_OK, other), None,
     "this is the exact stale-/tmp-file scenario")
case("same report vs its own board -> parses",
     fg.parse_drc(DRC_OK, LOGIC) is not None, True)

print("\n=== 4. DNP roster must be ASSERTED, not printed ===")
print("    (old code: always ('OK', <printed list>))")
case("expected roster passes", fg.check_dnp("nova_pcb_v6_power_v2", ["U5"])[0], "OK")
case("PLANTED stale U12 DNP flag -> FAIL",
     fg.check_dnp("nova_pcb_v6_power_v2", ["U5", "U12"])[0], "FAIL",
     "the real current state of the board file")
case("PLANTED arm buck accidentally populated -> FAIL",
     fg.check_dnp("nova_pcb_v6_power_v2", [])[0], "FAIL")
case("PLANTED unknown board -> WARN not OK",
     fg.check_dnp("some_new_board", ["U9"])[0], "WARN")
case("logic board clean", fg.check_dnp("nova_pcb_v6_logic", [])[0], "OK")

print("\n=== 5. Single-pad nets must BLOCK, not warn ===")
print("    (old code: WARN, which never touched any_fail)")
case("no singles -> OK", fg.check_single_pad_nets("nova_pcb_v6_power_v2", {})[0], "OK")
case("PLANTED stranded rail -> FAIL",
     fg.check_single_pad_nets("nova_pcb_v6_power_v2", {"V7V5_ARM": "U5.4"})[0],
     "FAIL", "the original bug this check was written for")

print("\n=== 6. A broken CLI must FAIL, never silently pass ===")
print("    (old code: run_cli's error return was discarded entirely)")
_real_cli = fg.CLI
fg.CLI = "/nonexistent/kicad-cli"
ok, out = fg.run_cli(["pcb", "drc"])
case("PLANTED missing binary -> run_cli ok=False", ok, False)
txt, err = fg.get_report("drc", LOGIC)
case("PLANTED missing binary -> get_report text is None", txt, None)
case("PLANTED missing binary -> parse_drc(None) is None", fg.parse_drc(txt, LOGIC), None)
lvl, _ = fg.check_gerbers(LOGIC, LOGIC_ZIP)
case("PLANTED missing binary -> gerber check FAILs", lvl, "FAIL",
     "cannot verify != verified")
fg.CLI = _real_cli

print("\n=== 7. Gerber freshness by CONTENT, not mtime ===")
if "--with-kicad" not in sys.argv:
    print("  SKIP (needs kicad-cli + a few seconds) - pass --with-kicad to run")
elif not os.path.exists(LOGIC_ZIP):
    print("  SKIP - no logic gerber zip present")
else:
    lvl, msg = fg.check_gerbers(LOGIC, LOGIC_ZIP)
    case("real shipped zip matches board", lvl, "OK", msg)

    # PLANT: mtime says fresh, content says otherwise. This is precisely the
    # case the old mtime check could not see.
    with tempfile.TemporaryDirectory() as td:
        tampered = os.path.join(td, "nova_pcb_v6_logic_gerbers.zip")
        with zipfile.ZipFile(LOGIC_ZIP) as src, \
             zipfile.ZipFile(tampered, "w") as dst:
            for n in src.namelist():
                data = src.read(n)
                if n.endswith("F_Cu.gtl"):
                    data = data + b"\nG04 planted difference*\n"
                dst.writestr(n, data)
        os.utime(tampered, None)          # newest file in the tree
        lvl2, msg2 = fg.check_gerbers(LOGIC, tampered)
        case("PLANTED altered copper, mtime NEWER -> FAIL", lvl2, "FAIL", msg2)

    # PLANT: a shipped file that the board can no longer reproduce.
    with tempfile.TemporaryDirectory() as td:
        extra = os.path.join(td, "nova_pcb_v6_logic_gerbers.zip")
        with zipfile.ZipFile(LOGIC_ZIP) as src, \
             zipfile.ZipFile(extra, "w") as dst:
            for n in src.namelist():
                dst.writestr(n, src.read(n))
            dst.writestr("nova_pcb_v6_logic-Ghost_Layer.gbr", "G04 ghost*\n")
        lvl3, msg3 = fg.check_gerbers(LOGIC, extra)
        case("PLANTED unreproducible file -> FAIL", lvl3, "FAIL", msg3)

print("\n=== 8. .gbrjob semantic compare — the exclusion must stay narrow ===")
JOB_A = ('{"GeneralSpecs":{"CreationDate":"2026-01-01T00:00:00","ProjectId":{"Name":"x"}},'
         '"FilesAttributes":[{"Path":"a-F_Cu.gtl","FileFunction":"Copper,L1,Top"}]}')
JOB_EXTRA = ('{"GeneralSpecs":{"CreationDate":"2026-07-31T00:00:00","ProjectId":{"Name":"x"}},'
             '"FilesAttributes":[{"Path":"a-F_Cu.gtl","FileFunction":"Copper,L1,Top"},'
             '{"Path":"a-F_Adhesive.gta","FileFunction":"Glue,Top"}]}')
JOB_CHANGED = ('{"GeneralSpecs":{"CreationDate":"2026-07-31T00:00:00","ProjectId":{"Name":"x"}},'
               '"FilesAttributes":[{"Path":"a-F_Cu.gtl","FileFunction":"Copper,L2,Top"}]}')
JOB_DROPPED = ('{"GeneralSpecs":{"CreationDate":"2026-07-31T00:00:00","ProjectId":{"Name":"x"}},'
               '"FilesAttributes":[]}')
JOB_SPECS = ('{"GeneralSpecs":{"CreationDate":"2026-07-31T00:00:00","ProjectId":{"Name":"DIFFERENT"}},'
             '"FilesAttributes":[{"Path":"a-F_Cu.gtl","FileFunction":"Copper,L1,Top"}]}')
case("extra fresh layers ignored (the real artifact)",
     fg.compare_gbrjob(JOB_A, JOB_EXTRA)[0], True)
case("PLANTED shipped file's FileFunction changed -> not ok",
     fg.compare_gbrjob(JOB_A, JOB_CHANGED)[0], False)
case("PLANTED shipped file no longer produced -> not ok",
     fg.compare_gbrjob(JOB_A, JOB_DROPPED)[0], False)
case("PLANTED specs differ -> not ok",
     fg.compare_gbrjob(JOB_A, JOB_SPECS)[0], False)

print("\n=== 9. norm_gerber strips ONLY timestamps ===")
case("timestamp line dropped",
     fg.norm_gerber("%TF.CreationDate,2026-01-01T00:00:00*%\nX1Y2D02*"), "X1Y2D02*")
case("PLANTED real copper change survives normalisation",
     fg.norm_gerber("X1Y2D02*") == fg.norm_gerber("X9Y9D02*"), False,
     "normalisation must not hide geometry")

bad = [r for r in RESULTS if not r[0]]
print("\n" + "=" * 64)
print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} cases passed")
if bad:
    print("FAILED CASES:")
    for _, name, got, want, note in bad:
        print(f"  - {name}: got {got!r}, want {want!r} {note}")
print("=" * 64)
sys.exit(1 if bad else 0)
