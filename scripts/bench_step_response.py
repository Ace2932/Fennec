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

STS3215 regs: TorqueEnable 0x28 · GoalPos 0x2A(2B LE) · PresentPos 0x38 ·
Speed 0x3A · Load 0x3C (each 2B LE, speed/load sign in bit15). 4096 cnt/rev.
"""
import argparse
import csv
import sys
import time

import serial  # pyserial

CNT_PER_REV = 4096
DEG_PER_CNT = 360.0 / CNT_PER_REV
REG_TORQUE, REG_GOAL, REG_PRESENT = 0x28, 0x2A, 0x38


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


def read_state(ser, sid):
    """(present_pos, speed, load) raw counts, or None."""
    b = read_bytes(ser, sid, REG_PRESENT, 6)
    if b is None:
        return None
    pos = b[0] | (b[1] << 8)
    spd = signed15(b[2] | (b[3] << 8))
    load = signed15(b[4] | (b[5] << 8))
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
    a = ap.parse_args()

    ser = serial.Serial(a.port, a.baud, timeout=0.02)

    if not ping(ser, a.id):
        sys.exit(f"no response from ID {a.id} on {a.port}")
    st = read_state(ser, a.id)
    print(f"ID {a.id} present pos={st[0]} ({st[0]*DEG_PER_CNT:.1f} deg) "
          f"speed={st[1]} load={st[2]}")
    if a.ping:
        return

    start_pos = st[0]
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
        w.writerow(["t_s", "cmd_cnt", "pos_cnt", "speed_raw", "load_raw"])
        w.writerows(rows)
    n = len(rows)
    rate = n / (rows[-1] and float(rows[-1][0]) or 1)
    print(f"wrote {n} samples (~{rate:.0f} Hz) to {a.out}")
    if settle is not None:
        print(f"  ~settle (within 2%) at {settle - step_t:.3f}s after step")
    print("  -> repeat for step 30/90 deg and with a known load; keep all CSVs.")


if __name__ == "__main__":
    main()
