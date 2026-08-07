"""GaitController core: modes, timing, bus ordering, backlash wiring.

Pure — imports nova_ops.joint_map (the canonical bus-ID map, also
rclpy-free) but never rclpy. node.py stays untested glue by doctrine.
"""

import pytest

from nova_locomotion.choreo.stand import pose_for
from nova_locomotion.controller import (
    JOINTS,
    LEGS,
    ControllerParams,
    GaitController,
    PreflightGate,
    gait_pose,
    pose_to_positions,
    positions_to_pose,
)
from nova_locomotion.gait.backlash import BacklashComp
from nova_locomotion.kinematics.leg_ik import KNEE_FORWARD, LEG_SIDE, within_limits
from nova_ops.joint_map import load_joint_id_map

P = ControllerParams()
ID_MAP = load_joint_id_map()


def _canon(leg, theta):
    return (-theta[0], theta[1], theta[2]) if LEG_SIDE[leg] == "right" else theta


# ---- bus ordering ----------------------------------------------------------


def test_pose_to_positions_orders_by_bus_id():
    # distinct sentinel per joint: leg index * 10 + chain index
    pose = {leg: tuple(li * 10.0 + j for j in range(3)) for li, leg in enumerate(LEGS)}
    positions = pose_to_positions(pose, ID_MAP)
    assert len(positions) == 12
    for leg in LEGS:
        for j, joint in enumerate(JOINTS):
            assert positions[ID_MAP[f"{leg}_{joint}"] - 1] == pose[leg][j]


def test_positions_pose_round_trip():
    pose = pose_for("stand", P.choreo)
    assert positions_to_pose(pose_to_positions(pose, ID_MAP), ID_MAP) == pose


# ---- mode machine ----------------------------------------------------------


def test_idle_before_any_command_is_none():
    c = GaitController(P)
    assert c.update(0.0) is None
    assert c.command_positions(0.0, ID_MAP) is None


def test_unknown_mode_raises():
    c = GaitController(P)
    with pytest.raises(ValueError):
        c.set_mode("moonwalk", 0.0)


def test_stand_up_reaches_stand_and_holds():
    c = GaitController(P)
    c.set_mode("stand_up", now=10.0)
    assert c.update(10.0) == pose_for("lie", P.choreo)  # default start
    stand = pose_for("stand", P.choreo)
    assert c.update(20.0) == stand  # well past the sequence: clamped to end
    assert c.update(25.0) == stand  # and holds
    # idle afterwards keeps holding the last pose
    c.set_mode("idle", now=26.0)
    assert c.update(27.0) == stand


def test_stand_up_seeds_from_current_pose():
    start = pose_for("crouch", P.choreo)
    c = GaitController(P)
    c.set_mode("stand_up", now=0.0, current_pose=start)
    assert c.update(0.0) == start


def test_sit_reaches_lie():
    c = GaitController(P)
    c.set_mode("sit", now=0.0)
    assert c.update(60.0) == pose_for("lie", P.choreo)


def test_choreo_timing_indexed_by_elapsed_time():
    # sampling at 100 Hz must NOT play a 50 Hz sequence at double speed:
    # halfway through the wall-clock duration we are near the middle frame
    c = GaitController(P)
    c.set_mode("stand_up", now=0.0)
    total = 1.2 + 1.5  # settle_s + rise_s (choreo defaults)
    mid = c.update(total / 2)
    assert mid != pose_for("lie", P.choreo)
    assert mid != pose_for("stand", P.choreo)


def test_gait_modes_produce_rom_valid_poses_over_a_cycle():
    # #47 (2026-07-11, MEASURED): the front hfe cap is no longer -50° (stale
    # — see leg_ik.LegParams.hfe_min_front) but -86°, matching REAR (see
    # test_trot.py/test_crawl.py for the per-gait cross-check). Passing
    # leg= now enforces the real per-leg split through the actual
    # controller.gait_pose() -> solve_side() funnel (the #47 clamp's choke
    # point) — no retune needed.
    for mode, freq in (("trot", P.trot_freq), ("crawl", P.crawl_freq)):
        c = GaitController(P)
        c.set_mode(mode, now=0.0)
        for i in range(60):
            pose = c.update(i / 60.0 / freq)  # one full stride
            for leg in LEGS:
                assert within_limits(
                    _canon(leg, pose[leg]), P.body.leg, KNEE_FORWARD[leg], leg=leg
                ), (mode, i, leg)


def test_gait_pose_rejects_non_gait_mode():
    with pytest.raises(ValueError):
        gait_pose("stand_up", 0.0, P)


# ---- preflight gate (#285) --------------------------------------------------


def test_preflight_gate_allows_idle_before_any_observation():
    gate = PreflightGate()
    assert gate.allows("idle") is True
    assert gate.allows("trot") is False


def test_preflight_gate_blocks_motion_modes_until_observed_ok():
    gate = PreflightGate()
    assert gate.allows("stand_up") is False
    gate.observe(False)  # e.g. preflight ran and a critical check FAILed
    assert gate.allows("stand_up") is False
    gate.observe(True)
    assert gate.allows("stand_up") is True


def test_preflight_gate_bypass_when_not_required():
    gate = PreflightGate(require=False)
    assert gate.allows("trot") is True  # no observe() needed


def test_gait_controller_set_mode_refuses_motion_before_preflight():
    gate = PreflightGate()
    c = GaitController(P, gate=gate)
    with pytest.raises(ValueError):
        c.set_mode("stand_up", now=0.0)
    assert c.mode == "idle"  # refused switch left the mode machine alone
    # idle itself is never refused
    c.set_mode("idle", now=0.0)
    assert c.mode == "idle"


def test_gait_controller_set_mode_accepts_motion_after_preflight_observed():
    gate = PreflightGate()
    gate.observe(True)
    c = GaitController(P, gate=gate)
    c.set_mode("stand_up", now=0.0)
    assert c.mode == "stand_up"


# ---- backlash wiring --------------------------------------------------------


def test_command_positions_apply_backlash_bias():
    b = 0.010
    comp = BacklashComp({f"{leg}_{j}": b for leg in LEGS for j in JOINTS})
    c = GaitController(P, backlash=comp)
    c.set_mode("trot", now=0.0)
    raw_a = pose_to_positions(c.update(0.001), ID_MAP)
    # fresh controller state: recompute through command_positions
    c2 = GaitController(
        P, backlash=BacklashComp({f"{leg}_{j}": b for leg in LEGS for j in JOINTS})
    )
    c2.set_mode("trot", now=0.0)
    first = c2.command_positions(0.001, ID_MAP)
    # first tick has no direction yet -> unbiased
    assert first == pytest.approx(raw_a)
    # subsequent ticks bias by half-backlash in the motion direction
    t = 0.05
    biased = c2.command_positions(t, ID_MAP)
    c3 = GaitController(P)
    c3.set_mode("trot", now=0.0)
    raw_b = c3.command_positions(t, ID_MAP)
    for i in range(12):
        delta = biased[i] - raw_b[i]
        if abs(raw_b[i] - first[i]) > 1e-9:  # joint actually moved
            assert abs(delta) == pytest.approx(b / 2)
