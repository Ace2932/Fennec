"""Tests for the derived haa servo-direction signs.

Two jobs:
  1. CONFIRM the kinematic half of the derivation (steps 4-6) by measuring the
     model, rather than re-asserting the algebra that produced it.
  2. NEGATIVE-CONTROL the confirmation check itself. A `confirm_haa_sign()` that
     cannot be made to raise is not protecting anything, and this constant is
     the one whose failure mode is a leg swinging into the LiPo pack at 40 deg.
"""

from __future__ import annotations

import math
import pathlib

import pytest

from nova_ops.safety_envelope import limits
from nova_ops.safety_envelope.derived_signs import (
    DERIVED_HAA_INBOARD_SIGN,
    DERIVED_HAA_URDF_SIGN,
    DERIVED_PITCH_URDF_SIGN,
    DERIVED_URDF_SIGN,
    HAA_IDS,
    HFE_IDS,
    HOME_TICK,
    KFE_IDS,
    SignMismatch,
    confirm_haa_sign,
    confirm_urdf_sign,
)

REPO = pathlib.Path(__file__).resolve().parents[4]
MJCF = REPO / "sim" / "nova_mjx" / "nova.xml"

LEFT = ("FL", "RL")
RIGHT = ("FR", "RR")


# --------------------------------------------------------------------------
# the derivation's internal structure
# --------------------------------------------------------------------------


def test_left_and_right_have_opposite_inboard_sign():
    for l_ in LEFT:
        for r_ in RIGHT:
            assert (
                DERIVED_HAA_INBOARD_SIGN[HAA_IDS[l_]]
                == -DERIVED_HAA_INBOARD_SIGN[HAA_IDS[r_]]
            )


def test_front_and_rear_share_a_sign():
    """Horns all-forward => rear is a TRANSLATION, not a mirror."""
    assert (
        DERIVED_HAA_INBOARD_SIGN[HAA_IDS["FL"]]
        == DERIVED_HAA_INBOARD_SIGN[HAA_IDS["RL"]]
    )
    assert (
        DERIVED_HAA_INBOARD_SIGN[HAA_IDS["FR"]]
        == DERIVED_HAA_INBOARD_SIGN[HAA_IDS["RR"]]
    )


def test_urdf_sign_is_uniform_across_hips():
    """Shaft is +x on all four, so raw-vs-URDF cannot differ between them."""
    assert set(DERIVED_HAA_URDF_SIGN.values()) == {-1}


def test_home_tick_matches_the_measured_homing_convention():
    assert HOME_TICK == 2048
    assert math.isclose(4096 / (2 * math.pi), 651.9, abs_tol=0.1)


# --------------------------------------------------------------------------
# steps 4-6, CONFIRMED against the model
# --------------------------------------------------------------------------


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_haa_ranges_are_exact_left_right_mirrors():
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    rng = {}
    for leg in LEFT + RIGHT:
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_haa")
        rng[leg] = tuple(m.jnt_range[j])
    for l_, r_ in (("FL", "FR"), ("RL", "RR")):
        assert rng[l_][0] == pytest.approx(-rng[r_][1], abs=1e-6)
        assert rng[l_][1] == pytest.approx(-rng[r_][0], abs=1e-6)
        # the generous direction is outboard: positive on the left
        assert abs(rng[l_][1]) > abs(rng[l_][0])


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_hfe_kfe_identical_across_all_four_legs():
    """No fore-aft mirroring -- corroborates '4 identical translated legs'."""
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    for joint in ("hfe", "kfe"):
        seen = set()
        for leg in LEFT + RIGHT:
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
            seen.add(tuple(round(v, 6) for v in m.jnt_range[j]))
        assert len(seen) == 1, f"{joint} ranges differ across legs: {seen}"


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_positive_haa_moves_every_foot_toward_plus_y():
    """Step 5, measured rather than predicted."""
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    d = mujoco.MjData(m)

    def foot_y(leg: str, ang: float) -> float:
        mujoco.mj_resetData(m, d)
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_haa")
        d.qpos[m.jnt_qposadr[j]] = ang
        mujoco.mj_forward(m, d)
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_foot")
        return float(d.xpos[b][1])

    for leg in LEFT + RIGHT:
        dy = foot_y(leg, 0.30) - foot_y(leg, 0.0)
        assert dy > 0.05, f"{leg}: +haa moved foot dy={dy:+.4f}, expected toward +y"


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_measured_outboard_direction_matches_the_derived_table():
    """Step 6 end-to-end: model geometry must reproduce the shipped signs."""
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    d = mujoco.MjData(m)

    for leg in LEFT + RIGHT:
        mujoco.mj_resetData(m, d)
        mujoco.mj_forward(m, d)
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_foot")
        y0 = float(d.xpos[b][1])

        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_haa")
        d.qpos[m.jnt_qposadr[j]] = 0.30
        mujoco.mj_forward(m, d)
        dy = float(d.xpos[b][1]) - y0

        # +tick is a NEGATIVE rotation about +x (steps 1-3), so it moves the
        # foot the other way from +haa.
        tick_dy = -dy
        side = 1 if y0 > 0 else -1
        inboard = (tick_dy * side) < 0
        expected = DERIVED_HAA_INBOARD_SIGN[HAA_IDS[leg]]
        assert (+1 if inboard else -1) == expected, leg


