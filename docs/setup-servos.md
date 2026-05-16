# Feetech STS3215 Servo Bus — Setup

ID assignment, bus wiring, and bring-up. v1 scope: **12 active servos** (4 hip + 8 femur/tibia). IDs 13-18 reserved for Phase 4 arm install.

Bus master in v1 is the **Teensy 4.1 (Pattern B)** via 74HC125 half-duplex driver. FE-URT-1 (Pattern A) is the bench / debug fallback selected by `JP_BUS_MASTER` solder bridge on PCB v6.

## Bring-up sequence

1. **Pattern A temporary — ID assignment:** flip `JP_BUS_MASTER` to A. Power one servo at a time. Use Feetech FD on Windows (or SCServo SDK Python from Mac/Jetson via FE-URT-1) to assign unique IDs 1-12 per the labeling convention. Physically label each servo.
2. **Flip `JP_BUS_MASTER` back to B (default).** Boot Teensy with firmware loaded.
3. **Single-servo bring-up via Teensy:** subscribe to `/joint_states` from Jetson, publish a single `/joint_commands` entry. Verify position tracking + status reads.
4. **Continuity + ping-all:** connect remaining servos, unpowered continuity check, then powered ping-all via Teensy.
5. **Latency measurement:** ROS 2 → Teensy → bus → return at 100 Hz across all 12 servos. **Pass criterion: p99 <2 ms** (Phase 1 acceptance gate per BOM §12).

## Will cover
- Feetech FD debug software (Windows) — ID assignment workflow (Pattern A only)
- Physical labeling convention (IDs 1-4 hips, 5-12 femur/tibia, 13-18 reserved arm)
- Daisy-chain wiring + continuity check (unpowered)
- Voltage rail split: 12V hip (×4) on Pololu D42V110F12; femur/tibia (×8) on Pololu D42V110F7 (7.5V output, within STS3215 7.4V-rated 6-8.4V spec). Arm rail D42V55F7 reserved (Phase 4).
- Per-servo torque/return-delay/temperature limit tuning
- Failure-mode recovery (lost servo, address collision, overheat)
- Teensy firmware verification procedure + gait-loop p99 measurement

> **Status:** placeholder — populate during Phase 1 servo bring-up.
