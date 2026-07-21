# Climb Reward (flagless v1, unidirectional stairs) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the quadruped climb stairs, by adding a non-farmable climb reward (signed `Δ min terrain-height-under-foot`) that is 0 on flat by construction, and switching the stair terrain from radial to unidirectional — per `docs/superpowers/specs/2026-07-21-climb-incentive-design.md` (READ IT; v3 + the flagless/ascent-only decisions this plan implements).

**Architecture:** No obs change, no mode flag. The climb reward is always in the reward sum but evaluates to ~0 on flat terrain (`Δ min(ground_z)=0`), positive during real ascent, negative during descent (ascent-only v1). Stairs rise unidirectionally in +x so a forward command climbs them; the yaw-aligned heightmap makes the policy heading-invariant. Reuse the existing 4-stage curriculum + flat-walker graft.

**Tech Stack:** jax 0.6.0 (CPU locally), brax 0.14.2, mujoco/mujoco-mjx 3.10 (in `proj/.venv`). Self-running test scripts (`JAX_PLATFORMS=cpu`).

## Global Constraints

- Branch: `sim/climb-reward` (create off `origin/main`).
- Repo root: `/Users/afox/codebases/NOVA/proj`. Python `.venv/bin/python`, run from `sim/nova_mjx/`.
- **Flat no-op invariant:** on flat terrain the climb reward is EXACTLY 0 (`Δ min(ground_z) = Δ0 = 0`), so the flat gait's reward is bit-identical to today. Guarded by a test.
- **Non-farmability:** climb reward = `W_CLIMB · signed (min_now − last_min)`, `min` over feet of `_terrain_ground_z(foot_xy)`. NEVER clip ≥ 0 (that is an unbounded thrash farm). `base_h`/`done` keep the SAME `jp.min(ground_z)` — that coupling is the lock; do not change them.
- **Do NOT change:** reward weights of existing terms, `FOOT_TARGET_Z`, `TZ`, `_sample_heightmap` (obs), the deployed flat 105-d path, #130's terrain-relative geometry, train.py resume accounting.
- **No obs change** — obs stays 226; the graft is the existing `nova_policy_hm.pkl` via `--restore-params-pkl` (no `--add-dims`).
- `W_CLIMB` default 40 (tune 25-60); reward stays inside the ±10 clip (`task ~2-3 + climb spike ≤ W_CLIMB·0.08`).
- Every red-test step must FAIL before its green step. Comment style: dense, why-focused, match env.py.
- Commit per task: `sim/env: <what> — <why>`.

---

### Task 1: Unidirectional stair terrain

**Files:**
- Modify: `sim/nova_mjx/terrain.py:84-89` (the `is_stair` branch)
- Create: `sim/nova_mjx/test_climb_reward.py`

**Interfaces:**
- Produces: `terrain_field(rng, level, step_frac, stair_frac)` — stair envs now rise in +x (world), flat for `x < center+FLAT_R`, plateau at `TZ`. Full-width in y. smooth/step envs unchanged (radial pad).

- [ ] **Step 1: Write failing tests T1a-T1c** — create `test_climb_reward.py`:

