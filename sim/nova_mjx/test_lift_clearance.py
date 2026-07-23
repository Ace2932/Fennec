"""Lift-v5: COMMANDED footswing clearance target (cmd_c). The one-sided clearance
cost's target is now info["cmd_c"] — teacher samples it (observed, obs 227), blind
holds BLIND_FOOTSWING (unobserved, obs 105). Design:
docs/superpowers/specs/2026-07-23-lift-v5-design.md

  JAX_PLATFORMS=cpu python test_lift_clearance.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick, FOOTSWING_MIN, FOOTSWING_MAX, BLIND_FOOTSWING


def _moving_state(e, base_lift, key=7):
    # Manufacture feet at a controlled height ABOVE local ground with real xy
    # foot speed: lift the base by `base_lift` (flat env -> foot_h ≈ base_lift
    # + spawn foot_h ≈ base_lift) and give the joints velocity so the feet
    # sweep horizontally (foot xy speed comes from joint motion, not base fall).
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q.at[2].add(base_lift)
    qd = s.pipeline_state.qd.at[6:].set(2.0)          # all joints moving
    ps = e.pipeline_init(q, qd)
    return e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))


def _moving_state_with_c(e, base_lift, c, key=7):
    # _moving_state + an info override of the COMMANDED target cmd_c before the
    # step, so the clearance cost bills against `c`. (The resample fires only at
    # step % 250 == 0; a fresh reset steps to step 1, so the override survives the
    # step and drives the clearance term.)
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q.at[2].add(base_lift)
    qd = s.pipeline_state.qd.at[6:].set(2.0)
    ps = e.pipeline_init(q, qd)
    s = s.replace(pipeline_state=ps, info={**s.info, "cmd_c": jp.asarray(c)})
    return e.step(s, jp.zeros(e.action_size))


def test_cmd_c_in_info_and_range():
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(21))
    c = float(s.info["cmd_c"])
    assert FOOTSWING_MIN - 1e-6 <= c <= FOOTSWING_MAX + 1e-6, c


def test_obs_227_teacher_last_dim_is_c():
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(22))
    assert s.obs.shape[-1] == 227, s.obs.shape
    # last dim carries the (scaled) commanded footswing c — assert correlation,
    # not raw equality: override cmd_c, rebuild obs, confirm the last dim tracks
    # c monotonically and shares the cmd scaling's positive sign.
    lasts = [float(e._get_obs({**s.info, "cmd_c": jp.asarray(c)}, s.pipeline_state)[-1])
             for c in (0.02, 0.04, 0.06)]
    assert lasts[0] < lasts[1] < lasts[2], lasts
    assert all(v > 0 for v in lasts), lasts


def test_obs_105_blind_unchanged_c_fixed():
    e = NovaJoystick()                       # heightmap=False
    s = e.reset(jax.random.PRNGKey(23))
    assert s.obs.shape[-1] == 105, s.obs.shape
    assert abs(float(s.info["cmd_c"]) - BLIND_FOOTSWING) < 1e-9
    assert abs(BLIND_FOOTSWING - 0.05) < 1e-9


def test_clearance_targets_cmd_c():
    # same manufactured below-target state, two c values via info override:
    # a bigger deficit (c - foot_h) scales the bill more negative.
    e = NovaJoystick(heightmap=True)
    lo = _moving_state_with_c(e, 0.0, c=0.03, key=24)
    hi = _moving_state_with_c(e, 0.0, c=0.06, key=24)
    assert float(hi.metrics["w_clearance"]) < float(lo.metrics["w_clearance"]) < -0.01


def test_footswing_max_kwarg():
    # FOOTSWING_MAX default + kwarg narrows the teacher sample range.
    assert abs(FOOTSWING_MAX - 0.06) < 1e-9
    e = NovaJoystick(heightmap=True, footswing_max=0.04)
    for k in range(5):
        c = float(e.reset(jax.random.PRNGKey(k)).info["cmd_c"])
        assert FOOTSWING_MIN - 1e-6 <= c <= 0.04 + 1e-6, c


def test_above_target_lift_is_free():
    # THE ceiling removal: all four feet ~0.25 m above ground (>> 0.07 target),
    # joints sweeping (nonzero foot xy speed). One-sided cost -> ~0. The old
    # |foot_h - target| form bills every one of those feet -> clearly negative.
    e = NovaJoystick()
    s = _moving_state(e, 0.25)
    assert float(s.metrics["w_clearance"]) > -0.01, s.metrics["w_clearance"]


def test_below_target_still_bills():
    # The floor is untouched: feet at ground level (foot_h ≈ 0 < target) with
    # sweeping joints must still pay under-lift cost (same |·|-equal branch).
    e = NovaJoystick()
    s = _moving_state(e, 0.0)
    assert float(s.metrics["w_clearance"]) < -0.05, s.metrics["w_clearance"]


def test_below_target_matches_abs_form():
    # max(t-h, 0) == |h-t| for h<t: recompute the old form from state and confirm
    # the billed cost matches it (below target only). Blind env -> target is the
    # fixed BLIND_FOOTSWING (the |·|-equality invariant is target-agnostic).
    e = NovaJoystick()
    s = _moving_state(e, 0.0)
    ps = s.pipeline_state
    target = BLIND_FOOTSWING                          # blind env cmd_c is fixed here
    foot_ids = np.asarray(e._foot_ids)
    foot_h = np.asarray(ps.x.pos[foot_ids, 2])        # flat env: ground_z = 0
    v = np.linalg.norm(np.asarray(ps.xd.vel[foot_ids, :2]), axis=-1)
    mask = foot_h < target
    expected = -e._w_clearance * float(np.sum(np.abs(foot_h - target) * np.sqrt(v) * mask)
                            + np.sum(np.maximum(target - foot_h, 0.0) * np.sqrt(v) * (~mask)))
    assert abs(float(s.metrics["w_clearance"]) - expected) < 0.02, \
        (s.metrics["w_clearance"], expected)


def test_pose_gate_all_planted_identical():
    # all four feet planted at spawn-ish pose: the contact-gated formula must
    # reproduce the old 8-joint sum bit-identically (every leg's gate = 1).
    e = NovaJoystick()
    s = e.reset(jax.random.PRNGKey(11))
    s2 = e.step(s, jp.zeros(e.action_size))
    q = np.asarray(s2.pipeline_state.q[7:])
    default = np.asarray(e._default_pose)
    hk = np.array([1, 2, 4, 5, 7, 8, 10, 11])
    old = 0.5 * np.exp(-2.0 * np.sum((q[hk] - default[hk]) ** 2))
    # only valid if all feet actually in contact this step — check, else settle more
    ps = s2.pipeline_state
    foot_ids = np.asarray(e._foot_ids)
    foot_h = np.asarray(ps.x.pos[foot_ids, 2])
    assert (foot_h - 0.014 < 1e-3).all(), ("all-planted precondition broken", foot_h)
    assert abs(float(s2.metrics["w_pose"]) - old) < 1e-5, (s2.metrics["w_pose"], old)


def test_pose_gate_airborne_leg_flexes_free():
    # lift the whole robot (all feet airborne, contact=0 everywhere) and FLEX the
    # joints hard away from default: gated pose_rew = exp(-0) -> w_pose = 0.5 (max),
    # where the old formula would collapse toward 0. THE veto removal.
    e = NovaJoystick()
    s = e.reset(jax.random.PRNGKey(12))
    q = s.pipeline_state.q
    q = q.at[2].add(0.30)                                  # airborne
    hk = jp.array([1, 2, 4, 5, 7, 8, 10, 11]) + 7
    q = q.at[hk].add(0.6)                                  # hard flexion
    ps = e.pipeline_init(q, s.pipeline_state.qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    assert float(s2.metrics["w_pose"]) > 0.45, s2.metrics["w_pose"]


def test_air_max_default_06_and_kwarg_04():
    # feet airborne with 0.5 s accrued: default (0.6) bills nothing; air_max=0.4
    # (the old onset) bills. Same manufactured state both envs.
    def carry_at(e):
        s = e.reset(jax.random.PRNGKey(13))
        q = s.pipeline_state.q.at[2].add(0.30)             # all feet airborne
        ps = e.pipeline_init(q, s.pipeline_state.qd)
        s = s.replace(pipeline_state=ps,
                      info={**s.info, "feet_air": jp.full(4, 0.5)})
        s = e.step(s, jp.zeros(e.action_size))
        return float(s.metrics["w_carry"])
    assert abs(carry_at(NovaJoystick())) < 1e-6, "0.5s air must be free at AIR_MAX 0.6"
    assert carry_at(NovaJoystick(air_max=0.4)) < -0.01, "old onset must bill 0.5s air"


def test_w_clearance_default_6_and_scales():
    # same below-target moving state: default weight bills 3x the w_clearance=2.0 env.
    e6, e2 = NovaJoystick(), NovaJoystick(w_clearance=2.0)
    c6 = float(_moving_state(e6, 0.0, key=14).metrics["w_clearance"])
    c2 = float(_moving_state(e2, 0.0, key=14).metrics["w_clearance"])
    assert c2 < -0.01, c2
    assert abs(c6 / c2 - 3.0) < 0.05, (c6, c2)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all lift-clearance tests passed")
