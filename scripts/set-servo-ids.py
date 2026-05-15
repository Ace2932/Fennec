#!/usr/bin/env python3
"""
set-servo-ids.py

Assign unique bus IDs to Feetech STS3215 servos one at a time via FE-URT-1.

STATUS: stub. Populate once the SCServo SDK is installed on the Jetson and
a single servo has been ID-walked manually with Feetech FD on Windows for
ground-truth comparison.

Planned workflow:
  1. Connect ONE servo at a time to the FE-URT-1 (factory default ID=1).
  2. Run: ./set-servo-ids.py --port /dev/ttyUSB0 --new-id <N>
  3. Script writes the new ID to EEPROM, then verifies by ping.
  4. Repeat for IDs 1-18 with physical labels applied between each.

ID plan:
   1- 4: hips (12V / 30kg)
   5-12: femur + tibia (7.4V / 19kg)
  13-18: arm (7.4V / 19kg, carried from SO-ARM101)
"""

import sys


def main() -> int:
    print("[set-servo-ids.py] stub — not yet implemented")
    print("  see docs/setup-servos.md for the manual procedure (Feetech FD)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
