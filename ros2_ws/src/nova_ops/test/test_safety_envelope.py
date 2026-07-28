"""Unit tests for the safety envelope library.

Pure-Python tests — no rclpy required. Validates limit storage,
counter accounting, and the clamp + velocity + load logic in isolation.
"""

import math
import pytest
import types


from nova_ops.safety_envelope import (
    EnvelopeCounters,
    JointLimit,
    JointLimits,
    SafeJointCommandPublisher,
    load_default_limits,
)


# ---- Limit table -----------------------------------------------------


def test_default_limits_cover_active_legs():
    lim = load_default_limits()
    for i in range(1, 13):
        assert i in lim, f"joint {i} missing"
    assert 13 not in lim, "arm IDs should NOT be in default (leg-only) table"


def test_arm_optional():
    lim = load_default_limits(include_arm=True)
    for i in range(13, 19):
        assert i in lim


def test_soft_margin_is_2_deg():
    lim = JointLimit(lower=-1.0, upper=1.0, velocity=10.0, effort=0.7)
    assert math.isclose(lim.soft_lower - lim.lower, math.radians(2.0))
    assert math.isclose(lim.upper - lim.soft_upper, math.radians(2.0))


# ---- Counters --------------------------------------------------------


def test_counter_flat_layout():
    c = EnvelopeCounters(joint_ids=[1, 2, 3])
    assert c.as_flat_list() == [0] * 9  # 3 modes * 3 joints
    c.increment("position", 1)
    c.increment("velocity", 2)
    c.increment("load", 3)
    flat = c.as_flat_list()
    # position_1=1, others zero; velocity_2=1; load_3=1
    assert flat[0] == 1
    assert flat[4] == 1  # position(3) + velocity(2-1) idx
    assert flat[8] == 1  # position(3) + velocity(3) + load(3-1) idx


def test_counter_ignores_untracked_joint():
    c = EnvelopeCounters(joint_ids=[1, 2])
    c.increment("position", 99)  # silently noop
    assert sum(c.as_flat_list()) == 0


def test_counter_reset():
    c = EnvelopeCounters(joint_ids=[1])
    c.increment("position", 1)
    c.increment("load", 1)
    c.reset()
    assert sum(c.as_flat_list()) == 0


# ---- Wrapper ---------------------------------------------------------


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self):
        self._ns = 0
        self.logs = []
        self._clock = types.SimpleNamespace(
            now=lambda: types.SimpleNamespace(nanoseconds=self._ns)
        )

    def get_clock(self):
        return self._clock

    def advance(self, sec):
        self._ns += int(sec * 1e9)

    def get_logger(self):
        node = self

        class _L:
            def warn(self, m):
                node.logs.append(m)

            def info(self, m):
                node.logs.append(m)

        return _L()


class _FakePub:
    def __init__(self):
        self.published = []

    def publish(self, msg):
        self.published.append(list(msg.position))


class _CmdMsg:
    def __init__(self, positions):
        self.position = list(positions)


def _hard_limit(
    lower=-math.pi / 4, upper=math.pi / 4, velocity=math.radians(180), effort=0.7
):
    return JointLimit(lower=lower, upper=upper, velocity=velocity, effort=effort)


def _wrapper(joint_count: int = 1):
    table = {i + 1: _hard_limit() for i in range(joint_count)}
    limits = JointLimits(table)
    node = _FakeNode()
    pub = _FakePub()
    sw = SafeJointCommandPublisher(node=node, limits=limits, raw_publisher=pub)
    return sw, node, pub


def test_publish_passes_in_bounds_command():
    sw, _, pub = _wrapper(1)
    sw.publish(_CmdMsg([0.0]))
    assert pub.published == [[0.0]]


def test_publish_clamps_out_of_bounds():
    sw, node, pub = _wrapper(1)
    sw.publish(_CmdMsg([math.pi]))  # WAY over upper
    assert pub.published
    out = pub.published[0][0]
    # Clamped to soft_upper = upper - 2° margin
    assert out < math.pi / 4
    assert out >= math.pi / 4 - math.radians(2.0) - 1e-6
    assert any("position" in m for m in node.logs)


