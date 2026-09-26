#!/usr/bin/env python3
"""STS3215 step-response logger via FE-URT-1 (raw Feetech protocol, no SDK).

Commands a POSITION STEP and logs present position/speed/load vs time to CSV.
This is the actuator-model + domain-randomization capture for the MJX sim
(kp/kv, latency, torque-speed). Same wire protocol as set-servo-ids.py.

  # 1) find the servo + confirm it's centered (2048 at nominal pose)
  ./bench_step_response.py --port /dev/ttyUSB0 --id 1 --ping

  # 2) no-load step: hold from center, jump +60 deg, log 1.5 s
  ./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 60 \
      --out ../docs/bench/servo1_step60_noload.csv

  # 3) repeat with a known mass on a known lever (write it in --note)
  ./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 60 \
      --note "load=200g lever=80mm" --out ../docs/bench/servo1_step60_load200.csv

Do a few magnitudes (30/60/90 deg) x (no-load / one loaded). Keep the CSVs —
that's everything the sim needs to stop guessing actuator dynamics.

  # 4) sine tracking (#428 check 4): does position mode pass a 1.4-2 Hz gait?
  ./bench_step_response.py --port /dev/ttyUSB0 --id 1 --sine-hz 0.5,1,1.4,2,3 \
      --sine-amp-deg 15 --out ../docs/bench/servo1_sine15.csv

--sine-hz streams goals at --cmd-hz (100 Hz = the firmware's command rate) and,
per frequency, least-squares fits a sine to command and response. It prints the
amplitude ratio (profile model predicts ~0.45 at 1.4-2 Hz, a plain position
servo ~0.87), the lag, and — when the servo is accel-limited (ratio < 0.9) —
an estimate of that ceiling: a bang-bang accel a gives a fundamental of
(4/pi) a / w^2, so a ~= A_out * w^2 * pi/4. Checked against a fake servo
limited at 7.5 rad/s^2: 7.5-7.9 at 1.4-2 Hz with >= 8 cycles; poor at 3 Hz,
where the motion is too small to fit.

--acc N writes GOAL_ACC (0x29, 100 steps/s^2 per count) and --torque-limit N
writes TORQUE_LIMIT (0x30, 0-1000) before the run (#428 checks 2-3). Both are
SRAM: the script restores the previous value after, and a power cycle does too.

STS3215 regs: TorqueEnable 0x28 · Acc 0x29 · GoalPos 0x2A(2B LE) · TorqueLimit
0x30 · PresentPos 0x38 · Speed 0x3A · Load 0x3C (each 2B LE). Speed sign is
bit 15. Load is the motor PWM DUTY in 0.1 % (Feetech memory table: "voltage
duty cycle"), sign in bit 10, NOT torque. 4096 cnt/rev.
"""
import argparse
import csv
import math
import sys
import time

import serial  # pyserial

CNT_PER_REV = 4096
DEG_PER_CNT = 360.0 / CNT_PER_REV
REG_TORQUE, REG_ACC, REG_GOAL, REG_TLIMIT, REG_PRESENT = 0x28, 0x29, 0x2A, 0x30, 0x38


def checksum(payload):
    return (~sum(payload)) & 0xFF


def frame(sid, instr, params=b""):
    body = bytes([sid, len(params) + 2, instr]) + bytes(params)
    return b"\xff\xff" + body + bytes([checksum(body)])


def transact(ser, out, resp_len):
    ser.reset_input_buffer()
    ser.write(out)
    ser.flush()
    return ser.read(resp_len)


def ping(ser, sid):
    r = transact(ser, frame(sid, 0x01), 6)
    return len(r) == 6 and r[2] == sid


def write_reg(ser, sid, reg, data):
    r = transact(ser, frame(sid, 0x03, bytes([reg]) + bytes(data)), 6)
    return len(r) == 6 and r[4] == 0


def read_bytes(ser, sid, reg, n):
    r = transact(ser, frame(sid, 0x02, bytes([reg, n])), 6 + n)
    if len(r) != 6 + n or r[2] != sid:
        return None
    return r[5:5 + n]


def signed15(v):
    return -(v & 0x7FFF) if v & 0x8000 else v


def signed10(v):
    """Present load: magnitude in bits 0-9, direction in bit 10 (Feetech SDK
    ReadLoad). signed15 read 0x0432 (-50) as +1074 — the '1048 raw @ 0.11 N·m'
    anchor in docs/bench/README.md was the direction bit, not load."""
    return -(v & 0x3FF) if v & 0x400 else (v & 0x3FF)


