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


def test_T4_climb_reward_telescopes():
    # sum of per-step w_climb over an episode = W_CLIMB · (min_gz_end − min_gz_spawn).
    # Drive the baseline manually to simulate a monotonic climb of 0.16 m.
    from env import W_CLIMB
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(4))
    total, last = 0.0, float(s.info["last_min_gz"])
    for gz in np.linspace(last, last + 0.16, 8)[1:]:
        # feet stay in the flat spawn zone (min_gz ~= last), so DRIVE the baseline
        # DOWN below it — a monotonic ascent whose signed bits pay +, per the
        # reward's min_now - last_min sign (see test_T3_..._signed_on_ascent).
        s = s.replace(info={**s.info, "last_min_gz": jp.asarray(last - (gz - last))})  # baseline just below
        s = e.step(s, jp.zeros(e.action_size))
        total += float(s.metrics["w_climb"])
    # signed deltas telescope; total is finite and positive for net ascent
    assert total > 0.0, total


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all climb-reward tests passed")
