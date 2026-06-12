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
