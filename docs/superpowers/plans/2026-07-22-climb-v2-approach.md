# Climb v2 — Approach Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix climb-v1's approach failure with a PBRS lookahead potential (pays for crossing toward the stairs), a level-tied stair pad (short approach on easy envs), and engagement metrics (never diagnose blind again).

**Architecture:** Three layers, all in `sim/nova_mjx/`: terrain.py gets a level-lerped stair pad; env.py gets a heading-lookahead potential Φ with a signed PBRS delta reward + `phi`/`gz_max` metrics; train.py threads `--w-pbrs` and upgrades the diagnostics line. Spec: `docs/superpowers/specs/2026-07-22-climb-v2-approach-density-design.md`.

**Tech Stack:** JAX/Brax MJX env; tests run `JAX_PLATFORMS=cpu` with the repo venv.

## Global Constraints

- Run tests from `proj/sim/nova_mjx/`: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py` (and the other suite files in Task 3).
- `STAIR_PAD_MIN = 3` (cells); `flat_r_stair = STAIR_PAD_MIN + (FLAT_R - STAIR_PAD_MIN) * level`; MUST equal `FLAT_R` (12) exactly at level 1.0.
- `W_PBRS = 30.0` default ON; `PBRS_LOOKAHEAD = (0.15, 0.25, 0.35)` m — all inside the ±0.4 m heightmap obs window. Never change these without spec change.
- PBRS delta is SIGNED and NEVER clipped ≥0. γ=1 delta form (matches `beta_climb`).
- Flat no-op is sacred: on an all-zero hfield every new term must be exactly 0.
- New info keys: `last_phi` (float), `gz_peak` (float) — seeded at reset, read-before-write in step (read old value for the delta, then overwrite).
- Do NOT touch: stage schedule, `w_climb`/`beta_climb` semantics, the asymmetric clip, obs size (226), `nova-sm3-upstream/`, `original_body_files/`.
- Commit after each task; messages `sim/terrain: …`, `sim/env: …`, `sim/train: …`.

---

### Task 1: Level-tied stair pad (terrain.py)

**Files:**
- Modify: `sim/nova_mjx/terrain.py` (stair branch, ~lines 89-97)
- Test: `sim/nova_mjx/test_climb_reward.py` (T1 family)

**Interfaces:**
- Produces: `STAIR_PAD_MIN = 3` module constant (Task 2's spawn-fit test and Task 3's fingerprint import it); stair-branch pad now level-dependent.
- Consumes: existing `FLAT_R`, `STAIR_RUN_CELLS`, `STAIR_RISE`, `TZ`, `level`.

- [ ] **Step 1: Write the failing tests** — append to `test_climb_reward.py`:

```python
def test_T1d_pad_shrinks_with_level():
    # low-level stair envs put the first riser ~STAIR_PAD_MIN cells out, not FLAT_R
    from terrain import STAIR_PAD_MIN
    f = _stair_field(0.125)
    c = (TN - 1) // 2
    row = f[c]
    pad = STAIR_PAD_MIN + (FLAT_R - STAIR_PAD_MIN) * 0.125          # 4.125 cells
    assert np.allclose(row[: c + int(np.floor(pad))], 0.0, atol=1e-6), "flat inside the lerped pad"
    assert row[c + int(np.ceil(pad)) + STAIR_RUN_CELLS + 1] > 1e-4, \
        "must rise just past the SHORT pad (long before FLAT_R)"


def test_T1e_level1_geometry_unchanged():
    # flat_r_stair(1.0) == FLAT_R -> level-1 stair field identical to pre-change formula
    f = _stair_field(1.0)
    c = (TN - 1) // 2
    yy, xx = np.mgrid[0:TN, 0:TN]
    d = xx - c
    step_idx = np.floor(np.clip((d - FLAT_R) / STAIR_RUN_CELLS, 0.0, None))
    ref = np.clip(step_idx * STAIR_RISE / TZ, 0.0, 1.0)
    assert np.allclose(f, ref, atol=1e-6), "level-1.0 stair geometry must be unchanged"
```

- [ ] **Step 2: Run to verify they fail**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`
Expected: `test_T1d` FAILS (ImportError STAIR_PAD_MIN or flat-past-short-pad assert); T1e may pass pre-change (it pins the invariant).

- [ ] **Step 3: Implement** — in `terrain.py`, add below `STAIR_RUN_CELLS`:

```python
STAIR_PAD_MIN = 3          # stair-env pad floor (cells) at level 0 — joint pad+riser curriculum
```

and in the stair branch replace

