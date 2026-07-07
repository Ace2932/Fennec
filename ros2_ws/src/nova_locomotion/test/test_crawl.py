"""Crawl gait: single-swing invariant, ROM, CoM shift smoothness + signs."""

import pytest

from nova_locomotion.gait.crawl import (
    LEGS,
    PHASE_OFFSET,
    CrawlParams,
    all_feet,
    body_shift,
    foot_target,
    in_swing,
)
from nova_locomotion.kinematics.body_pose import (
    BodyPose,
    BodyPoseParams,
    foot_targets,
    foot_world,
)
from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    solve_side,
    within_limits,
)

C = CrawlParams()
BP = BodyPoseParams()
N = 400  # dense phase samples


def _canon(leg, theta):
    return (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta


# ---- gait structure -------------------------------------------------------


def test_periodic():
    for leg in LEGS:
        assert foot_target(0.0, leg, C) == pytest.approx(foot_target(1.0, leg, C))


def test_at_most_one_leg_in_swing_and_four_stance_gaps_exist():
    # duty 0.8: 4 x 0.2 swing windows never overlap; the remaining 0.2 of
    # the cycle is four-stance (the CoM-shift gaps). Statically stable
    # needs >= 3 in stance — we guarantee >= 3 everywhere.
    saw_gap = False
    for i in range(N):
        swinging = [leg for leg in LEGS if in_swing(i / N, leg, C)]
        assert len(swinging) <= 1, (i / N, swinging)
        if not swinging:
            saw_gap = True
    assert saw_gap


def test_each_leg_swings_once_per_cycle():
    for leg in LEGS:
        frac = sum(in_swing(i / N, leg, C) for i in range(N)) / N
        assert frac == pytest.approx(1.0 - C.duty, abs=2.0 / N)


def test_lateral_sequence_order():
    # swing onsets in global phase: FL .80, RL .05, FR .30, RR .55 —
    # cyclically FL -> RL -> FR -> RR (front leg, then same-side hind)
    onset = {leg: (C.duty - PHASE_OFFSET[leg]) % 1.0 for leg in LEGS}
    order = sorted(LEGS, key=lambda leg: onset[leg])
    assert order == ["RL", "FR", "RR", "FL"]


def test_stance_feet_at_stand_height():
    for i in range(N):
        ph = i / N
        for leg in LEGS:
            if not in_swing(ph, leg, C):
                assert foot_target(ph, leg, C)[2] == pytest.approx(-C.stand_height)
            else:
                assert foot_target(ph, leg, C)[2] >= -C.stand_height - 1e-12


# ---- reachability (X-config) ----------------------------------------------


def test_targets_ik_reachable_within_x_config_limits():
    for i in range(100):
        ph = i / 100.0
        for leg, foot in all_feet(ph, C).items():
            theta = solve_side(LEG_SIDE[leg], foot, BP.leg, KNEE_FORWARD[leg])
            assert within_limits(_canon(leg, theta), BP.leg, KNEE_FORWARD[leg]), (
                ph,
                leg,
            )


def test_targets_reachable_with_com_shift_applied():
    # the real stage-2 composition: gait target -> world anchor, then the
    # CoM shift re-expressed through body-pose IK. Must stay in ROM.
    for i in range(100):
        ph = i / 100.0
        dx, dy = body_shift(ph, C)
        anchors = {
            leg: foot_world(BodyPose(), leg, foot_target(ph, leg, C), BP)
            for leg in LEGS
        }
        shifted = foot_targets(BodyPose(dx=dx, dy=dy), anchors, BP)
        for leg in LEGS:
            theta = solve_side(LEG_SIDE[leg], shifted[leg], BP.leg, KNEE_FORWARD[leg])
            assert within_limits(_canon(leg, theta), BP.leg, KNEE_FORWARD[leg]), (
                ph,
                leg,
            )


# ---- CoM shift -------------------------------------------------------------


def test_body_shift_periodic_and_continuous():
    assert body_shift(0.0, C) == pytest.approx(body_shift(1.0, C))
    prev = body_shift(0.0, C)
    worst = 0.0
    for i in range(1, N + 1):
        cur = body_shift(i / N, C)
        worst = max(worst, abs(cur[0] - prev[0]), abs(cur[1] - prev[1]))
        prev = cur
    # min-jerk peak slope 1.875/ramp * amp, and two crossfading ramps
    # can add — one dense step stays under 2x that (no jumps)
    step_bound = 2 * 1.875 / C.shift_ramp * C.shift_amp / N * 1.1
    assert worst < step_bound, (worst, step_bound)


def test_body_shift_bounded_by_amplitude():
    for i in range(N):
        dx, dy = body_shift(i / N, C)
        # at most one ramping-out + one ramping-in leg overlap; same-sign
        # components can momentarily sum, opposite cancel
        assert abs(dx) <= 2 * C.shift_amp + 1e-12
        assert abs(dy) <= 2 * C.shift_amp + 1e-12


def test_body_shift_points_away_from_swing_leg():
    # mid-swing of each leg the shift must be in the OPPOSITE corner
    for leg in LEGS:
        mid = (C.duty + 1.0) / 2.0 - PHASE_OFFSET[leg]
        dx, dy = body_shift(mid % 1.0, C)
        sx = 1.0 if leg in ("FL", "FR") else -1.0
        sy = 1.0 if leg in ("FL", "RL") else -1.0
        assert dx * sx < 0, (leg, dx)
        assert dy * sy < 0, (leg, dy)


def test_body_shift_holds_lateral_through_same_side_handoff():
    # ramp windows crossfade: during the FL->RL handoff (both LEFT legs,
    # phase [0, 0.05)) the min-jerk weights sum to 1, so dy holds at
    # exactly -amp (CoM parked on the RIGHT the whole time the left side
    # is stepping); mirrored for the FR->RR handoff at [0.5, 0.55)
    for ph in (0.005, 0.025, 0.045):
        assert body_shift(ph, C)[1] == pytest.approx(-C.shift_amp)
        assert body_shift(ph + 0.5, C)[1] == pytest.approx(+C.shift_amp)
