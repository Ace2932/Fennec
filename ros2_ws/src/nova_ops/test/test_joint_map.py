"""joint_id_map.yaml — loader + cross-consumer consistency lock.

The map was 'decided 2026-06-27' but every consumer restates it by
hand. These tests pin them all to the YAML so drift breaks CI instead
of a robot: loader semantics, per-leg-sequential convention, homing
config names, limits.py type grouping, URDF macro instantiation.
"""

import math
import os
import re

import pytest

from nova_ops.joint_map import (
    expected_name,
    id_to_name,
    load_joint_id_map,
)
from nova_ops.safety_envelope import load_default_limits


def _repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, "ros2_ws")):
        parent = os.path.dirname(d)
        assert parent != d, "repo root not found"
        d = parent
    return d


# ---- loader ------------------------------------------------------------


def test_yaml_loads_and_is_complete():
    m = load_joint_id_map()
    assert len(m) == 12
    assert sorted(m.values()) == list(range(1, 13))


def test_names_follow_per_leg_sequential_convention():
    m = load_joint_id_map()
    by_id = id_to_name(m)
    for bus_id in range(1, 13):
        assert by_id[bus_id] == expected_name(bus_id), (
            f"id {bus_id}: yaml says {by_id[bus_id]!r}, convention says "
            f"{expected_name(bus_id)!r}"
        )


def test_loader_rejects_malformed(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("joint_id_map: {FL_haa: 1, FL_hfe: 1}\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_joint_id_map(str(p))
    p.write_text("wrong_key: {}\n")
    with pytest.raises(ValueError, match="joint_id_map"):
        load_joint_id_map(str(p))


# ---- consumers ---------------------------------------------------------


def test_homing_config_names_match_yaml():
    from nova_calibration.servo_homing.config import JOINT_CONFIGS

    m = load_joint_id_map()
    by_id = id_to_name(m)
    for jid, cfg in JOINT_CONFIGS.items():
        assert cfg.name == by_id[jid], (
            f"servo_homing config id {jid} named {cfg.name!r} but the "
            f"canonical map says {by_id[jid]!r}"
        )


def test_limits_type_grouping_matches_yaml():
    """Each bus ID's limit values must be the ones for the joint TYPE the
    yaml assigns it (the 2026-06-27 type-grouping bug, locked forever)."""
    m = load_joint_id_map()
    lims = load_default_limits()
    expected_upper = {
        "haa": math.radians(15.0),  # conservative cap (firmware-limits lane)
        # 2026-07-25: MECHANICAL +86, not the old +50 riser-skirt cap. +50 is the
        # bound at ONE posture (full outboard splay + full knee fold); a per-joint
        # scalar cannot express a limit that depends on the other two joints, so
        # the chassis constraint moved to nova_ops.safety_envelope.rom_envelope
        # and this limit is now purely the linkage's own travel.
        "hfe": math.radians(86.0),
        # SIGNED and NEGATIVE: the translated knee config commands -95..-71.
        # Was +109, which clamped every knee command to the +5 floor.
        "kfe": math.radians(-5.0),
    }
    for name, jid in m.items():
        jtype = name.split("_")[1]
        assert math.isclose(lims.get(jid).upper, expected_upper[jtype]), (
            f"{name} (id {jid}) has upper "
            f"{math.degrees(lims.get(jid).upper):.1f} deg, expected the "
            f"{jtype} limit {math.degrees(expected_upper[jtype]):.1f}"
        )


def test_urdf_instantiates_every_leg_in_yaml():
    urdf = os.path.join(
        _repo_root(), "ros2_ws", "src", "nova_description", "urdf", "nova.urdf.xacro"
    )
    macro = os.path.join(os.path.dirname(urdf), "leg.macro.xacro")
    with open(urdf) as f:
        urdf_text = f.read()
    with open(macro) as f:
        macro_text = f.read()
    legs_in_urdf = set(re.findall(r'xacro:nova_leg\s+leg="(\w+)"', urdf_text))
    m = load_joint_id_map()
    legs_in_yaml = {name.split("_")[0] for name in m}
    assert legs_in_urdf == legs_in_yaml
    # macro must emit exactly the yaml's joint suffixes as ${leg}_<suffix>
    suffixes_in_yaml = {name.split("_")[1] for name in m}
    for s in suffixes_in_yaml:
        assert f'name="${{leg}}_{s}"' in macro_text, (
            f"leg macro missing joint suffix {s!r}"
        )
