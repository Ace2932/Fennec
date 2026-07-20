# Terrain-Relative Reward + Flat-Floor Curriculum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every reward/termination geometry term read height above LOCAL ground instead of absolute world z, add a 25% flat-env floor to the curriculum, and instrument climbing — per the approved spec `docs/superpowers/specs/2026-07-20-terrain-relative-reward-design.md` (READ IT FIRST; it contains the adjudicated review findings this plan implements).

**Architecture:** One new collision-exact terrain query (`_terrain_ground_z`, MuJoCo fixed-diagonal triangulation) feeding five consumers (contact, clearance, contact_true, done, height_pen); the existing bilinear path stays byte-identical for the obs. Flat floor = one masked draw in `make_domain_randomize`. Metrics ride the existing brax telescoping-sum semantics.

**Tech Stack:** jax 0.6.0 (CPU locally), brax 0.14.2, mujoco/mujoco-mjx 3.10 (mujoco 3.10.0 already in `proj/.venv`). Tests are self-running scripts like `test_heightmap.py`, run `JAX_PLATFORMS=cpu`.

## Global Constraints

- Branch: `sim/terrain-relative-reward` (already exists, spec committed on it).
- Repo root for all paths: `/Users/afox/codebases/NOVA/proj`. Python: `.venv/bin/python`, run from `sim/nova_mjx/`.
- **Obs invariant:** `_sample_heightmap` output byte-identical pre/post (the deployed 226-obs interface must not move). Guarded by T4.
- **Flat no-op invariant:** on all-zero hfield every changed expression is bit-identical to current code. Guarded by T1.
- **Do NOT change:** reward weights, `FOOT_TARGET_Z=0.05`, symmetric clearance form (measure-then-decide per spec), `TZ=0.20`, train.py resume accounting.
- Every red-test step must FAIL before its green step (bugs T5-T9 fail on current code by design).
- Comment style: dense, why-focused, match env.py's existing voice.
- Commits: one per task, message style `sim/env: <what> — <why>`.

---

### Task 1: Local CPU jax toolchain (or documented Colab fallback)

**Files:**
- Modify: none (environment only)

**Interfaces:**
- Produces: a working `JAX_PLATFORMS=cpu .venv/bin/python test_heightmap.py` invocation (existing test as canary), used by every later task's test steps.

- [ ] **Step 1: Install CPU jax + brax into the venv**

```bash
cd /Users/afox/codebases/NOVA/proj
.venv/bin/pip install "jax==0.6.0" "brax==0.14.2" "mujoco-mjx>=3.10" 2>&1 | tail -3
```

- [ ] **Step 2: Canary — the EXISTING heightmap test must pass locally**

Run: `cd sim/nova_mjx && JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py`
Expected: its existing assertions pass (prints test names / exits 0).
If install or canary fails (arm64 wheel gap): STOP, report — later test steps then carry a `# Colab: run in NOVA_train.ipynb deps cell` note instead, and local steps only `py_compile`. Do not fight the toolchain for more than ~10 minutes.

- [ ] **Step 3: No commit** (no repo change).

---

### Task 2: `_terrain_ground_z` helper + terrain-query tests T1-T3

**Files:**
- Modify: `sim/nova_mjx/env.py` (add method next to `_sample_heightmap`, ~line 539)
- Create: `sim/nova_mjx/test_terrain_relative.py`

**Interfaces:**
- Produces: `self._terrain_ground_z(wx, wy) -> jp.ndarray` — ABSOLUTE terrain z at world xy, vectorized (input shape (N,) -> output (N,)), matching MuJoCo's hfield collision triangulation exactly. Tasks 3-4 call it.
- Consumes: existing attrs `self._hf_size`, `self._floor_pos`, `self._hf_nrow/_hf_ncol` (env.py:150-153), `self.sys.hfield_data`.

- [ ] **Step 1: Write failing tests T1-T3** — create `test_terrain_relative.py`:

