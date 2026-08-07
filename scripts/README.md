# Scripts

Bring-up + maintenance helpers.

## Setup

`proj/.venv/bin/pip install -r scripts/requirements.txt` (pyserial, PyYAML —
see that file for why each is here).

## Files
- `flash-jetpack.sh` — JetPack 6.x microSD flash helper (stub)
- `set-servo-ids.py` — Feetech STS3215 bus-ID assignment via FE-URT-1.
  Protocol (checksum/frame/parse) is tested against mocks + the C++
  reference (`firmware/teensy/firmware/src/feetech_protocol.h`) in
  `test_set_servo_ids.py` — run with `.venv/bin/python -m pytest
  scripts/test_set_servo_ids.py`. Still bench-unproven: no real STS3215 has
  talked to it over an actual FE-URT-1 yet. Walkthrough in
  `docs/setup-servos.md`.

Each script is a stub until the corresponding hardware step has been
walked through manually at least once. Codifying happens after the
procedure works by hand — not before.
