# Remote work queue — 2-week computer-only window (set 2026-07-13)

No hardware access. Goal for the window: **get NOVA walking in sim** on the now-
calibrated actuator model, and clear the computer-only backlog. Ranked; do Tier 0
before training so the policy learns against real dynamics.

Physical captures still owed whenever back at the bench (NOT this window): weigh
tibia + remaining prints, heat-set/screw fit test (esp. femur-side servo mount),
L2 orientation, IMU axes, on-robot homing, 12-servo bus timing. See
`docs/bench-capture-tonight.md`.

---

## Tier 0 — Actuator fidelity (quick; unblocks good training)
Feed the bench+datasheet numbers into the sim BEFORE the big training run.
Source of truth: `docs/bench/README.md`.

- [ ] **Joint velocity cap** — `build_mjcf` `VEL=6.0` is DEAD CODE (never used).
      Add a real rate limit: **2.8 rad/s legs, 4.7 rad/s hips** (measured/datasheet
      no-load). Without it the policy learns joint speeds the servos can't hit.
      Options: per-joint MuJoCo velocity limit, or model the speed governor.
- [ ] **Deadband + backlash as joint slop** — firmware deadband **0.88°** (10 cnt)
      + backlash **0.87°** → add ~±1° joint position noise/bias to `domain_randomize`
      in `env.py`. Policy must tolerate it (real foot-placement uncertainty).
- [ ] **Latency** — confirm `env.py` action-delay buffer ≈ **75 ms** (measured
      command→motion deadtime). Already has a latency buffer; set/tune to 75 ms.
- [ ] Keep `EFF_LEG=1.8` / `EFF_HIP=2.9` (≈ datasheet stall 1.91 / 2.94). No change.
- [ ] Do NOT model the servo as a slow first-order lag — it's rate-limited + delay
      + deadband (see README correction). Guard against re-introducing a tau fit.

## Tier 1 — TRAIN (the main event)
- [ ] **Run PPO on Colab T4** (`train.py`, ~60M steps, 20–40 min) with the Tier-0
      model. Get a stable flat-ground walking gait. Iterate reward if needed.
- [ ] **Terrain curriculum** (built PR #86, `terrain.py`) — verify levels ramp,
      tune `TERRAIN_MAX`; train up the curriculum after flat-ground works.
- [ ] **Thermal/duty reward** — penalize sustained high torque (servos overheat
      under sustained ±90° in ~110 min, 2 kg trips overload). Keep gaits within
      continuous-duty torque; add a torque-magnitude / action-rate penalty.
- [ ] Export the trained policy (`export_policy.py` → npz + onnx) once it walks.

## Tier 2 — Deploy readiness (code)
- [ ] **Locate/verify `joint_map.py`** — `sim/nova_mjx/deploy/` is MISSING
      `joint_map.py` + `test_joint_map.py` (only `policy_node`/`policy_runner`
      present); there's a `ros2_ws/.../nova_ops/joint_map.py`. Check if the deploy
      joint_map got orphaned on a merged branch (recurring bug this session — see
      #88/#89). Recover or reconcile to one source.
- [ ] **Wire measured homing convention** into `JointMap`: `home_tick=2048`
      (center-cal), `+tick = CW from horn`. Per-joint `direction` sign finalized at
      on-robot homing, but set the convention + defaults now.
- [ ] Asymmetric privileged critic (Tier 2 sim) — critic sees true vel/friction/
      contacts, actor real-only. Brax `value_obs_key`. Better deployable policy.

## Tier 3 — Parallel non-sim (independent)
- [ ] **PCB v6 power_v2 DRC — 12 violations** (flagged at session start; boards
      already ORDERED, so a real catch is expensive). Verify benign vs blocking
      (KiCad + pcb-design skill). See `feedback-kicad-headless`, board memory.
- [ ] **BOM naming reconcile** — BOM says "STS3215" (Feetech); actual hardware is
      Waveshare "ST3215" (same OEM part). Confirm the gear variant NOVA has —
      **C001 = 1:345** (19.5 kg, SO-ARM101) vs C044 = 1:191 (faster). Update BOM.
- [ ] **Firmware unit tests** — bus scheduler + INA226 scaling (software-testable).
      With sync read/write, prototype/validate the 12-servo bus timing model for
      50 Hz (theoretical ~160 Hz; confirm in the Teensy scheduler logic).

---

### Notes
- Actuator model is CLOSED (bench + datasheet + robonine teardown cross-validated).
  Servo = 60 g measured. Biggest remaining sim2real unknowns are now the terrain
  perception (stairs, deferred) and on-robot bus/latency (bring-up).
- Each item lands as its own PR (branch fresh off `main` — do NOT reuse merged
  branches; two orphan-commit bugs already this session).