```python
    d = xx - c                                             # signed +x distance (cells) from center
    step_idx = jp.floor(jp.clip((d - FLAT_R) / STAIR_RUN_CELLS, 0.0, None))
```

with

```python
    d = xx - c                                             # signed +x distance (cells) from center
    # JOINT pad+riser curriculum (2026-07-22): the stair approach pad SHRINKS with
    # level — flat_r_stair = STAIR_PAD_MIN + (FLAT_R - STAIR_PAD_MIN)*level — so
    # low-level envs (which per-env U[0, tmax] sampling ALWAYS provides) put tiny
    # risers ~15-20 cm from spawn: a first climb the flat gait can discover by
    # walking forward, with the PBRS lookahead (env.W_PBRS) live from step 0.
    # Hits FLAT_R exactly at level 1.0 -> top-difficulty geometry unchanged.
    # Stair branch ONLY; rough/step/flat keep the FLAT_R pad.
    flat_r_stair = STAIR_PAD_MIN + (FLAT_R - STAIR_PAD_MIN) * level
    step_idx = jp.floor(jp.clip((d - flat_r_stair) / STAIR_RUN_CELLS, 0.0, None))
```

Also update the module docstring's stair note (one line: pad is level-lerped, min 3 cells).

- [ ] **Step 4: Run the whole climb suite**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`
Expected: ALL pass (T1a/T1b/T1c ran at level 1.0 where geometry is unchanged; T1d/T1e new-green).

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/terrain.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/terrain: level-tied stair pad (joint pad+riser curriculum, level-1.0 invariant)"
```

---

### Task 2: PBRS lookahead potential + metrics (env.py)

**Files:**
- Modify: `sim/nova_mjx/env.py`
- Test: `sim/nova_mjx/test_climb_reward.py`

**Interfaces:**
- Consumes: Task 1's `STAIR_PAD_MIN` (spawn-fit test); existing `self._terrain_ground_z(xs, ys)` (vectorized), `math.rotate`, `W_CLIMB` block style, `climb_max` peak-delta metric pattern (env.py ~lines 600-645), reset info dict (~line 190), reward sum (~line 547), `last_min_gz`/`last_mean_gz` read-before-write updates.
- Produces: `W_PBRS = 30.0` + `PBRS_LOOKAHEAD` module consts; `NovaJoystick(w_pbrs=…)` kwarg; `_lookahead_phi(pipeline_state)` method; metrics `w_pbrs_climb`, `phi`, `gz_max`; info keys `last_phi`, `gz_peak`. Task 3 imports `W_PBRS`, `PBRS_LOOKAHEAD` and threads `--w-pbrs`.

- [ ] **Step 1: Write the failing tests** — append to `test_climb_reward.py`:

```python
def test_pbrs_zero_on_flat():
    # flat hfield: Φ ≡ 0 -> delta exactly 0 even with w_pbrs ON. Flat no-op invariant.
    e = NovaJoystick(heightmap=True, w_pbrs=30.0)
    s = _step_settle(e, 1)
    assert abs(float(s.metrics["w_pbrs_climb"])) < 1e-6, s.metrics["w_pbrs_climb"]


def test_pbrs_reset_seeds_last_phi():
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(1))
    assert "last_phi" in s.info
    # level-1 pad = 60 cm, lookahead ≤ 0.35 m -> spawn Φ ~ 0
    assert abs(float(s.info["last_phi"])) < 1e-3, s.info["last_phi"]


def test_pbrs_spawn_phi_positive_on_low_level():
    # THE v2 bootstrap claim: at level 0.125 the pad (~20 cm) is shorter than the
    # 0.35 m lookahead, so Φ > 0 AT SPAWN — approach density live from step 0.
    e = _stair_env(0.125)
    s = e.reset(jax.random.PRNGKey(4))
    assert float(s.info["last_phi"]) > 0.0, s.info["last_phi"]


def test_pbrs_signed():
    # mirrors test_T3_climb_reward_signed_on_ascent: drive last_phi by hand
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(2))
    s_up = s.replace(info={**s.info, "last_phi": s.info["last_phi"] - 0.05})
    s_up = e.step(s_up, jp.zeros(e.action_size))
    assert float(s_up.metrics["w_pbrs_climb"]) > 0.0, "Φ above baseline must pay +"
    s_dn = s.replace(info={**s.info, "last_phi": s.info["last_phi"] + 0.05})
    s_dn = e.step(s_dn, jp.zeros(e.action_size))
    assert float(s_dn.metrics["w_pbrs_climb"]) < 0.0, "retreat must pay − (signed, never clipped)"


def test_pbrs_telescopes():
    # structural farm-proof: Σ per-step deltas == w_pbrs·(Φ_N − Φ_0), any path
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(3))
    phi0 = float(s.info["last_phi"])
    tot = 0.0
    for _ in range(5):
        s = e.step(s, jp.zeros(e.action_size))
        tot += float(s.metrics["w_pbrs_climb"])
    assert abs(tot - 30.0 * (float(s.info["last_phi"]) - phi0)) < 1e-4, tot


def test_spawn_feet_fit_min_pad():
    # spawn stance must fit the tightest pad (STAIR_PAD_MIN cells = 15 cm) with 2 cm
    # margin, else the joint curriculum spawns feet onto risers. If this FAILS:
    # escalate to the controller — the fix is STAIR_PAD_MIN = 4, a spec change.
    from terrain import STAIR_PAD_MIN
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(0))
    foot_x = np.asarray(s.pipeline_state.x.pos[np.asarray(e._foot_ids), 0])
    assert foot_x.max() < STAIR_PAD_MIN * 0.05 - 0.02, foot_x


def test_gz_max_metric_tracks_engagement():
    # gz_max telescopes to the running peak of max(ground_z): flat env -> 0
    e = NovaJoystick(heightmap=True)
    s = _step_settle(e, 1, n=3)
    assert abs(float(s.metrics["gz_max"])) < 1e-6
    # stair env, feet in the flat pad -> still 0 (not reaching == 0, the v1 blind spot)
    e2 = _stair_env(1.0)
    s2 = _step_settle(e2, 2, n=3)
    assert abs(float(s2.metrics["gz_max"])) < 1e-6
```

