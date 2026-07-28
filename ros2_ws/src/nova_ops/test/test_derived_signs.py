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
import sys

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


def _load_cad_module(rel_dir: str, name: str):
    """Load a CAD helper BY PATH, never by `sys.path` + module name.

    There are two `check_fit.py` in the tree -- `hardware/cad/chassis/` and
    `hardware/cad/leg_v6/`. Importing by bare name means whichever test ran
    first and inserted its directory wins, so the second silently gets the
    wrong module. That surfaced as a SKIP ("cannot import name
    HAA_INBOARD_MAX_DEG") which looked like an optional dependency and was
    really a drift guard that never ran. Explicit paths + distinct module
    names make it order-independent.
    """
    import importlib.util

    path = REPO / rel_dir / "check_fit.py"
    if not path.exists():
        pytest.skip(f"{path} not present")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    # The module still needs its OWN directory importable for sibling imports
    # (chassis/check_fit.py pulls in power_board_model). Binding it under a
    # unique name is what prevents the collision; the path entry is separate
    # and still required.
    added = str(path.parent)
    if added not in sys.path:
        sys.path.insert(0, added)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# the derivation's internal structure
# --------------------------------------------------------------------------


def test_left_and_right_are_opposite_WITHIN_AN_END():
    """Left/right oppose each other, but only end by end.

    This compared every LEFT leg against every RIGHT leg, which held under the
    translation premise and does not under the 180 deg rear yaw (#163): FL and
    RR are both +1. The mirror is still a mirror -- it just cannot be applied
    across the yaw.
    """
    for front, rear in ((("FL", "FR"), ("RL", "RR")),):
        for pair in (front, rear):
            a, c = pair
            assert (
                DERIVED_HAA_INBOARD_SIGN[HAA_IDS[a]]
                == -DERIVED_HAA_INBOARD_SIGN[HAA_IDS[c]]
            ), pair


def test_haa_inboard_sign_pairs_DIAGONALLY():
    """The rear hip is a 180 deg YAW (#163), not a translation.

    This test used to assert front == rear on the same side, which is what the
    translation premise implied. It passed, and it was wrong. A rear leg's horn
    faces REARWARD, so its foot swings the opposite way from the front leg
    beside it: FL pairs with RR, FR with RL. That diagonal is the same pairing
    #163 measured from the meshes by asking which corner takes which chirality
    -- two independent routes to the same answer.
    """
    assert (
        DERIVED_HAA_INBOARD_SIGN[HAA_IDS["FL"]]
        == DERIVED_HAA_INBOARD_SIGN[HAA_IDS["RR"]]
    )
    assert (
        DERIVED_HAA_INBOARD_SIGN[HAA_IDS["FR"]]
        == DERIVED_HAA_INBOARD_SIGN[HAA_IDS["RL"]]
    )
    # and NOT front==rear on a side, which is the premise that was wrong
    assert (
        DERIVED_HAA_INBOARD_SIGN[HAA_IDS["FL"]]
        != DERIVED_HAA_INBOARD_SIGN[HAA_IDS["RL"]]
    )


def test_haa_urdf_sign_splits_FRONT_from_REAR():
    """The yaw reverses the haa shaft, so raw-vs-URDF flips end to end.

    Was `== {-1}` for all four, which followed from the translation premise and
    is wrong. The URDF axis stays +x on all four; the SHAFT does not.
    """
    assert DERIVED_HAA_URDF_SIGN[HAA_IDS["FL"]] == -1
    assert DERIVED_HAA_URDF_SIGN[HAA_IDS["FR"]] == -1
    assert DERIVED_HAA_URDF_SIGN[HAA_IDS["RL"]] == +1
    assert DERIVED_HAA_URDF_SIGN[HAA_IDS["RR"]] == +1


def test_home_tick_matches_the_measured_homing_convention():
    assert HOME_TICK == 2048
    assert math.isclose(4096 / (2 * math.pi), 651.9, abs_tol=0.1)


