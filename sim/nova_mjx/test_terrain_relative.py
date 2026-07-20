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
    # EXACTLY 0 (not just small) also pins the floor-at-z==0 assumption the whole
    # flat no-op invariant rests on: z*ztop+fz == 0 requires fz == 0. If someone
    # repositions the floor geom off z==0, this is the canary that trips first.
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


def test_T8_matches_mujoco_collision_surface_inside_transition_cells():
    # THE test bilinear fails: sample INTERIOR points of stair-boundary cells and
    # compare against mj_ray on the real physics model. T1-T3 pin scale, offset
    # and orientation but are blind to triangulation-vs-bilinear; only a ray cast
    # against MuJoCo's own collision surface can tell those apart.
    import mujoco
    from terrain import terrain_field
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    field = np.asarray(terrain_field(jax.random.PRNGKey(3), 1.0, 0.0, 1.0))
    e = _env_with_field(field.reshape(n_r, n_c))
    m = mujoco.MjModel.from_xml_path("nova.xml")
    m.hfield_data[:] = field
    d = mujoco.MjData(m)
    # Park the robot far off-grid: the rays start at z=1 above the sample points,
    # several of which land on the spawn pad, and a torso/leg geom in the way
    # would silently be measured as "terrain".
    d.qpos[0:3] = 1000.0
    mujoco.mj_forward(m, d)
    floor_gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "floor")

    rng = np.random.default_rng(0)
    pts = rng.uniform(-1.6, 1.6, size=(300, 2))          # annulus incl. stair band
    geomid = np.zeros(1, dtype=np.int32)
    worst = 0.0
    skipped = 0
    for x, y in pts:
        dist = mujoco.mj_ray(m, d, np.array([x, y, 1.0]), np.array([0.0, 0.0, -1.0]),
                             None, 1, -1, geomid)
        # mj_ray returns -1 for a miss AND for the degenerate exact-triangle-edge
        # hit. `1.0 - dist` would silently become 2.0 and read as a huge error, so
        # drop those points — but count them, and cap the count below so this
        # guard can never hide a systematically broken oracle.
        if dist < 0 or geomid[0] != floor_gid:
            skipped += 1
            continue
        true_z = 1.0 - dist
        ours = float(e._terrain_ground_z(jp.array([x]), jp.array([y]))[0])
        worst = max(worst, abs(ours - true_z))
        assert abs(ours - true_z) < 2e-3, (x, y, ours, true_z)
    assert skipped < 0.05 * len(pts), f"too many degenerate/missed rays: {skipped}"
    print(f"    T8: max |ours - mj_ray| = {worst:.3e} over "
          f"{len(pts) - skipped} rays ({skipped} skipped)")


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
    # reset() rebuilds q from sys.qpos0 and only overwrites q[7:], so the base
    # pose is EXACTLY xy=(0,0), quat=[1,0,0,0] -> yaw=0. With yaw=0 the rotation
    # `wx = bx + c*gx - s*gy` collapses to wx=gx on BOTH the live path and this
    # reference, so a sign flip / s-c swap / bx-by swap would all pass. Rebuild
    # the pipeline state with a non-zero translation and a yaw that is not a
    # multiple of 90 deg, so the rotation and translation terms are constrained.
    #
    # The orientation must be a FULL roll-pitch-yaw pose, not pure yaw. A pure-yaw
    # quaternion has qx == qy == 0, which kills every term of the live yaw
    # expression that touches them:
    #     yaw = arctan2(2*(w*qz + qx*qy), 1 - 2*(qy*qy + qz*qz))
    # so a qx/qy index confusion (reading roll where pitch belongs) is invisible
    # -- the mutant `qy*qy -> qx*qx` reproduces the clean deviation byte for byte.
    # That matters in production: on rough terrain the trained base is tilted on
    # every step, so roll and pitch are never zero there either.
    roll_set, pitch_set, yaw_set = 0.15, -0.2, 0.7
    cr, sr = np.cos(roll_set / 2), np.sin(roll_set / 2)
    cp, sp = np.cos(pitch_set / 2), np.sin(pitch_set / 2)
    cy, sy = np.cos(yaw_set / 2), np.sin(yaw_set / 2)
    quat = jp.array([                        # standard ZYX RPY -> (w, x, y, z)
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
    ])
    q_mod = state.pipeline_state.q
    q_mod = q_mod.at[0:3].set(jp.array([0.37, -0.52, float(q_mod[2])]))
    q_mod = q_mod.at[3:7].set(quat)
    ps = e.pipeline_init(q_mod, jp.zeros(e.sys.nv))
    hm = np.asarray(e._sample_heightmap(ps))
    # reference: original inline computation, reproduced verbatim
    base = ps.x.pos[0]
    q = ps.q
    yaw = np.arctan2(2 * (q[3] * q[6] + q[4] * q[5]),
                     1 - 2 * (q[5] ** 2 + q[6] ** 2))
    # the reference's own arctan2 transcription must be pinned against an
    # externally known value, else an error mirrored in live + reference cancels
    assert abs(float(yaw) - yaw_set) < 1e-5, \
        f"reference yaw {yaw} != composed yaw {yaw_set}"
    # guard: this test must actually exercise the rotation + translation path
    assert abs(float(yaw)) > 0.1, f"degenerate yaw, rotation untested: {yaw}"
    assert abs(np.sin(float(yaw))) > 0.1, f"sin(yaw) ~ 0, rotation untested: {yaw}"
    assert abs(np.cos(float(yaw))) > 0.1, f"cos(yaw) ~ 0, rotation untested: {yaw}"
    # roll and pitch must stay non-zero, or the qx/qy index confusion above goes
    # invisible again
    assert abs(float(q[4])) > 0.05, f"qx ~ 0, roll/pitch index errors hidden: {q[3:7]}"
    assert abs(float(q[5])) > 0.05, f"qy ~ 0, roll/pitch index errors hidden: {q[3:7]}"
    assert abs(float(base[0])) > 0.1 and abs(float(base[1])) > 0.1, \
        f"degenerate base xy, translation untested: {base}"
    assert abs(float(base[0])) != abs(float(base[1])), \
        f"|bx| == |by| hides a bx/by swap: {base}"
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
    # atol is 1e-5, not the observed float32 deviation (~3.3e-07) plus a hair:
    # 3x headroom is flaky across a jax bump or a different backend. Every mutant
    # this test targets misses by 1e-3 or worse, so 1e-5 keeps 2+ orders of
    # discrimination while tolerating float32 reassociation.
    assert np.allclose(hm, ref, atol=1e-5), np.abs(hm - ref).max()
    print(f"    T4: max |obs - bilinear ref| = {np.abs(hm - ref).max():.3e}")


