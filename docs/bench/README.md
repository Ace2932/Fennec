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
Loaded captures (torque-speed) = TODO at bench.

## Loaded step @ 7.5 V — 201 g at 57.1 mm lever (~0.11 N·m horizontal)
s1_step{up60,dn60}_load201_r57.csv · static hold: load_raw ≈ 1048 @ 0.11 N·m.

| run | settle | peak speed (raw) | peak load (raw) |
|-----|--------|------------------|-----------------|
| no-load 60°   | 0.69 s | 1800 | 1548 |
| +60° lifting  | 0.69 s | 1800 | 1600 |
| −60° dropping | 0.69 s | 1800 |  500 |

- Speed UNCHANGED under 0.11 N·m (~6% stall) → in normal regime the servo is
  **speed-governed / rate-limited**, not torque-limited. Model it as a
  rate-limited position tracker in the sim (NOT a spring); torque-speed droop
  only near stall (~1.9 N·m ≈ 3.4 kg at this lever — not captured).
- Load register senses direction (lift 1600 vs drop 500); static hold anchors
  raw→N·m (~1048 raw @ 0.11 N·m).

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
ST3215 is ONE servo; torque/speed set by rail voltage (waveshare.com/st3215-servo.htm):
| spec | 7.4V leg rail | 12V hip rail |
|------|--------------|--------------|
| stall torque | 19.5 kg·cm = 1.91 N·m | 30 kg·cm = 2.94 N·m |
| no-load speed | ~28 RPM ≈ 2.8 rad/s | 45 RPM (0.222 s/60°) = 4.71 rad/s |
| stall / no-load current | — | 2.7 A / 180 mA |
| weight | 69 g | 69 g · op 6–12.6 V |

**Cross-validation:** bench peak 1800 raw @7.5V; Feetech speed unit = steps/s →
1800/4096·2π = 2.76 rad/s ≈ datasheet 7.4V no-load (~2.8). Datasheet + bench agree,
and confirms raw-speed = steps/s. Hip = same servo at 12V + shared control loop
(PID 32/32/0, ~75 ms deadtime) already measured → no 12V bench swap needed.

### Sim refinements this surfaced (computer-only TODO)
1. `build_mjcf` has NO joint velocity limit (`VEL=6.0` is dead code). Real caps:
   2.8 rad/s legs / 4.7 rad/s hips. Add a speed-governor/vel-limit so the policy
   can't learn unachievable joint speeds (sim2real). EFF_LEG=1.8 / EFF_HIP=2.9 ≈
   datasheet stall (1.91 / 2.94) — good.
2. `compute_inertials.SERVO_MASS` 60 → 69 g (datasheet) until a real servo is weighed.