# --------------------------------------------------------------------------
# steps 4-6, CONFIRMED against the model
# --------------------------------------------------------------------------


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_haa_ranges_are_exact_left_right_mirrors():
    mujoco = pytest.importorskip("mujoco")

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
def test_pitch_AXES_identical_across_all_four_legs():
    """No fore-aft mirroring of the pitch axes.

    This asserted that the hfe/kfe RANGES were identical across all four legs,
    to corroborate "4 identical translated legs" -- the premise #163 disproved
    (the rear hip is a 180 deg YAW). The ranges stopped being identical for a
    legitimate reason (#144): toward-the-trunk is +hfe at the front and -hfe at
    the rear, so the conservative chassis cap sits on opposite signs, and hfe is
    now a front/rear mirror by design.

    The AXIS is the invariant that actually carries the claim, and it survives
    untouched: all twelve pitch joints are "0 1 0". kfe, which has no chassis
    cap, is still range-identical too.
    """
    mujoco = pytest.importorskip("mujoco")

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    for joint in ("hfe", "kfe"):
        axes = set()
        for leg in LEFT + RIGHT:
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
            axes.add(tuple(round(v, 6) for v in m.jnt_axis[j]))
        assert axes == {(0.0, 1.0, 0.0)}, f"{joint} axes differ across legs: {axes}"

    def rng(leg, joint):
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
        return tuple(round(v, 6) for v in m.jnt_range[j])

    # kfe: no chassis cap, so still identical everywhere
    assert len({rng(leg, "kfe") for leg in LEFT + RIGHT}) == 1

    # hfe: front/rear MIRROR, not identical -- and not per-side either
    assert rng("FL", "hfe") == rng("FR", "hfe")
    assert rng("RL", "hfe") == rng("RR", "hfe")
    assert rng("FL", "hfe") == tuple(-v for v in reversed(rng("RL", "hfe")))


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_positive_haa_moves_every_foot_toward_plus_y():
    """Step 5, measured rather than predicted."""
    mujoco = pytest.importorskip("mujoco")

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
    mujoco = pytest.importorskip("mujoco")

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

        # +tick is a negative rotation about the SHAFT. The shaft is +x at the
        # front and -x at the rear (180 deg yaw, #163), so the sense of +tick
        # relative to +haa flips end to end. Reading the end from the model
        # rather than assuming it is what this test previously got wrong.
        hip = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_hip")
        shaft_x = 1.0 if m.body_pos[hip][0] > 0 else -1.0
        tick_dy = -shaft_x * dy
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
def test_pitch_AXIS_not_range_is_what_supports_the_shared_front_rear_sign():
    """The pitch sign is shared front/rear because the AXIS is, not the range.

    This asserted range-identity across all four legs -- a duplicate of the
    check above, and a non-sequitur besides: a LIMIT says nothing about the
    raw-vs-URDF DIRECTION. It happened to hold while the model carried one
    symmetric hfe range, and broke the moment the range became correctly
    end-keyed (#144), which is the tell that it was corroborating the modelling
    assumption rather than the sign.

    What the sign actually rests on: the pitch axis is "0 1 0" in the BODY frame
    on all four legs, so a given URDF angle is the same world rotation at both
    ends -- which is why DERIVED_PITCH_URDF_SIGN splits by SIDE (the mirror
    flips a lateral axis) and not by end.
    """
    mujoco = pytest.importorskip("mujoco")

    m = mujoco.MjModel.from_xml_path(str(MJCF))
    left_pitch = {HFE_IDS[leg] for leg in LEFT} | {KFE_IDS[leg] for leg in LEFT}
    for jid, sign in DERIVED_PITCH_URDF_SIGN.items():
        assert sign == (+1 if jid in left_pitch else -1), jid

    for joint in ("hfe", "kfe"):
        for leg in LEFT + RIGHT:
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_{joint}")
            assert tuple(round(v, 6) for v in m.jnt_axis[j]) == (0.0, 1.0, 0.0), (
                f"{leg}_{joint} axis is not body +y; the pitch sign derivation "
                "assumes a lateral axis identical at both ends"
            )


