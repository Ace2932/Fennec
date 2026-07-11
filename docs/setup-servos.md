# Feetech STS3215 Servo Bus — Setup

ID assignment, bus wiring, and bring-up. v1 scope: **12 active servos** (4 hip + 8 femur/tibia). IDs 13-18 reserved for Phase 4 arm install.

Bus master in v1 is the **Teensy 4.1 (Pattern B)** via SN74LVC125A half-duplex driver (5V-tolerant; NOT the original 74HC125). FE-URT-1 (Pattern A) is the bench / debug fallback selected by `JP_BUS_MASTER` solder bridge on PCB v6.

## Bring-up sequence

1. **ID assignment (pre-PCB or post-PCB):**
   - **Pre-PCB (Week 1-2, recommended):** wire FE-URT-1 directly to one servo at a time on the bench (no PCB needed). Use Feetech FD on Windows or SCServo SDK Python from Mac/Jetson via FE-URT-1 to assign unique IDs 1-12 per the labeling convention. Physically label each servo. Do this while waiting for PCB v6 to arrive.
   - **Post-PCB (alternative):** if PCB is already in hand, flip `JP_BUS_MASTER` to A and use the same FE-URT-1 path through the PCB's bus pads.
   Either way: ID setup uses Pattern A's hardware path.
2. **Flip `JP_BUS_MASTER` back to B (default).** Boot Teensy with firmware loaded.
3. **Single-servo bring-up via Teensy:** subscribe to `/joint_states` from Jetson, publish a single `/joint_commands` entry. Verify position tracking + status reads.
4. **Continuity + ping-all:** connect remaining servos, unpowered continuity check, then powered ping-all via Teensy.
5. **Acceptance gate** (per BOM §12 step 3): Teensy loop tick jitter p99 <100 µs + `/joint_commands` arrival rate ≥99% of 100 Hz target + RTT median <5 ms / p99 <20 ms (sanity). The first two are mandatory; RTT is Linux-bounded so don't gate on it.

## Will cover
- Feetech FD debug software (Windows) — ID assignment workflow (Pattern A only)
- ID convention = **PER-LEG SEQUENTIAL** (decided 2026-06-27, `joint_id_map.yaml`): FL haa/hfe/kfe = 1-3, FR = 4-6, RL = 7-9, RR = 10-12. Assign IDs walking the chain leg-by-leg. Hips (haa) = IDs 1,4,7,10 on the 12V rail; hfe/kfe = 7.5V. 13-18 reserved arm.
- Daisy-chain wiring + continuity check (unpowered)
- Voltage rail split: 12V hip (×4) on Pololu D42V110F12; femur/tibia (×8) on Pololu D42V110F7 (7.5V output, within STS3215 7.4V-rated 6-8.4V spec). Arm rail D42V55F7 reserved (Phase 4).
- Per-servo torque/return-delay/temperature limit tuning
- Failure-mode recovery (lost servo, address collision, overheat)
- Teensy firmware verification procedure + gait-loop p99 measurement

> **Status:** placeholder — populate during Phase 1 servo bring-up.