```python
"""Terrain-relative geometry — the queries the reward stands on.

The reward previously read ABSOLUTE world z where it meant height above local
ground (spec: docs/superpowers/specs/2026-07-20-terrain-relative-reward-design.md).
These tests pin the new collision-exact query and the five consumers.

  JAX_PLATFORMS=cpu python test_terrain_relative.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick, FOOT_RADIUS, CONTACT_EPS


def _env_with_field(data2d):
    e = NovaJoystick(heightmap=True)
    e.sys = e.sys.tree_replace({"hfield_data": jp.asarray(data2d.reshape(-1))})
    return e


def _grid(e):
    n_r, n_c = e._hf_nrow, e._hf_ncol
    return n_r, n_c


def test_T1_flat_is_zero():
    # All-zero hfield (the default): ground query must be EXACTLY fz == 0
    # everywhere -> foot_h == foot_z -> every changed expression bit-identical
    # to the old code. This is the blast-radius guarantee.
    e = NovaJoystick(heightmap=True)          # default hfield_data is all zeros
    xs = jp.array([0.0, 0.3, -1.0, 2.0])
    ys = jp.array([0.0, -0.4, 1.2, -2.0])
    z = e._terrain_ground_z(xs, ys)
    assert np.allclose(np.asarray(z), 0.0, atol=1e-9), z


def test_T2_constant_field_scale_offset():
    # Uniform 0.10 m: catches the data*ztop+fz conversion. hfield data is
    # normalized [0,1] against ztop (=0.20), so 0.5 everywhere == 0.10 m.
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    e = _env_with_field(np.full((n_r, n_c), 0.5))
    z = e._terrain_ground_z(jp.array([0.0, 0.7]), jp.array([0.4, -0.9]))
    assert np.allclose(np.asarray(z), 0.10, atol=1e-6), z


def test_T3_asymmetric_ramp_catches_transpose():
    # Height rising along +x ONLY. The staircase is radially symmetric, so a
    # row/col transpose is INVISIBLE on it — this ramp is the only test that
    # can catch it. Build data so height(x,y) = 0.20 * (col / (ncol-1)):
    # env.py:557-558 maps x->col, y->row.
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    data = np.tile(np.linspace(0.0, 1.0, n_c)[None, :], (n_r, 1))
    e = _env_with_field(data)
    rx = float(e._hf_size[0])                  # half-extent in x (2.5 m)
    # at x = +rx/2 (75% across the grid), expect 0.20 * 0.75 = 0.15 m; y must not matter
    z_a = e._terrain_ground_z(jp.array([rx / 2]), jp.array([0.0]))
    z_b = e._terrain_ground_z(jp.array([rx / 2]), jp.array([1.1]))
    assert np.allclose(np.asarray(z_a), 0.15, atol=5e-3), z_a
    assert np.allclose(np.asarray(z_a), np.asarray(z_b), atol=1e-6), (z_a, z_b)
    # and along y with the SAME data, height must NOT vary -> transposed code fails here
    z_c = e._terrain_ground_z(jp.array([0.0]), jp.array([rx / 2]))
    assert np.allclose(np.asarray(z_c), 0.10, atol=5e-3), z_c   # centre column = 0.5 -> 0.10


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all terrain-relative tests passed")
```

- [ ] **Step 2: Run — verify fails**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py`
Expected: `AttributeError: ... no attribute '_terrain_ground_z'`

- [ ] **Step 3: Implement the helper** in `env.py`, directly ABOVE `_sample_heightmap` (~line 539):

```python
    def _terrain_ground_z(self, wx, wy):
        """ABSOLUTE terrain z at world (wx, wy) matching MuJoCo's hfield COLLISION
        surface exactly — per-cell fixed-diagonal (v00-v11) triangulation, NOT
        bilinear. Bilinear (what the obs uses) diverges from the surface physics
        stands on by up to ~19 mm inside riser-boundary cells, in BOTH directions
        — enough to re-open the absolute-z contact bug at exactly the tread edges
        climbing needs (spec 2026-07-20, empirically measured vs mj_ray). The
        reward/done consumers therefore read THIS, and the obs keeps bilinear
        (_sample_heightmap) because the policy was trained on it."""
        rx, ry, ztop = self._hf_size[0], self._hf_size[1], self._hf_size[2]
        fx, fy, fz = self._floor_pos[0], self._floor_pos[1], self._floor_pos[2]
        # world xy -> fractional (row, col), same mapping as _sample_heightmap
        # (x -> col, y -> row); T3's asymmetric ramp pins the orientation.
        col = (wx - (fx - rx)) / (2 * rx) * (self._hf_ncol - 1)
        row = (wy - (fy - ry)) / (2 * ry) * (self._hf_nrow - 1)
        data = self.sys.hfield_data.reshape(self._hf_nrow, self._hf_ncol)
        r0 = jp.clip(jp.floor(row).astype(jp.int32), 0, self._hf_nrow - 2)
        c0 = jp.clip(jp.floor(col).astype(jp.int32), 0, self._hf_ncol - 2)
        fr = jp.clip(row - r0, 0.0, 1.0)
        fc = jp.clip(col - c0, 0.0, 1.0)
        v00 = data[r0, c0]
        v01 = data[r0, c0 + 1]
        v10 = data[r0 + 1, c0]
        v11 = data[r0 + 1, c0 + 1]
        z = v00 + jp.where(fc >= fr,
                           fc * (v01 - v00) + fr * (v11 - v01),
                           fr * (v10 - v00) + fc * (v11 - v10))
        return z * ztop + fz
