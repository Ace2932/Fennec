"""Offline fit of STS3215 actuator parameters from a step-response log.

Pure Python (lists only, no numpy) so it runs anywhere and unit-tests without
hardware. Input is the time-series captured by actuator_char/node.py:

    samples: list of (t, goal_raw, pos_raw, vel_raw, load_raw)

These params feed the sim actuator model (MuJoCo `position` actuator + velocity
limit + first-order lag + measured latency). The point is to model the *whole
deployed path* the policy will see — Teensy slew limit + bus latency + servo
internal PD — not the bare servo, so sim-to-real holds. See
[`docs/sim-training.md`].

Estimators (all robust to a single step edge; run one step per call):

    estimate_latency        command edge -> first position response
    estimate_max_velocity    peak |d pos / d t| during the move (raw/s)
    estimate_tau            first-order time constant (63.2% rise)
    fit_step                bundles the above + steady-state gain into a dict
"""
from dataclasses import dataclass


@dataclass
class StepFit:
    latency_s: float
    max_velocity_raw_s: float
    tau_s: float
    steady_gain: float       # (pos_inf - pos_0) / (goal_inf - goal_0)
    pos_0: int
    pos_inf: int
    goal_0: int
    goal_inf: int
    n_samples: int


def _col(samples, i):
    return [s[i] for s in samples]


def find_step_index(goal, min_delta=10):
    """Index of the first command edge (|goal change| >= min_delta)."""
    for k in range(1, len(goal)):
        if abs(goal[k] - goal[k - 1]) >= min_delta:
            return k
    return None


def estimate_latency(t, goal, pos, move_thresh=3, min_delta=10):
    """Seconds from command edge to first measurable position move.

    Returns None if no step or no response found.
    """
    k = find_step_index(goal, min_delta)
    if k is None:
        return None
    pos_at_step = pos[k - 1]
    for j in range(k, len(pos)):
        if abs(pos[j] - pos_at_step) >= move_thresh:
            return max(0.0, t[j] - t[k])
    return None


def estimate_max_velocity(t, pos):
    """Peak |d pos / d t| over the log, in raw counts/second."""
    vmax = 0.0
    for i in range(1, len(pos)):
        dt = t[i] - t[i - 1]
        if dt <= 0:
            continue
        v = abs(pos[i] - pos[i - 1]) / dt
        vmax = max(vmax, v)
    return vmax


def estimate_tau(t, goal, pos, min_delta=10):
    """First-order time constant: time to reach 63.2% of the step, in seconds.

    Measured from the command edge. Returns None if no clean step.
    """
    k = find_step_index(goal, min_delta)
    if k is None:
        return None
    p0 = pos[k - 1]
    p_inf = pos[-1]
    if abs(p_inf - p0) < min_delta:
        return None
    target = p0 + 0.632 * (p_inf - p0)
    rising = p_inf > p0
    for j in range(k, len(pos)):
        if (rising and pos[j] >= target) or (not rising and pos[j] <= target):
            return max(0.0, t[j] - t[k])
    return None


def fit_step(samples, min_delta=10) -> StepFit:
    """Fit a single-step log. Raises ValueError if no command step present."""
    if len(samples) < 3:
        raise ValueError('need >= 3 samples')
    t = _col(samples, 0)
    goal = _col(samples, 1)
    pos = _col(samples, 2)

    k = find_step_index(goal, min_delta)
    if k is None:
        raise ValueError('no command step found (increase amplitude?)')

    goal_0, goal_inf = goal[k - 1], goal[-1]
    pos_0, pos_inf = pos[k - 1], pos[-1]
    dgoal = goal_inf - goal_0
    gain = (pos_inf - pos_0) / dgoal if dgoal else 0.0

    lat = estimate_latency(t, goal, pos, min_delta=min_delta)
    tau = estimate_tau(t, goal, pos, min_delta=min_delta)

    return StepFit(
        latency_s=lat if lat is not None else float('nan'),
        max_velocity_raw_s=estimate_max_velocity(t, pos),
        tau_s=tau if tau is not None else float('nan'),
        steady_gain=gain,
        pos_0=pos_0, pos_inf=pos_inf, goal_0=goal_0, goal_inf=goal_inf,
        n_samples=len(samples),
    )
