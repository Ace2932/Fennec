"""Guard against the dual-source-geometry flaw: nova_locomotion's LegParams must
match the link lengths in the nova_description URDF. Both currently hold their
own (TODO-CAD placeholder) copies; this test fails loudly if a CAD refinement
updates one and not the other.

Mapping (URDF xacro property -> LegParams field):
  hip_to_upper_y  -> hip_offset
  |upper_to_lower_z| -> femur
  |lower_to_foot_z|  -> tibia
"""

import os
import re
import pytest

from nova_locomotion.kinematics.leg_ik import LegParams

# nova_description URDF, relative to this test file
_URDF = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "nova_description",
        "urdf",
        "nova.urdf.xacro",
    )
)


def _prop(text, name):
    m = re.search(rf'name="{re.escape(name)}"\s+value="(-?[0-9.]+)"', text)
    if not m:
        raise AssertionError(f"property {name} not found in URDF")
    return float(m.group(1))


@pytest.mark.skipif(
    not os.path.exists(_URDF),
    reason="nova_description URDF not present in this checkout",
)
def test_leg_lengths_match_urdf():
    text = open(_URDF).read()
    p = LegParams()
    assert _prop(text, "hip_to_upper_y") == pytest.approx(p.hip_offset), (
        "hip_offset diverged from URDF hip_to_upper_y"
    )
    assert abs(_prop(text, "upper_to_lower_z")) == pytest.approx(p.femur), (
        "femur diverged from URDF upper_to_lower_z"
    )
    assert abs(_prop(text, "lower_to_foot_z")) == pytest.approx(p.tibia), (
        "tibia diverged from URDF lower_to_foot_z"
    )
