# Power Budget — Worst-Case Current Math

Per-rail current analysis driving the v3.2 power-rail redesign (XL4016 → Pololu D42V110-class).

> **Why this exists:** v3.0 BOM used XL4016 12A modules for both servo rails. Reviewer caught that 8A continuous (the real XL4016 cont. rating, not the 12A peak headline) is below walking-gait average current for 8× 19kg servos on one rail and 4× 30kg hips on the other. This doc shows the math so the rail sizes are defensible.

---

## Servo current characteristics (Feetech STS3215)

Per Feetech datasheets + community measurement:

| Servo | Voltage | Idle/hold | Walk/move cycle | Stall |
|-------|---------|-----------|-----------------|-------|
| STS3215 19kg | 7.4V | 0.4-0.6A | 0.8-1.5A (dynamic) | ~2.0-2.5A |
| STS3215 30kg | 12V | 0.6-0.9A | 1.5-2.5A (dynamic) | ~4.0-5.0A |

Notes:
- "Walk/move cycle" = avg current during the duty-cycle portion when the servo is actively moving (not all 12 servos move continuously)
- Stall is brief (recovery from a stumble, impact at ground touchdown) but real
- Numbers vary with load, speed, and cable resistance — these are working estimates

---

## Rail 1 — Leg 7.4V (8× STS3215 19kg, femur + tibia)

### Walking gait (sustained)

8-phase walk: at any instant ~4 of 8 servos are in active swing/stance transition, ~4 are holding.

- 4 holding: 4 × 0.5A = 2.0A
- 4 moving: 4 × 1.2A = 4.8A
- **Average:** ~6.8A continuous during sustained walk

Add ~20% margin for hill ascents, dynamic gaits, faster cycles: **~8A continuous**.

### Impact transients

Touchdown impacts, recovery from stumble, dynamic balance corrections can cause near-simultaneous high-current pulls. Worst plausible case: 8 servos briefly draw stall-level current.

- 8 × 2.5A = 20A peak
- Duration: 10-50 ms
- **Frequency:** 1-2× per second during dynamic walk, more during recovery

Bulk caps at each star injection point (4× 1000 µF / 25V) absorb these — the buck provides the sustained current, the caps sag through the transient and recharge.

### Buck sizing

- **Need:** ≥8A continuous, transient-tolerant via local bulk caps
- **XL4016 (rejected):** 8A typ cont., often less under real conditions, no margin. Marginal modules thermal-shutdown at this load.
- **Pololu D42V110F7 (selected):** 6-16A range (per Pololu catalog row); ~10A+ continuous at 14.8V Vin per derating graph. **1.25× headroom over the ~8A sustained estimate.** Transient handling delegated to bulk caps + module's own bulk caps.

---

## Rail 2 — Hip + L2 12V (4× STS3215 30kg + Unitree L2 LiDAR)

### Walking gait (sustained)

Hips do most of the work during walking — they're the high-torque joints that lift and place the legs.

- All 4 hips active during dynamic walk: 4 × 2.0A = 8.0A average
- Plus L2 LiDAR: ~1.0A continuous (1A nominal at 12V)
- **Average:** ~9A continuous

### Impact transients

Hip recovery from a stumble or aggressive maneuver: all 4 briefly stall.

- 4 × 5.0A = 20A peak
- Duration: similar to leg rail (10-50 ms)

### Buck sizing

- **Need:** ≥9A continuous + transient-tolerant
- **Pololu D42V110F12 (selected):** ~10A+ continuous at 14.8V Vin. **~1.1× headroom — tighter than the leg rail.** Watch thermal behavior during Phase 1 walk validation; if it runs hot, consider parallel D42V110F12 (Pololu modules can be paralleled with current-share resistors) or upgrade to a higher-rated synchronous buck.

### LC filter on the L2 tap

Hip servos inject 200-1000 Hz current ripple into the 12V rail. UDP packet loss on the L2 is the failure mode — the LiDAR's internal regulator can't reject this efficiently.

- LC: 22 µH series choke + 470 µF / 25V electrolytic shunt
- Tap point: at L2 power connector, **downstream** of the LC
- Validation: scope before/after LC under hip walking load

---

## Rail 3 — Jetson 12V (Pololu D42V55F12)

### Sustained

- Jetson MAXN peak power: 25W
- 25W / 12V = **2.1A nominal**
- USB peripherals (D456 ~2-3W when streaming, FE-URT-1 ~0.5W): add ~0.5A
- **Total: ~2.5A continuous worst case**

### Buck sizing

- **Pololu D42V55F12 selected (already in BOM):** 4.5A typ @ 42V Vin, ~3A continuous at 14.8V Vin per derating graph
- **Headroom:** ~3A / 2.5A = **1.2×** — adequate but not generous. Watch thermal under sustained VLA inference + full RealSense stream + Nav2 planning.

### Dropout consideration

D42V55F12 min Vin = 12V (with dropout penalty starting earlier per the datasheet graph). 4S LiPo at 3.0V/cell = 12.0V is right at the dropout knee.

