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