```python
"""Climb reward + unidirectional stairs — the ascent objective and the terrain
that makes a forward command climb. Design:
docs/superpowers/specs/2026-07-21-climb-incentive-design.md

  JAX_PLATFORMS=cpu python test_climb_reward.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick
from terrain import terrain_field, TN, TZ, FLAT_R, STAIR_RISE, STAIR_RUN_CELLS


def _stair_field(level=1.0):
    # a pure staircase env (stair_frac=1 so is_stair always true)
    return np.asarray(terrain_field(jax.random.PRNGKey(0), level, 0.0, 1.0)).reshape(TN, TN)


def test_T1a_stairs_rise_in_x_flat_in_y_and_behind():
    # +x (col increasing) climbs; -x and lateral (y / row) stay flat.
    f = _stair_field(1.0)
    c = (TN - 1) // 2
    # forward (+x): height increases with col past the flat zone
    fwd = f[c, c + FLAT_R + 1 : c + FLAT_R + 1 + 3 * STAIR_RUN_CELLS]
    assert fwd[-1] > fwd[0] + 1e-3, ("stairs must rise in +x", fwd)
    # behind (-x): flat
    assert np.allclose(f[c, : c - FLAT_R], 0.0, atol=1e-6), "behind spawn must be flat"
    # lateral (y, same x=center): flat (height depends only on x)
    assert np.allclose(f[:, c], f[c, c], atol=1e-6), "same-x column must be one height (no y dependence)"


def test_T1b_spawn_zone_is_flat():
    # center (spawn, cell c,c) is flat, and the row through center is flat out to
    # center+FLAT_R, then rises.
    f = _stair_field(1.0)
    c = (TN - 1) // 2
    assert abs(f[c, c]) < 1e-6, "spawn cell must be flat"
    row = f[c]
    assert np.allclose(row[: c + FLAT_R], 0.0, atol=1e-6), "flat out to center+FLAT_R"
    assert row[c + FLAT_R + STAIR_RUN_CELLS + 1] > 1e-3, "rises past the flat zone"


def test_T1c_no_bypass_high_ground_only_by_climbing():
    # the ONLY high terrain is at high x (the top). No high cell at low x (no
    # bypass ramp to the top). max height at low-x half is ~0; high at high-x.
    f = _stair_field(1.0)
    c = (TN - 1) // 2
    low_x_max = f[:, : c + FLAT_R].max()
    high_x_max = f[:, c + FLAT_R :].max()
    assert low_x_max < 1e-6, ("no high ground reachable without climbing +x", low_x_max)
    assert high_x_max > 0.1, ("stairs reach real height", high_x_max)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all climb-reward tests passed")
```

- [ ] **Step 2: Run — verify fails**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`
Expected: T1a fails (current radial stairs rise in all directions, not just +x — the -x/lateral flat asserts fail).

- [ ] **Step 3: Implement — unidirectional stair branch** in `terrain.py`, replace lines 84-89:

```python
    # STAIRCASE (tier-2, UNIDIRECTIONAL): steps rising in +x (world) from the pad
    # edge, full-width in y, so a FORWARD command climbs them and the ONLY high
    # ground is up the stairs (no bypass — height depends only on x). The
    # yaw-aligned heightmap obs makes the policy heading-invariant, so fixed +x
    # generalises to any-direction approach at deploy. (Radial rose outward in
    # every direction, which let a velocity-commanded policy orbit a flat
    # constant-radius contour and never climb — see the 2026-07-21 design.)
    d = xx - c                                             # signed +x distance (cells) from center
    step_idx = jp.floor(jp.clip((d - FLAT_R) / STAIR_RUN_CELLS, 0.0, None))
    stair_m = step_idx * (STAIR_RISE * level)
    is_stair = jax.random.uniform(kstair, ()) < stair_frac
    height_m = jp.where(is_stair, stair_m, height_m)
```

(`xx`, `c` already exist at terrain.py:70-71; `xx` = columns = world x per the `_sample_heightmap` x→col mapping.)

- [ ] **Step 4: Run — verify T1a-T1c pass**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`
Expected: all three pass. Also confirm smooth/step envs unaffected: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py` still green.

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/terrain.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/terrain: unidirectional +x stairs — a forward command climbs, no orbit refuge"
```

---

### Task 2: Climb-reward state seeded at spawn

**Files:**
- Modify: `sim/nova_mjx/env.py` reset info (~:191-196)
- Modify: `sim/nova_mjx/test_climb_reward.py`