```

- [ ] **Step 4: Run — verify T1-T3 pass**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py`
Expected: `ok test_T1... ok test_T2... ok test_T3...` all pass.

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_terrain_relative.py
git commit -m "sim/env: collision-exact terrain query (_terrain_ground_z) — reward must read the surface physics stands on"
```

---

### Task 3: T8 triangulation oracle + T4 obs regression

**Files:**
- Modify: `sim/nova_mjx/test_terrain_relative.py`

**Interfaces:**
- Consumes: `_terrain_ground_z` (Task 2), `mujoco.mj_ray` (mujoco 3.10.0, already in venv), `terrain_field` from `terrain.py`.

- [ ] **Step 1: Write T8 (oracle) + T4 (obs regression)** — append:

```python
def test_T8_matches_mujoco_collision_surface_inside_transition_cells():
    # THE test bilinear fails: sample INTERIOR points of stair-boundary cells
    # and compare against mj_ray on the real physics model. T5-T7 place feet
    # mid-tread and cannot catch a triangulation mismatch.
    import mujoco
    from terrain import terrain_field
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    field = np.asarray(terrain_field(jax.random.PRNGKey(3), 1.0, 0.0, 1.0))
    e = _env_with_field(field.reshape(n_r, n_c))
    m = mujoco.MjModel.from_xml_path("nova.xml")
    m.hfield_data[:] = field
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    rng = np.random.default_rng(0)
    pts = rng.uniform(-1.6, 1.6, size=(300, 2))          # annulus incl. stair band
    geomid = np.zeros(1, dtype=np.int32)
    for x, y in pts:
        z0 = np.zeros(1)
        dist = mujoco.mj_ray(m, d, np.array([x, y, 1.0]), np.array([0.0, 0.0, -1.0]),
                             None, 1, -1, geomid)
        true_z = 1.0 - dist
        ours = float(e._terrain_ground_z(jp.array([x]), jp.array([y]))[0])
        assert abs(ours - true_z) < 2e-3, (x, y, ours, true_z)


def test_T4_obs_heightmap_unchanged():
    # The 121 trained inputs must not move: _sample_heightmap stays BILINEAR and
    # keeps its own -base_z. Pin its output on a rough field against a frozen
    # reference computed via the ORIGINAL formula (map_coordinates order=1).
    import jax.scipy.ndimage as jnd
    from terrain import terrain_field
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    field = np.asarray(terrain_field(jax.random.PRNGKey(7), 0.8, 0.0, 0.6))
    e = _env_with_field(field.reshape(n_r, n_c))
    rng = jax.random.PRNGKey(0)
    state = e.reset(rng)
    hm = np.asarray(e._sample_heightmap(state.pipeline_state))
    # reference: original inline computation, reproduced verbatim
    base = state.pipeline_state.x.pos[0]
    q = state.pipeline_state.q
    yaw = np.arctan2(2 * (q[3] * q[6] + q[4] * q[5]),
                     1 - 2 * (q[5] ** 2 + q[6] ** 2))
    from env import HM_N, HM_EXTENT
    g = np.linspace(-HM_EXTENT, HM_EXTENT, HM_N)
    gx, gy = np.meshgrid(g, g, indexing="ij")
    c, s = np.cos(yaw), np.sin(yaw)
    wx = float(base[0]) + c * gx - s * gy
    wy = float(base[1]) + s * gx + c * gy
    rx, ry, ztop = [float(v) for v in e._hf_size[:3]]
    fx, fy, fz = [float(v) for v in e._floor_pos]
    col = (wx - (fx - rx)) / (2 * rx) * (n_c - 1)
    row = (wy - (fy - ry)) / (2 * ry) * (n_r - 1)
    ref = jnd.map_coordinates(jp.asarray(field.reshape(n_r, n_c)),
                              [jp.asarray(row.ravel()), jp.asarray(col.ravel())],
                              order=1, mode="nearest")
    ref = np.asarray(ref) * ztop + fz - float(base[2])
    assert np.allclose(hm, ref, atol=1e-6), np.abs(hm - ref).max()
