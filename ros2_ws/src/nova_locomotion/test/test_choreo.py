"""Choreo: min-jerk stand/sit sequences — smoothness, limits, X-config."""

import math

from nova_locomotion.choreo import (
    ChoreoParams,
    min_jerk,
    pose_for,
    sequence,
    sit_down,
    stand_up,
)
from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    forward_kinematics,
    within_limits,
)

P = ChoreoParams()
LEGS = ("FL", "FR", "RL", "RR")


def _canon(leg, theta):
    return (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta


# ---- min-jerk primitive -------------------------------------------------


def test_min_jerk_endpoints_and_monotonic():
    assert min_jerk(0.0) == 0.0 and min_jerk(1.0) == 1.0
    xs = [min_jerk(i / 100) for i in range(101)]
    assert all(b >= a - 1e-12 for a, b in zip(xs, xs[1:]))
    # zero end velocity: tiny steps at the ends barely move
    assert min_jerk(0.02) < 1e-4 and 1.0 - min_jerk(0.98) < 1e-4


# ---- keyframes ----------------------------------------------------------


def test_keyframes_within_rom_all_legs_x_config():
    for name in ("lie", "crouch", "stand"):
        pose = pose_for(name, P)
        for leg in LEGS:
            assert within_limits(
                _canon(leg, pose[leg]), P.leg, KNEE_FORWARD[leg], leg=leg
            ), (
                name,
                leg,
            )


def test_translated_config_all_knees_backward():
    """TRANSLATED layout (corrected 2026-07-25): every knee bends BACKWARD.

    Was test_x_config_rear_knees_mirrored, which asserted front/rear kfe of
    OPPOSITE sign. The robot as built is translated — all four knees back — and
    the MJX sim always matched it (sim/nova_mjx DEFAULT_POSE kfe -1.2 on all
    four). See leg_ik.KNEE_FORWARD.
    """
    stand = pose_for("stand", P)
    # every leg takes the SAME elbow branch -> same-sign kfe, equal magnitude
    assert all(stand[leg][2] < 0 for leg in ("FL", "FR", "RL", "RR")), stand
    assert math.isclose(stand["FL"][2], stand["RL"][2], abs_tol=1e-9)
    # hfe likewise no longer mirrors front-to-rear
    assert math.isclose(stand["FL"][1], stand["RL"][1], abs_tol=1e-9)


def test_keyframe_feet_under_hips():
    for name in ("lie", "crouch", "stand"):
        pose = pose_for(name, P)
        for leg in ("FL", "RL"):  # canonical legs, x = fore-aft
            x, y, z = forward_kinematics(pose[leg], P.leg)
            assert abs(x) < 1e-9, (name, leg, x)  # feet under hips rule


# ---- sequences ----------------------------------------------------------


def _max_step(seq):
    poses = list(seq)
    worst = 0.0
    for a, b in zip(poses, poses[1:]):
        for leg in LEGS:
            for j in range(3):
                worst = max(worst, abs(b[leg][j] - a[leg][j]))
    return poses, worst


def test_stand_up_smooth_and_bounded():
    poses, worst = _max_step(stand_up(P))
    # velocity bound: worst per-dt step under the tightest envelope
    # velocity limit (haa 180 deg/s = 3.14 rad/s * dt)
    assert worst < 3.14 * P.dt, worst
    # endpoints exact
    assert poses[-1] == pose_for("stand", P)
    # every sample within ROM
    for pose in poses[::5]:
        for leg in LEGS:
            assert within_limits(
                _canon(leg, pose[leg]), P.leg, KNEE_FORWARD[leg], leg=leg
            )


def test_sit_down_reaches_lie():
    poses, worst = _max_step(sit_down(P))
    assert poses[-1] == pose_for("lie", P)
    assert worst < 3.14 * P.dt


def test_stand_up_from_arbitrary_start():
    # e.g. post-E-stop pose, deeper than the lie keyframe on one leg
    start = pose_for("lie", P)
    start = {leg: (t[0], t[1], t[2] * 1.02) for leg, t in start.items()}
    poses = list(stand_up(P, start_pose=start))
    assert poses[0] == start
    assert poses[-1] == pose_for("stand", P)


def test_sequence_duration_mismatch_raises():
    import pytest

    with pytest.raises(ValueError):
        list(sequence([pose_for("lie", P)], [1.0], P))


# ---- #145 / #297: sit/down unblock on a recorded haa confirmation --------
#
# pose_for('sit')/pose_for('down') are joint-space (JOINT_POSES) and need a
# ~40 deg OUTBOARD haa splay — outside the conservative symmetric +-15 deg
# gate window until nova_ops.safety_envelope.limits.HAA_INBOARD_SIGN is
# filled. #297 makes that fillable (record_haa_confirmation); these tests
# verify the unblock actually reaches pose_for(), not just that the storage
# plumbing round-trips.


def _isolate_haa_confirmations(monkeypatch):
    """Module-global HAA_INBOARD_SIGN/HAA_SIGN_CONFIRMATION are shared
    process-wide state (nova_ops.safety_envelope.limits) — copy them so a
    confirmation recorded here cannot leak into another test file run in the
    same pytest session."""
    from nova_ops.safety_envelope import limits as limits_mod

    monkeypatch.setattr(
        limits_mod, "HAA_INBOARD_SIGN", dict(limits_mod.HAA_INBOARD_SIGN)
    )
    monkeypatch.setattr(
        limits_mod, "HAA_SIGN_CONFIRMATION", dict(limits_mod.HAA_SIGN_CONFIRMATION)
    )


def test_sit_and_down_RAISE_without_a_haa_confirmation():
    """NEGATIVE CONTROL — the guard must still be up pre-homing."""
    import pytest

    for name in ("sit", "down"):
        with pytest.raises(ValueError, match="gate window"):
            pose_for(name, P)


def test_sit_and_down_UNLOCK_with_a_recorded_haa_confirmation(monkeypatch):
    """The actual #145/#297 unblock: GIVEN a recorded confirmation for every
    leg's haa, pose_for('sit')/pose_for('down') stop raising and return
    poses whose haa sits at the asymmetric window's 40 deg outboard edge
    (never the 15 deg inboard side — SIT_JOINTS only ever splays outboard)."""
    from nova_ops.safety_envelope.derived_signs import HAA_IDS
    from nova_ops.safety_envelope.limits import record_haa_confirmation

    _isolate_haa_confirmations(monkeypatch)
    # sign chosen per leg so the ALREADY-COMPUTED physical splay target
    # (+40 deg on left legs, -40 deg mirrored on right legs) lands inside
    # the confirmed asymmetric window -- see limits._hip_abduction.
    for leg, sign in (("FL", -1), ("FR", +1), ("RL", -1), ("RR", +1)):
        record_haa_confirmation(
            HAA_IDS[leg],
            sign=sign,
            observed_utc="2026-08-08T00:00:00",
            method="test",
            assembly=leg,
        )

    # 'sit' only splays the REAR pair (front legs hold 'stand', haa=0 —
    # see joint_keyframes' docstring); 'down' splays all four.
    splayed_legs = {"sit": ("RL", "RR"), "down": LEGS}
    for name in ("sit", "down"):
        pose = pose_for(name, P)  # must not raise
        for leg in splayed_legs[name]:
            haa_deg = math.degrees(pose[leg][0])
            # inside [15, 40] magnitude -- the asymmetric outboard window,
            # not the pre-confirmation +-15 conservative cap
            assert 15.0 - 1e-6 <= abs(haa_deg) <= 40.0 + 1e-6, (name, leg, haa_deg)
            assert abs(abs(haa_deg) - 40.0) < 1e-6, (name, leg, haa_deg)


def test_sit_and_down_still_raise_if_only_SOME_legs_are_confirmed(monkeypatch):
    """NEGATIVE CONTROL — a partial confirmation must not unlock every leg;
    each bus ID's window comes from ITS OWN confirmation."""
    import pytest

    from nova_ops.safety_envelope.derived_signs import HAA_IDS
    from nova_ops.safety_envelope.limits import record_haa_confirmation

    _isolate_haa_confirmations(monkeypatch)
    record_haa_confirmation(
        HAA_IDS["FL"], sign=-1, observed_utc="t", method="m", assembly="FL"
    )
    # RL, FR, RR left unconfirmed
    with pytest.raises(ValueError, match="gate window"):
        pose_for("down", P)
