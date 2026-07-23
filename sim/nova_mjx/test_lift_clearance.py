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
    expected = -2.0 * float(np.sum(np.abs(foot_h - e._foot_target_z) * np.sqrt(v) * mask)
                            + np.sum(np.maximum(e._foot_target_z - foot_h, 0.0) * np.sqrt(v) * (~mask)))
    assert abs(float(s.metrics["w_clearance"]) - expected) < 0.02, \
        (s.metrics["w_clearance"], expected)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all lift-clearance tests passed")
