#!/usr/bin/env python3
"""
check_length_match.py - headless PCB length-matching gate. (#416)

Sums routed (segment) length per net from a .kicad_pcb, groups nets per a
per-board length_match.json spec, and checks spread-vs-tolerance and
max-length. Nets are matched to the spec by LEAF name (the part of the KiCad
net name after the last "/") because several nets on these boards carry a
hierarchical sheet prefix that itself contains "/" and even "+"
(e.g. "/07 Aux MCU + Peripherals/SPI_SCK") -- splitting a spec string on "+"
would silently break on that sheet name, so the spec lists each net's short
name as a JSON array member instead of a delimited string.

stdlib only (sys, os, json, math, argparse) -- no pcbnew import, so this runs
in CI and does not need a KiCad install.

Exit codes:
  0 = every group's spread <= tolerance_mm and no member > max_mm
  1 = a group's spread > tolerance_mm, or a member length > max_mm
  2 = a net named in the spec is missing from the board, or present but
      unrouted (0 length, 0 vias) -- checked BEFORE 1, so a spec typo or a
      deleted net can never be silently graded as a pass.

Usage:
  python3 check_length_match.py <board.kicad_pcb> <length_match.json>
  python3 check_length_match.py --selftest
"""
import sys
import os
import json
import math
import argparse

# ---------------------------------------------------------------------------
# Minimal s-expression parser (KiCad's .kicad_pcb format). No regex scraping:
# a full parse means a net name or a coordinate that happens to contain a
# paren or a digit sequence resembling a record header can't be misread.
# ---------------------------------------------------------------------------

