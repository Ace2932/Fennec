# Servo bench captures — STS3215 (7.4V 19kg variant, ID 1)

Bench: Waveshare Bus Servo Adapter (A), USB-C data + external DC on DC+/DC−.
Supply: Kungber, **7.5 V** / 3 A limit (matches robot D42V110F7 leg rail).
Logger: `scripts/bench_step_response.py` (raw Feetech, ~2500 Hz sample).

## Config registers (as-shipped)
P/D/I gain = 32 / 32 / 0 · accel = 0 (unltd) · goal_speed = 0 (unltd)
max_torque = 1000 · angle limits 0..4095. Sim `kp=35` ≈ measured P=32 — good.

## No-load step response @ 7.5 V (s1_step{30,60,90}_noload.csv)
| step | latency (cmd→motion) | settle (2%) | peak speed (raw) | peak load (raw) |
|------|---------------------|-------------|------------------|-----------------|
| 30°  | 80 ms | 0.49 s | 1250 | 1388 |
| 60°  | 76 ms | 0.69 s | 1800 | 1548 |
| 90°  | 75 ms | 0.84 s | 2200 | 1668 |

- ~75 ms command→motion **deadtime is real** (static friction + deadband) — same
  at 5.3 V and 7.5 V, so not undervoltage. Feed this into the sim latency buffer.
- No overshoot — internal loop is well-damped / rate-governed, not springy.
- No-load motion is voltage-insensitive; load headroom is where voltage matters.

CSV cols: `t_s, cmd_cnt, pos_cnt, speed_raw, load_raw`. 4096 cnt/rev.

