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
