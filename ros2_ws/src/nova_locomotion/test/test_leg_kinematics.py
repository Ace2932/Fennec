"""Pure-math tests for the 3-DOF leg kinematics (no ROS, no hardware).

The core guarantee: FK(IK(p)) == p for reachable foot targets, across the joint
ranges. This catches any sign/convention error in the closed-form IK regardless
of the (placeholder) link lengths.
"""

import math
import pytest

from nova_ops.rom_envelope import hfe_bounds
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


def test_hfe_window_is_posture_aware_and_end_specific():
    """The chassis hfe bound is a FUNCTION of (haa, kfe), not a scalar.

    MEASURED by hardware/cad/chassis/hfe_envelope.py against the real meshes
    (riser / pocket / pack / rails / head) with check_fit's rear hip placement
    corrected from a reflection to a rotation. Two properties matter and both are
    asserted off the live table rather than hardcoded angles:

      1. POSTURE-AWARE — a FRONT leg may fold further toward the trunk when the
         hip is NOT splayed. Full outboard splay is where the old scalar +50
         came from; at haa 0 the real bound is ~+70.
      2. END-SPECIFIC — front and rear are constrained in OPPOSITE directions,
         because a positive canonical hfe swings the knee backward, which is
         toward the trunk at the front and away from it at the rear.
    """
    from nova_ops.rom_envelope import hfe_bounds

    # -105, not -109: kfe_range is 1.9 rad = 108.86 deg, so -109 fails the kfe
    # check first and would mask what this test is actually asserting.
    kfe = math.radians(-105.0)
    _lo_splay, hi_splay = hfe_bounds("FL", math.radians(40.0), kfe)
    _lo_neut, hi_neut = hfe_bounds("FL", 0.0, kfe)
    # splaying the hip TIGHTENS the front fold bound — the whole point
    assert hi_splay < hi_neut, (math.degrees(hi_splay), math.degrees(hi_neut))
    # and a pose legal at haa 0 can be illegal at full splay
    mid = 0.5 * (hi_splay + hi_neut)
    assert within_limits((0.0, mid, kfe), P, leg="FL")
    assert not within_limits((math.radians(40.0), mid, kfe), P, leg="FL")

    # ends are constrained in opposite directions
    front_lo, front_hi = hfe_bounds("FL", 0.0, kfe)
    rear_lo, rear_hi = hfe_bounds("RL", 0.0, kfe)
    assert front_hi < rear_hi   # front is the one capped going toward-trunk
    assert rear_lo > front_lo   # rear is the one capped going the other way

    # an unknown leg cannot know its end -> conservative INTERSECTION
    u_lo, u_hi = hfe_bounds(None, 0.0, kfe)
    assert u_hi <= front_hi and u_lo >= rear_lo


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
    rear_env_lo, _hi = hfe_bounds("RL", 0.0, math.radians(30.0))
    assert rear[1] == pytest.approx(max(rear_env_lo, p.hfe_min))
    right_clamped = solve_side("right", foot, p, knee_forward=True, leg="FR")
    assert right_clamped[1] == pytest.approx(p.hfe_min_front)
    assert right_clamped[0] == pytest.approx(-unclamped[0])

    # a target already inside the cap is untouched (no spurious clamping)
    theta_ok = (0.1, math.radians(-40.0), math.radians(20.0))
    foot_ok = forward_kinematics(theta_ok, p)
    out_ok = solve_side("left", foot_ok, p, knee_forward=True, leg="FL")
    assert out_ok == pytest.approx(solve_side("left", foot_ok, p, knee_forward=True))


def test_leg_ik_stays_pure_math_no_ros_package_pull_in():
    """leg_ik's docstring promises "pure math, no ROS/hardware". Keep it true.

    It needs the chassis envelope, which lives in nova_ops (it cannot live here:
    nova_locomotion.node already imports nova_ops, so the reverse would be a
    package cycle). The envelope itself is pure data + math — but if it is
    imported from under nova_ops.safety_envelope, that package's __init__ drags
    in wrapper/counters/firmware_limits, i.e. a kinematics module transitively
    depending on the ROS-facing safety publisher. It briefly did. This asserts
    it does not.
    """
    import subprocess
    import sys

    src = (
        "import sys, nova_locomotion.kinematics.leg_ik;"
        "print(repr([m for m in sys.modules "
        "if 'safety_envelope' in m or m == 'rclpy']))"
    )
    out = subprocess.run(
        [sys.executable, "-c", src], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "[]", f"leg_ik dragged in {out}"
