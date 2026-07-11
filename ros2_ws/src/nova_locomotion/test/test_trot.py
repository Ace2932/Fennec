"""Pure tests for the trot gait generator + IK integration."""

import pytest

from nova_locomotion.gait.trot import TrotParams, foot_target, all_feet, LEGS
from nova_locomotion.kinematics.leg_ik import (
    LegParams,
    inverse_kinematics,
    within_limits,
)

T = TrotParams()


def test_periodic():
    for leg in LEGS:
        assert foot_target(0.0, leg, T) == pytest.approx(foot_target(1.0, leg, T))


def test_stance_is_planted_swing_is_lifted():
    fl_stance = foot_target(0.1, "FL", T)  # FL phase 0.1 -> stance
    fl_swing = foot_target(0.75, "FL", T)  # FL phase 0.75 -> swing
    assert fl_stance[2] == pytest.approx(-T.stand_height)  # on ground
    assert fl_swing[2] > -T.stand_height  # lifted


def test_diagonal_pairs_synchronized():
    # FL & RR move together; FR & RL together; the two pairs are anti-phase
    for ph in (0.0, 0.2, 0.4, 0.6, 0.8):
        assert foot_target(ph, "FL", T) == pytest.approx(foot_target(ph, "RR", T))
        assert foot_target(ph, "FR", T) == pytest.approx(foot_target(ph, "RL", T))
        assert foot_target(ph, "FL", T) != pytest.approx(foot_target(ph, "FR", T))


def test_swing_apex_height():
    # mid-swing (local s=0.5) reaches step_height above stand
    # FL swing midpoint is at phase duty + (1-duty)/2 = 0.75
    z = foot_target(0.75, "FL", T)[2]
    assert z == pytest.approx(-T.stand_height + T.step_height, abs=1e-9)


def test_stride_spans_step_length():
    xs = [foot_target(ph / 100.0, "FL", T)[0] for ph in range(100)]
    assert max(xs) == pytest.approx(T.step_length / 2, abs=1e-3)
    assert min(xs) == pytest.approx(-T.step_length / 2, abs=1e-3)


def test_gait_targets_are_ik_reachable():
    """Every foot target over a full cycle must be IK-solvable and within limits
    for a leg whose link lengths can actually reach the configured stand height."""
    p = LegParams()
    # stand_height must be inside the leg's reach for this to hold
    assert T.stand_height < p.femur + p.tibia, (
        "stand height exceeds leg reach (adjust TrotParams/LegParams)"
    )
    # #47 (2026-07-11, MEASURED): the front hfe cap is no longer -50°
    # (stale — see leg_ik.LegParams.hfe_min_front) but -86°, matching
    # REAR. Passing leg= now enforces the real per-leg split; TrotParams'
    # worst-case front excursion (~-59°, hardware/cad/chassis/
    # head_cap_sweep.py cross-check) is comfortably inside it — no retune
    # needed, this was flagging a stale cap value, not bad gait tuning.
    for i in range(100):
        ph = i / 100.0
        for leg, foot in all_feet(ph, T).items():
            sol = inverse_kinematics(foot, p, knee_forward=True)
            assert within_limits(sol, p, leg=leg), f"{leg}@{ph}: {sol} out of limits"
