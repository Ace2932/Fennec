# Feetech STS3215 Servo Bus — Setup

ID assignment, bus wiring, and bring-up. v1 scope: **12 active servos** (4 hip + 8 femur/tibia). IDs 13-18 reserved for Phase 4 arm install.

Bus master in v1 is the **Teensy 4.1 (Pattern B)** via SN74LVC125A half-duplex driver (5V-tolerant; NOT the original 74HC125). FE-URT-1 (Pattern A) is the bench / debug fallback selected by `JP_BUS_MASTER` solder bridge on PCB v6.

## Bring-up sequence

1. **ID assignment (pre-PCB or post-PCB), via `scripts/set-servo-ids.py`:**
   `scripts/set-servo-ids.py` speaks raw Feetech protocol directly (no
   Feetech FD, no SCServo SDK) — byte-correct against
   `firmware/teensy/firmware/src/feetech_protocol.h`, unit-tested in
   `scripts/test_set_servo_ids.py`. Install its one dependency first:
   `proj/.venv/bin/pip install -r scripts/requirements.txt`.

   - **Pre-PCB (Week 1-2, recommended):** wire FE-URT-1 directly to one
     servo at a time on the bench (no PCB needed). Do this while waiting
     for PCB v6 to arrive.
   - **Post-PCB (alternative):** if PCB is already in hand, flip
     `JP_BUS_MASTER` to A and use the same FE-URT-1 path through the
     PCB's bus pads.
   Either way: ID setup uses Pattern A's hardware path, **one servo
   connected at a time** — every fresh STS3215 answers to factory ID 1,
   and a second servo on the bus collides with it. The script prints this
   warning itself at the start of every ID-assignment run.

   Walk all 12 IDs in `joint_id_map.yaml` order (FL haa/hfe/kfe = 1-3,
   FR = 4-6, RL = 7-9, RR = 10-12). For each servo: connect it alone,
   confirm it's on factory ID 1, assign, confirm, disconnect, connect the
   next one:
   ```
   # FL_haa (target ID 1) — first servo off the factory line needs no
   # reassignment, but verify + label it:
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --ping 1

   # FL_hfe (target ID 2) — connect only this servo, still on factory ID 1:
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 2
   # label the servo "FL_hfe / ID 2", disconnect, connect the next one

   # FL_kfe (target ID 3):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 3

   # FR_haa (target ID 4):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 4

   # FR_hfe (target ID 5):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 5

   # FR_kfe (target ID 6):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 6

   # RL_haa (target ID 7):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 7

   # RL_hfe (target ID 8):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 8

   # RL_kfe (target ID 9):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 9

   # RR_haa (target ID 10):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 10

   # RR_hfe (target ID 11):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 11

   # RR_kfe (target ID 12):
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --old-id 1 --new-id 12
   ```
   If any run prints `ERROR: EEPROM lock write ... FAILED`, that servo's ID
   is live but unpersisted — it can silently revert to the old ID on the
   next power-cycle. Re-run the same `--old-id`/`--new-id` command before
   moving on; do not proceed to the next servo with a failed lock.

   Finally, with all 12 servos daisy-chained on the bus, confirm the whole
   fleet matches `joint_id_map.yaml` in one shot:
   ```
   proj/.venv/bin/python scripts/set-servo-ids.py --port /dev/ttyUSB0 --verify-fleet
   ```
   This prints a table of every expected joint/ID and whether it answered,
   flags any unexpected ID that responds (1-20) but isn't in the map, and
   exits nonzero on any mismatch.

2. **Flip `JP_BUS_MASTER` back to B (default).** Boot Teensy with firmware loaded.
3. **Single-servo bring-up via Teensy:** subscribe to `/joint_states` from Jetson, publish a single `/joint_commands` entry. Verify position tracking + status reads.
4. **Continuity + ping-all:** connect remaining servos, unpowered continuity check, then powered ping-all via Teensy.
5. **Acceptance gate** (per BOM §12 step 3): Teensy loop tick jitter p99 <100 µs + `/joint_commands` arrival rate ≥99% of 100 Hz target + RTT median <5 ms / p99 <20 ms (sanity). The first two are mandatory; RTT is Linux-bounded so don't gate on it.

## Will cover
- ID convention = **PER-LEG SEQUENTIAL** (decided 2026-06-27, `joint_id_map.yaml`, the canonical source `scripts/set-servo-ids.py --verify-fleet` reads): FL haa/hfe/kfe = 1-3, FR = 4-6, RL = 7-9, RR = 10-12. Assign IDs walking the chain leg-by-leg. Hips (haa) = IDs 1,4,7,10 on the 12V rail; hfe/kfe = 7.5V. 13-18 reserved arm.
- Daisy-chain wiring + continuity check (unpowered)
- Voltage rail split: 12V hip (×4) on Pololu D42V110F12; femur/tibia (×8) on Pololu D42V110F7 (7.5V output, within STS3215 7.4V-rated 6-8.4V spec). Arm rail D42V55F7 reserved (Phase 4).
- Per-servo torque/return-delay/temperature limit tuning
- Failure-mode recovery (lost servo, address collision, overheat)
- Teensy firmware verification procedure + gait-loop p99 measurement

> **Status:** the ID-assignment section above is written against
> `scripts/set-servo-ids.py` and is bench-unproven (protocol tested against
> mocks + the firmware's C++ reference, no real STS3215 run yet). Everything
> else below step 1 — per-servo tuning, failure-mode recovery, and the
> Teensy verification procedure — remains a placeholder pending Phase 1
> bring-up.