⚠ **Load columns above and below are mis-decoded (corrected 2026-09-25).** The logger
read load with bit 15 as the sign; the STS3215 uses **bit 10** (Feetech SDK
`ReadLoad`, #422), and the register is the **motor PWM duty in 0.1 %**, not torque
(Feetech memory table 0x3C: "voltage duty cycle"). No sample has bits 11-15 set.
Re-decoded, the no-load peaks are **364 / 524 / 644** (36-64 % duty while moving with
no external load). New captures log `load_duty_permille`, decoded correctly.
Loaded captures (torque-speed) = TODO at bench.

## Loaded step @ 7.5 V — 201 g at 57.1 mm lever (~0.11 N·m horizontal)
s1_step{up60,dn60}_load201_r57.csv · static hold: ~~load_raw ≈ 1048 @ 0.11 N·m~~ →
**1048 = direction bit (1024) + 24**; re-decoded hold is 32-40, i.e. **3-4 % duty**
at ~6 % of stall torque (gearbox friction carries the rest). Corrected 2026-09-25.

| run | settle | peak speed (raw) | peak load (raw) |
|-----|--------|------------------|-----------------|
| no-load 60°   | 0.69 s | 1800 | 1548 |
| +60° lifting  | 0.69 s | 1800 | 1600 |
| −60° dropping | 0.69 s | 1800 |  500 |

- Speed UNCHANGED under 0.11 N·m (~6% stall) → in normal regime the servo is
  ~~**speed-governed / rate-limited**~~ **acceleration-limited** (corrected
  2026-09-25: peak speed rises with step size, 1.92 / 2.76 / 3.37 rad/s for
  30 / 60 / 90°, while v²/θ stays 7.0-7.3 rad/s². That is the servo's internal
  trajectory profile, ~7-9 rad/s² even at accel = 0; see #428), not torque-limited. Model it as a
  rate-limited position tracker in the sim (NOT a spring); torque-speed droop
  only near stall (~1.9 N·m ≈ 3.4 kg at this lever — not captured).
- Load register senses direction (lift 1600 vs drop 500); ~~static hold anchors
  raw→N·m (~1048 raw @ 0.11 N·m)~~ the register is duty, not torque, so there is
  no raw→N·m anchor here (corrected 2026-09-25, see the warning above).

## Sine tracking @ 7.5 V, no load (#428 check 4, measured 2026-09-25)
Leg servo (7.4 V part, the #462 control unit), horn free, ±15° about 2048, goals
streamed at 100 Hz (the firmware command rate), ~2400 samples/s.
`bench_step_response.py --sine-hz ...` · CSVs `leg_sine15_<hz>hz.csv`.

| Hz | amplitude ratio | lag | accel ceiling est. | peak duty |
|---:|---:|---:|---:|---:|
| 0.5 | 0.99 | 80 ms | tracking | 17 % |
| 1.0 | 1.01 | 237 ms | tracking | 38 % |
| **1.4** | **0.53** | 331 ms | 8.35 rad/s² | 37 % |
| **2.0** | **0.27** | 261 ms | 8.80 rad/s² | 26 % |
| 3.0 | 0.13 | 192 ms | 9.78 rad/s² | 22 % |

GOAL_ACC at 2 Hz (`leg_sine15_acc{0,50,254}_2hz.csv`): ratio 0.26 / 0.27 / 0.27,
ceiling 8.59 / 8.61 / 8.73 rad/s². **The register does not lift the ceiling.**

- **Position mode cannot pass a 1.4-2 Hz gait swing**: half the amplitude at
  1.4 Hz, a quarter at 2 Hz. It matches the sim's profile model (~0.45), not a
  plain position servo (~0.87).
- **It is not power**: peak duty stays at 17-38 %. The servo's own trajectory
  generator (~8.5 rad/s²) is the limit, so `NOVA_GOAL_ACC 50` and a torque
  limit of 600 change nothing here, unloaded.
- ~~Not tested: EEPROM reg 85 and MODE 2~~ → tested the same day, below.

### The ceiling is a register: reg 85 Maximum_Acceleration (measured 2026-09-25)
As-shipped reads: reg 85 = **50** (not in the Feetech memory table; LeRobot names it
`Maximum_Acceleration` and writes 254), reg 86 = 1, lock 0x37 = 1. 50 × 100 steps/s² =
5000 steps/s² = 7.7 rad/s²: that IS the ceiling above. All writes below were made with
the lock at 1 (lost at power cycle) and restored to the as-shipped values after.

| config | 1.4 Hz ratio / lag | 2 Hz ratio / lag | 3 Hz ratio / lag | ceiling est. |
|---|---|---|---|---|
| reg 85 = 50 (factory) | 0.53 / 331 ms | 0.27 / 261 ms | 0.13 / 192 ms | 8.4-9.8 rad/s² |
| **reg 85 = 254**, acc 0 or 254 | **0.97 / 60 ms** | **0.99 / 75 ms** | 0.55 / 173 ms | **40 rad/s²** (254 × 100 steps/s² = 39) |
| reg 85 = 254, TORQUE_LIMIT 600 | – | 1.00 / 75 ms | 0.56 / 173 ms | 41 rad/s² |
| **MODE 2 + host PD** (KP 2, KD 0.08, FF, ~1430 Hz loop) | 1.10 / 16 ms | 1.11 / 20 ms | 0.84 / 27 ms | – |

CSVs: `leg_sine15_r85_254_acc{0,254}_*`, `leg_sine15_r85_254_tl{1000,600}_*`.
MODE 2: `scripts/bench_mode2_pd.py` (printed table only).

- **Position mode can pass a 2 Hz gait swing once reg 85 is raised.** The ceiling was
  a factory setting, not physics. Setting it to 254 is the LeRobot default for every
  SO-100/101 servo.
- **TORQUE_LIMIT is a PWM duty cap (#428 check 1):** at 600 the peak duty clamps at
  exactly 600 and the 3 Hz top speed drops from 2500 to 2100 steps/s. With reg 85 at 254,
  unloaded 2 Hz already peaks at 64 % duty and 3 Hz at 81 %, so a 600 cap will bite
  under load.
- **MODE 2 + a host PD loop** tracks to 3 Hz with 8-27 ms lag against 60-75 ms for
  position mode at reg 85 = 254. Ratios above 1 are overshoot: the gains are untuned.
  This loop ran at ~1430 Hz on one servo from the Mac; the Teensy runs 12 servos at a
  200 Hz tick, so on the robot the lag will be larger. Unmeasured.

## Homing convention (measured, servo ID 1)
- **home_tick = 2048** by construction: Feetech one-key center (`--center`, reg
  0x28 <- 128) sets present-position = 2048 at the held pose. Home EVERY joint
  this way at assembly (joint at nominal) -> home_tick is always 2048.
- **+tick = CLOCKWISE** viewed from the horn/output-shaft side (measured: cmd
  2048->2388 rotated the arm CW). Fixed STS3215 property.
- Per-joint `direction` sign = this CW convention combined with the servo's
  mount orientation in each leg (mirrored L/R legs flip it) — finalize during
  on-robot homing. JointMap default: home_tick=2048, direction from mount.
- 4096 cnt/rev, RAW_PER_RAD = 4096/(2*pi) = 651.9.

## Datasheet (Waveshare ST3215) — hip servo modelable WITHOUT a bench swap
~~ST3215 is ONE servo; torque/speed set by rail voltage~~ **Corrected 2026-09-25:
two different products** (Feetech datasheets): the legs' STS3215 "7.4V 19KG" (6/7.4 V,
16.5/19.5 kg·cm, 42/52 RPM, 2.0/2.5 A stall) and the hips' **ST-3215-C018 "12V 30KG"**
(12 V, 30 kg·cm, 45 RPM, 2.7 A). Different motors, same outline and 25T spline.
The table below is the two parts side by side (waveshare.com/st3215-servo.htm):
| spec | 7.4V leg rail | 12V hip rail |
|------|--------------|--------------|
| stall torque | 19.5 kg·cm = 1.91 N·m | 30 kg·cm = 2.94 N·m |
| no-load speed | ~28 RPM ≈ 2.8 rad/s | 45 RPM (0.222 s/60°) = 4.71 rad/s |
| stall / no-load current | — | 2.7 A / 180 mA |
| weight | 69 g | 69 g · op 6–12.6 V |

### Hip identification (#462, measured 2026-09-25)
`scripts/set-servo-ids.py --identify` on the Waveshare adapter at 7.5 V / 0.5 A,
one servo at a time (all at factory ID 1). Reg 0x0E = EEPROM max input voltage.

| servo | reg 0x0E | family | fw | servo ver | max torque |
|-------|---------:|--------|----|-----------|-----------:|
| H1 | 14.0 V | **12 V** | 3.10 | 9.3 | 1000 |
| H2 | 14.0 V | **12 V** | 3.10 | 9.3 | 1000 |
| H3 | 14.0 V | **12 V** | 3.10 | 9.3 | 1000 |
| H4 | 14.0 V | **12 V** | 3.10 | 9.3 | 1000 |
| leg (control) | 8.0 V | 7.4 V | 3.10 | 9.3 | 1000 |

All four hips are the 12 V part; the leg control reads 8.0 V as the 7.4 V memory
table says, so the check separates the two on this hardware. **Firmware and servo
version are identical across both parts: reg 0x0E is the only register that tells
them apart.** Marked H1-H4 on the cases; IDs not yet assigned.

**Cross-validation:** bench peak 1800 raw @7.5V; Feetech speed unit = steps/s →
1800/4096·2π = 2.76 rad/s ≈ datasheet 7.4V no-load (~2.8). Datasheet + bench agree,
and confirms raw-speed = steps/s. ~~Hip = same servo at 12V + shared control loop
(PID 32/32/0, ~75 ms deadtime) already measured → no 12V bench swap needed.~~
Corrected 2026-09-25: the hip is a different motor, so its dynamics are NOT
measured. And the 1800 raw peak is the 60° step's accel-limited peak, not a
speed cap (the 90° step reaches 2200).

### Sim refinements this surfaced (computer-only TODO)
1. `build_mjcf` has NO joint velocity limit (`VEL=6.0` is dead code). Real caps:
   2.8 rad/s legs / 4.7 rad/s hips. Add a speed-governor/vel-limit so the policy
   can't learn unachievable joint speeds (sim2real). EFF_LEG=1.8 / EFF_HIP=2.9 ≈
   datasheet stall (1.91 / 2.94) — good.
2. `compute_inertials.SERVO_MASS` 60 → 69 g (datasheet) until a real servo is weighed.

## Online-sourced characterization (no bench needed) + corrections
Servo confirmed **60 g MEASURED** (datasheet 69 g includes horn/cable) → compute_inertials
SERVO_MASS=60 g is CORRECT, no change. Independent STS3215 teardown (robonine.com):
| property | measured | sim use |
|----------|----------|---------|
| backlash | 0.87° (0.015 rad) | joint slop → position DR / obs noise |
| firmware deadband | **10 counts = 0.88°** | won't move below 0.88° error → small-signal tracking floor |
| repeatability | ±0.17° (~2 cnt) | matches bench settle |
| real stall torque | ~35 kg·cm@12V (>30 rated) | margin |
| speed | 45.6 RPM@100%, 21.9@50% (linear) | confirms 2.8 rad/s @7.5V |
| thermal | 70°C protect; **±90° sustained overheats ~110 min; 2 kg trips overload** | DUTY limit — gait avoid sustained high torque |
| gear ratio | 1:345 (C001, = SO-ARM101) | reflected inertia = motor × 345² |

Bus rate: 8-axis daisy-chains run fine; LeRobot/SO-ARM drive 6+ at high rate via
SYNC read/write → 12 @ 50 Hz is established (protocol supports it). No bench test needed.

⚠ **CORRECTION to any first-order phase-lag reading:** the step response is
~~RATE-LIMITED (constant-velocity traverse at ~2.8 rad/s)~~ **ACCELERATION-LIMITED
(~7-9 rad/s², corrected 2026-09-25)**, NOT first-order. Fitting
tau to settle time (324–541 ms) OVERSTATES lag — the real model is
**rate-limiter (2.8/4.7 rad/s) + ~75 ms pure delay + 10-count deadband**, not a slow
lag. Do NOT bake "-140° @1.5 Hz" into the sim; use the rate+delay+deadband model.

Ref: zeroth-robotics/bam-feetech (BAM friction sysID method — pendulum→MuJoCo, reusable
later; no STS3215 params published yet). Feetech gear variants: C001=1:345 (19.5kg,
slower, SO-ARM), C044=1:191 (faster) — confirm which SKU NOVA has.