# --------------------------------------------------------------------------
# the confirmation check -- and its negative controls
# --------------------------------------------------------------------------


def test_confirm_accepts_a_matching_observation():
    for leg, jid in HAA_IDS.items():
        expect_inboard = DERIVED_HAA_INBOARD_SIGN[jid] > 0
        assert (
            confirm_haa_sign(jid, +40, expect_inboard) == DERIVED_HAA_INBOARD_SIGN[jid]
        )
        # a NEGATIVE command must flip the expected direction and still agree
        assert (
            confirm_haa_sign(jid, -40, not expect_inboard)
            == DERIVED_HAA_INBOARD_SIGN[jid]
        )


@pytest.mark.parametrize("leg", list(HAA_IDS))
def test_negative_control_flipped_observation_raises(leg):
    """Break what the check protects; confirm it screams."""
    jid = HAA_IDS[leg]
    wrong = DERIVED_HAA_INBOARD_SIGN[jid] < 0  # inverted on purpose
    with pytest.raises(SignMismatch):
        confirm_haa_sign(jid, +40, wrong)
    with pytest.raises(SignMismatch):
        confirm_haa_sign(jid, -40, not wrong)


def test_missing_observation_raises_rather_than_defaulting():
    with pytest.raises(SignMismatch):
        confirm_haa_sign(HAA_IDS["FL"], +40, None)
    with pytest.raises(SignMismatch):
        confirm_haa_sign(HAA_IDS["FL"], 0, True)


def test_non_haa_joint_rejected():
    with pytest.raises(ValueError):
        confirm_haa_sign(2, +40, True)  # FL_hfe


# --------------------------------------------------------------------------
# the contract: this is NOT wired into the runtime yet
# --------------------------------------------------------------------------


def test_pitch_joints_are_opposite_left_to_right():
    """The lateral shaft is exactly what an L/R mirror flips."""
    for l_, r_ in (("FL", "FR"), ("RL", "RR")):
        for ids in (HFE_IDS, KFE_IDS):
            assert DERIVED_PITCH_URDF_SIGN[ids[l_]] == -DERIVED_PITCH_URDF_SIGN[ids[r_]]


def test_pitch_joints_share_a_sign_front_to_rear():
    for ids in (HFE_IDS, KFE_IDS):
        assert DERIVED_PITCH_URDF_SIGN[ids["FL"]] == DERIVED_PITCH_URDF_SIGN[ids["RL"]]
        assert DERIVED_PITCH_URDF_SIGN[ids["FR"]] == DERIVED_PITCH_URDF_SIGN[ids["RR"]]


def test_hfe_and_kfe_agree_within_a_leg():
    """Both horns face inboard on the same lateral axis, so they cannot differ."""
    for leg in LEFT + RIGHT:
        assert (
            DERIVED_PITCH_URDF_SIGN[HFE_IDS[leg]]
            == DERIVED_PITCH_URDF_SIGN[KFE_IDS[leg]]
        )


def test_full_urdf_sign_table_covers_all_twelve_joints():
    assert sorted(DERIVED_URDF_SIGN) == list(range(1, 13))


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_pitch_ranges_identical_across_legs_supports_shared_front_rear_sign():
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    for joint in ("hfe", "kfe"):
        seen = {
            tuple(
                round(v, 6)
                for v in m.jnt_range[
                    mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
                ]
            )
            for leg in LEFT + RIGHT
        }
        assert len(seen) == 1