def test_velocity_clamp_applies_after_first_sample():
    sw, node, pub = _wrapper(1)
    # First publish establishes baseline at 0
    sw.publish(_CmdMsg([0.0]))
    # 10ms later, jump full range — way past velocity limit
    node.advance(0.010)
    sw.publish(_CmdMsg([math.pi / 4 - math.radians(3)]))  # in-position OK
    assert pub.published[-1][0] < math.pi / 4 - math.radians(2)
    # Effective velocity over 10ms would be ~3500 deg/s; limit is 180 deg/s
    # so it must have been clamped (output should be ~0 + 180°/s * 0.01s = 1.8°)
    out_deg = math.degrees(pub.published[-1][0])
    assert out_deg < 5.0, f"velocity not clamped: out={out_deg}°"
    assert any("velocity" in m for m in node.logs)


def test_load_refusal_holds_position():
    sw, node, pub = _wrapper(1)
    # Establish baseline
    sw.publish(_CmdMsg([0.1]))
    # Pretend load samples come in over the threshold
    js = types.SimpleNamespace(effort=[0.85])  # 85% > 70% threshold
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    node.advance(0.020)
    # Now try to move further — should be refused, position held at 0.1
    sw.publish(_CmdMsg([0.3]))
    out = pub.published[-1][0]
    assert math.isclose(out, 0.1, abs_tol=1e-6), f"expected hold at 0.1, got {out}"
    assert any("load" in m for m in node.logs)


def test_load_refusal_allows_backoff():
    """The fix: under sustained +load, a load-REDUCING (back-off) move must
    pass — only load-increasing moves are refused. Pre-fix it held both."""
    sw, node, pub = _wrapper(1)
    sw.publish(_CmdMsg([0.3]))  # baseline at +0.3
    js = types.SimpleNamespace(effort=[0.85])  # +85% load → straining toward +
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    sw.on_joint_states(js)
    node.advance(0.1)
    sw.publish(_CmdMsg([0.28]))  # small back-off (−, opposite +load)
    out = pub.published[-1][0]
    # Allowed: goal moves toward 0.28, NOT held at 0.3.
    assert math.isclose(out, 0.28, abs_tol=1e-6), (
        f"load-reducing back-off should pass, got {out}"
    )


# ---- posture gate (the chassis envelope, at the choke point) ---------------
#
# 2026-07-25 review finding: the chassis constraint is POSTURE-dependent (how far
# a leg may fold depends on haa splay and kfe fold together), and it was only
# enforced in nova_locomotion.solve_side — the GAIT path. nova_calibration's
# servo_homing and actuator_char publish /joint_commands directly and never touch
# it, and homing is the first thing that runs on real hardware. These lock the
# gate into the wrapper, which every publisher passes through.


def _posture_wrapper():
    """12-joint wrapper with hfe scalars wide open, so ONLY the posture gate
    can be what moves an hfe command."""
    table = {i + 1: _hard_limit(lower=-math.pi, upper=math.pi) for i in range(12)}
    node, pub = _FakeNode(), _FakePub()
    sw = SafeJointCommandPublisher(
        node=node, limits=JointLimits(table), raw_publisher=pub
    )
    return sw, pub


def _cmd_with(leg_ids, haa, hfe, kfe):
    pos = [0.0] * 12
    haa_id, hfe_id, kfe_id = leg_ids
    pos[haa_id - 1], pos[hfe_id - 1], pos[kfe_id - 1] = haa, hfe, kfe
    return _CmdMsg(pos)


