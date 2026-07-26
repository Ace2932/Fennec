"""Unit tests for the pure hard-stop algorithm (no ROS, no hardware).

A FakeServo models a joint that moves toward its goal until it hits a
mechanical stop, after which load climbs. Lets us verify stop detection,
home computation, timeout, overload, and abort paths deterministically.
"""
from nova_calibration.servo_homing.config import JointHomeConfig
from nova_calibration.servo_homing.hard_stop import (
    HardStopCalibrator, HardStopParams, Outcome)


class FakeServo:
    def __init__(self, start, stop_at, search_dir, step_follow=4):
        self.pos = start
        self.goal = start
        self.stop_at = stop_at
        self.search_dir = search_dir
        self.step_follow = step_follow
        self.load = 0

    def send_goal(self, jid, raw):
        self.goal = raw

    def tick(self):
        # Move toward goal, but never past the mechanical stop.
        delta = max(-self.step_follow, min(self.step_follow, self.goal - self.pos))
        nxt = self.pos + delta
        blocked = (self.search_dir > 0 and nxt >= self.stop_at) or \
                  (self.search_dir < 0 and nxt <= self.stop_at)
        if blocked:
            self.pos = self.stop_at
            self.load = 300            # pressing against the stop
        else:
            self.pos = nxt
            self.load = 20             # free motion

    def read_position(self, jid):
        return self.pos

    def read_load(self, jid):
        return self.load


def _make(servo, params=None, aborted=lambda: False):
    # sleep_tick advances the fake servo one physics step instead of sleeping.
    return HardStopCalibrator(
        read_position=servo.read_position,
        read_load=servo.read_load,
        send_goal=servo.send_goal,
        is_aborted=aborted,
        sleep_tick=servo.tick,
        params=params or HardStopParams(timeout_s=5.0),
    )


def test_detects_stop_and_computes_home():
    cfg = JointHomeConfig(1, 'FL_coxa', search_dir=+1,
                          stop_to_home_raw=100, placeholder=False)
    # 200 raw of travel @ 4 raw/tick = ~50 ticks, within the 5 s timeout.
    servo = FakeServo(start=1000, stop_at=1200, search_dir=+1)
    res = _make(servo).run_joint(cfg)
    assert res.outcome == Outcome.OK
    assert res.stop_pos_raw == 1200
    # home = stop - search_dir*offset = 1200 - 100
    assert res.home_raw == 1100


def test_negative_direction():
    cfg = JointHomeConfig(2, 'FR_coxa', search_dir=-1,
                          stop_to_home_raw=100, placeholder=False)
    servo = FakeServo(start=1200, stop_at=1000, search_dir=-1)
    res = _make(servo).run_joint(cfg)
    assert res.outcome == Outcome.OK
    assert res.stop_pos_raw == 1000
    assert res.home_raw == 1100


def test_placeholder_skipped():
    cfg = JointHomeConfig(3, 'x', search_dir=+1, stop_to_home_raw=100)  # placeholder=True
    servo = FakeServo(start=0, stop_at=100, search_dir=+1)
    res = _make(servo).run_joint(cfg)
    assert res.outcome == Outcome.SKIPPED


def test_timeout_when_no_stop():
    cfg = JointHomeConfig(4, 'x', search_dir=+1,
                          stop_to_home_raw=100, placeholder=False)
    # stop_at far past full scale: clamp pins goal at 4095, never reaches load.
    servo = FakeServo(start=0, stop_at=999999, search_dir=+1)
    res = _make(servo, params=HardStopParams(timeout_s=0.5)).run_joint(cfg)
    assert res.outcome == Outcome.TIMEOUT


def test_abort():
    cfg = JointHomeConfig(5, 'x', search_dir=+1,
                          stop_to_home_raw=100, placeholder=False)
    servo = FakeServo(start=0, stop_at=4000, search_dir=+1)
    res = _make(servo, aborted=lambda: True).run_joint(cfg)
    assert res.outcome == Outcome.ABORTED


class CompliantStopServo(FakeServo):
    """Models a springy printed-PA6 stop: past `stop_at` the joint keeps
    creeping (compliance) and load rises only modestly — staying BELOW
    load_threshold. Pre-leash, the goal ran open-loop to the 0/4095 clamp
    while the gears ground against the spring."""

    def tick(self):
        delta = max(-self.step_follow, min(self.step_follow, self.goal - self.pos))
        nxt = self.pos + delta
        past = (self.search_dir > 0 and nxt >= self.stop_at) or \
               (self.search_dir < 0 and nxt <= self.stop_at)
        if past:
            # creep 1 raw/tick into the compliant stop, load sub-threshold
            self.pos += self.search_dir * 1
            self.load = 150
        else:
            self.pos = nxt
            self.load = 20


