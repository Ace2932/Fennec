#!/usr/bin/env python3
"""
test_check_length_match.py - pytest suite for check_length_match.py. (#416)

Separate from check_length_match.py's own --selftest (which is the synthetic
in-tool fixture the issue asks for and is not pytest-collectible on its own
merits either way -- it's a script, run standalone). This file exists so the
gate has an ordinary pytest-collectible regression suite next to
test_fab_gate.py, per #416's verify section: "must fail if the checker
ignores a missing net or a spread over tolerance."

Run: pytest hardware/pcb-mods/tools/test_check_length_match.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_length_match as clm

SPEC = {
    "via_allowance_mm": 1.6,
    "via_allowance_budget": "test fixture",
    "groups": [{
        "name": "g",
        "tolerance_mm": 5.0,
        "budget": "test",
        "members": [{"nets": ["A"]}, {"nets": ["B"]}],
    }],
}


def _board(net_defs, segment_defs, via_defs=()):
    return clm._synth_board(net_defs, segment_defs, via_defs)


def test_clean_board_passes():
    board = _board([(0, ""), (1, "A"), (2, "B")],
                    [(1, 0, 0, 10, 0), (2, 0, 0, 10, 1)])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    code, _ = clm.evaluate_spec(SPEC, length_by_net, vias_by_net, leaf_map)
    assert code == 0


def test_spread_over_tolerance_fails():
    """The checker must NOT ignore a spread over tolerance -- exit 1, group named."""
    board = _board([(0, ""), (1, "A"), (2, "B")],
                    [(1, 0, 0, 10, 0), (2, 0, 0, 100, 0)])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    code, lines = clm.evaluate_spec(SPEC, length_by_net, vias_by_net, leaf_map)
    assert code == 1
    assert any("FAIL" in l and "spread=" in l for l in lines)


def test_missing_net_is_exit_2_not_silently_skipped():
    """A net named in the spec but absent from the board must FAIL (2), never
    be treated as 0-length or silently dropped from the group."""
    spec = {
        "via_allowance_mm": 1.6, "via_allowance_budget": "test",
        "groups": [{"name": "g", "tolerance_mm": 5.0, "budget": "test",
                     "members": [{"nets": ["A"]}, {"nets": ["GHOST"]}]}],
    }
    board = _board([(0, ""), (1, "A")], [(1, 0, 0, 10, 0)])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    code, lines = clm.evaluate_spec(spec, length_by_net, vias_by_net, leaf_map)
    assert code == 2
    assert any("GHOST" in l for l in lines)


def test_unrouted_net_is_exit_2():
    """A net declared on the board (has an id) but with zero copper and zero
    vias must FAIL (2), not be scored as 0.0 mm and averaged into the group."""
    board = _board([(0, ""), (1, "A"), (2, "B")], [(1, 0, 0, 10, 0)])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    code, lines = clm.evaluate_spec(SPEC, length_by_net, vias_by_net, leaf_map)
    assert code == 2
    assert any("unrouted" in l for l in lines)


def test_via_allowance_is_applied():
    board = _board([(0, ""), (1, "A"), (2, "B")],
                    [(1, 0, 0, 10, 0), (2, 0, 0, 10, 0)], via_defs=[2])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    a = clm.resolve_member(["A"], leaf_map, length_by_net, vias_by_net, 1.6)
    b = clm.resolve_member(["B"], leaf_map, length_by_net, vias_by_net, 1.6)
    assert round(b - a, 4) == 1.6


def test_multi_net_member_sums():
    board = _board([(0, ""), (1, "A"), (2, "A_F")],
                    [(1, 0, 0, 10, 0), (2, 0, 0, 5, 0)])
    length_by_net, vias_by_net, net_names = clm.measure_board(board)
    leaf_map = clm.build_leaf_map(net_names)
    total = clm.resolve_member(["A", "A_F"], leaf_map, length_by_net, vias_by_net, 0.0)
    assert total == 15.0


def test_real_boards_pass_on_main():
    """Both v6 boards must PASS with the committed tolerances (#416)."""
    here = os.path.dirname(os.path.abspath(__file__))
    pcbmods = os.path.dirname(here)
    for board_dir, board_file in [
        ("nova_pcb_v6_logic", "nova_pcb_v6_logic.kicad_pcb"),
        ("nova_pcb_v6_power_v2", "nova_pcb_v6_power_v2.kicad_pcb"),
    ]:
        board_path = os.path.join(pcbmods, board_dir, board_file)
        spec_path = os.path.join(pcbmods, board_dir, "length_match.json")
        assert clm.run(board_path, spec_path) == 0, board_dir


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