def fit_sine(ts, ys, hz):
    """Least-squares y = a sin(wt) + b cos(wt) + c at a known frequency.
    Returns (amplitude, phase_rad). Pure Python so CI needs no numpy."""
    w = 2 * math.pi * hz
    rows = [(math.sin(w * t), math.cos(w * t), 1.0) for t in ts]
    m = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    v = [sum(r[i] * y for r, y in zip(rows, ys)) for i in range(3)]
    a, b, _ = _solve3(m, v)
    return math.hypot(a, b), math.atan2(b, a)


def _solve3(m, v):
    """Gaussian elimination with partial pivoting, 3x3."""
    m = [row[:] + [x] for row, x in zip(m, v)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, 3):
            f = m[r][c] / m[c][c]
            m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    out = [0.0] * 3
    for r in (2, 1, 0):
        out[r] = (m[r][3] - sum(m[r][k] * out[k] for k in range(r + 1, 3))) / m[r][r]
    return out


def tracking(ts, cmd, pos, hz):
    """(amplitude ratio, lag_ms, accel-ceiling estimate rad/s^2 or None).
    The estimate assumes bang-bang accel (fundamental = (4/pi) a / w^2), so it
    is only reported when the servo is clearly clipping (ratio < 0.9)."""
    a_cmd, ph_cmd = fit_sine(ts, cmd, hz)
    a_pos, ph_pos = fit_sine(ts, pos, hz)
    lag = (ph_cmd - ph_pos) % (2 * math.pi)
    a_out_rad = a_pos * 2 * math.pi / CNT_PER_REV
    ratio = a_pos / a_cmd
    a_est = a_out_rad * (2 * math.pi * hz) ** 2 * math.pi / 4 if ratio < 0.9 else None
    return ratio, lag / (2 * math.pi * hz) * 1000.0, a_est


def read_state(ser, sid):
    """(present_pos, speed, load) raw counts, or None."""
    b = read_bytes(ser, sid, REG_PRESENT, 6)
    if b is None:
        return None
    pos = b[0] | (b[1] << 8)
    spd = signed15(b[2] | (b[3] << 8))
    load = signed10(b[4] | (b[5] << 8))
    return pos, spd, load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=1000000)
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--ping", action="store_true", help="ping + print state, exit")
    ap.add_argument("--step-deg", type=float, default=60.0,
                    help="step size from CURRENT position (deg)")
    ap.add_argument("--dur", type=float, default=1.5, help="log duration (s)")
    ap.add_argument("--pre", type=float, default=0.2,
                    help="baseline log BEFORE the step (s)")
    ap.add_argument("--out", default="step_response.csv")
    ap.add_argument("--note", default="", help="load/lever/temp — goes in the CSV header")
    ap.add_argument("--sine-hz", default="",
                    help="comma list of frequencies: run sine tracking instead of a step")
    ap.add_argument("--sine-amp-deg", type=float, default=15.0)
    ap.add_argument("--cycles", type=int, default=10,
                    help="cycles per frequency; the first 3 are discarded (transient)")
    ap.add_argument("--cmd-hz", type=float, default=100.0,
                    help="goal write rate (firmware SYNC_WRITE rate is 100 Hz)")
    ap.add_argument("--acc", type=int, help="write GOAL_ACC 0x29 (0-254) first")
    ap.add_argument("--torque-limit", type=int, help="write TORQUE_LIMIT 0x30 (0-1000) first")
    a = ap.parse_args()

    ser = serial.Serial(a.port, a.baud, timeout=0.02)

    if not ping(ser, a.id):
        sys.exit(f"no response from ID {a.id} on {a.port}")
    st = read_state(ser, a.id)
    print(f"ID {a.id} present pos={st[0]} ({st[0]*DEG_PER_CNT:.1f} deg) "
          f"speed={st[1]} load={st[2]}")
    if a.ping:
        return

    restore = apply_limits(ser, a)
    try:
        if a.sine_hz:
            run_sine(ser, a, st[0])
        else:
            run_step(ser, a, st[0])
    finally:
        for reg, data in restore:
            write_reg(ser, a.id, reg, data)


def apply_limits(ser, a):
    """Write --acc / --torque-limit; return [(reg, old_bytes)] to put back."""
    restore = []
    for val, reg, n in ((a.acc, REG_ACC, 1), (a.torque_limit, REG_TLIMIT, 2)):
        if val is None:
            continue
        old = read_bytes(ser, a.id, reg, n)
        if old is None:
            sys.exit(f"could not read reg 0x{reg:02X} before writing it")
        data = bytes([val]) if n == 1 else bytes([val & 0xFF, (val >> 8) & 0xFF])
        if not write_reg(ser, a.id, reg, data):
            sys.exit(f"write reg 0x{reg:02X}={val} failed")
        restore.append((reg, bytes(old)))
        print(f"reg 0x{reg:02X}: {int.from_bytes(bytes(old), 'little')} -> {val} (restored after)")
    return restore


