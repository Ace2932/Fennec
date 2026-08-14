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
    LEGS,
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


# ---- #142 backstop: payload row <-> bus ID <-> firmware array index -------
#
# The posture-aware hfe backstop crosses the yaml THREE times and reads it
# zero times:
#
#   joint_id_map.yaml          FL_haa=1 FL_hfe=2  FR=4/5  RL=7/8  RR=10/11
#   firmware_limits._ENV_LEGS  the same eight IDs, retyped, plus the row order
#   hfe_envelope.h             haa_index = 3*leg, hfe_index = 3*leg + 1
#
# main.cpp fills `ids[i] = SERVO_ID_BASE + i`, so array index i IS bus ID
# i - 1... i.e. bus id i+1. Row p of the payload therefore has to land on
# indices (yaml[LEGS[p]+"_haa"] - 1, yaml[LEGS[p]+"_hfe"] - 1) or the firmware
# clamps one leg's fold against a different leg's hip -- the interface-boundary
# failure this project keeps paying for, on the one path whose whole job is
# keeping a leg out of the belly pack.
#
# hfe_envelope.h's own comment says the two helpers are "named here and tested
# rather than inlined as a bare 3". They are not. test_hfe_envelope.cpp only
# ever addresses arrays THROUGH the helpers (`t[hfe_env_haa_index(0)] = 100;
# ... TEST_ASSERT(..., t[hfe_env_hfe_index(0)])`), so it is invariant to what
# they return: swap the two bodies and every assertion in that suite still
# passes while the firmware selects each leg's window with its hfe count and
# clamps its haa. Using a helper is not testing it.
_ENV_IDX_RE = re.compile(
    r"inline\s+size_t\s+hfe_env_(haa|hfe)_index\s*\(\s*size_t\s+leg\s*\)\s*\{\s*"
    r"return\s+(\d+)\s*\*\s*leg\s*(?:\+\s*(\d+)\s*)?;\s*\}"
)


def test_hfe_envelope_payload_rows_match_yaml():
    """Host half: _ENV_LEGS is a hand copy of eight yaml IDs."""
    from nova_ops.safety_envelope.firmware_limits import _ENV_LEGS

    m = load_joint_id_map()
    assert tuple(leg for leg, _, _ in _ENV_LEGS) == LEGS, (
        f"_ENV_LEGS emits rows in {tuple(l for l, _, _ in _ENV_LEGS)}, but the "
        f"firmware indexes row p as leg p of {LEGS}"
    )
    for leg, haa_id, hfe_id in _ENV_LEGS:
        assert (haa_id, hfe_id) == (m[f"{leg}_haa"], m[f"{leg}_hfe"]), (
            f"_ENV_LEGS says {leg} is haa={haa_id} hfe={hfe_id}, yaml says "
            f"haa={m[f'{leg}_haa']} hfe={m[f'{leg}_hfe']}"
        )


def test_firmware_hfe_envelope_indexing_matches_yaml():
    """Firmware half: the 3*leg arithmetic against the yaml's real IDs."""
    src = os.path.join(
        _repo_root(), "firmware", "teensy", "firmware", "src", "hfe_envelope.h"
    )
    with open(src) as f:
        text = f.read()

    found = {j: (int(mul), int(off or 0)) for j, mul, off in _ENV_IDX_RE.findall(text)}
    assert set(found) == {"haa", "hfe"}, (
        f"parsed {sorted(found)} from hfe_envelope.h, expected haa and hfe -- "
        "the helper signatures changed shape, so this gate is no longer "
        "reading them. Fix the regex; deleting it restores the blind spot."
    )

    n_legs = re.search(r"HFE_ENV_LEGS\s*=\s*(\d+)", text)
    assert n_legs and int(n_legs.group(1)) == len(LEGS), (
        f"hfe_envelope.h HFE_ENV_LEGS={n_legs and n_legs.group(1)}, yaml has "
        f"{len(LEGS)} legs -- load() would reject the host's table on size and "
        "the backstop would sit inactive, which fails OPEN"
    )

    m = load_joint_id_map()
    for pos, leg in enumerate(LEGS):
        for joint in ("haa", "hfe"):
            mul, off = found[joint]
            assert mul * pos + off == m[f"{leg}_{joint}"] - 1, (
                f"payload row {pos} is {leg}: hfe_env_{joint}_index({pos}) = "
                f"{mul * pos + off}, but {leg}_{joint} is bus id "
                f"{m[f'{leg}_{joint}']} = array index {m[f'{leg}_{joint}'] - 1}"
            )