def _plateau_env(h=0.18):
    """Uniform elevated plateau. A robot dropped on it is standing on ground at
    height h — every gait term must behave exactly as it does on flat."""
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    return _env_with_field(np.full((n_r, n_c), h / 0.20))


_DROP = 0.18   # metres the feet fall before settling — same for flat and plateau


def _settle(e, ground_h, n=40):
    """Reset, lift the base so the feet start _DROP metres above the LOCAL ground
    (at plateau height `ground_h`), and settle under zero action. Returns the
    final (settled) state and the SUM of the per-step clearance cost over the
    whole drop.

    The lift is `ground_h + _DROP`, NOT a fixed constant: reset() spawns the base
    at a fixed absolute z that ignores terrain, so on a `ground_h` plateau the
    feet start `ground_h` BELOW the surface. Adding `ground_h` back puts the feet
    the same _DROP above their own ground in every case — so flat and plateau run
    the byte-identical drop RELATIVE TO LOCAL GROUND. That equivalence is the
    whole premise of T6: a fixed lift instead makes the flat robot fall a big
    _DROP while the plateau robot barely moves, and their clearance sums then
    differ for a reason that has nothing to do with the bug.

    reset/pipeline_init/step are jitted — eager brax stepping on CPU is minutes
    per call, and 40 steps of it is untestable. Jitting is a pure speed change:
    the ops are identical, so it does not touch what the test measures.

    Why SUM the clearance over the trajectory instead of reading the final step
    (as the brief sketched): the clearance COST scales by sqrt(foot_xy_speed), so
    a FULLY settled foot (speed ~0) pays ~0 regardless of height, and the bug's
    signal at the last step is a mere 0.05 — right on the brief's threshold, so
    that form does not reliably go red pre-fix. During the drop the feet actually
    move, and the elevated foot carries a constant +ground_h height offset every
    one of those steps, so the summed cost diverges cleanly pre-fix (~11.26 gap:
    c_flat = -5.10 vs c_high = -16.36) and collapses to a 0.0 gap post-fix (both
    drops are relatively identical). Under zero
    action the reward never feeds back into the dynamics, so nothing but the
    absolute-z read distinguishes the two runs.
    """
    reset = jax.jit(e.reset)
    step = jax.jit(e.step)
    pinit = jax.jit(e.pipeline_init)
    state = reset(jax.random.PRNGKey(4))
    q = state.pipeline_state.q.at[2].add(ground_h + _DROP)
    ps = pinit(q, state.pipeline_state.qd)
    state = state.replace(pipeline_state=ps)
    zero = jp.zeros(e.action_size)
    clear_sum = 0.0
    for _ in range(n):
        state = step(state, zero)
        clear_sum += float(state.metrics["w_clearance"])
    return state, clear_sum