def test_cad_places_every_pitch_horn_inboard():
    """Reproduce the horn direction from the authoritative placement code.

    This is the CAD-side evidence the pitch signs rest on, so it is a test and
    not a comment: if `coax_to_trunk_bases()` ever changes handedness or the
    coax frame is redefined, the derived table must be revisited.
    """
    np = pytest.importorskip("numpy")
    chassis = REPO / "hardware" / "cad" / "chassis"
    if not (chassis / "check_fit.py").exists():
        pytest.skip("check_fit not present")
    import sys

    sys.path.insert(0, str(chassis))
    try:
        from check_fit import coax_to_trunk_bases
    except Exception as exc:  # pragma: no cover - trimesh optional locally
        pytest.skip(f"check_fit unavailable: {exc}")

    dets = {}
    for name, B in coax_to_trunk_bases():
        R = B[:3, :3]
        hip_y = B[1, 3]
        shaft = R @ np.array([-1.0, 0.0, 0.0])  # coax -X = the hfe/kfe horn
        # inboard == the shaft points back toward the centerline
        assert shaft[1] * np.sign(hip_y) < 0, f"{name}: pitch horn is not inboard"
        dets[name] = round(float(np.linalg.det(R)), 3)

    # left legs are mirror images of right legs -- opposite handedness
    assert dets["FR"] == dets["RR"] == 1.0
    assert dets["FL"] == dets["RL"] == -1.0


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_cad_and_convention_reproduce_the_shipped_pitch_table():
    """End-to-end: CAD horn facing + servo convention MUST give the table.

    Without this, a GLOBAL polarity flip of DERIVED_PITCH_URDF_SIGN passes every
    other test here -- they are all relative (left-vs-right, hfe-vs-kfe), and
    the CAD test asserts "inboard" without tying it back to a sign. This is the
    pitch-side counterpart of the measured haa check.

    Chain, with every input read rather than assumed:
      * CAD  -> the hfe/kfe shaft points INBOARD (frame-independent relation,
        so it bridges check_fit's trunk frame and the MJCF body frame safely --
        the two disagree on which side +y is).
      * MJCF -> which body side each leg is actually on.
      * measured convention -> +tick is a NEGATIVE rotation about the shaft.
      * URDF -> hfe/kfe axis is +y on all four legs.
    """
    import mujoco
    import numpy as np

    m = mujoco.MjModel.from_xml_path(str(MJCF))

    for leg in LEFT + RIGHT:
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_hip")
        side = float(np.sign(m.body_pos[b][1]))  # +1 => leg sits at +y
        assert side != 0

        # shaft points inboard, i.e. back toward the centerline
        shaft_dot_y = -side
        # +tick is a negative rotation about the shaft; the URDF axis is +y
        urdf_sign = int(-shaft_dot_y)

        for ids in (HFE_IDS, KFE_IDS):
            assert DERIVED_PITCH_URDF_SIGN[ids[leg]] == urdf_sign, (
                f"{leg}: CAD+convention give urdf_sign={urdf_sign:+d}, "
                f"table says {DERIVED_PITCH_URDF_SIGN[ids[leg]]:+d}"
            )


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_haa_axis_is_fore_aft_and_pitch_axis_is_lateral():
    """The whole left/right asymmetry rests on which axis the mirror flips."""
    import mujoco
    import numpy as np

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    for leg in LEFT + RIGHT:
        haa = m.jnt_axis[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_haa")]
        assert np.allclose(haa, [1, 0, 0]), f"{leg}_haa axis {haa}"
        for joint in ("hfe", "kfe"):
            ax = m.jnt_axis[
                mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
            ]
            assert np.allclose(ax, [0, 1, 0]), f"{leg}_{joint} axis {ax}"


# --------------------------------------------------------------------------
# the generic urdf_sign confirmation
# --------------------------------------------------------------------------


def test_confirm_urdf_sign_accepts_matching_observations():
    for jid, sign in DERIVED_URDF_SIGN.items():
        assert confirm_urdf_sign(jid, +100, sign * 0.15) == sign
        assert confirm_urdf_sign(jid, -100, sign * -0.15) == sign


@pytest.mark.parametrize("jid", sorted(DERIVED_URDF_SIGN))
def test_negative_control_inverted_joint_raises(jid):
    """An inverted joint drives away from target at full authority. Catch it."""
    sign = DERIVED_URDF_SIGN[jid]
    with pytest.raises(SignMismatch):
        confirm_urdf_sign(jid, +100, -sign * 0.15)


def test_confirm_urdf_sign_rejects_unusable_input():
    with pytest.raises(SignMismatch):
        confirm_urdf_sign(1, 0, 0.1)
    with pytest.raises(SignMismatch):
        confirm_urdf_sign(1, +100, 0.0)
    with pytest.raises(ValueError):
        confirm_urdf_sign(99, +100, 0.1)


def test_runtime_haa_sign_is_still_unset():
    """Guard the derive-then-confirm boundary.

    If someone wires DERIVED_* into limits without an on-robot confirmation,
    this fails. Deleting this test is the decision to trust an unconfirmed sign
    with 40 deg of travel toward the battery -- make it deliberately.
    """
    assert set(limits.HAA_INBOARD_SIGN) == set(HAA_IDS.values())
    assert all(v is None for v in limits.HAA_INBOARD_SIGN.values()), (
        "haa signs are now populated at runtime -- confirm each hip with "
        "confirm_haa_sign() at homing before relying on them"
    )
