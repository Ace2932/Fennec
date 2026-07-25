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


def test_within_limits_front_rear_hfe_split():
    """LA-13 introduced within_limits' leg= selector (FRONT_LEGS use
    p.hfe_min_front, REAR_LEGS/unknown use p.hfe_min). #47 (2026-07-11,
    MEASURED — hardware/cad/chassis/head_cap_sweep.py): the front cap's
    -50deg value was stale (no head/L2/D456 contact found anywhere in the
    front leg's structurally-reachable hfe range), so hfe_min_front ==
    hfe_min today and there's no longer an angle that's legal for one and
    illegal for the other. Test the SELECTOR MECHANISM itself (front picks
    hfe_min_front, rear picks hfe_min) parametrically off the live values
    instead of a hardcoded angle, so this keeps working if a future head
    redesign reintroduces a real split."""
    eps = math.radians(0.01)
    just_inside_front = (0.0, P.hfe_min_front + eps, 0.0)
    just_outside_front = (0.0, P.hfe_min_front - eps, 0.0)
    for leg in ("FL", "FR"):
        assert within_limits(just_inside_front, P, leg=leg), leg
        assert not within_limits(just_outside_front, P, leg=leg), leg
    # REAR is the MIRROR window, not the same one (corrected 2026-07-25 from the
    # measured check_fit crouch sweep): a rear leg's toward-trunk fold is
    # NEGATIVE canonical hfe, so its window is [-hfe_max, -hfe_min].
    just_inside_rear = (0.0, -P.hfe_max + eps, 0.0)
    just_outside_rear = (0.0, -P.hfe_max - eps, 0.0)
    for leg in ("RL", "RR"):
        assert within_limits(just_inside_rear, P, leg=leg), leg
        assert not within_limits(just_outside_rear, P, leg=leg), leg
    # the two ends genuinely disagree now: the front's away-trunk reach is
    # ILLEGAL for a rear leg, and vice versa.
    assert within_limits(just_inside_front, P, leg="FL")
    assert not within_limits(just_inside_front, P, leg="RL")
    # an unrecognized/omitted leg cannot know which end it is, so it gets the
    # CONSERVATIVE INTERSECTION of the two windows, not a permissive default.
    assert within_limits((0.0, 0.0, 0.0), P)
    assert not within_limits(just_inside_front, P)
    assert not within_limits(just_inside_front, P, leg="unknown")


def test_workspace_reach_matches_links():
    """Max straight-leg reach equals a1+a2 along -z (knee straight)."""
    foot = forward_kinematics((0.0, 0.0, 0.0), P)
    reach = math.hypot(foot[0], foot[2])  # sagittal distance from hip in x-z
    assert abs(reach - (P.femur + P.tibia)) < 1e-9


def test_solve_side_mirrors_haa_only():
    from nova_locomotion.kinematics.leg_ik import (
        LegParams,
        solve_side,
        forward_kinematics,
    )

    p = LegParams()
    foot = (0.03, p.hip_offset + 0.01, -0.17)
    l = solve_side("left", foot, p)
    r = solve_side("right", foot, p)
    assert r[0] == -l[0] and r[1] == l[1] and r[2] == l[2]
    # canonical FK of the left solution reproduces the target
    assert forward_kinematics(l, p) == __import__("pytest").approx(foot)


def test_solve_side_rejects_unknown():
    import pytest
    from nova_locomotion.kinematics.leg_ik import LegParams, solve_side

    with pytest.raises(ValueError):
        solve_side("starboard", (0, 0.07, -0.17), LegParams())


def test_solve_side_clamps_front_hfe_to_cap():
    """#47 RUNTIME SAFETY CLAMP: solve_side(..., leg="FL"/"FR") must clamp
    the physical hfe to hfe_min_front regardless of how far the requested
    foot target would otherwise push it — the backstop for any gait
    source that hasn't been (or can't be) fully retuned. Construct a foot
    target whose unclamped IK solution sits well past the cap (-90°, vs
    the -86° cap) via FK(theta) so the target is guaranteed reachable."""
    from nova_locomotion.kinematics.leg_ik import solve_side

    p = LegParams()
    theta = (0.0, math.radians(-90.0), math.radians(30.0))
    foot = forward_kinematics(theta, p)

    unclamped = solve_side("left", foot, p, knee_forward=True)
    assert math.degrees(unclamped[1]) == pytest.approx(-90.0)

    clamped = solve_side("left", foot, p, knee_forward=True, leg="FL")
    assert clamped[1] == pytest.approx(p.hfe_min_front)
    # haa/kfe pass through untouched — only hfe is clamped
    assert clamped[0] == pytest.approx(unclamped[0])
    assert clamped[2] == pytest.approx(unclamped[2])

    # REAR legs ARE clamped now (added 2026-07-25) — to the MIRROR window.
    # They previously had no runtime backstop at all, on the belief that the
    # +50 riser-skirt cap was front-only; the corrected check_fit crouch sweep
    # cuts the riser at rear hfe -86/-45 while +45..+86 is clean.
    rear = solve_side("left", foot, p, knee_forward=True, leg="RL")
    assert rear[1] == pytest.approx(-p.hfe_max)
    right_clamped = solve_side("right", foot, p, knee_forward=True, leg="FR")
    assert right_clamped[1] == pytest.approx(p.hfe_min_front)
    assert right_clamped[0] == pytest.approx(-unclamped[0])

    # a target already inside the cap is untouched (no spurious clamping)
    theta_ok = (0.1, math.radians(-40.0), math.radians(20.0))
    foot_ok = forward_kinematics(theta_ok, p)
    out_ok = solve_side("left", foot_ok, p, knee_forward=True, leg="FL")
    assert out_ok == pytest.approx(solve_side("left", foot_ok, p, knee_forward=True))