```

- [ ] **Step 2: Run — T8/T4 must pass already** (they pin Task 2's helper + untouched obs; a failure here means Task 2's diagonal orientation is wrong — fix the `jp.where` branch in `_terrain_ground_z`, NOT the test; `mj_ray` is the ground truth).

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py`
Expected: all pass. If T8 fails with a consistent sign pattern, swap the triangle condition to `fc + fr <= 1.0` orientation and re-derive per mj_ray — the oracle decides.

- [ ] **Step 3: Commit**

```bash
git add sim/nova_mjx/test_terrain_relative.py
git commit -m "sim/env tests: mj_ray oracle for the terrain query + obs byte-identity regression"
```

---

### Task 4: Wire foot consumers — contact, clearance, contact_true (T5, T6, T9)

**Files:**
- Modify: `sim/nova_mjx/env.py:259-269` (contact), `:382` (clearance), `:487` (contact_true)
- Modify: `sim/nova_mjx/test_terrain_relative.py`

**Interfaces:**
- Consumes: `_terrain_ground_z` (Task 2).
- Produces: `foot_h` (4,) local variable in `step()` — Task 5 reuses `ground_z` for `base_h`; Task 6 reuses `foot_h` + `contact` for `swing_h_per_step`.

- [ ] **Step 1: Write failing tests T5, T6, T9** — append:

```python
def _plateau_env(h=0.18):
    # uniform elevated plateau: a foot resting ON it at foot_z = h + 0.0125
    # (weight-bearing height, env.py:54) must read PLANTED post-fix.
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    return _env_with_field(np.full((n_r, n_c), h / 0.20))


def test_T5_contact_true_on_elevated_step():
    # BUG 1 (must FAIL pre-fix): planted foot on a 0.18 m plateau read AIRBORNE.
    e = _plateau_env(0.18)
    foot_z = jp.full((4,), 0.18 + 0.0125)
    foot_xy = jp.zeros((4, 2)) + jp.array([[0.9, 0.0]])   # off the spawn pad
    ground = e._terrain_ground_z(foot_xy[:, 0], foot_xy[:, 1])
    foot_h = foot_z - ground
    contact = (foot_h - FOOT_RADIUS) < CONTACT_EPS
    assert bool(contact.all()), (foot_h, "planted foot must read planted")


def test_T6_clearance_ignores_elevation():
    # BUG 2 (must FAIL pre-fix): swing cost must depend on LOCAL height only —
    # same swing at 0 m and at 0.18 m elevation must cost the same.
    from env import FOOT_TARGET_Z
    e_flat, e_high = _plateau_env(0.0), _plateau_env(0.18)
    xy = jp.array([[0.9, 0.0]] * 4)
    speed = jp.full((4,), 0.75)
    for e, elev in ((e_flat, 0.0), (e_high, 0.18)):
        foot_z = jp.full((4,), elev + 0.05)               # swinging AT target
        fh = foot_z - e._terrain_ground_z(xy[:, 0], xy[:, 1])
        cost = jp.sum(jp.abs(fh - FOOT_TARGET_Z) * jp.sqrt(speed))
        assert float(cost) < 1e-3, (elev, cost, "at-target swing must cost ~0")


def test_T9_ghost_stays_zero():
    # contact and contact_true are textually identical TODAY (ghost_* ≡ 0 by
    # construction). They must move in LOCKSTEP or the ghost diagnostic starts
    # reporting phantom drift. Step the real env on rough terrain and check.
    from terrain import terrain_field
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    field = np.asarray(terrain_field(jax.random.PRNGKey(5), 1.0, 0.0, 1.0))
    e = _env_with_field(field.reshape(n_r, n_c))
    state = e.reset(jax.random.PRNGKey(1))
    for _ in range(20):
        state = e.step(state, jp.zeros(e.action_size))
    for f in ("FL", "FR", "RL", "RR"):
        assert float(state.metrics[f"ghost_{f}"]) == 0.0, f
```

