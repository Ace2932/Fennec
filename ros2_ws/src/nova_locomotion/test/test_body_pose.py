"""Body-pose IK: identity, sign conventions, ROM solvability, round-trips."""

import math

import pytest

from nova_locomotion.kinematics.body_pose import (
    LEGS,
    BodyPose,
    BodyPoseParams,
    foot_targets,
    foot_world,
    neutral_anchors,
)
from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    forward_kinematics,
    inverse_kinematics,
    solve_side,
    within_limits,
)

P = BodyPoseParams()
A = neutral_anchors(P)


def _canon(leg, theta):
    return (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta


# ---- identity -----------------------------------------------------------


def test_zero_pose_is_identity_stance():
    targets = foot_targets(BodyPose(), A, P)
    for leg in LEGS:
        # same canonical stance target trot.py / choreo use
        assert targets[leg] == pytest.approx((0.0, P.stand_y, -P.stand_height))


# ---- pure translations --------------------------------------------------


def test_pure_dz_moves_all_feet_symmetrically():
    # lowering the body onto the feet (dz < 0) brings every foot 20 mm
    # closer to its hip, identically; x/y untouched
    down = foot_targets(BodyPose(dz=-0.02), A, P)
    up = foot_targets(BodyPose(dz=+0.02), A, P)
    for leg in LEGS:
        assert down[leg] == pytest.approx((0.0, P.stand_y, -P.stand_height + 0.02))
        assert up[leg] == pytest.approx((0.0, P.stand_y, -P.stand_height - 0.02))


def test_pure_dx_shifts_feet_backward_in_hip_frame():
    # body forward => world-fixed feet move BACK relative to the hips
    targets = foot_targets(BodyPose(dx=0.03), A, P)
    for leg in LEGS:
        assert targets[leg][0] == pytest.approx(-0.03)
        assert targets[leg][1:] == pytest.approx((P.stand_y, -P.stand_height))


def test_pure_dy_is_mirrored_at_the_canonical_boundary():
    # body shifts LEFT: left feet get closer (less outboard), right feet
    # further outboard — canonical +y is outboard for every leg
    targets = foot_targets(BodyPose(dy=0.02), A, P)
    for leg in ("FL", "RL"):
        assert targets[leg][1] == pytest.approx(P.stand_y - 0.02)
    for leg in ("FR", "RR"):
        assert targets[leg][1] == pytest.approx(P.stand_y + 0.02)


# ---- pure rotations -----------------------------------------------------


def test_pure_roll_antisymmetric_left_right():
    # +roll raises the LEFT side => left targets deepen (leg must extend),
    # right targets rise. Antisymmetric about a second-order (cos-1)
    # common-mode; pin the exact geometry: lever = anchor |y|.
    r = 0.15
    targets = foot_targets(BodyPose(roll=r), A, P)
    n = -P.stand_height
    lever = P.half_y + P.stand_y
    common = (math.cos(r) - 1.0) * n
    dz_l = targets["FL"][2] - n
    dz_r = targets["FR"][2] - n
    assert dz_l < 0 < dz_r
    assert dz_l == pytest.approx(-math.sin(r) * lever + common)
    assert dz_r == pytest.approx(+math.sin(r) * lever + common)
    # fore-aft symmetric under pure roll
    assert targets["FL"] == pytest.approx(targets["RL"])
    assert targets["FR"] == pytest.approx(targets["RR"])


def test_pure_pitch_antisymmetric_front_rear():
    # +pitch lowers the nose => front targets rise, rear targets deepen
    # (same second-order common-mode as roll; lever = anchor |x|)
    q = 0.15
    targets = foot_targets(BodyPose(pitch=q), A, P)
    n = -P.stand_height
    common = (math.cos(q) - 1.0) * n
    dz_f = targets["FL"][2] - n
    dz_r = targets["RL"][2] - n
    assert dz_f > 0 > dz_r
    assert dz_f == pytest.approx(+math.sin(q) * P.half_x + common)
    assert dz_r == pytest.approx(-math.sin(q) * P.half_x + common)
    # left-right symmetric under pure pitch (canonical frames)
    assert targets["FL"] == pytest.approx(targets["FR"])
    assert targets["RL"] == pytest.approx(targets["RR"])


def test_pure_yaw_antisymmetric_diagonals():
    targets = foot_targets(BodyPose(yaw=0.15), A, P)
    # yaw swings feet fore-aft opposite ways on the two sides; z untouched
    assert targets["FL"][0] == pytest.approx(-targets["RR"][0])
    assert targets["FR"][0] == pytest.approx(-targets["RL"][0])
    assert targets["FL"][0] != pytest.approx(0.0)
    for leg in LEGS:
        assert targets[leg][2] == pytest.approx(-P.stand_height)


# ---- solvability at moderate poses (the stage-1.4 weight-shift box) ------

MODERATE = (
    [BodyPose(roll=math.radians(s * 10)) for s in (-1, 1)]
    + [BodyPose(pitch=math.radians(s * 10)) for s in (-1, 1)]
    + [BodyPose(yaw=math.radians(s * 10)) for s in (-1, 1)]
    + [BodyPose(dx=s * 0.03) for s in (-1, 1)]
    + [BodyPose(dy=s * 0.03) for s in (-1, 1)]
    + [BodyPose(dz=s * 0.03) for s in (-1, 1)]
    + [
        # mild combos (weight-shift box corners: xy shift + a little attitude)
        BodyPose(roll=math.radians(5), pitch=math.radians(5), dx=0.02, dy=0.015),
        BodyPose(roll=math.radians(-5), pitch=math.radians(5), dx=-0.02, dy=0.015),
        BodyPose(roll=math.radians(5), yaw=math.radians(5), dy=-0.015, dz=-0.02),
    ]
)


def test_moderate_poses_solvable_within_x_config_rom():
    # NOT passing leg= to within_limits below (LA-13, 2026-07-11): the
    # +-10deg pitch/roll weight-shift cases here push FL/FR hfe WELL past
    # the -50deg front head-clearance cap (up to ~-66deg, see
    # leg_ik.within_limits' docstring) — the raibert/body_pose weight-shift
    # authority was tuned against the old symmetric +-86 window. Fixing
    # this for real means bounding that authority (a control-tuning change,
    # not a constant swap), which needs its own pass. Flagged, not
    # silently fixed.
    for pose in MODERATE:
        targets = foot_targets(pose, A, P)
        for leg in LEGS:
            theta = solve_side(LEG_SIDE[leg], targets[leg], P.leg, KNEE_FORWARD[leg])
            assert within_limits(_canon(leg, theta), P.leg, KNEE_FORWARD[leg]), (
                pose,
                leg,
                theta,
            )


# ---- round-trips ---------------------------------------------------------


def test_fk_round_trip_canonical():
    pose = BodyPose(roll=0.1, pitch=-0.08, yaw=0.05, dx=0.02, dy=-0.01, dz=-0.015)
    targets = foot_targets(pose, A, P)
    for leg in LEGS:
        theta = inverse_kinematics(targets[leg], P.leg, KNEE_FORWARD[leg])
        assert forward_kinematics(theta, P.leg) == pytest.approx(targets[leg])


def test_world_round_trip_feet_stay_on_anchors():
    pose = BodyPose(roll=-0.12, pitch=0.07, yaw=-0.06, dx=-0.025, dy=0.02, dz=0.01)
    targets = foot_targets(pose, A, P)
    for leg in LEGS:
        assert foot_world(pose, leg, targets[leg], P) == pytest.approx(A[leg])