- **LVC alarm at 3.3V/cell = 13.2V** keeps the 12V rail clean across the usable pack range.
- MOSFET hard-cutoff at 3.1V/cell = 12.4V is the autonomous backstop.

---

## Rail 4 — Aux 5V (UBEC, off-board)

- Ethernet switch (TP-Link LS105G or NETGEAR GS305): ~3W = 0.6A
- Fans (if any, 2× 40mm): ~0.5A combined
- Aux peripherals (PIR, ultrasonic, OLED, RGB LEDs, etc.): ~0.5A
- **Total: ~1.5A continuous**

UBEC 5V/5A handles this with 3× headroom. Already owned, no change.

---

## Rail 5 — Reserved arm 7.4V (Phase 4 only)

When the arm is installed, the 6× STS3215 19kg servos add to the 7.4V load. **Critically: arm is on its own rail, not shared with legs.**

### Sustained (estimated)

- 6 servos holding pose: 6 × 0.5A = 3.0A average
- 6 servos active grasp + reach: ~6 × 1.0A = 6.0A peak

### Buck sizing

- **Pololu D42V55F7 (reserved footprint, not populated v1):** 3-8A range, ~5A continuous at 14.8V Vin
- **Headroom:** ~5A / 6A peak = **0.83× headroom on peak, ~1.7× on average**
- Acceptable for an arm that doesn't sustain peak load — but **bench-validate before populating** when Phase 4 hardware install begins

---

## Why three rails, not two?

Putting all 14× 7.4V servos (8 leg + 6 arm) on one rail was the v3.0 design. Replaced with separate leg + arm rails for v3.2:

1. **Fault isolation.** Arm stall on shared rail → voltage sag → all 8 legs see low-voltage → cascading bus faults → robot collapses. Separate rails: arm stall kills arm only, legs stay standing.
2. **Different load profiles.** Legs walk continuously (5-8A duty). Arm holds + grasps intermittently (2-6A intermittent). Sizing one shared buck for "leg avg + arm peak" forces oversize.
3. **Star injection geography.** Arm lives on top-rear of chassis; legs spread across chassis floor. One shared trunk means long high-current run + IR drop.
4. **Independent fusing + E-stop.** Arm-only kill = pause manipulation while robot stays upright for debug.
5. **Telemetry clarity.** Per-rail INA226 → "arm pulling 4A" separate from "legs 8A". One rail = combined number, can't see which subsystem is misbehaving.

Cost of splitting: +1 buck module (~$32 for D42V55F7), +1 wire harness, +chassis volume. For a walking quadruped with a moving arm carrying a payload, fault isolation is worth it.

---

## Total battery current at peak

4S LiPo 4000mAh / 14.8V nominal.

**Sustained walk (v1 quadruped):**
- Leg rail: 8A @ 7.4V = 59W → 4.0A @ 14.8V
- Hip+L2: 9A @ 12V = 108W → 7.3A @ 14.8V
- Jetson: 2.5A @ 12V = 30W → 2.0A @ 14.8V
- 5V aux: 1.5A @ 5V = 7.5W → 0.5A @ 14.8V
- **Total: ~14A @ 14.8V** ≈ 207W sustained

**Pack runtime at 14A:** 4000 mAh / 14000 mA = **~17 minutes sustained walking**.

This is plausible for a dev session; longer runs need either pack swap (you have two) or stationary intervals.

**Worst-case transient:** sustained + impact ≈ 25-30A briefly. ANL 30A fuse should handle without nuisance-tripping; verify fuse selection (slow-blow if needed).

---

## Validation plan

Mapped into BOM §12 step 2:

- [ ] D42V55F12 Vin sweep 16.8V → 13.2V under MAXN — confirm dropout knee setpoint
- [ ] D42V110F7 ramp load: 1× → 4× → 8× STS3215 19kg walking-stand-in; thermal IR after 10 min sustained
- [ ] D42V110F12 ramp load: 1× 30kg hip + L2; scope LC filter before/after under hip transients
- [ ] MOSFET hard-cutoff trip at 12.4V via bench-supply sweep
- [ ] E-stop kills leg + hip rails only; Jetson stays alive
- [ ] INA226 ×3 sanity reads under nominal and loaded

---

## Future revisits

| Trigger | Action |
|---------|--------|
| Walking-gait sustained pull >9A on leg rail | Upgrade D42V110F7 → D42V110-class higher-current variant, or parallel two with current-share |
| L2 UDP loss >1% under walk | Tighten LC filter (bigger inductor) or move L2 to dedicated 12V buck |
| Pack runtime <12 min at sustained walk | Step up to 6S battery + add 3S→4S range buck, OR drop to lower-power gait |
| Hard-cutoff nuisance trips | Add hysteresis to comparator, or raise trip to 12.6V |

---

> **Status:** baseline at BOM v3.2 / v0.3.0-arch-revised. Update with measured numbers after Phase 1 bench validation.