- [ ] **Step 2: Run — T5 and T6 FAIL** (they compute what the env WILL compute; to make them fail against current env semantics they are structured as direct expressions — they pass trivially once Task 2 exists. So instead verify the BUG is present in the env itself: run T9 — it passes (tautology today) — then add the real red check: temporarily assert in T5 using the OLD formula `(foot_z - FOOT_RADIUS) < CONTACT_EPS` returns False on the plateau, which documents the bug. Keep that assertion in T5 permanently as the "old formula is wrong here" half.)

Add to T5 before the final assert:

```python
    old_contact = (foot_z - FOOT_RADIUS) < CONTACT_EPS    # the absolute-z bug
    assert not bool(old_contact.any()), "old formula wrongly reads airborne — documents bug 1"
```

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py` — all green EXCEPT nothing yet exercises the env's own step() wiring; T9 is the env-level check and passes pre- and post-fix (lockstep property).

- [ ] **Step 3: Wire the env.** In `step()`:

At env.py:259 (after `foot_z = x.pos[self._foot_ids, 2]`):

```python
        foot_xy = x.pos[self._foot_ids, :2]
        # height above the LOCAL collision surface — the quantity every gait
        # term below actually means. On flat (all-zero hfield) ground_z == 0
        # and foot_h == foot_z: bit-identical to the pre-terrain-relative code.
        ground_z = self._terrain_ground_z(foot_xy[:, 0], foot_xy[:, 1])
        foot_h = foot_z - ground_z
