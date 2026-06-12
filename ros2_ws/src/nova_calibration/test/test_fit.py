"""Unit tests for actuator_char.fit — synthetic first-order step responses."""
import math

from nova_calibration.actuator_char.fit import (
    estimate_latency, estimate_max_velocity, estimate_tau, fit_step,
    find_step_index)


def make_step(dt=0.02, pre=0.5, dur=2.0, p0=1000, p_inf=1200,
              tau=0.15, latency=0.04):
    """First-order rise from p0->p_inf after a command edge at t=pre,
    with `latency` dead time. Goal jumps p0->p_inf at t=pre."""
    samples = []
    n_pre = int(pre / dt)
    n = int((pre + dur) / dt)
    for k in range(n):
        t = k * dt
        goal = p0 if k < n_pre else p_inf
        if t < pre + latency:
            pos = p0
        else:
            x = (t - pre - latency) / tau
            pos = p0 + (p_inf - p0) * (1.0 - math.exp(-x))
        samples.append((t, goal, int(round(pos)), 0, 0))
    return samples


def test_find_step_index():
    g = [10, 10, 10, 200, 200]
    assert find_step_index(g) == 3


def test_latency_recovered():
    s = make_step(latency=0.04, dt=0.02)
    t = [r[0] for r in s]; g = [r[1] for r in s]; p = [r[2] for r in s]
    lat = estimate_latency(t, g, p)
    # within one sample period of the injected 0.04 s
    assert lat is not None
    assert abs(lat - 0.04) <= 0.02 + 1e-9


def test_tau_recovered():
    s = make_step(tau=0.15, latency=0.0, dt=0.01)
    t = [r[0] for r in s]; g = [r[1] for r in s]; p = [r[2] for r in s]
    tau = estimate_tau(t, g, p)
    assert tau is not None
    # 63.2% crossing should land near tau (a couple sample periods slack)
    assert abs(tau - 0.15) <= 0.03


def test_max_velocity_positive():
    s = make_step()
    t = [r[0] for r in s]; p = [r[2] for r in s]
    assert estimate_max_velocity(t, p) > 0


def test_fit_step_bundle():
    s = make_step(p0=1000, p_inf=1200)
    f = fit_step(s)
    assert f.goal_0 == 1000 and f.goal_inf == 1200
    assert abs(f.steady_gain - 1.0) < 0.05      # pos tracks goal 1:1 at steady
    assert f.n_samples == len(s)


def test_fit_step_no_step_raises():
    flat = [(k * 0.02, 1000, 1000, 0, 0) for k in range(10)]
    try:
        fit_step(flat)
        assert False, 'expected ValueError'
    except ValueError:
        pass
