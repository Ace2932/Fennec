#!/usr/bin/env python3
"""Assembly-time STS3215 tool via FE-URT-1 (raw Feetech protocol, no SDK).

  ./set-servo-ids.py --port /dev/ttyUSB0 --ping 1
  ./set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 7
  ./set-servo-ids.py --port /dev/ttyUSB0 --center 7   # one-key MID calibrate
  ./set-servo-ids.py --port /dev/ttyUSB0 --verify-fleet

--center writes 128 to reg 0x28 (torque-enable) = Feetech one-key
calibration: CURRENT position becomes 2048. Run it with the joint held at
its NOMINAL pose during assembly — the +/-126deg mechanical ROM then spans
614..3482 counts and never crosses the 4095<->0 encoder wrap (wrap makes
present-position jump mid-motion; classic bus-servo field failure).

ID plan = PER-LEG SEQUENTIAL, loaded from joint_id_map.yaml (canonical,
2026-06-27) — see --verify-fleet, which pings every ID that file declares:
  FL haa/hfe/kfe = 1-3 · FR = 4-6 · RL = 7-9 · RR = 10-12 · arm 13-18.
  Hips (haa) are IDs 1,4,7,10 — NOT a contiguous 1-4 block.

⚠️  --old-id/--new-id must run ONE SERVO AT A TIME on the bus. Every fresh
STS3215 answers to the factory default ID 1; with more than one servo
connected, a broadcast/ping to ID 1 collides and the response is garbage.
"""
import argparse
import os
import sys

import serial  # pyserial
import yaml

JOINT_ID_MAP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "ros2_ws", "src", "nova_description", "config", "joint_id_map.yaml",
)


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


def _valid_status(r, sid):
    """Structurally validate a fixed-size (no-payload) status response:
    FF FF id len err checksum. Mirrors feetech_protocol.h's parse_response()
    checksum check — a corrupted frame with a coincidentally-right length/id
    must not read as a real response. Returns the err byte on success, or
    None if the frame is malformed/corrupt."""
    if len(r) != 6 or r[2] != sid:
        return None
    body = bytes(r[2:5])  # id, len, err
    if r[5] != checksum(body):
        return None
    return r[4]


def ping(ser, sid):
    r = transact(ser, frame(sid, 0x01), 6)
    return _valid_status(r, sid) is not None


def write_reg(ser, sid, reg, data):
    r = transact(ser, frame(sid, 0x03, bytes([reg]) + bytes(data)), 6)
    err = _valid_status(r, sid)
    return err == 0  # err byte clear


def load_joint_id_map(path=JOINT_ID_MAP_PATH):
    """{joint_name: bus_id} from the canonical yaml. Never hand-list the 12
    IDs here — that's exactly the drift joint_map.py was written to kill."""
    with open(path) as f:
        doc = yaml.safe_load(f)
    return doc["joint_id_map"]


def verify_fleet(ser, expected):
    """Ping every ID joint_id_map.yaml declares, plus scan 1..20 for IDs that
    answer but aren't expected. Returns True iff the fleet matches exactly."""
    present = {sid: ping(ser, sid) for sid in range(1, 21)}

    print(f"{'joint':<10} {'id':>3}  status")
    all_ok = True
    for name, sid in sorted(expected.items(), key=lambda kv: kv[1]):
        ok = present[sid]
        print(f"{name:<10} {sid:>3}  {'present' if ok else 'MISSING'}")
        all_ok &= ok

    unexpected = [sid for sid, ok in present.items() if ok and sid not in expected.values()]
    for sid in unexpected:
        print(f"{'?':<10} {sid:>3}  UNEXPECTED (not in joint_id_map.yaml)")
        all_ok = False

    return all_ok


def reassign_id(ser, old_id, new_id):
    """Move a servo from old_id to new_id, EEPROM-locked. Returns True only
    if every step (unlock, ID write, lock, re-ping) succeeded — a failed
    lock write must not report success (#287): the new ID would then be
    unpersisted and can silently revert to old_id on power-cycle."""
    print("WARNING: one servo on the bus at a time — every fresh STS3215 "
          "answers to factory ID 1, and a second one collides with it.")
    if not ping(ser, old_id):
        print(f"servo {old_id} not responding")
        return False
    unlock_ok = write_reg(ser, old_id, 0x37, [0])   # EEPROM unlock
    id_ok = write_reg(ser, old_id, 0x05, [new_id])  # REG_ID
    lock_ok = write_reg(ser, new_id, 0x37, [1])     # lock
    if not lock_ok:
        print(f"ERROR: EEPROM lock write on ID {new_id} FAILED — "
              f"the new ID is NOT persisted and can revert to "
              f"{old_id} on the next power-cycle.")
    ok = unlock_ok and id_ok and lock_ok and ping(ser, new_id)
    print(f"ID {old_id} -> {new_id}: {'OK' if ok else 'FAILED'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=1000000)
    ap.add_argument("--ping", type=int)
    ap.add_argument("--old-id", type=int)
    ap.add_argument("--new-id", type=int)
    ap.add_argument("--center", type=int, metavar="ID",
                    help="one-key mid calibration at the CURRENT pose")
    ap.add_argument("--verify-fleet", action="store_true",
                    help="ping every ID in joint_id_map.yaml + flag unexpected IDs")
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

    if a.verify_fleet:
        expected = load_joint_id_map()
        ok = verify_fleet(ser, expected)
        print(f"fleet verify: {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1

    if a.old_id is not None and a.new_id is not None:
        ok = reassign_id(ser, a.old_id, a.new_id)
        return 0 if ok else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