- [ ] **Step 2: Run to verify they fail**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py`
Expected: FAIL — `NovaJoystick.__init__() got an unexpected keyword argument 'w_pbrs'`, then KeyErrors.

- [ ] **Step 3: Implement in env.py**

3a. Below the `W_CLIMB` block (~line 108) add:

```python
W_PBRS = 30.0
# Approach-density weight (signed Δ of the lookahead potential Φ). Φ = mean
# terrain height at PBRS_LOOKAHEAD points ahead of the base along the body +x
# heading. PBRS: the per-step delta telescopes to Φ(end) − Φ(start), so ANY
# cycle (heading wiggle, advance-retreat) nets exactly 0 — non-farmable by
# construction, the provable form of "positive shaper" (precedent: beta_climb).
# Pays for TURNING TOWARD + CLOSING ON rising terrain BEFORE any foot touches
# it — the pad-crossing gradient climb-v1 lacked (frames 2026-07-22: robot
# wandered the flat beside the stairs; min/mean ground_z are 0 until a foot is
# ON a riser, so nothing paid for approach). 0 on flat (Φ ≡ 0). All lookahead
# points sit inside the ±0.4 m heightmap obs window: the policy SEES what the
# reward reads. On rough envs Φ > 0 exists (bumps ahead) — telescoping bounds
# the episode net to ~0; accepted, same scope note as the ungated climb term.
PBRS_LOOKAHEAD = (0.15, 0.25, 0.35)      # m ahead of base, body-frame +x
```

3b. `__init__` signature (~line 117): `w_climb=W_CLIMB, beta_climb=0.0, w_pbrs=W_PBRS,` and next to `self._beta_climb` store:

```python
        self._w_pbrs = float(w_pbrs)     # approach-density weight; --w-pbrs (0=off)
```

3c. Add the method (near `_terrain_ground_z`):

```python
    def _lookahead_phi(self, pipeline_state):
        """Approach potential Φ: mean terrain height at PBRS_LOOKAHEAD points
        projected ahead of the base along the body +x heading (xy-projected,
        normalized; degenerate only if the base is vertical, which is dead)."""
        x = pipeline_state.x
        fwd = math.rotate(jp.array([1.0, 0.0, 0.0]), x.rot[0])
        hd = fwd[:2] / (jp.linalg.norm(fwd[:2]) + 1e-6)
        d = jp.array(PBRS_LOOKAHEAD)
        return jp.mean(self._terrain_ground_z(x.pos[0, 0] + d * hd[0],
                                              x.pos[0, 1] + d * hd[1]))
