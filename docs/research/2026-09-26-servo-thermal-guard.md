# Servo protection vs walking and climbing: research (2026-09-26)

**Scope:** #428 / #483. How to protect the STS3215 legs without giving up trotting and step climbing, and
whether a different gait, hardware or training approach removes the conflict. This is research and a
recommendation only. Nothing here changes firmware. The robot is not assembled, so everything below is
for later.

**Status of claims:**
- **SIM** = measured in MJX (v-next model `sim/v-next` @ 83a2b8b, seeds and episode counts given).
- **CALC** = hand calculation.
- **SRC** = external source, opened and read (list at the end).
- **UNVERIFIED** = say so, and name the bench test that settles it.

## TL;DR

1. **The 100 ms load guard protects against nothing that happens in 100 ms.** Heat takes seconds to
   minutes, jams take 2 s or more, and rail brownout takes milliseconds. Replace it with guards split by
   harm: an **I²t thermal bucket per joint** (derate, then sit), the **servo's own overload unload** plus
   a **≥3 s jam-signature backstop**, and **rail current on the INA226**.
2. **At TL 1.0, walking heats a knee about half as much as a locked jam** (mean i² 0.52-0.57 vs 1.0).
   So "detect jams" is the wrong question and **the thermal budget is the real constraint**. A τ = 30 s
   bucket separates walking (peak ≤ 0.65, 9/9 seed-scenarios) from a full jam (crosses 0.8 in ~24 s).
3. **Whether walking fits the thermal budget is unknown.** My estimate of the sustainable i² spans
   0.5-0.85, and walking sits at 0.55. **One bench test decides it:** hold 1.47 N·m on a leg servo and
   log the temperature.
4. **Best levers for walk + climb, in order:**
   - idle stand mode (the policy trots in place at cmd 0);
   - a copper-loss (Σ τ²) cost, never tried: `energy` is Σ action²;
   - **STS3250**: same 45.22×24.72×35 case, same 25T spline, 4.9 N·m @ 12 V, $43;
   - taller stance;
   - crawl for stairs.
5. **The leg rail is probably undersized for TL 1.0 walking**, jams or not: ≥10-11 A mean (lower
   bound) against a ~10 A buck and a 6.8 A budget.

## 1. What we were missing

| # | Missed | Evidence |
|---|---|---|
| M1 | The guard was aimed at a **timescale where no harm happens.** Winding heat takes seconds to minutes. Jams are handled by the servo itself at 2 s. Rail sag takes milliseconds. 100 ms of high duty damages nothing. | SRC Robonine (static 50 % hold: 48 °C at 10 min, flat >1 h). SRC Feetech regs 34/35/36 (2 s, 20 %). |
| M2 | **Walking is thermally half a jam.** A duty threshold cannot separate them. Heat (I²t) can, and heat is the actual damage mechanism. | SIM §2 |
| M3 | **A sag-weakened jam heats less than walking** (i² 0.49 vs 0.55). A thermal guard treating it as "not urgent" is *correct*. Duty-based detection still catches it in 2 s, because duty saturates at 100 % whatever the current. | SIM + CALC |
| M4 | **The servo already has a per-joint, graceful overload guard** (>80 % for 2 s → 20 % output, not torque-off). Nobody reads it back: no firmware or script touches regs 19/34/35/36. LeRobot, on the same servo, also relies on factory defaults. | `grep` of firmware/ and scripts/ (0 hits); SRC LeRobot `feetech.py` |
| M5 | **Idle is not idle.** At cmd = 0 the policy trots in place: knee i² 0.46 vs 0.17 for a static stand, same 1.38 Hz spectral peak as walking. | SIM |
| M6 | **No copper-loss cost was ever tried.** `env.py:998` `energy = Σ action²`. The duty cost that killed climbing was a *hinge above 0.8*, which bills exactly the climbing bursts. Σ τ² bills the continuous bang-bang use that fennec-22 measured (front hfe/kfe ≥90 % duty on 79-83 % of steps). | code |
| M7 | **A same-outline 12 V upgrade exists:** STS3250, 45.22×24.72×35 mm, 25T/OD5.9, 1/345, 50 kg·cm. | SRC servodatabase, wowrobo |
| M8 | **Leg-rail current:** walking at TL 1.0 draws ≥10-11 A (lower bound). `docs/power-budget.md` assumed 6.8 A, and the D42V110F7 does ~10 A continuous. | SIM §2 |
| M9 | **The DR's "battery sag" cannot reach the servos:** the servo rails are buck-regulated. Real sources of torque loss are copper temperature (~0.39 %/K, so +45 K ≈ −15 % stall) and transient rail droop. The 0.7-1.0 range is really a *hot servo* range, which ties back to M2. | CALC |

