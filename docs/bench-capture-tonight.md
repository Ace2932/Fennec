# Bench capture — last physical access before 2-week trip

Everything below can ONLY be done at the bench. Computer-only work (sim, CAD, PCB,
firmware) stays unblocked for the 2 weeks IF this data exists. Ranked by leverage.
Save all raw files under `proj/docs/bench/` and commit — I read them remotely.

Priority if short on time: **#1 + #2**. Do **#3** to avoid being stuck with an
un-fixable print fit for two weeks.

---

## 1. Servo step-response (STS3215) — HIGHEST leverage
Unblocks the whole 2 weeks of sim training. Sim's actuator DR (kp/kv/latency/
torque) is currently guessed; this replaces guesses with measured dynamics.

**Rig:** one STS3215 on FE-URT-1 (or your bus adapter) + power. Horn accessible.
Note the `/dev/tty...` port.

**Steps** (script does the logging — `proj/scripts/bench_step_response.py`):
```
cd proj/scripts
mkdir -p ../docs/bench
# confirm it talks + is centered
./bench_step_response.py --port /dev/ttyUSB0 --id 1 --ping
# no-load steps, 3 magnitudes
./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 30 --out ../docs/bench/s1_step30_noload.csv
./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 60 --out ../docs/bench/s1_step60_noload.csv
./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 90 --out ../docs/bench/s1_step90_noload.csv
# loaded: hang a KNOWN mass on a KNOWN lever from the horn, repeat 60 deg
./bench_step_response.py --port /dev/ttyUSB0 --id 1 --step-deg 60 \
    --note "load=200g lever=80mm" --out ../docs/bench/s1_step60_load200.csv
```
**Record separately (paper is fine):**
- Bus **baud** actually used, and the **sample rate** the script prints (Hz).
- Supply **voltage** at the servo (measured, not nominal).
- For the loaded run: exact **mass (g)** and **lever length (mm)** hung on the horn.
- Anything odd: overshoot, buzzing, position jump (encoder wrap), thermal.

CSV columns: `t_s, cmd_cnt, pos_cnt, speed_raw, load_raw`. Keep every file.

> If the bus/port differs from `set-servo-ids.py`, use that same port/baud — the
> protocol is identical.

---

## 2. Weigh every printed part — locks each link's inertia
Scale in grams, **supports removed, no servo, no hardware**. Femur done (57 g).

| part | weight (g) | infill | notes |
|------|-----------|--------|-------|
| femur_R | 57 | 40% | DONE |
| tibia_R | ____ | 25% | only had slicer 51 g — weigh REAL |
| coax_R | ____ | 40% | |
| knee_arm | ____ | 40% | |
| shoulder | ____ | 40% | |
| shoulder_plate | ____ | 40% | |
| **one assembled STS3215** | ____ | — | verifies the 60 g assumed in every link |

Any part >±10% off its slicer estimate → tell me, I rescale that link's inertial.

---

## 3. Heat-set + screw FIT test — catch a redesign while you can still print
Rule: no self-tap into filament; if an insert/screw won't seat → redesign. You
can't iterate fit for 2 weeks, so prove it TONIGHT.

For each printed part, physically:
- [ ] Heat-set insert seats fully, square, no filament crack/blow-out
- [ ] Correct screw threads into the seated insert, pulls a real clamp
- [ ] Mating parts bolt together flush (the gated joints)

**Specifically the femur-side servo mount** — you flagged this one had issues
(coax pocket was confirmed good). If any insert/screw does NOT seat: message me
the part + which hole + what fails, and I redesign before you leave.

---

## 4. Free grabs IF servos are already powered
- **Home ticks + direction** per joint: with each joint held at its nominal pose,
  run `set-servo-ids.py --center <id>` (writes 2048 = center) OR just record the
  present `pos_cnt` and which physical direction is + vs -. Fills the `JointMap`
  home_tick/direction placeholders (currently blocking real deploy).
  → record: `joint, id, home_cnt, +dir = (which way)`.
- **IMU axis check** (only if ICM-42688-P is wired): rest level, then tilt +X,
  +Y, +Z one at a time; log gyro + accel sign each. Fills the `policy_node`
  IMU-frame TODO. → record: `tilt axis -> gyro sign, accel sign`.

---

## 5. L2 LiDAR mount orientation
L2 can physically seat 4 ways. Confirm/photo which orientation it actually mounts
in (connector direction + which face is "forward"). Affects the ear self-filter
+ SLAM sensor frame. → one photo + a note: "connector points ___, forward face = ___".

---

### After the bench
```
cd proj && git add docs/bench && git commit -m "bench: physical captures pre-trip" && git push
```
Then the 2 weeks of sim/CAD/PCB work runs off real numbers instead of guesses.