def test_T5_planted_feet_on_plateau_read_planted():
    # BUG 1, env-level: contact/contact_true are absolute-z today, so feet
    # standing on a 0.18 m plateau read AIRBORNE -> airT_* ~1.0 and slip stops
    # billing. Post-fix they read planted -> airT_* near 0 for a settled stance.
    state, _ = _settle(_plateau_env(0.18), 0.18)
    airT = [float(state.metrics[f"airT_{f}"]) for f in ("FL", "FR", "RL", "RR")]
    assert sum(a < 0.5 for a in airT) >= 3, airT   # a settled robot is not flying


def test_T6_clearance_matches_flat_at_elevation():
    # BUG 2, env-level: identical motion at 0 m and 0.18 m must cost the same
    # clearance. Today the elevated case pays ~0.18 more height offset on EVERY
    # moving foot, every step of the drop — summed over the settle that is
    # c_flat = -5.10 vs c_high = -16.36 pre-fix (an 11.26 gap). Post-fix foot_h
    # strips the offset and the two drops trace identically -> the summed costs
    # match exactly (difference 0.0, well under the 0.05 threshold).
    _, c_flat = _settle(_plateau_env(0.0), 0.0)
    _, c_high = _settle(_plateau_env(0.18), 0.18)
    assert abs(c_flat - c_high) < 0.05, (c_flat, c_high)