def run_sine(ser, a, center):
    """Stream center + A sin(2 pi f t) at cmd_hz; log and fit each frequency."""
    amp = a.sine_amp_deg / DEG_PER_CNT
    if center - amp < 0 or center + amp > CNT_PER_REV - 1:
        sys.exit("sine would cross the encoder wrap; re-center the servo (--center in set-servo-ids.py)")
    write_reg(ser, a.id, REG_TORQUE, bytes([1]))
    hdr = (f"# servo_id={a.id} center={center} amp_deg={a.sine_amp_deg} cmd_hz={a.cmd_hz} "
           f"acc={a.acc} torque_limit={a.torque_limit} note={a.note!r}")
    print("  hz   ratio   lag_ms   accel_ceiling_est_rad/s2")
    for hz in (float(x) for x in a.sine_hz.split(",")):
        rows, t0, next_cmd, goal = [], time.perf_counter(), 0.0, center
        dur = a.cycles / hz
        while (t := time.perf_counter() - t0) < dur:
            if t >= next_cmd:
                goal = int(round(center + amp * math.sin(2 * math.pi * hz * t)))
                write_reg(ser, a.id, REG_GOAL, bytes([goal & 0xFF, (goal >> 8) & 0xFF]))
                next_cmd += 1.0 / a.cmd_hz
            s = read_state(ser, a.id)
            if s is not None:
                rows.append((t, goal, s[0], s[1], s[2]))
        keep = [r for r in rows if r[0] >= 3.0 / hz]
        ratio, lag_ms, acc = tracking([r[0] for r in keep], [r[1] for r in keep],
                                      [r[2] for r in keep], hz)
        acc_s = f"{acc:6.2f}" if acc is not None else "     - (tracking)"
        print(f"  {hz:4.1f}  {ratio:5.2f}  {lag_ms:7.1f}   {acc_s}")
        out = a.out.replace(".csv", f"_{hz:g}hz.csv")
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([hdr + f" hz={hz} ratio={ratio:.3f} lag_ms={lag_ms:.1f} accel_est={acc}"])
            w.writerow(["t_s", "cmd_cnt", "pos_cnt", "speed_raw", "load_duty_permille"])
            w.writerows((f"{r[0]:.4f}",) + r[1:] for r in rows)
        # return to center between frequencies so each starts from rest
        write_reg(ser, a.id, REG_GOAL, bytes([center & 0xFF, (center >> 8) & 0xFF]))
        time.sleep(1.0)
    print(f"  wrote {a.out.replace('.csv', '_<hz>hz.csv')}")


def run_step(ser, a, start_pos):
    goal = int(round(start_pos + a.step_deg / DEG_PER_CNT))
    goal = max(0, min(CNT_PER_REV - 1, goal))
    print(f"step: {start_pos} -> {goal} ({a.step_deg:+.0f} deg). "
          f"torque ON, logging {a.pre}s pre + {a.dur}s post to {a.out}")

    # torque enable
    write_reg(ser, a.id, REG_TORQUE, bytes([1]))

    rows = []
    t0 = time.perf_counter()
    stepped = False
    step_t = None
    while True:
        t = time.perf_counter() - t0
        if not stepped and t >= a.pre:
            write_reg(ser, a.id, REG_GOAL, bytes([goal & 0xFF, (goal >> 8) & 0xFF]))
            step_t = time.perf_counter() - t0
            stepped = True
        s = read_state(ser, a.id)
        if s is not None:
            rows.append((f"{t:.4f}", goal if stepped else start_pos,
                         s[0], s[1], s[2]))
        if t >= a.pre + a.dur:
            break

    # first sample that reaches within 1% of the commanded step = settle proxy
    band = abs(goal - start_pos) * 0.02
    settle = next((float(r[0]) for r in rows
                   if r[1] == goal and abs(r[2] - goal) <= band), None)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# servo_id={a.id} start={start_pos} goal={goal} "
                    f"step_deg={a.step_deg} step_t={step_t:.4f}s "
                    f"cnt_per_rev={CNT_PER_REV} note={a.note!r}"])
        w.writerow(["t_s", "cmd_cnt", "pos_cnt", "speed_raw", "load_duty_permille"])
        w.writerows(rows)
    n = len(rows)
    rate = n / (rows[-1] and float(rows[-1][0]) or 1)
    print(f"wrote {n} samples (~{rate:.0f} Hz) to {a.out}")
    if settle is not None:
        print(f"  ~settle (within 2%) at {settle - step_t:.3f}s after step")
    print("  -> repeat for step 30/90 deg and with a known load; keep all CSVs.")


if __name__ == "__main__":
    main()