def test_posture_gate_clamps_fold_that_would_reach_the_skirt():
    """Splayed + folded is refused; the SAME fold at neutral haa is allowed.

    This is the behaviour a per-joint scalar cannot express, and the reason the
    firmware hfe cap could be loosened to mechanical at all.
    """
    sw, pub = _posture_wrapper()
    assert sw._leg_ids, "posture gate inactive — joint map did not load"
    fl = sw._leg_ids["FL"]
    kfe = math.radians(-105.0)
    fold = math.radians(60.0)

    sw.publish(_cmd_with(fl, math.radians(40.0), fold, kfe))   # full outboard splay
    splayed = pub.published[-1][fl[1] - 1]
    sw.publish(_cmd_with(fl, 0.0, fold, kfe))                  # neutral hip
    neutral = pub.published[-1][fl[1] - 1]

    assert splayed < fold - 1e-9, "splayed fold was NOT clamped — skirt exposure"
    assert neutral == pytest.approx(fold), "neutral fold was clamped — over-tight"


def test_posture_gate_is_conservative_while_haa_sign_is_unknown():
    """/joint_commands is in the SERVO frame, where the inboard haa direction is
    unknown until homing fills HAA_INBOARD_SIGN. Until then BOTH interpretations
    of a commanded haa must be respected, so a splay magnitude is clamped
    whichever sign it arrives with."""
    sw, pub = _posture_wrapper()
    fl = sw._leg_ids["FL"]
    kfe, fold = math.radians(-105.0), math.radians(60.0)
    out = []
    for sign in (+1.0, -1.0):
        sw.publish(_cmd_with(fl, sign * math.radians(40.0), fold, kfe))
        out.append(pub.published[-1][fl[1] - 1])
    assert out[0] == pytest.approx(out[1]), "haa sign changed the bound"
    assert out[0] < fold - 1e-9


# ---- END-TO-END: a real gait pose must survive the envelope ------------------
#
# THE MISSING TEST CLASS. solve_side, within_limits and limits.py were each
# tested in isolation, and all passed, while the path BETWEEN them was broken:
# limits.py held kfe as a positive magnitude [+5, +109] while leg_ik emits it
# SIGNED and negative, and nothing converts. Result — every knee command was
# clamped to the +5 floor (trot RL: commanded -95.1, published +7.0), i.e. the
# robot would have been driven to near-straight knees under load on first stand.
#
# No unit test could see it. This one walks the real chain:
#   gait -> solve_side -> pose_to_positions -> SafeJointCommandPublisher.publish


def _gait_positions(phase: float):
    from nova_locomotion.controller import pose_to_positions, LEGS
    from nova_locomotion.gait.trot import TrotParams, all_feet
    from nova_locomotion.kinematics.leg_ik import (
        KNEE_FORWARD, LEG_SIDE, LegParams, solve_side,
    )
    from nova_ops.joint_map import load_joint_id_map

    p = LegParams()
    feet = all_feet(phase, TrotParams())
    pose = {
        leg: solve_side(LEG_SIDE[leg], feet[leg], p, KNEE_FORWARD[leg], leg=leg)
        for leg in LEGS
    }
    return pose_to_positions(pose, load_joint_id_map()), load_joint_id_map()


def test_end_to_end_gait_survives_the_envelope():
    """Every joint a real trot commands must publish UNCHANGED.

    A clamp here is not a safety win — it means the gait and the envelope
    disagree about what a legal pose is, and the robot executes neither.
    """
    from nova_ops.safety_envelope import load_default_limits

    node, pub = _FakeNode(), _FakePub()
    sw = SafeJointCommandPublisher(
        node=node, limits=load_default_limits(), raw_publisher=pub
    )
    worst = []
    for phase in [i / 24.0 for i in range(24)]:
        pos, idm = _gait_positions(phase)
        sw.publish(_CmdMsg(pos))
        out = pub.published[-1]
        for name, jid in idm.items():
            i = jid - 1
            if i < len(pos) and abs(out[i] - pos[i]) > 1e-9:
                worst.append(
                    f"{name}@phase{phase:.2f}: commanded "
                    f"{math.degrees(pos[i]):+.1f}° -> published "
                    f"{math.degrees(out[i]):+.1f}°"
                )
    assert not worst, (
        "the safety envelope altered a real gait command:\n  "
        + "\n  ".join(worst[:8])
        + (f"\n  ...and {len(worst) - 8} more" if len(worst) > 8 else "")
    )


