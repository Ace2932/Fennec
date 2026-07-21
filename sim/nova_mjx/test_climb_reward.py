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
