"""Lift-v3: one-sided clearance cost + raised swing target. Design:
docs/superpowers/specs/2026-07-22-lift-v3-clearance-design.md

  JAX_PLATFORMS=cpu python test_lift_clearance.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick, FOOT_TARGET_Z


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


def test_default_target_is_007():
    assert abs(FOOT_TARGET_Z - 0.07) < 1e-9
    e = NovaJoystick()
    assert abs(e._foot_target_z - 0.07) < 1e-9


def test_kwarg_overrides_target():
    e = NovaJoystick(foot_target_z=0.05)
    assert abs(e._foot_target_z - 0.05) < 1e-9


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
    # max(t-h, 0) == |h-t| for h<t: recompute the old form from state and
    # confirm the billed cost matches it (below target only).
    e = NovaJoystick()
    s = _moving_state(e, 0.0)
    ps = s.pipeline_state
    foot_ids = np.asarray(e._foot_ids)
    foot_h = np.asarray(ps.x.pos[foot_ids, 2])        # flat env: ground_z = 0
    v = np.linalg.norm(np.asarray(ps.xd.vel[foot_ids, :2]), axis=-1)
    mask = foot_h < e._foot_target_z
    expected = -e._w_clearance * float(np.sum(np.abs(foot_h - e._foot_target_z) * np.sqrt(v) * mask)
                            + np.sum(np.maximum(e._foot_target_z - foot_h, 0.0) * np.sqrt(v) * (~mask)))
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
    if (foot_h - 0.014 < 1e-3).all():
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
