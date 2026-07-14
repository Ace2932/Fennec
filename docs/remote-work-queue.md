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

**✅ TIER 0 DONE — PR #91 (2026-07-14), all mujoco-validated.**
- [x] **Joint velocity cap** — motor torque-speed model: per-joint damping =
      stall/no_load (caps 2.8 leg / 4.71 hip rad/s even on ballistic swings),
      kv=0 folded in, frictionloss 0.20 for gravity backdrive. (`VEL` dead code
      was the symptom; real fix is the torque-speed curve.)
- [x] **Deadband + backlash** — 0.88° deadband as target-hysteresis in `env.py`
      + per-episode 0.87° joint_bias in obs (like gyro_bias). Obs shape unchanged.
- [x] **Latency** — `_max_delay` 3→5; sim intrinsic ~32 ms + transport brackets
      the real 75 ms.
- [x] EFF_LEG=1.8 / EFF_HIP=2.9 kept (≈ stall). DR narrowed to measured
      (kp 25-45, kv 0-0.3, damping 0.8-1.3×).
- [x] Servo NOT modeled as first-order lag — rate-limit + delay + deadband.

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
- [x] **PCB v6 power_v2 DRC — DONE, PR #93.** All 12 = benign cosmetic (9 lib
      footprint-mismatch = intentional edits, don't update-from-lib; 3 silk).
      0 errors, clearance enforced via netclasses. Ordered boards good, no re-spin.
      Verdict in `hardware/pcb-mods/nova_pcb_v6_power_v2/DRC_REVIEW.md`.
- [x] **BOM naming reconcile — DONE, PR #94.** STS3215 (Feetech) = ST3215
      (Waveshare), same OEM part; variant C001 1:345 bench-confirmed. Specs +
      pointer to `docs/bench/README.md` added to `BOM.md`.
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