## 2. Sim evidence: per-joint heating

`sim/nova_mjx/thermal_trace.py`, CPU, 64 DR episodes per scenario per seed, overload model on, slew
3.07, reg85 = 254 (GOAL_ACC 0).
- **Flat scenarios:** 9 s. Longer episodes walk off the 5 m hfield, and the first 30 s attempt read 100 % falls for that reason.
- **Curb:** the 400-step 3 cm one-cell *ramp* (5 cm cells, not a riser).
- **i** = |τ| / nominal stall (haa 2.9, hfe/kfe 1.8 N·m). Motor current ∝ torque, so **i² = copper loss as a fraction of locked-rotor stall.** Nominal, not DR-sagged, is the right denominator.
- About 90 % of the knee i² is below 5 Hz (0.2 s moving average), so this is gait load, not solver chatter.

**Mean i², kfe / hfe / haa, seeds s0 / s1 / s2:**

| scenario | TL 1.0 (VA_tl1.0_noduty) | TL 0.8 (VN_tl0.8) |
|---|---|---|
| fwd 0.25 m/s | kfe .56/.55/.56 · hfe .54/.56/.54 · haa .28/.29/.29 | kfe .42/.42/.42 · hfe .38/.38/.38 |
| mixed cmds | kfe .52/.53/.52 · hfe .51/.52/.49 | kfe .40/.40/.39 · hfe .36/.36/.36 |
| 3 cm ramp | kfe .57/.45/.57 · hfe .55/.52/.55 | kfe .33/.34/.29 · hfe .35/.37/.37 |
| ramp success | **97 / 59 / 98 %** | **39 / 9 / 6 %** |
| stand (cmd 0) | kfe .46 · hfe .45 (s0) | kfe .36/.36/.36 |
| worst joint-episode | 0.85-0.89 | ≤ 0.60 |
| time at i ≥ 0.9 (kfe) | 16-23 % | 0 % |
| servo self-unloads / robot / episode | mixed 0.06 / 0 / 0.17 · ramp 0.03 / 0 / 0 | 0 |

**Reference points:**
- static 4-leg stand: 0.17 (41 %²);
- a jam at TL 1.0: i² = tscale², so 0.49-1.0;
- a jam at TL 0.8: 0.31-0.64.

**Leaky bucket** E (dE/dt = (i² − E)/τ, started at the walking mean). Peak over all 9 TL 1.0
seed-scenarios, any joint:

| τ | walking peak (max) | full jam (i² = 1) crosses 0.8 after | full jam crosses 0.85 after |
|---|---|---|---|
| 2 s | 0.91 | no separation | no separation |
| 5 s | 0.84 | no separation | ~5 s |
| 10 s | 0.76 | ~7.9 s | ~10.8 s |
| 30 s | 0.65 | ~24 s | ~33 s |

At TL 0.8 every bucket stays at or below 0.63 (τ 2 s) and 0.46 (τ 30 s).

**Leg-rail current, lower bound.** When stalled, supply ≈ duty × I_motor ≈ i² × I_stall, with
I_stall = 2.5 A at 7.4 V. Moving joints draw *more* than this bound.

| | TL 1.0 | TL 0.8 |
|---|---|---|
| leg rail, 8 servos | mean 10.0-11.2 A, 1 s peak ≤ 13.5 A | 6.6-8.0 A, 1 s peak ≤ 9.4 A |
| stand-in-place | 9.1 A | 6.7-6.9 A |
| hip rail | 2.9-3.4 A | — |

### Thermal budget: what's sustainable (UNVERIFIED)

Robonine's anchor is on the 12 V C018: a static hold at ~50 % stall (i² ≈ 0.25) gives ΔT ≈ +23 K.
- **Straight from the C018 anchor:** 70 °C at 25 °C ambient allows i² ≈ 0.49.
- **Scaled to the C001 leg servo's stall power** (18.5 W vs 32.4 W, same case, same thermal
  resistance assumed): i² ≈ 0.85.
- **Walking at TL 1.0 (0.52-0.57) sits inside that 0.5-0.85 band.** Its worst joint-episode is above it.
- Static friction assist (0.11 N·m read as 3-4 % duty, not 6 %) would make the real i² *lower* than the sim's.