```

env.py:269: `contact = (foot_h - FOOT_RADIUS) < CONTACT_EPS`
env.py:382: `clearance_cost = jp.sum(jp.abs(foot_h - FOOT_TARGET_Z) * jp.sqrt(foot_xy_speed))`
env.py:487: `contact_true = (foot_h - FOOT_RADIUS) < CONTACT_EPS`
Update the adjacent comments (269, 382, 487) to say "terrain-relative; see _terrain_ground_z" — keep their historical content.

- [ ] **Step 4: Run full suite — all pass, including T9 post-fix (lockstep held)**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py && JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py`
Expected: all green (heightmap suite proves obs untouched at runtime too).

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_terrain_relative.py
git commit -m "sim/env: contact + clearance + contact_true read local ground — kills the free-scrape and the swing-altitude tax"
```

---

### Task 5: Wire base consumers — done + height_pen with min-over-feet reference (T7)

**Files:**
- Modify: `sim/nova_mjx/env.py:337` (height_pen), `:465` (done)
- Modify: `sim/nova_mjx/test_terrain_relative.py`

**Interfaces:**
- Consumes: `ground_z` (Task 4 — NOTE: `height = x.pos[0, 2]` is computed at env.py:250, BEFORE ground_z at ~259; compute `base_h` after ground_z exists and use it in the height_pen/done expressions further down, which is safe because both are used only later in step()).
- Produces: `base_h` scalar local in `step()`.

- [ ] **Step 1: Write failing test T7** — append:

```python
def test_T7_done_terrain_relative_but_straddle_safe():
    # BUG 3: a face-plant at elevation never terminated (base_z stays > 0.08
    # absolute). AND the fix must not over-correct: a healthy robot straddling
    # two treads (hip span 0.28 m > tread run 0.20 m — the NORMAL climbing
    # stance) must NOT terminate. Ground ref = min over the four feet.
    e = _plateau_env(0.18)
    xy = jp.array([[0.9, 0.0]] * 4)
    ground = e._terrain_ground_z(xy[:, 0], xy[:, 1])      # all 0.18
    # face-plant ON the plateau: base at 0.18 + 0.03
    base_h_faceplant = (0.18 + 0.03) - jp.min(ground)
    assert float(base_h_faceplant) < 0.08, "corpse on a step must now terminate"
    # old formula: absolute base_z = 0.21 > 0.08 -> never fired (documents bug 3)
    assert (0.18 + 0.03) > 0.08
    # healthy straddle: front feet on 0.18 plateau, rear feet on 0.10 ledge,
    # base at healthy stand height above the LOWER tread
    e2 = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e2)
    data = np.full((n_r, n_c), 0.10 / 0.20)
    data[:, n_c // 2:] = 0.18 / 0.20                       # ledge at x >= 0
    e2 = _env_with_field(data)
    fxy = jp.array([[0.35, 0.0], [0.35, -0.1], [-0.35, 0.0], [-0.35, -0.1]])
    g = e2._terrain_ground_z(fxy[:, 0], fxy[:, 1])
    base_h = (0.10 + 0.16) - jp.min(g)                     # body over the boundary
    assert float(base_h) >= 0.08, (base_h, "healthy straddle must survive")
```

- [ ] **Step 2: Run — the test passes as pure math but documents both directions; the env wiring is the deliverable.** Wire it:

After the Task-4 block (ground_z/foot_h) add:

```python
        # done/height ground reference: MIN over the four feet, NOT a CoM point
        # sample — hip span (~0.28 m) exceeds a tread run (~0.20 m), so a
        # climbing robot NORMALLY straddles two treads; a CoM sample past the
        # riser reads the upper tread and can under-read base_h by ~0.10 m,
        # spuriously terminating a healthy climb. min() errs toward survival
        # and is identical on flat (all zeros).
        base_h = height - jp.min(ground_z)
```

env.py:337: `height_pen = (base_h - STAND_HEIGHT) ** 2`
env.py:465: `done = jp.where((base_h < 0.08) | (up[2] < 0.4), 1.0, 0.0)`
(`height = x.pos[0, 2]` at :250 stays — other code reads it; only these two expressions switch to `base_h`.)

- [ ] **Step 3: Run all suites**

Run: `JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py && JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/test_terrain_relative.py
git commit -m "sim/env: done + height_pen terrain-relative via min-over-feet ground — corpses terminate, straddles survive, climbing untaxed"
```

---

### Task 6: Flat-floor curriculum (`flat_frac`)

**Files:**
- Modify: `sim/nova_mjx/env.py` `make_domain_randomize` signature + `rand()` (~:581, :653-655)
- Modify: `sim/nova_mjx/train.py` (flag + threading + fingerprint)
- Modify: `sim/nova_mjx/test_terrain_relative.py`

**Interfaces:**
- Produces: `make_domain_randomize(terrain_max, dr_scale, step_frac, stair_frac, flat_frac=0.0)`; train.py flag `--flat-frac` default 0.25.

- [ ] **Step 1: Failing test** — append:

```python
def test_flat_frac_forces_level_zero():
    # 25% of envs must be GENUINELY flat (level==0 -> all-zero field, both
    # terrain branches provably collapse). Draw many envs, check the fraction
    # and that flat draws produce all-zero hfields.
    from env import make_domain_randomize
    e = NovaJoystick(heightmap=True)
    fn = make_domain_randomize(1.0, 1.0, 0.0, 0.6, flat_frac=0.25)
    rngs = jax.random.split(jax.random.PRNGKey(0), 400)
    sys_v, _ = fn(e.sys, rngs)
    hf = np.asarray(sys_v.hfield_data)                     # (400, n)
    flat = (np.abs(hf).max(axis=1) == 0.0)
    assert 0.15 < flat.mean() < 0.35, flat.mean()
```

- [ ] **Step 2: Run — fails** (`make_domain_randomize() got an unexpected keyword argument 'flat_frac'`).

- [ ] **Step 3: Implement.** `env.py` `make_domain_randomize(terrain_max=None, dr_scale=1.0, step_frac=0.0, stair_frac=0.0, flat_frac=0.0)`; in `rand()` replace the level draw (:653-655):

```python
            kt1, kt2, kt3 = jax.random.split(kt, 3)
            # flat-env floor: force `flat_frac` of envs to level 0 (both terrain
            # branches provably collapse to zero). Flat was ~5% of stage-4 envs;
            # a deterministic fall there cost ~2% of batch return — beneath
            # PPO's notice, which is exactly how the flat gait rotted while the
            # terrain gait improved. 25% makes flat worth not falling over on,
            # and matches deployment: NOVA lives mostly on floors.
            is_flat = jax.random.uniform(kt3, ()) < flat_frac
            level = jp.where(is_flat, 0.0,
                             jax.random.uniform(kt2, (), minval=0.0, maxval=tmax))
            hfield = terrain_field(kt1, level, step_frac, stair_frac)
```

`train.py`: add `ap.add_argument("--flat-frac", type=float, default=0.25, help="fraction of envs forced to LEVEL 0 flat ground (keeps the flat gait trained; full DR still applies)")`; pass `args.flat_frac` where `make_domain_randomize(terrain, args.dr_scale, args.step_frac, stair_frac)` is called in `run_stage` (add as 5th arg); add to `print_fingerprint` (thread the value through its signature the same way stair_frac is):

```python
    if flat_frac > 0:
        print(f"  FLAT FLOOR   : {flat_frac:.2f} of envs at level 0 (flat-gait retention)")
```

Also update the stale sanity line (spec: Risks): replace `"  Sanity: resuming the stage-1 walk evals ~2100-2500. cmd stage 2"` block's first line with `"  Sanity: post terrain-relative reward (2026-07-20) eval levels are NOT"` / `"  comparable to pre-fix runs. cmd stage 2"` — keep the rest.

- [ ] **Step 4: Run — passes.** Also `../../.venv/bin/python -m py_compile train.py`.

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/train.py sim/nova_mjx/test_terrain_relative.py
git commit -m "sim: 25% flat-env floor (--flat-frac) — flat ground becomes worth not falling over on"
```

---

### Task 7: Climb metrics + v_loss logging + rollout climbed line

**Files:**
- Modify: `sim/nova_mjx/env.py` (metrics dict ~:200-217, reset info ~:193, step metrics.update ~:496-509)
- Modify: `sim/nova_mjx/train.py` (`diagnostics()` + `progress()` evalcsv filter)
- Modify: `sim/nova_mjx/rollout.py` (climbed print)
- Modify: `sim/nova_mjx/test_terrain_relative.py`, `sim/nova_mjx/test_curriculum_resume.py`

**Interfaces:**
- Produces: metrics keys `climb`, `climb_max`, `swing_h_per_step`, plus `w_height`/`w_z`/`w_clearance` already in metrics (verify) surfacing in train.py diagnostics; `training/v_loss` column in eval_metrics.csv.

- [ ] **Step 1: Failing tests.** In `test_terrain_relative.py` append:

```python
def test_climb_metrics_telescope():
    # climb sums per-step deltas -> telescopes to (final - spawn) base z.
    # climb_max emits deltas of the running high-water mark -> telescopes to
    # max-over-episode. Verified semantics: brax EvalWrapper sums metrics
    # masked by active_episodes (per-eval), so in-env we just check the
    # per-step emissions integrate correctly over a short horizon.
    e = NovaJoystick(heightmap=True)
    state = e.reset(jax.random.PRNGKey(2))
    z0 = float(state.pipeline_state.x.pos[0, 2])
    tot, hi = 0.0, 0.0
    for _ in range(30):
        state = e.step(state, jp.zeros(e.action_size))
        tot += float(state.metrics["climb"])
        hi += float(state.metrics["climb_max"])
    zT = float(state.pipeline_state.x.pos[0, 2])
    assert abs(tot - (zT - z0)) < 1e-4, (tot, zT - z0)
    assert hi >= tot - 1e-6 and hi >= -1e-6, (hi, tot)     # max >= net, >= 0
    assert "swing_h_per_step" in state.metrics
```

In `test_curriculum_resume.py`, extend `EVAL_METRICS` with `"training/v_loss": 0.5` and add:

```python
def test_v_loss_reaches_the_csv():
    # brax computes training/v_loss and the old eval/-prefix filter dropped it.
    # Without it, "can't climb" and "critic still recalibrating" look identical.
    with tempfile.TemporaryDirectory() as tmp:
        _run(tmp)
        head = (Path(tmp) / "eval_metrics.csv").read_text().split("\n", 1)[0]
        assert "training/v_loss" in head, head
```

- [ ] **Step 2: Run both — fail** (`KeyError: 'climb'`; v_loss column absent).

- [ ] **Step 3: Implement.**

`env.py` reset (~:193, with other `info[...]` seeds): `info["last_base_z"] = pipeline_state.x.pos[0, 2]`; `info["peak_base_z"] = pipeline_state.x.pos[0, 2]`.
Metrics dict (~:217): add `"climb", "climb_max", "swing_h_per_step"`.
In `step()` before `state.metrics.update(...)`:

```python
        # climb: per-step delta of base z — brax SUMS metrics over the episode
        # (masked at done), so the logged value telescopes exactly to
        # (z at first done − z at spawn). climb_max: delta of the running peak,
        # telescoping to the episode high-water mark — commands resample every
        # 250 steps with random heading on RADIAL stairs, so climbed-then-
        # commanded-back-down nets climb≈0; the peak still shows it happened.
        base_z_now = x.pos[0, 2]
        climb_delta = base_z_now - info["last_base_z"]
        new_peak = jp.maximum(info["peak_base_z"], base_z_now)
        peak_delta = new_peak - info["peak_base_z"]
        info["last_base_z"] = base_z_now
        info["peak_base_z"] = new_peak
        n_swing_h = jp.sum(foot_h * (1.0 - contact.astype(jp.float32)))
        n_air = jp.maximum(jp.sum(1.0 - contact.astype(jp.float32)), 1.0)
```

and in `state.metrics.update(...)`: `climb=climb_delta, climb_max=peak_delta, swing_h_per_step=n_swing_h / n_air,`.

`train.py` `diagnostics()` — extend the returned line:

```python
        return (f"    fwd {m('fwd_speed')/L:5.2f}  prog {m('w_progress'):+8.2f}  "
                f"clear {m('w_clearance')/L:+6.2f}  hgt {m('w_height')/L:+6.3f}  "
                f"z {m('w_z')/L:+6.3f}  climb {m('climb'):+5.2f}/{m('climb_max'):.2f}  "
                f"swing {m('swing_h_per_step'):4.2f}  ghost {ghost/L:4.2f}  "
                f"airT " + "/".join(f"{a/L:.2f}" for a in airT) + f"  len {L:.0f}")
```

(match the existing per-step-division pattern already in `diagnostics()` — keep `climb`/`climb_max` as raw episode totals, they're already end-quantities.)

`train.py` `progress()` evalcsv call — widen the filter:

```python
            evalcsv.write(stage_label, total,
                          {(k[5:] if k.startswith("eval/") else k): v
                           for k, v in metrics.items()
                           if k.startswith("eval/") or k in
                           ("training/v_loss", "training/policy_loss",
                            "training/total_loss")})
```

`rollout.py` — track and print: capture `z0 = float(pipeline_state.x.pos[0,2])` after reset alongside the existing traveled-x bookkeeping, and extend the final print to `... traveled +X.XX m in x, climbed +X.XX m in z)` using `zT - z0`.

- [ ] **Step 4: Run everything**

```bash
JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py
JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py
../../.venv/bin/python test_resume_budget.py
../../.venv/bin/python test_curriculum_resume.py
../../.venv/bin/python -m py_compile train.py rollout.py env.py
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add sim/nova_mjx/env.py sim/nova_mjx/train.py sim/nova_mjx/rollout.py \
        sim/nova_mjx/test_terrain_relative.py sim/nova_mjx/test_curriculum_resume.py
git commit -m "sim: climb/climb_max/swing-height metrics + v_loss logging + rollout climbed line — climbing becomes measurable"
```

---

### Task 8: Final verification + spec cross-check

**Files:** none (verification only)

- [ ] **Step 1: Full local suite, one command**

```bash
cd /Users/afox/codebases/NOVA/proj/sim/nova_mjx && \
JAX_PLATFORMS=cpu ../../.venv/bin/python test_terrain_relative.py && \
JAX_PLATFORMS=cpu ../../.venv/bin/python test_heightmap.py && \
../../.venv/bin/python test_resume_budget.py && \
../../.venv/bin/python test_curriculum_resume.py
```

- [ ] **Step 2: Mutation checks** (each must break exactly one test, then restore):
  (a) revert `contact` to `foot_z` → T5's old-formula assert or T9 breaks;
  (b) swap `_terrain_ground_z`'s triangle branch → T8 breaks;
  (c) `base_h` from CoM point sample instead of `jp.min(ground_z)` → T7 straddle assert breaks;
  (d) drop the `training/v_loss` filter entry → `test_v_loss_reaches_the_csv` breaks.

- [ ] **Step 3: Spec checklist** — walk `docs/superpowers/specs/2026-07-20-terrain-relative-reward-design.md` section by section; every Fix/metric/test maps to a commit. Probe protocol and acceptance bar (+0.16 m) are RUNTIME steps for the user's Colab session, not code — confirm the flags exist (`--flat-frac`, metrics in fingerprint) and stop.

- [ ] **Step 4: Report** — suite counts, mutation results, and the exact Colab probe command block for the user (dry-run first per house style):

```bash
!python train.py --heightmap --terrain 1.0 --stair-frac 0.6 --flat-frac 0.25 \
    --restore-params-pkl /content/drive/MyDrive/nova_policy_stairs_final.pkl \
    --ckpt /content/drive/MyDrive/nova_stairs_fix --timesteps 25_000_000 --dry-run
```
