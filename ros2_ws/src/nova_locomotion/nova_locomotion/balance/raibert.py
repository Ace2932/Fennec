"""Raibert-heuristic foot placement + attitude regulation (pure logic).

Roadmap stage 4 items 3+4 (docs/roadmap-trot-balance.md): THE balance
controller for position servos — you place feet, you don't torque
joints. Pure math with no state estimator dependency; the estimator
(stage 4.1) and contact detection (4.2) feed it later. Buildable and
testable now, per the roadmap's pre-hardware list.

touchdown_target(): classic Raibert stepping plus a capture-point term,

    x_td = neutral + (T_st/2)·v_cmd + k_v·(v_act − v_cmd)
                   + cap_gain·sqrt(h/g)·(v_act − v_cmd)

per axis (x fore-aft, y lateral IN THE CANONICAL FRAME: the y offset is
relative to the stand_y stance line, +y outboard — a lateral shove
recovery steps outboard on one side, inboard on the other, and
solve_side owns the physical mirror as always). Two clamps, both here
so no caller can forget them: step-vector norm <= max_step, then the
leg's reachable disc at stand height from the real link lengths
(sphere |p| <= margin·(a1+a2) cut at z = -h, solved analytically as a
scale-back toward neutral).

attitude_deltas(): PD on roll/pitch error -> per-stance-leg Δz through
the hip-grid corner signs. Sign contract (matches body_pose, linearized
with BodyPose(roll=-roll_err, pitch=-pitch_err)): +roll_err = left side
high -> SHORTEN left legs (Δz > 0 pulls that side down), extend right;
+pitch_err = nose down -> EXTEND front legs (Δz < 0 pushes the nose
up), shorten rear. Promotes the stage-3.5 trim tab to full bandwidth;
gains are m per rad (kp) / m per rad/s (kd), clamped to max_dz.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple

from nova_locomotion.kinematics.leg_ik import LegParams

_G = 9.81

LEGS = ("FL", "FR", "RL", "RR")
# hip-grid corner signs, body frame x forward / canonical roll sense
SIGN_X = {"FL": 1.0, "FR": 1.0, "RL": -1.0, "RR": -1.0}
SIGN_Y = {"FL": 1.0, "FR": -1.0, "RL": 1.0, "RR": -1.0}


@dataclass(frozen=True)
class RaibertParams:
    k_v: float = 0.03  # feedback gain on velocity error (s) — Raibert term
    cap_gain: float = 0.5  # capture-point weight (dimensionless, 0..1)
    neutral_x: float = 0.0  # fore-aft neutral point under the hip (m)
    max_step: float = 0.05  # step-offset norm cap from neutral (m)
    reach_margin: float = 0.95  # fraction of (femur+tibia) treated reachable
    leg: LegParams = LegParams()
    stand_y: float = 0.0643  # canonical stance line = hip_offset (stock)


def touchdown_target(
    v_actual: Tuple[float, float],
    v_cmd: Tuple[float, float],
    stance_duration: float,
    body_height: float,
    p: RaibertParams = RaibertParams(),
) -> Tuple[float, float]:
    """Swing-leg touchdown (x, dy) in the CANONICAL hip frame.

    x is fore-aft; dy is lateral offset from the stand_y stance line
    (foot y target = stand_y + dy). Velocities are body-frame (vx, vy)
    m/s — pass the canonical-frame lateral for the leg (mirror-free:
    the caller hands BODY vy and this stays symmetric because both
    clamps are radial; solve_side handles sides downstream).
    """
    ex = v_actual[0] - v_cmd[0]
    ey = v_actual[1] - v_cmd[1]
    gain = p.k_v + p.cap_gain * math.sqrt(max(body_height, 0.0) / _G)
    x = p.neutral_x + 0.5 * stance_duration * v_cmd[0] + gain * ex
    dy = 0.5 * stance_duration * v_cmd[1] + gain * ey

    # clamp 1: step-offset norm from the neutral point
    ox, oy = x - p.neutral_x, dy
    n = math.hypot(ox, oy)
    if n > p.max_step:
        s = p.max_step / n
        ox, oy = ox * s, oy * s

    # clamp 2: the leg's reachable disc at stand height. Foot target is
    # (nx+ox, stand_y+oy, -h); reachable iff x^2 + (y^2 + h^2 - d^2)
    # <= (margin*(a1+a2))^2 (the leg_ik workspace sphere). Solve the
    # largest scale s in [0,1] of the offset keeping that true —
    # quadratic in s, monotone shrink toward neutral.
    a = p.leg
    r2 = (p.reach_margin * (a.femur + a.tibia)) ** 2
    h2 = body_height * body_height
    nx, sy = p.neutral_x, p.stand_y
    qa = ox * ox + oy * oy
    qb = 2.0 * (nx * ox + sy * oy)
    qc = nx * nx + sy * sy + h2 - a.hip_offset * a.hip_offset - r2
    if qa > 0.0 and qa + qb + qc > 0.0:  # s=1 violates the disc
        disc = qb * qb - 4.0 * qa * qc
        s = max(0.0, (-qb + math.sqrt(max(disc, 0.0))) / (2.0 * qa))
        s = min(1.0, s)
        ox, oy = ox * s, oy * s

    return (p.neutral_x + ox, oy)


def attitude_deltas(
    roll_err: float,
    pitch_err: float,
    kp: float,
    kd: float,
    roll_rate: float = 0.0,
    pitch_rate: float = 0.0,
    max_dz: float = 0.02,
) -> Dict[str, float]:
    """PD attitude regulation -> per-leg stance-foot Δz (m), CANONICAL z.

    Apply to STANCE legs only (a swing leg gets its Raibert touchdown
    instead). Δz adds to the foot target z: positive = foot closer to
    hip = that corner of the body drops. Signs from the hip grid:
    Δz = u_roll·SIGN_Y − u_pitch·SIGN_X (see module docstring contract).
    Each leg's delta is clamped to ±max_dz.
    """
    u_roll = kp * roll_err + kd * roll_rate
    u_pitch = kp * pitch_err + kd * pitch_rate
    out: Dict[str, float] = {}
    for leg in LEGS:
        dz = u_roll * SIGN_Y[leg] - u_pitch * SIGN_X[leg]
        out[leg] = max(-max_dz, min(max_dz, dz))
    return out