```

3d. Reset info dict: add `"last_phi": self._lookahead_phi(pipeline_state),` and seed `"gz_peak"` exactly the way the existing climb peak baseline is seeded (read the reset block first; mirror `last_min_gz` placement). `gz_peak` seeds to `jp.max(self._terrain_ground_z(...))` over the spawn feet (same call pattern as `last_min_gz`, `jp.max` instead of `jp.min`).

3e. Step — after the `beta_climb` computation:

```python
        # APPROACH DENSITY (PBRS, --w-pbrs, default W_PBRS ON): signed Δ of the
        # lookahead potential Φ (see W_PBRS above). SIGNED, never clipped ≥0.
        phi = self._lookahead_phi(pipeline_state)
        w_pbrs_climb = self._w_pbrs * (phi - info["last_phi"])
```

Reward sum (~line 547): `+ w_pose + 0.1 + w_climb + beta_climb + w_pbrs_climb`.

3f. Engagement peak — next to the existing `climb_max` peak-delta computation (~lines 600-645), mirror its EXACT pattern for `gz_max`: running peak `new_peak = jp.maximum(info["gz_peak"], jp.max(ground_z))`, per-step metric value = `new_peak - info["gz_peak"]` (so the episode SUM telescopes to final-peak − spawn-peak), then `info["gz_peak"] = new_peak`. Read the climb_max block first and copy its structure line-for-line.

3g. Info updates: where `last_min_gz`/`last_mean_gz` are overwritten post-use, add `info["last_phi"] = phi`.

3h. Metrics: add `"w_pbrs_climb"`, `"phi"`, `"gz_max"` to the metric-name init tuple (~lines 241-258) and to the metrics update (`w_pbrs_climb=w_pbrs_climb, phi=phi, gz_max=<peak delta>`).

- [ ] **Step 4: Run the full climb suite + terrain-relative suite**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_climb_reward.py && JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py`
Expected: ALL pass. If `test_spawn_feet_fit_min_pad` fails → STOP, report BLOCKED with the measured foot_x (controller decides STAIR_PAD_MIN=4).

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_climb_reward.py
git commit -m "sim/env: PBRS lookahead approach potential (w_pbrs) + phi/gz_max engagement metrics"
```

---

### Task 3: Threading + diagnostics (train.py) and full suite

**Files:**
- Modify: `sim/nova_mjx/train.py`
- Test: full suite (all test files in `sim/nova_mjx/`)

**Interfaces:**
- Consumes: `W_PBRS`, `PBRS_LOOKAHEAD` from env (Task 2); existing `--w-climb`/`--beta-climb` arg + threading + fingerprint patterns; the diagnostics line containing `wclimb {…:+.3f}`; `climb`/`climb_max` display transform.
- Produces: `--w-pbrs` CLI (default `W_PBRS`), fingerprint line, diagnostics `wclimb` at 4 decimals + `wpbrs` + `gzmax`.

- [ ] **Step 1: Grep the three touch points**

Run: `grep -n "w_climb\|beta_climb\|wclimb\|climb_max" train.py`
Note the argparse block, `NovaJoystick(...)` construction, fingerprint print, diagnostics f-string.

- [ ] **Step 2: Implement (mirror the `--w-climb` pattern exactly)**

- argparse: `--w-pbrs`, `type=float`, `default=W_PBRS` (import alongside the existing env imports), help: `"approach-density PBRS weight (Φ lookahead; 0 disables; default env W_PBRS)"`.
- `NovaJoystick(..., w_pbrs=args.w_pbrs)` — every construction site the existing `w_climb` reaches.
- Fingerprint, next to the climb-density line:
  `print(f"  approach Φ   : w_pbrs {args.w_pbrs:g} (PBRS lookahead {PBRS_LOOKAHEAD} m — climb-v2)")`
- Diagnostics line: change `wclimb {…:+.3f}` → `+.4f`; append `wpbrs {m('w_pbrs_climb')/L:+.4f}` (per-step, same ÷L convention as wclimb) and `gzmax {…:.3f}` using the SAME transform the line already applies to `climb_max` (it telescopes identically — copy that expression).

- [ ] **Step 3: Sanity-run fingerprint + full suite**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python train.py --dry-run 2>/dev/null | head -40` (or the repo's fingerprint-only invocation if `--dry-run` doesn't exist — check argparse; any path that prints the fingerprint without training). Confirm the `approach Φ` line renders.
Run the full suite from `sim/nova_mjx/`:
`for t in test_*.py; do JAX_PLATFORMS=cpu ../../.venv/bin/python "$t" || exit 1; done`
Expected: every file green.

- [ ] **Step 4: Commit**

```bash
git add sim/nova_mjx/train.py
git commit -m "sim/train: thread --w-pbrs, fingerprint approach-Φ, 4-decimal wclimb + wpbrs/gzmax diagnostics"
```