def tokenize(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            toks.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            toks.append(("str", "".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            toks.append(("atom", text[i:j]))
            i = j
    return toks


def parse_sexp(text):
    toks = tokenize(text)
    pos = [0]

    def read():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            items = []
            while toks[pos[0]] != ")":
                items.append(read())
            pos[0] += 1
            return items
        if t == ")":
            raise ValueError("unbalanced parens")
        if isinstance(t, tuple) and t[0] == "str":
            return t[1]
        v = t[1]
        try:
            return int(v)
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return v

    if not toks:
        return []
    return read()


def walk_collect(node, head, out):
    """Recursively collect every list whose first element == head."""
    if isinstance(node, list):
        if node and node[0] == head:
            out.append(node)
        for child in node:
            walk_collect(child, head, out)


def field(node, key):
    """First sub-list under `node` whose head is `key`; returns its tail, or None."""
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c[1:]
    return None


# ---------------------------------------------------------------------------
# Board measurement
# ---------------------------------------------------------------------------

def measure_board(text):
    """Return (length_by_net_id, vias_by_net_id, net_name_by_id)."""
    tree = parse_sexp(text)

    net_decls = []
    walk_collect(tree, "net", net_decls)
    net_names = {}
    for nd in net_decls:
        if len(nd) == 3 and isinstance(nd[1], int) and isinstance(nd[2], str):
            net_names[nd[1]] = nd[2]

    segments = []
    walk_collect(tree, "segment", segments)
    vias = []
    walk_collect(tree, "via", vias)

    length_by_net = {}
    for s in segments:
        start = field(s, "start")
        end = field(s, "end")
        net = field(s, "net")
        if start is None or end is None or net is None:
            continue
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_by_net[net[0]] = length_by_net.get(net[0], 0.0) + math.hypot(dx, dy)

    vias_by_net = {}
    for v in vias:
        net = field(v, "net")
        if net is None:
            continue
        vias_by_net[net[0]] = vias_by_net.get(net[0], 0) + 1

    return length_by_net, vias_by_net, net_names


def leaf_name(full_name):
    return full_name.rsplit("/", 1)[-1]


def build_leaf_map(net_names):
    """leaf net name -> net id. Net 0 (unconnected/no-net) is never a spec target."""
    leaf = {}
    for nid, name in net_names.items():
        if nid == 0:
            continue
        leaf.setdefault(leaf_name(name), []).append(nid)
    return leaf


# ---------------------------------------------------------------------------
# Spec evaluation
# ---------------------------------------------------------------------------

class NetProblem(Exception):
    """A spec-named net is missing or unrouted -- always exit 2."""


def resolve_member(net_list, leaf_map, length_by_net, vias_by_net, via_allowance_mm):
    """Sum length (+ via allowance) for one match-group member (>=1 net names).

    Raises NetProblem naming the first missing/unrouted net; that is exit-2
    territory and must never be swallowed into a plain 0.0 / an average / a
    silently-skipped member -- that is exactly the "oosRate stayed null"
    failure shape #416 calls out.
    """
    total = 0.0
    total_vias = 0
    for net in net_list:
        ids = leaf_map.get(net)
        if not ids:
            raise NetProblem(f"net '{net}' not found on board (spec/board name mismatch?)")
        for nid in ids:
            length = length_by_net.get(nid, 0.0)
            vias = vias_by_net.get(nid, 0)
            if length == 0.0 and vias == 0:
                raise NetProblem(f"net '{net}' present but unrouted (0 length, 0 vias)")
            total += length
            total_vias += vias
    total += total_vias * via_allowance_mm
    return total


def evaluate_spec(spec, length_by_net, vias_by_net, leaf_map):
    """Return (exit_code, report_lines: list[str])."""
    via_allowance_mm = spec["via_allowance_mm"]
    lines = []
    lines.append(f"via allowance: {via_allowance_mm:g} mm/via "
                  f"({spec.get('via_allowance_budget', 'no budget string given')})")

    worst_exit = 0
    for group in spec["groups"]:
        name = group["name"]
        tol = group["tolerance_mm"]
        max_mm = group.get("max_mm")
        lines.append(f"\n[{name}]  tolerance={tol:g} mm"
                      + (f"  max={max_mm:g} mm" if max_mm is not None else ""))
        lines.append(f"  budget: {group['budget']}")

        member_lengths = {}
        for member in group["members"]:
            label = "+".join(member["nets"])
            try:
                length = resolve_member(member["nets"], leaf_map, length_by_net,
                                         vias_by_net, via_allowance_mm)
            except NetProblem as e:
                lines.append(f"  x {label}: {e}")
                worst_exit = 2
                continue
            member_lengths[label] = length

        if not member_lengths:
            continue  # every member in this group hit a NetProblem above

        lo_label = min(member_lengths, key=member_lengths.get)
        hi_label = max(member_lengths, key=member_lengths.get)
        lo, hi = member_lengths[lo_label], member_lengths[hi_label]
        spread = hi - lo

        for label, length in sorted(member_lengths.items(), key=lambda kv: kv[1]):
            over = length > max_mm if max_mm is not None else False
            flag = " OVER MAX" if over else ""
            lines.append(f"    {label}: {length:.4f} mm{flag}")
            if over and worst_exit < 2:
                worst_exit = max(worst_exit, 1)

        spread_bad = spread > tol
        lines.append(f"  min={lo:.4f}  max={hi:.4f}  spread={spread:.4f} mm"
                     + ("  FAIL (> tolerance)" if spread_bad else "  OK"))
        if spread_bad and worst_exit < 2:
            worst_exit = max(worst_exit, 1)

    return worst_exit, lines


def run(board_path, spec_path):
    with open(board_path, encoding="utf-8") as f:
        text = f.read()
    length_by_net, vias_by_net, net_names = measure_board(text)
    leaf_map = build_leaf_map(net_names)

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    code, lines = evaluate_spec(spec, length_by_net, vias_by_net, leaf_map)
    print(f"=== length-match gate: {os.path.basename(board_path)} "
          f"vs {os.path.basename(spec_path)} ===")
    for l in lines:
        print(l)
    verdict = {0: "PASS", 1: "FAIL (spread/max)", 2: "FAIL (missing/unrouted net)"}[code]
    print(f"\nRESULT: {verdict}  (exit {code})")
    return code


# ---------------------------------------------------------------------------
# --selftest: synthetic two-segment board fixture, no real board files needed.
# ---------------------------------------------------------------------------

def _synth_board(net_defs, segment_defs, via_defs=()):
    """net_defs: [(id,name)]; segment_defs: [(id,x1,y1,x2,y2)]; via_defs: [id,...]."""
    lines = ["(kicad_pcb", "  (general (thickness 1.6))"]
    for nid, name in net_defs:
        lines.append(f'  (net {nid} "{name}")')
    for nid, x1, y1, x2, y2 in segment_defs:
        lines.append(f"  (segment (start {x1} {y1}) (end {x2} {y2}) "
                      f'(width 0.25) (layer "F.Cu") (net {nid}) (uuid "x"))')
    for nid in via_defs:
        lines.append(f'  (via (at 0 0) (size 0.6) (drill 0.3) '
                      f'(layers "F.Cu" "B.Cu") (net {nid}) (uuid "y"))')
    lines.append(")")
    return "\n".join(lines)


def selftest():
    results = []

    def case(name, got, want):
        ok = got == want
        results.append((ok, name, got, want))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + ("" if ok else f"   got={got!r} want={want!r}"))

    print("=== check_length_match.py --selftest ===")

    # A: PASS case -- two nets, near-equal length, comfortably under tolerance.
    board_pass = _synth_board(
        [(0, ""), (1, "A"), (2, "B")],
        [(1, 0, 0, 10, 0), (2, 0, 0, 10, 1)],
    )
    spec_pass = {
        "via_allowance_mm": 1.6,
        "via_allowance_budget": "test fixture",
        "groups": [{
            "name": "g", "tolerance_mm": 5.0, "budget": "test",
            "members": [{"nets": ["A"]}, {"nets": ["B"]}],
        }],
    }
    length_by_net, vias_by_net, net_names = measure_board(board_pass)
    leaf_map = build_leaf_map(net_names)
    code, _ = evaluate_spec(spec_pass, length_by_net, vias_by_net, leaf_map)
    case("clean board, spread << tolerance -> exit 0", code, 0)

    # B: PLANTED spread-over-tolerance -- one net 10x the other.
    board_spread = _synth_board(
        [(0, ""), (1, "A"), (2, "B")],
        [(1, 0, 0, 10, 0), (2, 0, 0, 100, 0)],
    )
    length_by_net, vias_by_net, net_names = measure_board(board_spread)
    leaf_map = build_leaf_map(net_names)
    code, lines = evaluate_spec(spec_pass, length_by_net, vias_by_net, leaf_map)
    case("PLANTED 90mm spread vs 5mm tolerance -> exit 1", code, 1)
    case("  names the FAIL group", any("spread=90" in l and "FAIL" in l for l in lines), True)

    # C: PLANTED missing net -- spec names a net absent from the board entirely.
    spec_missing = {
        "via_allowance_mm": 1.6, "via_allowance_budget": "test fixture",
        "groups": [{
            "name": "g", "tolerance_mm": 5.0, "budget": "test",
            "members": [{"nets": ["A"]}, {"nets": ["GHOST"]}],
        }],
    }
    length_by_net, vias_by_net, net_names = measure_board(board_pass)
    leaf_map = build_leaf_map(net_names)
    code, lines = evaluate_spec(spec_missing, length_by_net, vias_by_net, leaf_map)
    case("PLANTED net named in spec, absent from board -> exit 2", code, 2)
    case("  names the missing net", any("GHOST" in l and "not found" in l for l in lines), True)

    # D: PLANTED unrouted net -- net declared on the board but zero copper, zero vias.
    board_unrouted = _synth_board(
        [(0, ""), (1, "A"), (2, "B")],  # B declared, never routed
        [(1, 0, 0, 10, 0)],
    )
    length_by_net, vias_by_net, net_names = measure_board(board_unrouted)
    leaf_map = build_leaf_map(net_names)
    code, lines = evaluate_spec(spec_pass, length_by_net, vias_by_net, leaf_map)
    case("PLANTED declared-but-unrouted net -> exit 2", code, 2)
    case("  names it unrouted", any("unrouted" in l for l in lines), True)

    # E: via allowance actually changes the summed length.
    board_via = _synth_board(
        [(0, ""), (1, "A"), (2, "B")],
        [(1, 0, 0, 10, 0), (2, 0, 0, 10, 0)],
        via_defs=[2],
    )
    length_by_net, vias_by_net, net_names = measure_board(board_via)
    leaf_map = build_leaf_map(net_names)
    a = resolve_member(["A"], leaf_map, length_by_net, vias_by_net, 1.6)
    b = resolve_member(["B"], leaf_map, length_by_net, vias_by_net, 1.6)
    case("equal copper length, B has a via -> B is 1.6mm longer", round(b - a, 4), 1.6)

    # F: multi-net member (the SPI "base+_F" case) sums correctly.
    board_multi = _synth_board(
        [(0, ""), (1, "A"), (2, "A_F")],
        [(1, 0, 0, 10, 0), (2, 0, 0, 5, 0)],
    )
    length_by_net, vias_by_net, net_names = measure_board(board_multi)
    leaf_map = build_leaf_map(net_names)
    total = resolve_member(["A", "A_F"], leaf_map, length_by_net, vias_by_net, 0.0)
    case("multi-net member sums (10 + 5 = 15)", total, 15.0)

    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)}/{len(results)} selftest cases passed")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", help=".kicad_pcb path")
    ap.add_argument("spec", nargs="?", help="length_match.json path")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.board or not args.spec:
        ap.error("board and spec are required unless --selftest is given")
    return run(args.board, args.spec)


if __name__ == "__main__":
    sys.exit(main())