def test_compliant_stop_goal_error_is_bounded():
    cfg = JointHomeConfig(1, 'FL_knee', search_dir=+1,
                          stop_to_home_raw=100, placeholder=False)
    servo = CompliantStopServo(start=1000, stop_at=1200, search_dir=+1)
    params = HardStopParams(timeout_s=5.0)

    max_err = {'v': 0}
    orig_send = servo.send_goal

    def tracking_send(jid, raw):
        orig_send(jid, raw)
        max_err['v'] = max(max_err['v'], abs(raw - servo.pos))

    calib = HardStopCalibrator(
        read_position=servo.read_position, read_load=servo.read_load,
        send_goal=tracking_send, is_aborted=lambda: False,
        sleep_tick=servo.tick, params=params)
    res = calib.run_joint(cfg)

    # Semantically correct outcome for a sub-threshold compliant stop:
    # TIMEOUT ("check threshold/mechanics"), NOT silent grinding.
    assert res.outcome == Outcome.TIMEOUT
    # The real assertion: goal never ran away — position error (∝ torque)
    # stays bounded by the leash + one step.
    assert max_err['v'] <= params.leash_raw + params.step_raw, max_err['v']


def test_leash_does_not_break_normal_detection():
    cfg = JointHomeConfig(1, 'FL_coxa', search_dir=-1,
                          stop_to_home_raw=80, placeholder=False)
    servo = FakeServo(start=2000, stop_at=1800, search_dir=-1)
    calib = _make(servo)
    res = calib.run_joint(cfg)
    assert res.outcome == Outcome.OK
    assert res.stop_pos_raw == 1800


# ---- urdf_sign is OBSERVED by the sweep, not guessed ------------------------


def test_observed_urdf_sign_truth_table():
    """sign = search_dir * (+1 upper / -1 lower).

    Driving in search_dir reached the stop at that URDF end, so the two
    together give the raw-vs-URDF direction with no extra motion.
    """
    from nova_calibration.servo_homing.config import observed_urdf_sign

    assert observed_urdf_sign(+1, "upper") == +1  # raw up -> angle up
    assert observed_urdf_sign(+1, "lower") == -1  # raw up -> angle down
    assert observed_urdf_sign(-1, "upper") == -1
    assert observed_urdf_sign(-1, "lower") == +1


def test_observed_urdf_sign_rejects_nonsense():
    import pytest

    from nova_calibration.servo_homing.config import observed_urdf_sign

    with pytest.raises(ValueError, match="search_dir"):
        observed_urdf_sign(0, "upper")
    with pytest.raises(ValueError, match="stop_urdf_end"):
        observed_urdf_sign(+1, "middle")


def test_observed_sign_agrees_with_the_cad_derivation_for_every_joint():
    """The two independent routes to the same 12 bits must agree.

    Left side: the sweep's config (search_dir + which URDF end its stop is).
    Right side: derived_signs, from the measured servo convention composed
    with the CAD mount orientation. If a config entry is filled in a way that
    contradicts the derivation, that is either a wrong config or a wrong
    derivation -- either way it must not reach the command path silently.

    Skipped while every config entry is still a PLACEHOLDER: search_dir is a
    guess until measured from the leg CAD, so comparing it would assert on
    noise.
    """
    from nova_calibration.servo_homing.config import (
        JOINT_CONFIGS,
        observed_urdf_sign,
    )

    try:
        from nova_ops.safety_envelope.derived_signs import DERIVED_URDF_SIGN
    except ImportError:
        import pytest

        pytest.skip("nova_ops.derived_signs not on the path")

    checked = 0
    for jid, cfg in JOINT_CONFIGS.items():
        if cfg.placeholder:
            continue
        checked += 1
        assert observed_urdf_sign(cfg.search_dir, cfg.stop_urdf_end) == (
            DERIVED_URDF_SIGN[jid]
        ), (
            f"joint {jid} {cfg.name}: config implies "
            f"{observed_urdf_sign(cfg.search_dir, cfg.stop_urdf_end):+d}, "
            f"CAD derivation says {DERIVED_URDF_SIGN[jid]:+d}"
        )
    if checked == 0:
        import pytest

        pytest.skip("every JOINT_CONFIGS entry is still a placeholder")


def test_storage_persists_urdf_sign():
    """The command path's urdf_sign param had no producer at all before this."""
    from nova_calibration.servo_homing.hard_stop import HardStopResult, Outcome

    r = HardStopResult(joint_id=1, outcome=Outcome.OK)
    assert hasattr(r, "urdf_sign") and r.urdf_sign == 0  # 0 = not observed
    r.urdf_sign = -1
    assert r.urdf_sign == -1