Precedent that this matters: on a Unitree A1 carrying 3 kg, the baseline overheated in ~5 min, and a
thermal-state residual policy extended that past 13 min (SRC Wan et al. 2026). **Bench B3 settles it.**

## 3. Protection: ranked

| rank | design | catches | walking false trips (sim) | cost |
|---|---|---|---|---|
| **1** | **Split by harm.** (a) per-joint I²t bucket, τ ≈ 30 s (set from B3), derate that joint's TORQUE_LIMIT at E ≥ 0.8, controlled sit (#145 limp_controller) at E ≥ 0.95 or 70 °C; (b) the servo's own reg 36/35/34 unload, **read back at every arm**; (c) the #483 jam signature at **persist ≥ 3 s** → fleet limp; (d) leg/hip rail current from the INA226 → fleet TL foldback. **Delete the 100 ms rule.** | heat (the damage), real jams (2 s servo, 3 s firmware), rail overcurrent | 0 / 9 seed-scenarios (bucket peak 0.65 < 0.8; jam-run max 1.48 s < 3 s) | firmware only. Poll block 0x38-0x46 for Present Current, +7 bytes ≈ +70 µs per read at 1 Mbaud; per-servo TL write |
| 2 | fennec-22's option (2): jam signature + ~2 s persist, alone | jams (it duplicates the servo's own 2 s layer) | persist must be > 1.48 s | tiny. **Misses M2:** walking itself may overheat |
| 3 | TL 800 + the old guard | guard can never fire; heat is 25 % lower (i² .42 vs .56) | 0 | climbing 3 cm: 6-39 % vs 59-98 % |

Why not per-joint derate for everything: a jam should still fleet-limp, because a leg that won't move
can't be walked on. Heat is not a jam. The joint still works, so derate it and sit the robot *under
control*. Today overload never gets a controlled limp (`main.cpp:354`), so a hot knee drops the robot
on its belly.

**Constrained RL (CaT, P3O, Lagrangian PPO) is rank-2 work.** Use it only if B3 shows walking exceeds
the budget. The right formulation then is a constraint on the *bucket state* (E ≤ 0.8), not on duty.
- CaT turns constraint violations into stochastic termination on top of PPO. It was shown on Solo (SRC).
- The ETH comparison (Lee et al. 2023) is the reference for picking an algorithm.
- The A1 residual-thermal paper is the closest precedent (SRC).

### fennec-22's gap questions

- **(a) Gear and horn stress against a hard stop.** A servo cannot push harder than stall. Walking already
  puts the knee at i ≥ 0.9 for 16-23 % of the time, so a static jam at stall is **not a higher gear
  load than normal walking**. The danger case is **external backdrive**: body momentum driving a leg
  caught on a stair nosing *into* the gears above stall. That happens in milliseconds, no current guard
  sees it, and it is a mechanical problem (foot and shin geometry, compliance), not a guard problem.
  Sustained static load does not cycle, so it adds no fatigue. The servo's 2 s → 20 % unload also caps
  its duration.
- **(b) Rail current.** Walking alone is the rail problem (≥10-11 A leg, §2). A jam *replaces* that
  joint's walking draw (~1.4 A mean) with ≤ 2.5 A, so each jam adds at most ~1.1 A. Four hip jams are
  4 × 2.7 = 10.8 A, against a 3 A walking mean on that rail. Brownout is a millisecond event, faster
  than any polled duty guard. It belongs on the INA226 (rail-level foldback) and the buck's own limit.
  **Action:** redo `docs/power-budget.md` Rail 1 with measured current (B6).
- **(c) Should a short jam trip stay alongside the bucket?** Keep a jam trip, but **not a short one.**
  #483 measured walking jam-runs up to 1.48 s (3 seeds, mixed), so anything under ~1.5 s trips walking.
  The servo's own layer already catches every jam in 2 s, sagged jams included, because duty saturates.
  So the firmware jam signature is a **backstop at ≥ 3 s** (2× the walking max), for the case where the
  servo layer is misconfigured or disabled (hence the read-back).
  - **Watch:** the servo's own layer *also* fired in sim walking (0.06-0.17 per robot per 9 s mixed
    episode at TL 1.0). On hardware that is a mid-walk 20 % drop.
  - **Knob:** reg 35 up to 254 (2.54 s max, 10 ms/LSB), or reg 36 raised. Test in sim first (`OVERLOAD_S`).

## 4. Walking and climbing: ranked levers

Knee torque in a 2-leg trot stance is 1.47 N·m (82 %, `probe_stance_torque`). My geometry calculation
(thigh 0.1069, shank 0.129, elbow-back) gives 80 % for the same pose, a cross-check within 2 points.