**Interfaces:**
- Produces: `info["last_min_gz"]` = `min(ground_z)` at spawn (the telescoping baseline for the climb reward). Step (Task 3) reads/updates it.
- Consumes: `_terrain_ground_z` (#130), the foot positions at reset.

- [ ] **Step 1: Failing test** — append to `test_climb_reward.py`:

```python
def _stair_env(level=1.0):
    e = NovaJoystick(heightmap=True)
    n = e._hf_nrow
    field = np.asarray(terrain_field(jax.random.PRNGKey(0), level, 0.0, 1.0))
    e.sys = e.sys.tree_replace({"hfield_data": jp.asarray(field)})
    return e


def test_T2_reset_seeds_last_min_gz_to_spawn():
    e = _stair_env(1.0)
    state = e.reset(jax.random.PRNGKey(1))
    assert "last_min_gz" in state.info
    # spawn is in the flat zone -> min ground under feet is ~0
    assert abs(float(state.info["last_min_gz"])) < 1e-3, state.info["last_min_gz"]
```

- [ ] **Step 2: Run — fails** (`KeyError` / assert: `last_min_gz` absent).

- [ ] **Step 3: Implement** — in `reset()`, in the `info` dict next to `last_base_z` (env.py:195):

```python
            # climb-reward telescoping baseline: min terrain-height-under-foot at
            # spawn. The reward pays W_CLIMB·(min_now − last_min_gz) each step
            # (signed), which telescopes to net ascent. Seeded here so the first
            # step's Δ is ~0 (spawn is flat).
            "last_min_gz": jp.min(self._terrain_ground_z(
                pipeline_state.x.pos[self._foot_ids, 0],
                pipeline_state.x.pos[self._foot_ids, 1])),
```

- [ ] **Step 4: Run — passes.** `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/env: seed the climb-reward baseline (min ground_z at spawn)"
```

---

### Task 3: The climb reward term (always-on, signed, 0 on flat)

**Files:**
- Modify: `sim/nova_mjx/env.py` — add `W_CLIMB` const, compute the term (~:271 where `ground_z`/`base_h` live), add to the reward sum (~:502), update `last_min_gz` (~:560), add a `w_climb` metric (~:568).
- Modify: `sim/nova_mjx/test_climb_reward.py`

**Interfaces:**
- Consumes: `ground_z` (env.py:271), `info["last_min_gz"]` (Task 2).
- Produces: reward includes `w_climb_term`; `state.metrics["w_climb"]`.

- [ ] **Step 1: Failing tests** — append (env-level, step the real env):

```python
def _step_settle(e, key, n=1):
    state = e.reset(jax.random.PRNGKey(key))
    for _ in range(n):
        state = e.step(state, jp.zeros(e.action_size))
    return state


def test_T3_climb_reward_zero_on_flat():
    # flat env (default all-zero hfield): Δ min(ground_z) ≡ 0 → w_climb metric 0
    # → reward bit-identical to pre-change. THE flat no-op invariant.
    e = NovaJoystick(heightmap=True)          # default hfield = flat
    s = _step_settle(e, 1)
    assert abs(float(s.metrics["w_climb"])) < 1e-6, s.metrics["w_climb"]


def test_T3_climb_reward_signed_on_ascent():
    # Manufacture a min-ground-z increase: move last_min_gz DOWN by hand, step,
    # and confirm w_climb > 0 (min_now > last_min). Then set last_min ABOVE
    # min_now and confirm w_climb < 0 (descent penalised, not clipped).
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(2))
    s_up = s.replace(info={**s.info, "last_min_gz": s.info["last_min_gz"] - 0.05})
    s_up = e.step(s_up, jp.zeros(e.action_size))
    assert float(s_up.metrics["w_climb"]) > 0.0, "min above baseline must pay +"
    s_dn = s.replace(info={**s.info, "last_min_gz": s.info["last_min_gz"] + 0.05})
    s_dn = e.step(s_dn, jp.zeros(e.action_size))
    assert float(s_dn.metrics["w_climb"]) < 0.0, "descent must be signed-negative (never clipped ≥0)"


def test_T3_climb_reward_not_farmable_by_posture():
    # Rearing/standing tall changes base_z but NOT foot xy -> ground_z unchanged
    # -> Δ min = 0 -> w_climb 0. Non-farmable by posture.
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(3))
    # lift the base straight up (posture, feet xy unchanged), step
    q = s.pipeline_state.q.at[2].add(0.05)
    ps = e.pipeline_init(q, s.pipeline_state.qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    # base rose but feet xy ~same -> min(ground_z) ~same -> w_climb ~0
    assert abs(float(s2.metrics["w_climb"])) < 0.05, ("posture must not pay", s2.metrics["w_climb"])
```

- [ ] **Step 2: Run — T3_zero_on_flat + others FAIL** (`KeyError: 'w_climb'`). The flat-zero test is the flat no-op guard; the ascent/posture tests pin sign + non-farmability.

- [ ] **Step 3: Implement.**

`env.py` top-level const (near the other terrain/reward consts, after the imports block, ~line 100):

```python
W_CLIMB = 40.0   # climb-reward weight (signed Δ min terrain-height-under-foot).
# 0 on flat by construction; ~STAIR_RISE·level per stride on stairs. Tune 25-60:
# too low won't beat the energy of climbing, too high spikes the shared value
# head and rots the flat gait. NOT clip≥0 (that is an unbounded thrash farm).
```

In `step()`, right after `base_h = height - jp.min(ground_z)` (env.py:271), add:

```python
        # CLIMB REWARD — the ascent objective. Signed Δ of min terrain-height-
        # under-foot: pays for the trailing (lowest) foot stepping onto a higher
        # tread (real climbing), 0 on flat (Δ0), negative on descent. Non-farmable
        # — rearing/pogo/standing-tall don't move terrain-under-foot; and base_h
        # (= height − this same min) couples it to the done/height_pen survival
        # constraint, so the one lean/airborne exploit self-limits into death
        # pressure. NEVER clip ≥0 (an unbounded climb-descend-thrash farm).
        min_gz = jp.min(ground_z)
        w_climb = W_CLIMB * (min_gz - info["last_min_gz"])
```

In the reward sum (env.py:502-503), add `+ w_climb`:

```python
        reward = (w_track + w_yaw + w_progress + w_air + w_clearance
                  + w_pose + 0.1 + w_climb
                  + w_upright + w_angvel + w_height + w_z
                  + w_slip + w_splay + w_carry
                  + w_actrate + w_energy + w_jerk + w_stand)
```

Update the baseline every step — next to the `info["last_base_z"] = base_z_now` update (env.py:560):

```python
        info["last_min_gz"] = min_gz
```

Add the metric to `state.metrics.update(...)` (env.py:568) — next to `w_stand=w_stand`:

```python
            w_climb=w_climb,
```

Add `"w_climb"` to the metrics-init dict (search the `metrics = {k: 0.0 for k in (...)}` block near env.py:200 and add `"w_climb"` to the tuple).

- [ ] **Step 4: Run — all green + regressions**

```bash
JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py
JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py
JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py
```
Expected: all green. `test_terrain_relative` (flat no-op of #130) still passes — proves the climb term didn't perturb flat behaviour.

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/env: always-on signed climb reward (0 on flat, non-farmable) — makes ascent pay"
```

---

### Task 4: Telescoping test + w_climb CLI knob + diagnostics

**Files:**
- Modify: `sim/nova_mjx/env.py` (make `W_CLIMB` overridable), `sim/nova_mjx/train.py` (`--w-climb` + diagnostics line), `sim/nova_mjx/test_climb_reward.py`

**Interfaces:**
- Produces: `--w-climb` CLI (default 40) threaded to the env; `w_climb` on the per-eval diagnostics line.

- [ ] **Step 1: Failing test** — telescoping over a hand-built ascent, and the CLI knob:

```python
def test_T4_climb_reward_telescopes():
    # sum of per-step w_climb over an episode = W_CLIMB · (min_gz_end − min_gz_spawn).
    # Drive the baseline manually to simulate a monotonic climb of 0.16 m.
    from env import W_CLIMB
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(4))
    total, last = 0.0, float(s.info["last_min_gz"])
    for gz in np.linspace(last, last + 0.16, 8)[1:]:
        s = s.replace(info={**s.info, "last_min_gz": jp.asarray(gz - 0.02)})  # baseline just below
        s = e.step(s, jp.zeros(e.action_size))
        total += float(s.metrics["w_climb"])
    # signed deltas telescope; total is finite and positive for net ascent
    assert total > 0.0, total
```

(This is a smoke test that the metric is signed and accumulates; the exact telescoping identity is covered by the env's brax-sum semantics, verified for `climb` in `test_terrain_relative`.)

- [ ] **Step 2: Run — passes already** (Task 3 gave `w_climb`); if it fails, the metric wiring is wrong — fix env.py, not the test.

- [ ] **Step 3: Implement the CLI knob + diagnostics.**

`env.py`: make `W_CLIMB` a constructor arg with the const as default, so training can sweep it:
- In `NovaJoystick.__init__`, add `w_climb=W_CLIMB` param, store `self._w_climb = w_climb`, and use `self._w_climb` in the `w_climb = ... * (min_gz - ...)` line.

`train.py`: add `ap.add_argument("--w-climb", type=float, default=40.0, help="climb-reward weight (signed Δ min ground_z; 0 on flat). Tune 25-60.")`; pass `w_climb=args.w_climb` into `NovaJoystick(...)` (find the `env = NovaJoystick(...)` construction). Add `w_climb` to `print_fingerprint` (one line: `climb reward : w_climb {w_climb:.0f} (signed Δ min ground_z, 0 on flat)`). Add `climb` reward to the `diagnostics()` line — it already prints `climb`/`climb_max` (base-z metrics); add `wclimb {m('w_climb')/L:+.3f}` so the per-step climb REWARD is visible next to the base-z climb metric.

- [ ] **Step 4: Run — all suites + py_compile**

```bash
JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py
../../.venv/bin/python test_curriculum_resume.py
../../.venv/bin/python test_resume_budget.py
../../.venv/bin/python -m py_compile env.py train.py terrain.py
```

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/train.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/train: --w-climb knob + climb-reward on the diagnostics line"
```

---

### Task 5: Final verification + mutation checks + Colab command

**Files:** none (verification only)

- [ ] **Step 1: Full local suite**

```bash
cd /Users/afox/codebases/NOVA/proj/sim/nova_mjx && \
JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py && \
JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py && \
JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py && \
../../.venv/bin/python test_curriculum_resume.py && \
../../.venv/bin/python test_resume_budget.py
```

- [ ] **Step 2: Mutation checks** (each breaks exactly one test, then restore):
  (a) clip the climb reward `jp.maximum(min_gz - last_min, 0.0)` → `test_T3_..._signed_on_ascent` (descent-negative half) breaks;
  (b) use `base_z_now` instead of `min_gz` → `test_T3_..._not_farmable_by_posture` breaks;
  (c) revert the stair branch to radial `r` → `test_T1a` breaks;
  (d) `W_CLIMB = 0` → the ascent-pays half of T3 breaks.

- [ ] **Step 3: Reward-clip sanity** — confirm `task (~2-3) + W_CLIMB·STAIR_RISE (40·0.08=3.2)` stays inside the ±10 `jp.clip`. If a multi-riser stride could exceed it, note raising the clip for the climb term (do NOT silently let the clip eat the climb reward).

- [ ] **Step 4: Report + the Colab probe command** (flagless, ascent-only, unidirectional; graft the flat walker, reuse the curriculum):

```bash
# dry-run first
!python train.py --heightmap --stair-frac 0.6 --terrain 1.0 --curriculum --flat-frac 0.25 \
    --w-climb 40 --restore-params-pkl /content/drive/MyDrive/nova_policy_hm.pkl \
    --ckpt /content/drive/MyDrive/nova_climb_reward_v1 --timesteps 120_000_000 --dry-run
```
Watch on the real run: the diagnostics `wclimb` (climb REWARD per step — should lift off 0 on stair envs) and `climb`/`climb_max` (base-z ascent). **Early kill:** if `wclimb` and `climb_max` stay ~0 through stage 1-2 with `v_loss` plateaued, the cold-start didn't bootstrap → add the softmin/mean-PBRS density term (design risk 1) before scaling. Judge with a `--stair-level 1.0` rollout: `climbed ≥ +0.16 m` (two 8 cm risers, the TZ cap).
