"""Guard against the dual-source-geometry flaw: nova_locomotion's LegParams must
match the link lengths in the nova_description URDF. Both currently hold their
own (TODO-CAD placeholder) copies; this test fails loudly if a CAD refinement
updates one and not the other.

Mapping (URDF xacro property -> LegParams field):
  hip_to_upper_y + upper_to_lower_y + lower_to_foot_y -> hip_offset
    (the URDF distributes the lateral offset per joint — haa->hfe, the
     hfe->kfe shift, and the tibia S-curve; the planar IK folds all three
     into one d. Measured 2026-07-02 from the A360 assembly.)
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
    lateral = (
        _prop(text, "hip_to_upper_y")
        + _prop(text, "upper_to_lower_y")
        + _prop(text, "lower_to_foot_y")
    )
    assert lateral == pytest.approx(p.hip_offset), (
        "hip_offset diverged from URDF lateral offset sum "
        "(hip_to_upper_y + upper_to_lower_y + lower_to_foot_y)"
    )
    assert abs(_prop(text, "upper_to_lower_z")) == pytest.approx(p.femur), (
        "femur diverged from URDF upper_to_lower_z"
    )
    assert abs(_prop(text, "lower_to_foot_z")) == pytest.approx(p.tibia), (
        "tibia diverged from URDF lower_to_foot_z"
    )


# ---- #165: the pitch-axis station, across CAD -> URDF -> MJCF ---------------
#
# This is the seam the bug lived in for as long as it did. Every file was
# internally consistent; the URDF simply carried the STOCK hfe station (141.2)
# while leg_v6 had moved the built one to 129.6, and nothing compared them. So
# compare them here, from the CAD constants that are the authority — not from a
# number retyped into the test.

_REPO = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_CHECK_FIT = os.path.join(_REPO, "hardware", "cad", "chassis", "check_fit.py")
_COAX = os.path.join(_REPO, "hardware", "cad", "leg_v6", "coax.scad")
_MJCF = os.path.join(_REPO, "sim", "nova_mjx", "nova.xml")

_CAD_SOURCES = (_CHECK_FIT, _COAX)


def _cad_pitch_station_mm():
    """haa station minus the hfe offset along the trunk axis, from the CAD."""
    hip_fa = float(
        re.search(
            r"HIP_FA,\s*HIP_LAT,\s*HIP_Z\s*=\s*([0-9.]+)", open(_CHECK_FIT).read()
        ).group(1)
    )
    hfe_y = float(re.search(r"HFE_Y\s*=\s*([0-9.]+)\s*;", open(_COAX).read()).group(1))
    # coax.scad's HFE_Y runs TOWARD THE TRUNK from the haa station, at both ends
    return hip_fa - hfe_y


@pytest.mark.skipif(
    not all(os.path.exists(p) for p in _CAD_SOURCES + (_URDF,)),
    reason="CAD sources or URDF not present in this checkout",
)
def test_urdf_pitch_axis_station_matches_the_CAD():
    """The URDF hip grid must land the HFE axes where leg_v6 actually puts them.

    Was ±141.2 (the stock hfe station) with hip_to_upper_x = 0 — legal for
    stock, where the identity holds because the haa axis is fore-aft parallel.
    leg_v6 broke the identity and the model kept the stock pair, so the modeled
    stance was 23.2 mm (8.9%) too long.
    """
    text = open(_URDF).read()
    station_m = _prop(text, "body_half_x") - _prop(text, "hip_to_upper_x")
    assert station_m * 1000.0 == pytest.approx(_cad_pitch_station_mm(), abs=0.05), (
        "URDF pitch-axis station disagrees with shoulder.scad/coax.scad "
        f"({station_m * 1000:.1f} vs {_cad_pitch_station_mm():.1f} mm)"
    )


@pytest.mark.skipif(
    not all(os.path.exists(p) for p in _CAD_SOURCES + (_MJCF,)),
    reason="CAD sources or generated MJCF not present in this checkout",
)
def test_mjcf_pitch_axis_station_matches_the_CAD_and_is_keyed_PER_END():
    """Same station in the sim model — and the offset must flip front-to-rear.

    Toward-the-trunk is -x at the front and +x at the rear. A per-SIDE sign
    (the `reflect` pattern used for every lateral term in this file) would look
    right on the left legs and put both rear hips on the far side of their own
    hip station, which is the shape of #163 all over again. Asserting the
    front/rear signs are opposite is the negative control for that.
    """
    xml = open(_MJCF).read()
    stations = {}
    for leg in ("FL", "FR", "RL", "RR"):
        hip_x = float(re.search(rf'name="{leg}_hip" pos="(-?[0-9.]+)', xml).group(1))
        upper_x = float(
            re.search(rf'name="{leg}_upper" pos="(-?[0-9.]+)', xml).group(1)
        )
        stations[leg] = (hip_x, upper_x)

    expected = _cad_pitch_station_mm()
    for leg, (hip_x, upper_x) in stations.items():
        pitch_mm = abs(hip_x + upper_x) * 1000.0
        assert pitch_mm == pytest.approx(expected, abs=0.05), (leg, pitch_mm)

    # per END: front offsets negative, rear positive — never per side
    assert stations["FL"][1] < 0 and stations["FR"][1] < 0, stations
    assert stations["RL"][1] > 0 and stations["RR"][1] > 0, stations
    # and the two ends carry the same magnitude
    assert abs(stations["FL"][1]) == pytest.approx(abs(stations["RL"][1]))


@pytest.mark.skipif(
    not (os.path.exists(_MJCF) and os.path.exists(_URDF)),
    reason="URDF or generated MJCF not present in this checkout",
)
def test_urdf_and_mjcf_agree_on_the_hip_grid():
    """build_mjcf.py hand-copies the URDF numbers, so pin the copy."""
    text = open(_URDF).read()
    xml = open(_MJCF).read()
    hip_x = float(re.search(r'name="FL_hip" pos="(-?[0-9.]+)', xml).group(1))
    upper_x = float(re.search(r'name="FL_upper" pos="(-?[0-9.]+)', xml).group(1))
    assert hip_x == pytest.approx(_prop(text, "body_half_x"), abs=1e-4)
    assert abs(upper_x) == pytest.approx(_prop(text, "hip_to_upper_x"), abs=1e-4)


# ---- #144: the sim's hfe cap is the sim's ONLY chassis protection -----------
#
# On the robot the chassis constraint is enforced PER POSTURE at runtime
# (nova_ops.rom_envelope + safety_envelope.wrapper), so the URDF can carry the
# mechanical +-86 and be right. The sim has neither of those, and every leg geom
# in nova.xml is class="viz" (contype 0) — a thigh passes through the trunk box
# without generating a contact. So the hfe JOINT LIMIT is the only thing keeping
# a learned gait out of the chassis, which makes it worth pinning here.


def _mjcf_hfe_ranges():
    xml = open(_MJCF).read()
    out = {}
    for leg in ("FL", "FR", "RL", "RR"):
        m = re.search(rf'name="{leg}_hfe"[^/]*range="(-?[0-9.]+) (-?[0-9.]+)"', xml)
        assert m, f"no hfe range for {leg}"
        out[leg] = (float(m.group(1)), float(m.group(2)))
    return out


@pytest.mark.skipif(not os.path.exists(_MJCF), reason="generated MJCF not present")
def test_mjcf_hfe_cap_is_END_KEYED_toward_the_trunk():
    """Toward-the-trunk is +hfe at the FRONT and -hfe at the REAR.

    The MJCF hfe axis is "0 1 0" on all four legs, so canonical +hfe is one
    world rotation: all four feet swing rearward, which is toward the trunk at
    the front and away at the rear. A single symmetric range therefore puts the
    conservative cap on the front's toward-trunk side and the rear's AWAY side —
    the stock symmetric assumption #163/#164 disproved for the runtime gate.
    """
    r = _mjcf_hfe_ranges()
    for leg in ("FL", "FR"):
        assert abs(r[leg][1]) < abs(r[leg][0]), (leg, r[leg])   # tight on +
    for leg in ("RL", "RR"):
        assert abs(r[leg][0]) < abs(r[leg][1]), (leg, r[leg])   # tight on -
    # the two ends are mirror images, not independent numbers
    assert r["FL"][1] == pytest.approx(-r["RL"][0])
    assert r["FL"][0] == pytest.approx(-r["RL"][1])
    assert r["FL"] == r["FR"] and r["RL"] == r["RR"]


@pytest.mark.skipif(not os.path.exists(_MJCF), reason="generated MJCF not present")
def test_sim_never_permits_a_fold_the_chassis_gate_would_REFUSE():
    """The cross-seam check, and the one that catches the real bug.

    A sim that allows a posture the robot's gate refuses trains a policy that
    cannot transfer — and this is the fold direction that reaches the riser
    skirt and the belly pack. Compared at the nominal gait posture (haa 0,
    kfe -109), where both primary gaits run.

    Measured before the fix: the rear legs were capped at -86.0 where the gate
    stops at -67.9, i.e. 18.1 deg of fold into chassis the robot would refuse.
    The front was the mirror error — 17.9 deg TIGHTER than the gate allows,
    costing stride for nothing.
    """
    import math

    from nova_ops.rom_envelope import hfe_bounds

    r = _mjcf_hfe_ranges()
    for leg, (lo, hi) in r.items():
        g_lo, g_hi = hfe_bounds(leg, 0.0, math.radians(-109))
        if leg[0] == "F":                      # toward trunk = +hfe
            assert hi <= g_hi + 1e-9, (
                f"{leg}: sim permits +{math.degrees(hi):.1f} deg toward the "
                f"trunk, gate stops at +{math.degrees(g_hi):.1f}"
            )
        else:                                  # toward trunk = -hfe
            assert lo >= g_lo - 1e-9, (
                f"{leg}: sim permits {math.degrees(lo):.1f} deg toward the "
                f"trunk, gate stops at {math.degrees(g_lo):.1f}"
            )


@pytest.mark.skipif(not os.path.exists(_MJCF), reason="generated MJCF not present")
def test_the_OLD_symmetric_range_would_fail_that_check():
    """Negative control. If a symmetric range passed, the test above proves
    nothing — and symmetric is exactly what the file carried."""
    import math

    from nova_ops.rom_envelope import hfe_bounds

    old_lo, old_hi = -1.5010, 0.8730          # what every leg used to get
    g_lo, _ = hfe_bounds("RL", 0.0, math.radians(-109))
    assert old_lo < g_lo, (
        "the old symmetric rear range should violate the gate bound; if it "
        "does not, this check has stopped discriminating"
    )