| rank | lever | number | cost / risk | test |
|---|---|---|---|---|
| **1** | **Idle stand mode:** at \|cmd\| ≈ 0, hold a static stand pose instead of running the policy (policy_runner gate), or train a stand reward | knee i² 0.46 → 0.17 at idle (2.7× less heat); leg rail 9.1 → ~3.4 A | small host code; the transition in and out of the gait needs a blend | SIM stand trace |
| **2** | **Copper-loss cost** w·Σ(τ/τ_stall)² at TL 1.0 | targets the bang-bang use (M6); predicted to lower mean i² without billing short climbing bursts (a burst is a small share of the integral), which the hinge did | **unproven**; could still hurt climbing | tower sweep, report i² **and** ramp for each point (§6) |
| **3** | **STS3250 legs** (4.9 N·m @ 12 V) | 1.47 N·m = 30 % → i² ≈ 0.09 in static stance. A policy retrained with this authority should use it (fennec-22: an *un*-retrained policy just eats extra authority) | 8 × $43 ≈ $344; +~20 g each (74.5 g vs STS3215 ~55 g, UNVERIFIED; +0.16 kg ≈ +4 % mass); leg rail must become 12 V (D42V110F7 → F12 module; check the footprint is shared). Stall current and speed **UNVERIFIED**. Cheapest now, while unassembled | `--eff-scale 2.72` training run; check holes and screws on one unit |
| 3b | C018 legs (2.94 N·m @ 12 V, same SKU as the hips) | 50 % stance, i² ≈ 0.25 | 8 × ~$20; same 12 V rail change; 45 vs 52 RPM | `--eff-scale 1.63` |
| 4 | **Taller stance** h 0.188 → 0.21 m | peak knee over a ±3 cm stance stroke 96 % → 76 % | less leg reserve for climbing; higher CoM | change DEFAULT_POSE/STAND_HEIGHT, retrain |
| 5 | **Crawl for climbing** (3 legs down; v8 `CRAWL_DUTY` 0.75 schedule already in env) | knee 64 % peak (54 % static) vs 80-96 % | slow; needs gait switching (terrain-aware, Phase 3 path #413) | stair courses (§5) |
| 6 | Mass cut | −10 % mass → −10 % torque, −19 % i² | the trunk is 2.83 of 4.11 kg; nothing obvious | — |
| 7 | Knee parallel spring | offsets stance torque, adds it to swing; bonus: a limp robot sits instead of dropping | mechanical redesign | last |

Not recommended:
- **STS3046** (40 kg·cm @ 7.4 V): 40×20×43 mm case, so a leg CAD redesign.
- Buying bigger servos *without retraining*.

## 5. Stairs, done properly

The 3 cm "curb" is a 31° ramp (5 cm cells). A real riser needs MJX **box geoms** (exact vertical faces,
cheap collision) or 1-1.5 cm hfield cells (#456/#457).
- Put climbing numbers on risers before choosing hardware on the strength of ramp results.
- The perceptive path (heightmap teacher → blind/perceptive student, #413) plus the existing crawl
  schedule is the correct architecture for stairs. Nothing here changes that; it only says the trot is
  the wrong gait for tall steps on this actuator.

## 6. Next experiments

### Bench (Aiden, at assembly, one leg servo, 7.5 V bench supply)

| id | test | settles |
|---|---|---|
| **B3** | **Thermal step.** Horn lever, 1.47 N·m (2.05 kg at 7.3 cm, or 1.5 kg at 10 cm). Log Present Temperature at 1 Hz and Present Current; torque off at 65 °C or 20 min. Repeat at 0.73 N·m. | τ_th, ΔT per i², so the bucket τ and threshold, and whether walking fits the budget (§2). **The decisive test.** |
| B1 | **Torque ↔ duty ↔ current.** Hanging weights 0.3-1.8 N·m, loading and unloading. Record Present Load, Present Current, \|goal − pos\|. | friction assist on hold (sim pessimism, M9); jam-signature error threshold; Present Current units |
| B4 | **Jam.** Block the horn, command 30° away. Record time to self-unload (expect 2.0 s), output after (expect 20 %), recovery behaviour, temperature rise rate. | the servo layer works on *our* units; the sim models it as latched |
| B5 | **Protection read-back.** Read regs 13, 19, 34, 35, 36 on all 12 (add to `set-servo-ids.py --identify`). | M4: factory defaults assumed, never read |
| B6 | **Rail.** INA226 leg-rail current during a tethered stand and a tethered trot in place. | M8, power budget |
| B2 | **Stall, cold vs hot.** Max holdable weight cold and after B3. | DR torque range (M9) |

### Tower (queue behind fennec-train@vnext2; GPU only)

1. **w_tau2 sweep** at TL 1.0: {3e-3, 1e-2, 3e-2} × Σ(τ/τ_stall)², 3 seeds each. For every point report mean i² (this script), fwd/mixed speed, and **1-cell ramp 2/3/4 cm success**. Kill criterion: 3 cm < 80 % median.
2. **eff_scale 2.72 and 1.63** (STS3250 / C018 legs), retrained, TL 1.0, same scorecard + i².
3. **Idle stand:** mixed eval with the cmd-0 segments gated to a static pose. Measure transition stability.
4. **OVERLOAD_S 2.54** (reg 35 max): self-unload rate in mixed.
5. After B3: bucket τ and threshold → re-score all of the above with the bucket as a metric.

### Firmware (for later; spec only, fennec-8f / #483 owner)

- Extend the poll block to 0x46 (Present Current).
- Per-joint bucket (fixed-point, τ from B3).
- Per-servo TL derate.
- Controlled sit on thermal (not torque-off).
- Jam signature at ≥ 3 s.
- Read back regs 19/34/35/36 at arm and refuse to arm on mismatch.
- Rail foldback from the INA226.
- Remove the `NOVA_STALL_LOAD_RAW`/`NOVA_STALL_PERSIST` 100 ms rule.

Native tests: a walking trace (from `thermal_trace.py` npz) must not trip; a planted jam must trip at ≥ 3 s.

## Reproduce

```
# tower, CPU only (the GPU is shared)
JAX_PLATFORMS=cpu python sim/nova_mjx/thermal_trace.py --policy <run>/curbs/policy.pkl --asym --tl 1.0 --out x.npz
python sim/nova_mjx/analyze_thermal.py x.npz
```

Run against `sim/v-next` @ 83a2b8b (the model in the tables). The scripts use only APIs that main also
has, but they have not been run against main's model.

## Sources (opened and read 2026-09-26)

- Feetech STS3215 memory table, reg 13/16/19/28/34/35/36/48/60/63/69: https://github.com/commanderfun/STS3215/blob/main/REGISTER_REFERENCE.md (third-party). **Correction to that page:** Protection Time (35) is **10 ms/LSB** (254 max = 2540 ms), so the default of 200 = **2 s**. This matches the official V3.7 table parsed in memory `reference-sts3215-control-truth`, and the sim's `OVERLOAD_S = 2.0`.
- Robonine STS3215 (12 V) bench, static/oscillation temperature and overload: https://robonine.com/testing-of-feetech-sts3215-servomotor-backlash-repeatability-and-torque/
- LeRobot feetech driver (no protection registers written): https://github.com/huggingface/lerobot/blob/main/src/lerobot/motors/feetech/feetech.py
- ODrive thermistor current foldback (lower/upper limits, fault +5 °C): https://docs.odriverobotics.com/v/0.6.12/thermistors.html
- Katz et al., Mini Cheetah (continuous torque set by the thermal limit): https://ieeexplore.ieee.org/document/8793865
- Grimminger et al. 2020, ODRI Solo (no thermal protection described): https://arxiv.org/abs/1910.00093
- Chane-Sane et al., "CaT: Constraints as Terminations for Legged Locomotion RL" (2024, Solo): https://arxiv.org/abs/2403.18765
- Zhang et al., P3O (2022): https://arxiv.org/abs/2205.11814
- Lee et al., "Evaluation of Constrained RL Algorithms for Legged Locomotion" (2023): https://arxiv.org/abs/2309.15430
- Wan et al., "Learning to Balance Motor Thermal Safety and Quadrupedal Locomotion Performance with Residual Policy" (2026, A1): https://arxiv.org/abs/2605.27046
- STS3250 specs: https://servodatabase.com/servo/feetech/sts3250 · price: https://shop.wowrobo.com/products/feetech-sts3250-c002-servo-12v-50kg-1-345-servo
- STS3046: https://www.feetechrc.com/74v-40-kgcm-metal-shell-steel-teeth-360-degree-magnetic-code-single-shaft-ttl-serial-port-steering-gear.html

**UNVERIFIED:**
- Unitree/ANYmal overtemp thresholds (no readable primary source).
- STS3250 stall current, speed and hole pattern.
- STS3215 thermal time constant.
- Whether Present Current is motor current or supply current.