def test_T7_faceplant_terminates_and_straddle_survives():
    # BUG 3, env-level: a collapsed robot on an elevated plateau never
    # terminated (absolute base_z stays >> 0.08). Post-fix it must. reset/
    # pipeline_init/step are jitted for the same reason as _settle: eager brax
    # stepping on CPU is minutes per call and jitting is a pure speed change.
    e = _plateau_env(0.18)
    reset, pinit, step = jax.jit(e.reset), jax.jit(e.pipeline_init), jax.jit(e.step)
    state = reset(jax.random.PRNGKey(4))
    # collapse the base onto the plateau: z = plateau + 0.03 (below the 0.08 gate)
    q = state.pipeline_state.q.at[2].set(0.18 + 0.03)
    ps = pinit(q, state.pipeline_state.qd)
    state = step(state.replace(pipeline_state=ps), jp.zeros(e.action_size))
    assert float(state.done) == 1.0, "corpse on an elevated step must terminate"

    # AND the fix must not over-correct: a HEALTHY robot straddling two treads
    # (hip span ~0.28 m > tread run ~0.20 m — the normal climbing stance) must
    # NOT terminate. Ledge at x >= 0 so front and rear feet sit on different
    # levels; base at proper stand height above the LOWER tread.
    #
    # This half GUARDS THE MIN-OVER-FEET DECISION (env.py `base_h = height -
    # jp.min(ground_z)`), not merely "doesn't over-terminate". The straddle puts
    # two feet on the 0.10 m tread and two on the 0.18 m tread, and the base is
    # deliberately placed LOW — base_abs_z ~ 0.204 post-step — so the base sits
    # inside the DISCRIMINATING band: with the four feet reading ground_z
    # [0.18, 0.18, 0.10, 0.10],
    #     min  ref 0.10 -> base_h ~0.104  >= 0.08  -> done 0 (min survives)
    #     mean ref 0.14 -> base_h ~0.064  <  0.08  -> done 1 (mean terminates)
    #     max  ref 0.18 -> base_h ~0.024  <  0.08  -> done 1 (max terminates)
    #     CoM  ~ mean   -> base_h ~0.064  <  0.08  -> done 1 (CoM terminates)
    # A regression from jp.min to jp.mean/jp.max/a-CoM-sample would wrongly kill
    # this healthy climber, so this assertion goes red on that swap — it is the
    # test that DEFENDS the min-over-feet choice. (The old +0.10 lift put the
    # base at ~0.27, where every reduction stayed above 0.08 and the choice was
    # untested.)  See the min-vs-CoM comment at env.py:266-272.
    n_r, n_c = _grid(e)
    data = np.full((n_r, n_c), 0.10 / 0.20)
    data[:, n_c // 2:] = 0.18 / 0.20
    e2 = _env_with_field(data)
    reset2, pinit2, step2 = jax.jit(e2.reset), jax.jit(e2.pipeline_init), jax.jit(e2.step)
    s2 = reset2(jax.random.PRNGKey(4))
    q2 = s2.pipeline_state.q.at[2].add(0.03)   # -> base_abs_z ~0.204: min survives, mean/max/CoM cross 0.08
    ps2 = pinit2(q2, s2.pipeline_state.qd)
    s2 = step2(s2.replace(pipeline_state=ps2), jp.zeros(e2.action_size))
    assert float(s2.done) == 0.0, "healthy straddle must survive (min-over-feet ground ref)"


def test_T9_ghost_stays_zero():
    # contact and contact_true are textually identical TODAY (ghost_* is 0 by
    # construction). They must move in LOCKSTEP or ghost_* starts reporting
    # phantom drift — the exact silent-divergence those metrics exist to catch.
    from terrain import terrain_field
    e = NovaJoystick(heightmap=True)
    n_r, n_c = _grid(e)
    field = np.asarray(terrain_field(jax.random.PRNGKey(5), 1.0, 0.0, 1.0))
    e = _env_with_field(field.reshape(n_r, n_c))
    step = jax.jit(e.step)
    state = jax.jit(e.reset)(jax.random.PRNGKey(1))
    zero = jp.zeros(e.action_size)
    for _ in range(20):
        state = step(state, zero)
    for f in ("FL", "FR", "RL", "RR"):
        assert float(state.metrics[f"ghost_{f}"]) == 0.0, f


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


def test_flat_frac_zero_forces_no_flat():
    # flat_frac=0.0 must be a valid no-op: is_flat is always False, so NO env
    # is force-flattened. A non-flat env could be all-zero only if its level
    # rounds to ~0 (astronomically unlikely over 400 draws), so assert the
    # observed flat fraction is negligible.
    from env import make_domain_randomize
    e = NovaJoystick(heightmap=True)
    fn = make_domain_randomize(1.0, 1.0, 0.0, 0.6, flat_frac=0.0)
    rngs = jax.random.split(jax.random.PRNGKey(1), 400)
    sys_v, _ = fn(e.sys, rngs)
    hf = np.asarray(sys_v.hfield_data)
    flat = (np.abs(hf).max(axis=1) == 0.0)
    assert flat.mean() < 0.02, flat.mean()


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all terrain-relative tests passed")