def test_cad_places_every_pitch_horn_inboard():
    """Reproduce the horn direction from the authoritative placement code.

    This is the CAD-side evidence the pitch signs rest on, so it is a test and
    not a comment: if `coax_to_trunk_bases()` ever changes handedness or the
    coax frame is redefined, the derived table must be revisited.
    """
    np = pytest.importorskip("numpy")
    try:
        cf = _load_cad_module("hardware/cad/chassis", "_nova_chassis_check_fit")
    except ImportError as exc:  # pragma: no cover - trimesh optional locally
        pytest.skip(f"chassis check_fit unavailable: {exc}")
    coax_to_trunk_bases = cf.coax_to_trunk_bases

    dets = {}
    for name, B in coax_to_trunk_bases():
        R = B[:3, :3]
        hip_y = B[1, 3]
        shaft = R @ np.array([-1.0, 0.0, 0.0])  # coax -X = the hfe/kfe horn
        # inboard == the shaft points back toward the centerline
        assert shaft[1] * np.sign(hip_y) < 0, f"{name}: pitch horn is not inboard"
        dets[name] = round(float(np.linalg.det(R)), 3)

    # Handedness is DIAGONAL, not per-side (#163): the rear hip is a 180 deg
    # YAW, so the +y corner takes the unmirrored part at the FRONT and the
    # mirrored one at the REAR. det here encodes WHICH CHIRALITY sits at each
    # corner -- a reflection applied to the right-leg cloud IS the left part.
    # This assertion used to read FR==RR==+1 / FL==RL==-1, which encoded the
    # translation premise and failed the moment the placement was corrected.
    assert dets["FR"] == dets["RL"] == 1.0
    assert dets["FL"] == dets["RR"] == -1.0


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
    mujoco = pytest.importorskip("mujoco")
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
    mujoco = pytest.importorskip("mujoco")
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


def test_runtime_haa_sign_carries_provenance(monkeypatch):
    """Guard the derive-then-confirm boundary — by PROVENANCE, not emptiness.

    This asserted every runtime sign was still None (#161). That guard had to
    be DELETED to ship confirmed signs, and a test you must remove to make
    progress is one people remove without much thought — on the constant whose
    failure mode is a leg swinging under the LiPo at 40 deg. The moment it was
    legitimately in the way was the moment it stopped protecting anything.

    So: a sign may be populated, but only WITH a recorded observation. None is
    still fine (uncalibrated). What is forbidden is the derived table typed
    straight in, which is the thing the old test was really trying to prevent
    and the one state it could not distinguish once deletion was on the table.
    """
    assert set(limits.HAA_INBOARD_SIGN) == set(HAA_IDS.values())
    limits.check_haa_sign_provenance()  # raises if any sign lacks a record


def test_provenance_check_catches_a_sign_typed_STRAIGHT_IN(monkeypatch):
    """The negative control: the exact move the old guard existed to stop."""
    monkeypatch.setitem(limits.HAA_INBOARD_SIGN, HAA_IDS["FL"], +1)
    with pytest.raises(limits.UnconfirmedSign, match="no recorded confirmation"):
        limits.check_haa_sign_provenance()


def test_recording_a_confirmation_populates_the_sign(monkeypatch):
    monkeypatch.setattr(limits, "HAA_INBOARD_SIGN", dict(limits.HAA_INBOARD_SIGN))
    monkeypatch.setattr(
        limits, "HAA_SIGN_CONFIRMATION", dict(limits.HAA_SIGN_CONFIRMATION)
    )
    jid = HAA_IDS["RR"]
    limits.record_haa_confirmation(
        jid,
        sign=DERIVED_HAA_INBOARD_SIGN[jid],
        observed_utc="2026-07-27T18:00:00Z",
        method="homing: +200 counts, watched the foot cross toward the belly",
        assembly="leg_v6 rev2 / RR / servo 10",
    )
    assert limits.HAA_INBOARD_SIGN[jid] == DERIVED_HAA_INBOARD_SIGN[jid]
    limits.check_haa_sign_provenance()  # sign + record agree


def test_confirmation_survives_neither_a_blank_field_nor_a_bad_sign(monkeypatch):
    """A record with an empty method or assembly is not provenance.

    'When, how, against which assembly' is what makes the value survivable
    across a servo swap or a re-seat -- a bare timestamp does not.
    """
    monkeypatch.setattr(limits, "HAA_INBOARD_SIGN", dict(limits.HAA_INBOARD_SIGN))
    monkeypatch.setattr(
        limits, "HAA_SIGN_CONFIRMATION", dict(limits.HAA_SIGN_CONFIRMATION)
    )
    ok = dict(
        sign=+1,
        observed_utc="2026-07-27T18:00:00Z",
        method="homing sweep",
        assembly="leg_v6 rev2 / FL",
    )
    for field in ("observed_utc", "method", "assembly"):
        with pytest.raises(ValueError, match=field):
            limits.record_haa_confirmation(HAA_IDS["FL"], **{**ok, field: "  "})
    with pytest.raises(ValueError, match="sign"):
        limits.record_haa_confirmation(HAA_IDS["FL"], **{**ok, "sign": 0})
    with pytest.raises(ValueError, match="not a haa"):
        limits.record_haa_confirmation(2, **ok)
    # nothing partial got written on the way out
    assert limits.HAA_INBOARD_SIGN[HAA_IDS["FL"]] is None
    assert limits.HAA_SIGN_CONFIRMATION[HAA_IDS["FL"]] is None


