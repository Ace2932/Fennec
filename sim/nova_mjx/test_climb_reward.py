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


def test_T4_climb_reward_signed_accumulation():
    # SIGNED-ACCUMULATION smoke test (NOT a true telescope — a zeros action keeps
    # the feet in the flat spawn zone so min_gz stays 0; we drive the baseline by
    # hand). The real (final − spawn) telescoping is a property of brax's episode
    # metric-sum, verified for `climb` in test_terrain_relative. Here we only
    # confirm w_climb is SIGNED and accumulates + when min_gz sits above the
    # baseline: drive the baseline DOWN below the (constant 0) min_gz, so each
    # step pays w_climb·(0 − baseline) > 0 (see test_T3_..._signed_on_ascent).
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(4))
    total, last = 0.0, float(s.info["last_min_gz"])
    for gz in np.linspace(last, last + 0.16, 8)[1:]:
        s = s.replace(info={**s.info, "last_min_gz": jp.asarray(last - (gz - last))})  # baseline below min_gz
        s = e.step(s, jp.zeros(e.action_size))
        total += float(s.metrics["w_climb"])
    assert total > 0.0, total


def _stair_env_beta(beta, level=1.0):
    # a staircase env with a nonzero PBRS density weight (--beta-climb)
    e = NovaJoystick(heightmap=True, beta_climb=beta)
    field = np.asarray(terrain_field(jax.random.PRNGKey(0), level, 0.0, 1.0))
    e.sys = e.sys.tree_replace({"hfield_data": jp.asarray(field)})
    return e


def test_beta_climb_default_is_zero():
    # THE no-op guarantee: with the default beta_climb (0.0) the density term is
    # 0·anything ≡ 0.0 EXACTLY, even on a stair env with a live mean_gz Δ. This is
    # what keeps a --beta-climb-0 run bit-identical to the #131 min-only reward.
    e = _stair_env(1.0)                       # default beta_climb=0
    s = _step_settle(e, 1)
    assert s.metrics["w_beta_climb"] == 0.0, s.metrics["w_beta_climb"]


def test_beta_climb_zero_on_flat():
    # On flat terrain the mean terrain-height-under-foot never changes (Δ0), so the
    # density term is 0 even with beta ON — mirrors the min-term flat no-op (T3).
    e = NovaJoystick(heightmap=True, beta_climb=10.0)   # default hfield = flat
    s = _step_settle(e, 1)
    assert abs(float(s.metrics["w_beta_climb"])) < 1e-6, s.metrics["w_beta_climb"]


def test_beta_climb_signed():
    # SIGNED (mirrors the T3 min test): drive last_mean_gz DOWN below the current
    # mean -> density pays + (feet advanced up); drive it UP -> pays - (descent).
    e = _stair_env_beta(10.0, 1.0)
    s = e.reset(jax.random.PRNGKey(2))
    s_up = s.replace(info={**s.info, "last_mean_gz": s.info["last_mean_gz"] - 0.05})
    s_up = e.step(s_up, jp.zeros(e.action_size))
    assert float(s_up.metrics["w_beta_climb"]) > 0.0, "mean above baseline must pay +"
    s_dn = s.replace(info={**s.info, "last_mean_gz": s.info["last_mean_gz"] + 0.05})
    s_dn = e.step(s_dn, jp.zeros(e.action_size))
    assert float(s_dn.metrics["w_beta_climb"]) < 0.0, "mean below baseline must pay -"


def test_clip_scales_with_w_climb():
    # The reward clip must LIFT with w_climb: manufacture a big ascent (raw climb
    # term ≈ w_climb·0.3 = 30) that would be silently truncated to 10 under #131's
    # fixed ±10 clip; confirm the reward exceeds 10 (clip lifted) yet stays bounded
    # by the new CLIP = 10 + w_climb·0.08.
    e = _stair_env(1.0)
    e._w_climb = 100.0
    s = e.reset(jax.random.PRNGKey(5))
    s_up = s.replace(info={**s.info, "last_min_gz": s.info["last_min_gz"] - 0.3})
    s_up = e.step(s_up, jp.zeros(e.action_size))
    r = float(s_up.reward)
    assert r > 10.0, ("clip must lift above the old fixed 10 bound", r)
    assert r <= 10.0 + 100.0 * 0.08 + 1e-3, ("clip must still bound at 10+w_climb·0.08", r)


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
    # terrain.py centers on the true (even-N) grid center (n-1)/2.0 = 49.5, not the
    # integer cell 49; the reference must use the SAME center or it shears by one
    # column at the stair transition (the invariant is about the geometry, not the
    # rounding of the center). All other T1 tests slice loosely so 49 suffices there.
    c = (TN - 1) / 2.0
    yy, xx = np.mgrid[0:TN, 0:TN]
    d = xx - c
    step_idx = np.floor(np.clip((d - FLAT_R) / STAIR_RUN_CELLS, 0.0, None))
    ref = np.clip(step_idx * STAIR_RISE / TZ, 0.0, 1.0)
    assert np.allclose(f, ref, atol=1e-6), "level-1.0 stair geometry must be unchanged"


def test_pbrs_zero_on_flat():
    # flat hfield: Φ ≡ 0 -> delta exactly 0 even with w_pbrs ON. Flat no-op invariant.
    e = NovaJoystick(heightmap=True, w_pbrs=30.0)
    s = _step_settle(e, 1)
    assert abs(float(s.metrics["w_pbrs_climb"])) < 1e-6, s.metrics["w_pbrs_climb"]


def test_pbrs_reset_seeds_last_phi():
    e = _stair_env(1.0)
    s = e.reset(jax.random.PRNGKey(1))
    assert "last_phi" in s.info
    # spawn Φ ~ 0 at EVERY level: the first elevated cell sits past the ground-
    # level tread (≥0.4 m out) — beyond the 0.35 m lookahead — at all levels, not
    # just level 1 (see task-2 report 2026-07-22, test_pbrs_phi_positive_within_short_advance).
    assert abs(float(s.info["last_phi"])) < 1e-3, s.info["last_phi"]


def test_pbrs_phi_positive_within_short_advance():
    # Spawn Φ is 0 (first ELEVATED cell sits past the ground-level tread, ≥0.4 m
    # out — outside the 0.35 m lookahead; see task-2 report 2026-07-22). The
    # requirement that matters: after a SHORT forward advance under the velocity
    # command (~0.2 m, a second of walking), the lookahead sweeps onto risers and
    # the PBRS gradient goes live. Level 0.125, STAIR_PAD_MIN=4: pad 5 cells
    # (0.25 m) + 4-cell tread -> first elevated cell ~0.45 m; base at 0.20 m puts
    # lookahead points at 0.35/0.45/0.55 m -> two elevated -> Φ > 0.
    e = _stair_env(0.125)
    s = e.reset(jax.random.PRNGKey(4))
    q = s.pipeline_state.q.at[0].add(0.20)          # advance base 0.20 m in +x
    ps = e.pipeline_init(q, s.pipeline_state.qd)
    assert float(e._lookahead_phi(ps)) > 0.0


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all climb-reward tests passed")
