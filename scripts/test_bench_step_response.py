"""Tests for bench_step_response.py: the sine fit, the load decode, and an
end-to-end sine run against a fake accel-limited servo (#428 check 4), so the
capture is known to work before it meets hardware.

Run: .venv/bin/python -m pytest scripts/test_bench_step_response.py -q
"""
import importlib.util
import math
import os
import types

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "bench_step_response", os.path.join(_HERE, "bench_step_response.py")
)
bsr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsr)

CNT_PER_RAD = bsr.CNT_PER_REV / (2 * math.pi)


def test_fit_sine_recovers_amplitude_and_phase():
    ts = [i / 500 for i in range(2000)]
    ys = [100 + 37.0 * math.sin(2 * math.pi * 2.0 * t + 0.6) for t in ts]
    amp, ph = bsr.fit_sine(ts, ys, 2.0)
    assert amp == pytest.approx(37.0, abs=1e-6)
    assert ph == pytest.approx(0.6, abs=1e-6)


def test_tracking_reports_ratio_lag_and_accel():
    hz, ts = 1.5, [i / 400 for i in range(1600)]
    cmd = [2048 + 170 * math.sin(2 * math.pi * hz * t) for t in ts]
    pos = [2048 + 85 * math.sin(2 * math.pi * hz * (t - 0.040)) for t in ts]  # half, 40 ms late
    ratio, lag_ms, acc = bsr.tracking(ts, cmd, pos, hz)
    assert ratio == pytest.approx(0.5, abs=1e-6)
    assert lag_ms == pytest.approx(40.0, abs=1e-3)
    assert acc == pytest.approx(85 / CNT_PER_RAD * (2 * math.pi * hz) ** 2 * math.pi / 4, rel=1e-6)


def test_tracking_reports_no_accel_estimate_when_it_tracks():
    hz, ts = 0.5, [i / 400 for i in range(1600)]
    cmd = [2048 + 170 * math.sin(2 * math.pi * hz * t) for t in ts]
    assert bsr.tracking(ts, cmd, cmd, hz)[2] is None


@pytest.mark.parametrize("raw,val", [(0x0032, 50), (0x0432, -50), (0x03E8, 1000), (0x07E8, -1000)])
def test_signed10_load_direction_is_bit_10(raw, val):
    assert bsr.signed10(raw) == val


class FakeAccelServo:
    """Speaks the Feetech frames the script sends; moves toward the goal under a
    hard acceleration limit (the STS3215 position-mode profile, ~7.5 rad/s^2)."""

    def __init__(self, sid, clock, a_max=7.5):
        self.sid, self.clock = sid, clock
        self.a = a_max * CNT_PER_RAD
        self.pos, self.vel, self.goal, self.t = 2048.0, 0.0, 2048, clock()
        self.regs = {bsr.REG_ACC: 0, bsr.REG_TLIMIT: 1000}
        self._resp = b""

    def _advance(self):
        now = self.clock()
        dt, self.t = now - self.t, now
        e = self.goal - self.pos
        v_want = math.copysign(math.sqrt(2 * self.a * abs(e)), e)
        dv = max(-self.a * dt, min(self.a * dt, v_want - self.vel))
        self.vel += dv
        self.pos += self.vel * dt

    def _reply(self, data=b""):
        body = bytes([self.sid, len(data) + 2, 0]) + bytes(data)
        self._resp = b"\xff\xff" + body + bytes([bsr.checksum(body)])

    def reset_input_buffer(self):
        pass

    def flush(self):
        pass

    def write(self, out):
        self._advance()
        instr, params = out[4], out[5:-1]
        if instr == 0x01:
            self._reply()
        elif instr == 0x03:
            reg, data = params[0], params[1:]
            if reg == bsr.REG_GOAL:
                self.goal = data[0] | (data[1] << 8)
            else:
                self.regs[reg] = int.from_bytes(data, "little")
            self._reply()
        elif instr == 0x02:
            reg, n = params
            if reg == bsr.REG_PRESENT:
                p = int(round(self.pos)) & 0xFFFF
                self._reply(bytes([p & 0xFF, p >> 8, 0, 0, 0, 0]))
            else:
                self._reply(self.regs.get(reg, 0).to_bytes(n, "little"))

    def read(self, n):
        r, self._resp = self._resp, b""
        return r


class Clock:
    """Simulated clock: each serial transaction costs 1 ms, sleep() is instant."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.001
        return self.t

    def sleep(self, s):
        self.t += s


def _run_sine(monkeypatch, tmp_path, hz_list):
    clock = Clock()
    monkeypatch.setattr(bsr.time, "perf_counter", clock)
    monkeypatch.setattr(bsr.time, "sleep", clock.sleep)
    servo = FakeAccelServo(1, clock)
    args = types.SimpleNamespace(id=1, sine_hz=hz_list, sine_amp_deg=15.0, cycles=10,
                                 cmd_hz=100.0, acc=None, torque_limit=None, note="",
                                 out=str(tmp_path / "sine.csv"))
    bsr.run_sine(servo, args, 2048)
    return servo


def test_sine_run_shows_the_accel_ceiling(monkeypatch, tmp_path, capsys):
    _run_sine(monkeypatch, tmp_path, "0.5,1.4,2")
    rows = [line.split() for line in capsys.readouterr().out.splitlines()
            if line.strip()[:1].isdigit()]
    by_hz = {float(r[0]): r for r in rows}
    assert float(by_hz[0.5][1]) > 0.9      # 0.5 Hz needs ~2.6 rad/s^2: tracks
    assert float(by_hz[1.4][1]) == pytest.approx(0.45, abs=0.08)  # the sim's profile prediction
    assert float(by_hz[2.0][1]) < 0.35     # 2 Hz needs ~41 rad/s^2: clipped
    for hz in (1.4, 2.0):                  # the estimate recovers the fake's 7.5 ceiling
        assert float(by_hz[hz][3]) == pytest.approx(7.5, rel=0.1)
    assert (tmp_path / "sine_2hz.csv").exists()


def test_limits_are_written_then_restored(monkeypatch, tmp_path):
    clock = Clock()
    monkeypatch.setattr(bsr.time, "perf_counter", clock)
    servo = FakeAccelServo(1, clock)
    a = types.SimpleNamespace(id=1, acc=50, torque_limit=600)
    restore = bsr.apply_limits(servo, a)
    assert servo.regs[bsr.REG_ACC] == 50 and servo.regs[bsr.REG_TLIMIT] == 600
    for reg, data in restore:
        bsr.write_reg(servo, 1, reg, data)
    assert servo.regs[bsr.REG_ACC] == 0 and servo.regs[bsr.REG_TLIMIT] == 1000