def test_clearing_a_confirmation_takes_the_sign_WITH_it(monkeypatch):
    """A servo swap or re-seat invalidates the observation. Clearing must drop
    the sign too, or the hip keeps the wide ROM on a record that no longer
    describes the hardware in front of you."""
    monkeypatch.setattr(limits, "HAA_INBOARD_SIGN", dict(limits.HAA_INBOARD_SIGN))
    monkeypatch.setattr(
        limits, "HAA_SIGN_CONFIRMATION", dict(limits.HAA_SIGN_CONFIRMATION)
    )
    jid = HAA_IDS["FR"]
    limits.record_haa_confirmation(
        jid,
        sign=-1,
        observed_utc="2026-07-27T18:00:00Z",
        method="homing sweep",
        assembly="leg_v6 rev2 / FR",
    )
    limits.clear_haa_confirmation(jid)
    assert limits.HAA_INBOARD_SIGN[jid] is None
    assert limits.HAA_SIGN_CONFIRMATION[jid] is None
    limits.check_haa_sign_provenance()


def test_an_UNCONFIRMED_sign_does_not_unlock_the_wide_ROM(monkeypatch):
    """Provenance has to be load-bearing, not decorative.

    If only the test enforced it, the check would be one CI edit away from
    meaning nothing. So the CONFIRMATION unlocks the asymmetric window, not the
    number: a sign typed straight in leaves the hip on the conservative
    symmetric ±15 — the fail-safe answer to "we do not know which way this hip
    swings", and 40 deg of it would be toward the LiPo.
    """
    jid = HAA_IDS["FL"]
    monkeypatch.setitem(limits.HAA_INBOARD_SIGN, jid, +1)  # no record
    lim = limits._hip_abduction(jid)
    assert lim.lower == pytest.approx(-math.radians(15.0))
    assert lim.upper == pytest.approx(+math.radians(15.0))
    assert limits.confirmed_haa_sign(jid) is None


def test_a_CONFIRMED_sign_does_unlock_it(monkeypatch):
    monkeypatch.setattr(limits, "HAA_INBOARD_SIGN", dict(limits.HAA_INBOARD_SIGN))
    monkeypatch.setattr(
        limits, "HAA_SIGN_CONFIRMATION", dict(limits.HAA_SIGN_CONFIRMATION)
    )
    jid = HAA_IDS["FL"]
    limits.record_haa_confirmation(
        jid,
        sign=+1,  # +counts = inboard, so outboard is the NEGATIVE side
        observed_utc="2026-07-27T18:00:00Z",
        method="homing sweep",
        assembly="leg_v6 rev2 / FL",
    )
    lim = limits._hip_abduction(jid)
    assert lim.lower == pytest.approx(-math.radians(40.0))
    assert lim.upper == pytest.approx(+math.radians(15.0))


def test_a_confirmation_disagreeing_with_its_own_sign_is_caught(monkeypatch):
    """The two must not drift. Recording writes both; poking one is the drift."""
    monkeypatch.setattr(limits, "HAA_INBOARD_SIGN", dict(limits.HAA_INBOARD_SIGN))
    monkeypatch.setattr(
        limits, "HAA_SIGN_CONFIRMATION", dict(limits.HAA_SIGN_CONFIRMATION)
    )
    jid = HAA_IDS["RL"]
    limits.record_haa_confirmation(
        jid,
        sign=-1,
        observed_utc="2026-07-27T18:00:00Z",
        method="homing sweep",
        assembly="leg_v6 rev2 / RL",
    )
    limits.HAA_INBOARD_SIGN[jid] = +1  # someone "fixed" the sign in place
    with pytest.raises(limits.UnconfirmedSign, match="disagrees"):
        limits.check_haa_sign_provenance()
