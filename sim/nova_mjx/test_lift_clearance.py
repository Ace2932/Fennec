"""Lift-v5: COMMANDED footswing clearance target (cmd_c). The one-sided clearance
cost's target is now info["cmd_c"] — teacher samples it (observed, obs 227), blind
holds BLIND_FOOTSWING (unobserved, obs 105). Design:
docs/superpowers/specs/2026-07-23-lift-v5-design.md

  JAX_PLATFORMS=cpu python test_lift_clearance.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import (NovaJoystick, FOOTSWING_MIN, FOOTSWING_MAX, BLIND_FOOTSWING,
                 POSE_SHARPNESS)


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
    # reproduce the closed-form weighted 8-joint sum bit-identically (every leg's
    # gate = 1). LIFT-V5: the dev is now billed with PER-JOINT weights (hfe 1.0,
    # kfe 0.1), so the reference carries the same [1,0.1] per (hfe,kfe) pair.
    e = NovaJoystick()
    s = e.reset(jax.random.PRNGKey(11))
    s2 = e.step(s, jp.zeros(e.action_size))
    q = np.asarray(s2.pipeline_state.q[7:])
    default = np.asarray(e._default_pose)
    hk = np.array([1, 2, 4, 5, 7, 8, 10, 11])
    jw = np.array([1.0, 0.1] * 4)                     # (hfe,kfe) per leg, hk order
    old = 0.5 * np.exp(-POSE_SHARPNESS * np.sum((q[hk] - default[hk]) ** 2 * jw))
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


def _planted_pose_state(e, which, delta, key=11):
    # Manufacture a planted stance with `delta` flexion added to the (hfe|kfe)
    # joints of ALL FOUR legs, then step and read w_pose. Base is NOT lifted, so
    # every foot stays in contact (gate == 1 on all legs) and the pose penalty
    # actually bills. `which`: "hfe" or "kfe"; "none" = baseline (delta ignored).
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q
    if which == "hfe":
        idxs = jp.array([1, 4, 7, 10]) + 7     # hfe local idx per leg, +7 base offset
        q = q.at[idxs].add(delta)
    elif which == "kfe":
        idxs = jp.array([2, 5, 8, 11]) + 7     # kfe local idx per leg
        q = q.at[idxs].add(delta)
    ps = e.pipeline_init(q, s.pipeline_state.qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    ps2 = s2.pipeline_state
    foot_h = np.asarray(ps2.x.pos[np.asarray(e._foot_ids), 2])   # flat env: ground_z=0
    planted = bool((foot_h - 0.014 < 1e-3).all())
    return float(s2.metrics["w_pose"]), planted


def test_pose_knee_deweighted():
    # kfe (knee = the LIFT dof) dev is billed 0.1x the hfe dev inside the pose
    # regularizer (Playground per-joint [1,1,0.1]). Manufacture EQUAL flexion on
    # the hfe-only vs kfe-only joints of all four planted legs (shared spawn key
    # -> identical jitter, so the only difference is which joint moved): the
    # kfe-flexed pose income must sit far closer to the baseline than the
    # hfe-flexed one, and in log space the hfe penalty must be ~10x the kfe one.
    e = NovaJoystick()
    delta = 0.3
    base_wp, base_ok = _planted_pose_state(e, "none", 0.0)
    hfe_wp, hfe_ok = _planted_pose_state(e, "hfe", delta)
    kfe_wp, kfe_ok = _planted_pose_state(e, "kfe", delta)
    assert base_ok and hfe_ok and kfe_ok, \
        ("all-planted precondition broken", base_ok, hfe_ok, kfe_ok)
    # both flexions bill SOME pose penalty (income below the no-flex baseline)
    assert hfe_wp < base_wp and kfe_wp < base_wp, (base_wp, hfe_wp, kfe_wp)
    # knee de-weight -> kfe flexion is much less penalized -> closer to baseline
    assert kfe_wp > hfe_wp, (hfe_wp, kfe_wp)
    # log-space penalty (pose_rew = exp(-POSE_SHARPNESS*sum), so log(income) is
    # linear in the weighted dev sum) -> the ratio isolates the per-joint dev
    # weight (10x), softened by the one-step servo pull-back. NOTE the ratio ph/pk
    # is INVARIANT to POSE_SHARPNESS: both penalties carry the same POSE_SHARPNESS
    # factor, which cancels in the ratio (log-space isolates the dev-weight, not
    # the temperature). So the softer 0.5 exp compresses the raw incomes toward 1
    # but leaves this log-ratio band unchanged; assert the rough 10x, not exact.
    ph = np.log(base_wp) - np.log(hfe_wp)      # hfe penalty (weight 1.0)
    pk = np.log(base_wp) - np.log(kfe_wp)      # kfe penalty (weight 0.1)
    assert pk > 0.0, ("kfe flex must still bill something", pk)
    assert 5.0 < ph / pk < 16.0, ("expected ~10x dev-weight effect", ph / pk, ph, pk)


def _tilt_quat_about_y(theta):
    # axis-angle -> quat for a tilt of `theta` rad about the body y-axis:
    # q = [cos(t/2), 0, sin(t/2), 0]. env reads up = rotate(z, quat_inv(q)) =
    # [-sin(t), 0, cos(t)], so up_x^2 + up_y^2 = sin^2(theta) exactly.
    return jp.array([np.cos(theta / 2.0), 0.0, np.sin(theta / 2.0), 0.0])


def _upright_metric_at_tilt(e, theta_deg, key=31):
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q
    q = q.at[2].add(0.30)                                   # airborne: no righting torque
    q = q.at[3:7].set(_tilt_quat_about_y(np.radians(theta_deg)))
    ps = e.pipeline_init(q, jp.zeros(e.sys.nv))             # qd=0 -> orientation held
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    # w_upright = -2.5 * upright; the raw upright term = -w_upright / 2.5.
    return -float(s2.metrics["w_upright"]) / 2.5


def test_upright_deadzone():
    # Deadzone (lift-v5) frees tilts up to 25 deg (sin^2(25) = 0.179). A 10 deg
    # tilt (sin^2 = 0.030 < 0.179) still costs EXACTLY 0 where the old 2(1-cos)
    # form billed it; the billed case must now sit BEYOND the widened zone, so
    # use 35 deg (sin^2(35) = 0.329 > 0.179) — 25 deg is now the deadzone edge
    # (free), not a billed tilt.
    e = NovaJoystick()
    u10 = _upright_metric_at_tilt(e, 10.0)
    u35 = _upright_metric_at_tilt(e, 35.0)
    assert u10 == 0.0, ("10deg tilt must be inside the deadzone (0)", u10)
    assert u35 > 0.0, ("35deg tilt must bill beyond the 25deg deadzone", u35)


def test_w_air_weight():
    # w_air coefficient doubled 0.5 -> 1.0. Manufacture a LANDING: feet_air 0.3
    # (> the 0.2 window floor) entering the step, feet in contact this step
    # (first_contact fires), a nonzero forward command, and real forward base
    # velocity so cmd_moving and move_gate both open. The metrics expose air
    # (= air_rew) and move_gate, so the coefficient is reconstructable directly:
    # w_air must equal 1.0*move_gate*air_rew, and NOT the old 0.5*move_gate*air.
    e = NovaJoystick()
    s = e.reset(jax.random.PRNGKey(41))
    qd = s.pipeline_state.qd.at[0].set(0.3)                 # forward base velocity
    ps = e.pipeline_init(s.pipeline_state.q, qd)
    s = s.replace(pipeline_state=ps,
                  info={**s.info,
                        "cmd": jp.array([0.3, 0.0, 0.0]),   # forward command
                        "feet_air": jp.full(4, 0.3)})       # past the 0.2 window floor
    s2 = e.step(s, jp.zeros(e.action_size))
    air = float(s2.metrics["air"])                          # = air_rew
    move_gate = float(s2.metrics["move_gate"])
    w_air = float(s2.metrics["w_air"])
    # the landing actually scored (else the coefficient assertion is vacuous)
    assert air > 0.0 and move_gate > 0.0 and w_air > 0.0, (air, move_gate, w_air)
    # coefficient is 1.0 (doubled), verified against the observable reconstruction
    assert abs(w_air - 1.0 * move_gate * air) < 1e-6, (w_air, move_gate, air)
    # and it is NOT the old 0.5 coefficient
    assert abs(w_air - 0.5 * move_gate * air) > 1e-3, (w_air, move_gate, air)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all lift-clearance tests passed")
