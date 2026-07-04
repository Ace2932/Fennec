"""Pure-math tests for the 3-DOF leg kinematics (no ROS, no hardware).

The core guarantee: FK(IK(p)) == p for reachable foot targets, across the joint
ranges. This catches any sign/convention error in the closed-form IK regardless
of the (placeholder) link lengths.
"""

import math
import pytest

from nova_locomotion.kinematics.leg_ik import (
    LegParams,
    forward_kinematics,
    inverse_kinematics,
    within_limits,
    Unreachable,
)

P = LegParams()


def _close(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def test_neutral_pose_is_straight_down():
    foot = forward_kinematics((0.0, 0.0, 0.0), P)
    assert _close(foot, (0.0, P.hip_offset, -(P.femur + P.tibia)))


def test_fk_ik_roundtrip_grid():
    """FK(IK(FK(theta))) == FK(theta) over a grid within joint limits."""
    n = 0
    for t1 in [-0.5, -0.2, 0.0, 0.3, 0.6]:
        for t2 in [-1.2, -0.5, 0.0, 0.5, 1.2]:
            for t3 in [0.2, 0.6, 1.0, 1.6, 2.1]:  # knee bent forward (>0)
                theta = (t1, t2, t3)
                foot = forward_kinematics(theta, P)
                sol = inverse_kinematics(foot, P, knee_forward=True)
                foot2 = forward_kinematics(sol, P)
                assert _close(foot, foot2, 1e-6), (
                    f"{theta} -> {foot} -> {sol} -> {foot2}"
                )
                n += 1
    assert n > 100


def test_ik_recovers_angles_when_in_branch():
    """For knee>0 targets, IK should recover the exact joint angles."""
    for theta in [(0.0, 0.0, 0.5), (0.3, -0.4, 1.0), (-0.4, 0.6, 1.5)]:
        foot = forward_kinematics(theta, P)
        sol = inverse_kinematics(foot, P, knee_forward=True)
        assert _close(sol, theta, 1e-6), f"{theta} != {sol}"


def test_unreachable_too_far():
    # straight out past full extension
    with pytest.raises(Unreachable):
        inverse_kinematics((P.femur + P.tibia + 0.05, P.hip_offset, 0.0), P)


def test_unreachable_inside_hip_offset():
    with pytest.raises(Unreachable):
        inverse_kinematics((0.0, 0.0, 0.0), P)  # |yz| < d


def test_within_limits():
    assert within_limits((0.0, 0.0, 0.0), P)
    assert not within_limits((10.0, 0.0, 0.0), P)


def test_workspace_reach_matches_links():
    """Max straight-leg reach equals a1+a2 along -z (knee straight)."""
    foot = forward_kinematics((0.0, 0.0, 0.0), P)
    reach = math.hypot(foot[0], foot[2])  # sagittal distance from hip in x-z
    assert abs(reach - (P.femur + P.tibia)) < 1e-9


def test_solve_side_mirrors_haa_only():
    from nova_locomotion.kinematics.leg_ik import (
        LegParams, solve_side, forward_kinematics)
    p = LegParams()
    foot = (0.03, p.hip_offset + 0.01, -0.17)
    l = solve_side('left', foot, p)
    r = solve_side('right', foot, p)
    assert r[0] == -l[0] and r[1] == l[1] and r[2] == l[2]
    # canonical FK of the left solution reproduces the target
    assert forward_kinematics(l, p) == __import__('pytest').approx(foot)


def test_solve_side_rejects_unknown():
    import pytest
    from nova_locomotion.kinematics.leg_ik import LegParams, solve_side
    with pytest.raises(ValueError):
        solve_side('starboard', (0, 0.07, -0.17), LegParams())
