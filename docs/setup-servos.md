# Feetech STS3215 Servo Bus — Setup

ID assignment, bus wiring, and bring-up. v1 scope: **12 active servos** (4 hip + 8 femur/tibia). IDs 13-18 reserved for Phase 4 arm install.

## Will cover
- Feetech FD debug software (Windows) — ID assignment workflow
- Physical labeling convention (IDs 1-4 hips, 5-12 femur/tibia, 13-18 reserved arm)
- Single-servo bench test via FE-URT-1 → Jetson (SCServo SDK Python)
- Daisy-chain wiring + continuity check (unpowered)
- Full 12-servo ping-all (powered) for v1; expand to 18 in Phase 4a
- Voltage rail split: 12V hip (×4) on Pololu D42V110F12; 7.4V femur/tibia (×8) on Pololu D42V110F7. Arm rail D42V55F7 reserved.
- Per-servo torque/return-delay/temperature limit tuning
- Failure-mode recovery (lost servo, address collision, overheat)
- Gait-loop p99 latency measurement procedure → resolves Pattern A vs Pattern B

> **Status:** placeholder — populate during Phase 1 servo bring-up.