# ---- #164: the table is LEG-LOCAL hfe; the consumer converts ---------------


def test_to_canonical_front_is_identity_rear_negates_and_swaps():
    """Rear hip is a 180 deg YAW (#163), so leg-local +hfe is the opposite
    world rotation from the front's. MEASURED: leg-local +hfe moves the foot
    -x at the front and +x at the rear, while URDF +hfe moves it -x on all
    four. Endpoints must SWAP as well as negate -- negating an interval
    reverses which end is the low one.
    """
    from nova_ops.rom_envelope import _to_canonical

    assert _to_canonical("FL", -95.0, 67.9) == (-95.0, 67.9)
    assert _to_canonical("FR", -95.0, 67.9) == (-95.0, 67.9)
    assert _to_canonical("RL", -95.0, 67.9) == (-67.9, 95.0)
    assert _to_canonical("RR", -95.0, 67.9) == (-67.9, 95.0)


def test_rear_canonical_window_stays_bounded_BELOW():
    """The direction check that catches a sign error.

    At the REAR, folding toward the trunk is FORWARD, which is canonical
    NEGATIVE hfe -- so the restrictive bound must sit on the negative side. If
    the conversion were dropped (or applied twice) the tight bound would land
    on the positive side, permitting exactly the folds that reach the riser.
    """
    import math

    from nova_ops.rom_envelope import hfe_bounds

    f_lo, f_hi = hfe_bounds("FL", 0.0, math.radians(-109))
    r_lo, r_hi = hfe_bounds("RL", 0.0, math.radians(-109))
    # front: tight on the POSITIVE side; rear: tight on the NEGATIVE side
    assert abs(f_hi) < abs(f_lo), (math.degrees(f_lo), math.degrees(f_hi))
    assert abs(r_lo) < abs(r_hi), (math.degrees(r_lo), math.degrees(r_hi))
    # and they are mirror images of each other
    assert math.degrees(r_lo) == pytest.approx(-math.degrees(f_hi), abs=0.01)


def test_table_rows_are_LEG_LOCAL_not_pre_negated():
    """Guard against a DOUBLE negation.

    hfe_envelope.py emits leg-local and says so; rom_envelope converts. If a
    future regeneration also negated rear rows generator-side, the consumer
    would negate again and put the rear bound back on the wrong side. In
    leg-local the rear rows MIRROR the front rows (same sign, same side); if
    they ever come back pre-negated this fails.
    """
    from nova_ops.rom_envelope_table import ENVELOPE, HAAS

    i0 = HAAS.index(0)   # NOT a hardcoded index: the haa grid is refined from
                         # time to time (#181), and a stale literal would keep
                         # passing while silently checking a different posture
    for kfe in (-109, -50, 0):
        f_lo, f_hi = ENVELOPE["FL"][kfe][i0]
        r_lo, r_hi = ENVELOPE["RL"][kfe][i0]
        assert r_lo == pytest.approx(f_lo, abs=3.0), (kfe, f_lo, r_lo)
        assert r_hi == pytest.approx(f_hi, abs=3.0), (kfe, f_hi, r_hi)


def test_rear_rows_are_kfe_dependent_again():
    """The stale rear rows were flat across all ten kfe values -- the tell that
    they were an artefact of the backwards placement (the knee folded AWAY from
    the chassis, so kfe stopped mattering)."""
    from nova_ops.rom_envelope_table import ENVELOPE, HAAS, KFES

    i0 = HAAS.index(0)
    his = [ENVELOPE["RL"][k][i0][1] for k in KFES]
    assert max(his) - min(his) > 3.0, f"rear still flat across kfe: {his}"
