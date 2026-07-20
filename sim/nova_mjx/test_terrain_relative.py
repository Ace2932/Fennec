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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all terrain-relative tests passed")
