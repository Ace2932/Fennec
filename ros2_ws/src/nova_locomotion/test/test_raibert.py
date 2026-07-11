"""Raibert stepper + attitude PD: signs, clamps, reachability."""

import math

import pytest

from nova_locomotion.balance.raibert import (
    LEGS,
    RaibertParams,
    attitude_deltas,
    touchdown_target,
)
from nova_locomotion.kinematics.leg_ik import (
    KNEE_FORWARD,
    LEG_SIDE,
    solve_side,
)

P = RaibertParams()
H = 0.18  # stand height (m)
T_ST = 0.3  # stance duration (s)


# ---- touchdown target ------------------------------------------------------


def test_zero_everything_is_neutral():
    assert touchdown_target((0, 0), (0, 0), T_ST, H, P) == pytest.approx(
        (P.neutral_x, 0.0)
    )


def test_tracking_command_gives_pure_feedforward():
    # no velocity error: touchdown = neutral + (T/2)*v_cmd, both axes
    v = (0.10, 0.04)
    x, dy = touchdown_target(v, v, T_ST, H, P)
    assert x == pytest.approx(P.neutral_x + 0.5 * T_ST * v[0])
    assert dy == pytest.approx(0.5 * T_ST * v[1])


def test_velocity_error_shifts_touchdown_correct_sign():
    # moving faster than commanded => place the foot FURTHER FORWARD to
    # brake; slower => behind neutral to accelerate. Same logic laterally.
    fast_x = touchdown_target((0.10, 0.0), (0.0, 0.0), T_ST, H, P)
    slow_x = touchdown_target((-0.10, 0.0), (0.0, 0.0), T_ST, H, P)
    assert fast_x[0] > P.neutral_x > slow_x[0]
    shove_y = touchdown_target((0.0, 0.08), (0.0, 0.0), T_ST, H, P)
    assert shove_y[1] > 0.0
    # capture-point term makes the gain scale with sqrt(h): taller body,
    # bigger corrective step for the same error
    tall = touchdown_target((0.10, 0.0), (0.0, 0.0), T_ST, 0.20, P)
    low = touchdown_target((0.10, 0.0), (0.0, 0.0), T_ST, 0.14, P)
    assert tall[0] > low[0]


def test_max_step_clamp_honored():
    x, dy = touchdown_target((5.0, 5.0), (0.0, 0.0), T_ST, H, P)
    assert math.hypot(x - P.neutral_x, dy) == pytest.approx(P.max_step)


def test_reachable_disc_clamp_and_ik_solvable():
    # loosen max_step so the DISC clamp is the binding one, then the
    # result must still be an IK-solvable foot target at stand height
    loose = RaibertParams(max_step=1.0)
    for vx, vy in [(3.0, 0.0), (-3.0, 0.0), (0.0, 3.0), (2.0, -2.0), (-1.5, 2.5)]:
        x, dy = touchdown_target((vx, vy), (0.0, 0.0), T_ST, H, loose)
        assert math.hypot(x, dy) < loose.leg.femur + loose.leg.tibia
        foot = (x, loose.stand_y + dy, -H)
        for leg in LEGS:  # solvable on every leg, both knee branches
            solve_side(LEG_SIDE[leg], foot, loose.leg, KNEE_FORWARD[leg])


def test_clamps_never_flip_direction():
    x, dy = touchdown_target((4.0, 1.0), (0.0, 0.0), T_ST, H, P)
    assert x > P.neutral_x and dy > 0.0


# ---- attitude regulation ----------------------------------------------------


def test_zero_error_zero_deltas():
    assert attitude_deltas(0.0, 0.0, kp=0.05, kd=0.01) == {leg: 0.0 for leg in LEGS}


def test_roll_error_antisymmetric_left_right():
    # +roll_err = left side high -> shorten left (dz>0), extend right
    d = attitude_deltas(0.2, 0.0, kp=0.05, kd=0.0)
    assert d["FL"] > 0 > d["FR"]
    assert d["FL"] == pytest.approx(-d["FR"])
    assert d["FL"] == pytest.approx(d["RL"])
    assert d["FR"] == pytest.approx(d["RR"])


def test_pitch_error_antisymmetric_front_rear():
    # +pitch_err = nose down -> EXTEND front legs (dz<0), shorten rear
    d = attitude_deltas(0.0, 0.2, kp=0.05, kd=0.0)
    assert d["FL"] < 0 < d["RL"]
    assert d["FL"] == pytest.approx(-d["RL"])
    assert d["FL"] == pytest.approx(d["FR"])
    assert d["RL"] == pytest.approx(d["RR"])


def test_derivative_term_acts_like_error():
    d_rate = attitude_deltas(0.0, 0.0, kp=0.05, kd=0.02, roll_rate=1.0)
    d_err = attitude_deltas(0.4, 0.0, kp=0.05, kd=0.0)
    for leg in LEGS:
        assert d_rate[leg] == pytest.approx(d_err[leg])


def test_deltas_bounded():
    d = attitude_deltas(10.0, -10.0, kp=1.0, kd=0.0, max_dz=0.02)
    for leg in LEGS:
        assert abs(d[leg]) <= 0.02 + 1e-12
    # both channels saturated: corners where they add still clamp
    assert d["FL"] == pytest.approx(0.02)  # +roll shorten left, -pitch shorten front
