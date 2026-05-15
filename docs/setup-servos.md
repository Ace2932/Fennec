# Feetech STS3215 Servo Bus — Setup

ID assignment, bus wiring, and bring-up for the 18-servo unified TTL bus.

## Will cover
- Feetech FD debug software (Windows) — ID assignment workflow
- Physical labeling convention (IDs 1-12 legs, 13-18 arm)
- Single-servo bench test via FE-URT-1 → Jetson (SCServo SDK Python)
- Daisy-chain wiring + continuity check (unpowered)
- Full 18-servo ping-all (powered)
- Voltage rail split: 12V hip (×4) vs 6.8V femur/tibia/arm (×14)
- Per-servo torque/return-delay/temperature limit tuning
- Failure-mode recovery (lost servo, address collision, overheat)

> **Status:** placeholder — populate during Phase 1 servo bring-up.
