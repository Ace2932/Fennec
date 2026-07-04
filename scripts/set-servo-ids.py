#!/usr/bin/env python3
"""Assembly-time STS3215 tool via FE-URT-1 (raw Feetech protocol, no SDK).

  ./set-servo-ids.py --port /dev/ttyUSB0 --ping 1
  ./set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 7
  ./set-servo-ids.py --port /dev/ttyUSB0 --center 7   # one-key MID calibrate

--center writes 128 to reg 0x28 (torque-enable) = Feetech one-key
calibration: CURRENT position becomes 2048. Run it with the joint held at
its NOMINAL pose during assembly — the +/-126deg mechanical ROM then spans
614..3482 counts and never crosses the 4095<->0 encoder wrap (wrap makes
present-position jump mid-motion; classic bus-servo field failure).

ID plan = PER-LEG SEQUENTIAL (joint_id_map.yaml, 2026-06-27):
  FL haa/hfe/kfe = 1-3 · FR = 4-6 · RL = 7-9 · RR = 10-12 · arm 13-18.
  Hips (haa) are IDs 1,4,7,10 — NOT a contiguous 1-4 block.
"""
import argparse
import sys

import serial  # pyserial


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
    return len(r) == 6 and r[4] == 0  # err byte clear


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=1000000)
    ap.add_argument("--ping", type=int)
    ap.add_argument("--old-id", type=int)
    ap.add_argument("--new-id", type=int)
    ap.add_argument("--center", type=int, metavar="ID",
                    help="one-key mid calibration at the CURRENT pose")
    a = ap.parse_args()
    ser = serial.Serial(a.port, a.baud, timeout=0.05)

    if a.ping is not None:
        ok = ping(ser, a.ping)
        print(f"ping {a.ping}: {'OK' if ok else 'no response'}")
        return 0 if ok else 1

    if a.center is not None:
        if not ping(ser, a.center):
            print(f"servo {a.center} not responding"); return 1
        ok = write_reg(ser, a.center, 0x28, [128])
        print(f"center {a.center}: {'position set to 2048' if ok else 'FAILED'}")
        return 0 if ok else 1

    if a.old_id is not None and a.new_id is not None:
        if not ping(ser, a.old_id):
            print(f"servo {a.old_id} not responding"); return 1
        write_reg(ser, a.old_id, 0x37, [0])            # EEPROM unlock
        ok = write_reg(ser, a.old_id, 0x05, [a.new_id])  # REG_ID
        write_reg(ser, a.new_id, 0x37, [1])            # lock
        ok = ok and ping(ser, a.new_id)
        print(f"ID {a.old_id} -> {a.new_id}: {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
