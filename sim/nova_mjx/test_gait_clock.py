"""Gait-clock-v6: COMMANDED trot timing. A per-env trot clock (info["gait_phase"]
θ advanced by info["cmd_f"]·dt) drives a smoothed stance/swing schedule; a
cmd_moving-gated COST bills schedule violations. Teacher-only (obs 227->230);
blind (heightmap=False) carries NO clock and its 105-d obs + reward are
byte-unchanged. Design:
docs/superpowers/specs/2026-07-24-gait-clock-v6-design.md

  JAX_PLATFORMS=cpu python test_gait_clock.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import (NovaJoystick, F_MIN, F_MAX, BLIND_CMD_F, GAIT_DUTY, GAIT_SMOOTH,
                 GAIT_OFFSETS, W_GAIT, F_OBS_SCALE)

# leg base offsets into q[7:] in LEG_NAMES order (FL,FR,RL,RR): [haa,hfe,kfe] each
_LEG_BASE = {"FL": 0, "FR": 3, "RL": 6, "RR": 9}
# diagonal pairs. Lifting the base then EXTENDING the named legs' (hfe,kfe) by
# (-0.5, +0.8) plants ONLY those feet (empirically calibrated on the flat env):
#   legs_down=[FL,RR] -> contact [1,0,0,1]  (compliant with the θ=0.25 schedule)
#   legs_down=[FR,RL] -> contact [0,1,1,0]  (anti-phase with it)
_COMPLIANT_LEGS = ["FL", "RR"]
_ANTI_LEGS = ["FR", "RL"]


def _contact(e, ps):
    """Radius-corrected contact per foot (flat env: ground_z==0), as the reward
    computes it. (4,) bool in LEG_NAMES order."""
    foot_z = np.asarray(ps.x.pos[np.asarray(e._foot_ids), 2])
    return (foot_z - 0.014) < 1e-3


def _split_state(e, legs_down, theta, cmd, key=7):
    """Manufacture a step with a chosen diagonal contact split + clock phase +
    command. Lift the base 0.03 (all feet airborne), then extend `legs_down` back
    to the floor so exactly those feet plant. Override gait_phase=theta and the
    command before stepping (the resample fires only at step%250, so a fresh
    reset's first step preserves the overrides)."""
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q.at[2].add(0.03)
    for leg in legs_down:
        b = 7 + _LEG_BASE[leg]
        q = q.at[b + 1].add(-0.5).at[b + 2].add(0.8)     # hfe -0.5, kfe +0.8
    ps = e.pipeline_init(q, jp.zeros(e.sys.nv))
    s = s.replace(pipeline_state=ps,
                  info={**s.info, "gait_phase": jp.asarray(theta),
                        "cmd": jp.asarray(cmd, dtype=jp.float32)})
    return e.step(s, jp.zeros(e.action_size))


def test_clock_advances_and_wraps():
    # θ(t+1) == frac(θ(t) + cmd_f·dt), and it wraps past 1.
    e = NovaJoystick(heightmap=True)
    s0 = e.reset(jax.random.PRNGKey(3))
    th0 = float(s0.info["gait_phase"])
    f0 = float(s0.info["cmd_f"])
    s1 = e.step(s0, jp.zeros(e.action_size))
    expected = (th0 + f0 * e._dt) % 1.0
    assert abs(float(s1.info["gait_phase"]) - expected) < 1e-6, \
        (float(s1.info["gait_phase"]), expected)
    # wrap: phase 0.99 + 2.0Hz·0.02s = 1.03 -> frac 0.03
    s = s0.replace(info={**s0.info, "gait_phase": jp.asarray(0.99),
                         "cmd_f": jp.asarray(2.0)})
    s = e.step(s, jp.zeros(e.action_size))
    assert abs(float(s.info["gait_phase"]) - 0.03) < 1e-6, float(s.info["gait_phase"])


def test_cmd_f_range_and_blind_fixed():
    # teacher cmd_f ~ U(F_MIN,F_MAX); blind cmd_f is the fixed BLIND_CMD_F (1.4).
    te = NovaJoystick(heightmap=True)
    fs = [float(te.reset(jax.random.PRNGKey(k)).info["cmd_f"]) for k in range(12)]
    for f in fs:
        assert F_MIN - 1e-6 <= f <= F_MAX + 1e-6, f
    assert max(fs) - min(fs) > 0.2, ("cmd_f should vary across resets", fs)
    be = NovaJoystick()                       # heightmap=False
    assert abs(float(be.reset(jax.random.PRNGKey(1)).info["cmd_f"]) - BLIND_CMD_F) < 1e-6
    assert abs(BLIND_CMD_F - 1.4) < 1e-9


def test_schedule_windows():
    # at θ=0.25: FL (offset 0) is mid-STANCE, FR (offset 0.5) is mid-SWING — the
    # trot antiphase — and stance_sched integrates to duty 0.5 over the cycle.
    e = NovaJoystick(heightmap=True)
    stance, swing, _ = e._gait_schedule(jp.asarray(0.25))
    stance, swing = np.asarray(stance), np.asarray(swing)
    # LEG_NAMES order: [0]=FL [1]=FR [2]=RL [3]=RR. Offsets [0,.5,.5,0] -> FL,RR
    # (offset 0) planted; FR,RL (offset 0.5) swinging.
    assert stance[0] > 0.99 and stance[1] < 0.01, stance      # FL stance, FR swing
    assert swing[1] > 0.99 and swing[0] < 0.01, swing         # antiphase pair
    assert stance[1] < 0.01 and stance[2] < 0.01, stance      # FR,RL both swing
    assert stance[3] > 0.99, stance                           # RR (offset 0) stance
    # duty 0.5: mean stance_sched over the cycle == GAIT_DUTY (per foot)
    grid = jp.linspace(0.0, 1.0, 2001)[:-1]
    st = np.asarray(jax.vmap(e._gait_schedule)(grid)[0])      # (N,4)
    assert abs(st[:, 0].mean() - GAIT_DUTY) < 0.01, st[:, 0].mean()
    # antiphase pairs sum to exactly 1 at every θ -> stance sums to 2
    tot = np.asarray(jax.vmap(e._gait_schedule)(grid)[0]).sum(axis=1)
    assert np.allclose(tot, 2.0, atol=1e-5), (tot.min(), tot.max())


def test_schedule_edges_smooth():
    # raised-cosine edges -> the indicator is CONTINUOUS across the θ grid (no
    # reward cliffs): the max step of stance_sched between adjacent fine samples
    # stays well under 0.15.
    e = NovaJoystick(heightmap=True)
    grid = jp.linspace(0.0, 1.0, 4001)
    st = np.asarray(jax.vmap(e._gait_schedule)(grid)[0])      # (N,4)
    max_step = np.abs(np.diff(st, axis=0)).max()
    assert max_step < 0.15, max_step
    # and it actually reaches both rails (a real boxcar, not a constant)
    assert st[:, 0].max() > 0.99 and st[:, 0].min() < 0.01, (st[:, 0].max(), st[:, 0].min())
    # M-1 WRAP SEAM: the schedule is built on circular distance, so it must be
    # continuous ACROSS θ=0 too (the diff grid above never straddles the seam).
    # stance(θ=0) ≈ stance(θ=1⁻) per foot — no discontinuity at the wrap.
    st0 = np.asarray(e._gait_schedule(jp.asarray(0.0))[0])
    st1 = np.asarray(e._gait_schedule(jp.asarray(1.0 - 1e-6))[0])
    assert np.abs(st0 - st1).max() < 1e-3, (st0, st1)


def test_gait_cost_zero_when_compliant():
    # contact pattern == schedule (FL,RR planted / FR,RL swinging at θ=0.25) with a
    # moving command -> the violation cost is ~0.
    e = NovaJoystick(heightmap=True)
    s = _split_state(e, _COMPLIANT_LEGS, 0.25, [0.3, 0.0, 0.0])
    assert (_contact(e, s.pipeline_state) == [1, 0, 0, 1]).all(), \
        ("compliant precondition broken", _contact(e, s.pipeline_state))
    assert float(s.metrics["w_gait"]) > -0.02, s.metrics["w_gait"]


def test_gait_cost_bills_antiphase():
    # contact pattern inverted (FL,RR swinging / FR,RL planted at θ=0.25) with a
    # moving command -> all four feet violate -> strongly negative (~-W_GAIT·4).
    e = NovaJoystick(heightmap=True)
    s = _split_state(e, _ANTI_LEGS, 0.25, [0.3, 0.0, 0.0])
    assert (_contact(e, s.pipeline_state) == [0, 1, 1, 0]).all(), \
        ("anti precondition broken", _contact(e, s.pipeline_state))
    assert float(s.metrics["w_gait"]) <= -W_GAIT * 4 * 0.7, s.metrics["w_gait"]


def test_gait_cost_idle_gated():
    # SAME inverted (would-bill) contact pattern, but an IDLE command -> the
    # cmd_moving gate zeroes the cost (idle means STAND, no step-in-place forcing).
    e = NovaJoystick(heightmap=True)
    s = _split_state(e, _ANTI_LEGS, 0.25, [0.0, 0.0, 0.0])
    assert (_contact(e, s.pipeline_state) == [0, 1, 1, 0]).all(), \
        ("anti precondition broken", _contact(e, s.pipeline_state))
    assert float(s.metrics["w_gait"]) == 0.0, s.metrics["w_gait"]


def test_obs_230_teacher_105_blind():
    # teacher obs 230, last 3 = [sin 2πθ, cos 2πθ, cmd_f·F_OBS_SCALE]; blind obs 105
    # and its reward is byte-unchanged by the gait term (the --w-gait kwarg is
    # ignored on the blind path — regression pin for the deploy artifact).
    te = NovaJoystick(heightmap=True)
    s = te.reset(jax.random.PRNGKey(5))
    assert s.obs.shape[-1] == 230, s.obs.shape
    th, f = float(s.info["gait_phase"]), float(s.info["cmd_f"])
    last3 = np.asarray(s.obs[-3:])
    assert abs(last3[0] - np.sin(2 * np.pi * th)) < 1e-5, last3
    assert abs(last3[1] - np.cos(2 * np.pi * th)) < 1e-5, last3
    assert abs(last3[2] - f * F_OBS_SCALE) < 1e-5, last3
    # blind: 105-d obs, no clock dims
    be = NovaJoystick()
    assert be.reset(jax.random.PRNGKey(5)).obs.shape[-1] == 105

    # blind reward byte-unchanged: two blind envs differing ONLY in --w-gait must
    # produce the identical reward on the identical manufactured moving state.
    def blind_reward(w_gait):
        e = NovaJoystick(w_gait=w_gait)
        s = e.reset(jax.random.PRNGKey(7))
        q = s.pipeline_state.q.at[2].add(0.02)
        qd = s.pipeline_state.qd.at[6:].set(2.0)
        ps = e.pipeline_init(q, qd)
        s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
        return float(s2.reward), float(s2.metrics["w_gait"])
    r0, g0 = blind_reward(0.0)
    r9, g9 = blind_reward(50.0)
    assert r0 == r9, ("blind reward must ignore --w-gait", r0, r9)
    assert g0 == 0.0 and g9 == 0.0, ("blind gait cost must be OFF", g0, g9)


# ---------------------------------------------------------------------------
# Task 2: phase-native clearance (teacher enveloped + swing-masked) + the I-1
# numeric blind-reward pin. The teacher clearance now bills a below-target foot
# ONLY in its scheduled swing window, against target = cmd_c·sin(π·swing_frac)
# (0 at swing edges, cmd_c mid-swing). Blind keeps the v5 always-on flat-target
# form EXACTLY. Design: spec §4 + Audit amendments.
# ---------------------------------------------------------------------------

def _teacher_clear_state(theta, c, base_lift=0.0, cmd=(0.3, 0.0, 0.0), key=24):
    """Manufacture a TEACHER step with feet moving (joint qd 2.0) at a controlled
    height, with cmd_c and the clock phase θ pinned before the step (resample
    fires only at step%250, so a fresh reset's first step preserves the override).
    Returns (env, stepped_state)."""
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q.at[2].add(base_lift)
    qd = s.pipeline_state.qd.at[6:].set(2.0)
    ps = e.pipeline_init(q, qd)
    s = s.replace(pipeline_state=ps,
                  info={**s.info, "cmd_c": jp.asarray(c),
                        "gait_phase": jp.asarray(theta),
                        "cmd": jp.asarray(cmd, dtype=jp.float32)})
    return e, e.step(s, jp.zeros(e.action_size))


def _foot_h_and_v(e, ps):
    """Per-foot (foot_h above local ground, |xy| foot speed) as the reward reads
    them, from the POST-step pipeline_state. (4,) each, LEG_NAMES order."""
    fid = np.asarray(e._foot_ids)
    foot_xy = ps.x.pos[e._foot_ids, :2]
    ground_z = np.asarray(e._terrain_ground_z(foot_xy[:, 0], foot_xy[:, 1]))
    foot_h = np.asarray(ps.x.pos[fid, 2]) - ground_z
    v = np.linalg.norm(np.asarray(ps.xd.vel[fid, :2]), axis=-1)
    return foot_h, v


def test_teacher_clearance_matches_enveloped_form():
    # EXACT reconstruction: the billed teacher clearance equals the enveloped,
    # swing-masked one-sided cost recomputed from state — covers envelope AND mask
    # in one shot. θ=0.25 puts FR,RL mid-swing (envelope 1) and FL,RR in stance.
    theta, c = 0.25, 0.06
    e, s = _teacher_clear_state(theta, c)
    foot_h, v = _foot_h_and_v(e, s.pipeline_state)
    st, sw, sf = (np.asarray(x) for x in e._gait_schedule(jp.asarray(theta)))
    env = np.sin(np.pi * sf)
    expected = -e._w_clearance * float(
        np.sum(np.maximum(c * env - foot_h, 0.0) * np.sqrt(v) * sw))
    assert abs(float(s.metrics["w_clearance"]) - expected) < 1e-4, \
        (s.metrics["w_clearance"], expected)


def test_stance_foot_below_target_masked():
    # A STANCE-scheduled foot below target bills 0 (swing_sched mask). At θ=0.25
    # FL,RR are stance; all four feet sit near spawn height (foot_h ≪ c), so every
    # foot IS below target — yet the billed cost equals the swing-feet-only (FR,RL)
    # sum, i.e. the stance feet contribute exactly nothing.
    theta, c = 0.25, 0.06
    e, s = _teacher_clear_state(theta, c)
    foot_h, v = _foot_h_and_v(e, s.pipeline_state)
    assert (foot_h < c).all(), ("precondition: all feet below target", foot_h, c)
    st, sw, sf = (np.asarray(x) for x in e._gait_schedule(jp.asarray(theta)))
    env = np.sin(np.pi * sf)
    per_foot = np.maximum(c * env - foot_h, 0.0) * np.sqrt(v) * sw
    swing = np.array([1, 2])                       # FR,RL scheduled swing at θ=0.25
    stance = np.array([0, 3])                      # FL,RR scheduled stance
    assert (sw[stance] < 1e-3).all(), sw           # stance feet masked
    assert per_foot[stance].sum() < 1e-9, per_foot # ...so they bill 0
    expected = -e._w_clearance * float(per_foot[swing].sum())
    assert abs(float(s.metrics["w_clearance"]) - expected) < 1e-4, \
        (s.metrics["w_clearance"], expected)

    # TRANSITION-ZONE θ (Task-2 review carry-in): at θ=0.47 no foot is fully
    # stance — FL,RR sit in the raised-cosine edge (swing_sched ≈ 0.096), so the
    # mask is FRACTIONAL, not 0/1. The billed cost must still equal the exact
    # enveloped+masked reconstruction, i.e. the partial mask attenuates (does not
    # zero) the stance-side feet's contribution rather than dropping it wholesale.
    theta_t = 0.47
    et, st_t = _teacher_clear_state(theta_t, c)
    foot_h_t, v_t = _foot_h_and_v(et, st_t.pipeline_state)
    sc_t, sw_t, sf_t = (np.asarray(x) for x in et._gait_schedule(jp.asarray(theta_t)))
    stance_side = np.array([0, 3])                 # FL,RR: stance-side but in the edge
    assert ((sw_t[stance_side] > 0.01) & (sw_t[stance_side] < 0.5)).all(), \
        ("FL,RR must be a partial (fractional) mask at θ=0.47", sw_t)
    env_t = np.sin(np.pi * sf_t)
    expected_t = -et._w_clearance * float(
        np.sum(np.maximum(c * env_t - foot_h_t, 0.0) * np.sqrt(v_t) * sw_t))
    assert abs(float(st_t.metrics["w_clearance"]) - expected_t) < 1e-4, \
        (st_t.metrics["w_clearance"], expected_t)


def test_envelope_peak_mid_swing():
    # ENVELOPE PEAK: at swing_frac 0.5 the target equals cmd_c (sin(π·0.5)=1). θ=0.25
    # puts FR,RL at swing_frac 0.5 -> envelope 1 -> target == cmd_c.
    e = NovaJoystick(heightmap=True)
    _, _, sf = e._gait_schedule(jp.asarray(0.25))
    sf = np.asarray(sf)
    env = np.sin(np.pi * sf)
    assert abs(sf[1] - 0.5) < 1e-6 and abs(sf[2] - 0.5) < 1e-6, sf
    assert abs(env[1] - 1.0) < 1e-6 and abs(env[2] - 1.0) < 1e-6, env
    # target = cmd_c · envelope == cmd_c at the peak
    c = 0.05
    assert abs(c * env[1] - c) < 1e-9


def test_envelope_zero_at_swing_edges():
    # ENVELOPE 0 at both swing edges (liftoff swing_frac 0, touchdown swing_frac 1):
    # target -> 0, so no clearance is billed there regardless of foot height. FL
    # is at the liftoff edge at θ=0.5 (swing_frac 0) and the touchdown edge at
    # θ=1⁻ (swing_frac 1).
    e = NovaJoystick(heightmap=True)
    _, _, sf_lift = e._gait_schedule(jp.asarray(0.5))
    _, _, sf_land = e._gait_schedule(jp.asarray(1.0 - 1e-6))
    env_lift = np.sin(np.pi * np.asarray(sf_lift))
    env_land = np.sin(np.pi * np.asarray(sf_land))
    assert env_lift[0] < 1e-6, (sf_lift[0], env_lift[0])   # liftoff edge
    assert env_land[0] < 1e-5, (sf_land[0], env_land[0])   # touchdown edge


def test_teacher_clearance_le_v5_form():
    # The enveloped+masked teacher cost is STRICTLY ≤ the v5 always-on form on the
    # SAME state (envelope only lowers the target ≤ cmd_c; the mask only removes
    # terms) — v6 never bills MORE than v5 anywhere.
    theta, c = 0.25, 0.06
    e, s = _teacher_clear_state(theta, c)
    foot_h, v = _foot_h_and_v(e, s.pipeline_state)
    v5_cost = float(np.sum(np.maximum(c - foot_h, 0.0) * np.sqrt(v)))   # always-on
    v5_billed = -e._w_clearance * v5_cost
    teacher_billed = float(s.metrics["w_clearance"])
    # both are ≤ 0 costs; |teacher| ≤ |v5| means teacher is the LESS negative one.
    assert teacher_billed >= v5_billed - 1e-6, (teacher_billed, v5_billed)
    # and here it is strictly lower-magnitude (stance feet dropped + edge taper)
    assert teacher_billed > v5_billed + 1e-3, (teacher_billed, v5_billed)

    # TRANSITION-ZONE θ (Task-2 review carry-in): θ=0.47 puts FL,RR in the
    # raised-cosine EDGE (swing_sched ≈ 0.096, a partial mask — not a rail), so the
    # ≤-v5 invariant is exercised where the envelope AND the fractional mask both
    # attenuate. It must still hold: envelope ≤ 1 and swing_sched ≤ 1 can only lower
    # the bill vs the always-on v5 form.
    theta_t = 0.47
    et, st = _teacher_clear_state(theta_t, c)
    foot_h_t, v_t = _foot_h_and_v(et, st.pipeline_state)
    _, sw_t, _ = (np.asarray(x) for x in et._gait_schedule(jp.asarray(theta_t)))
    assert 0.01 < sw_t[0] < 0.99, ("θ=0.47 must be a genuine edge for FL", sw_t)
    v5_billed_t = -et._w_clearance * float(np.sum(np.maximum(c - foot_h_t, 0.0) * np.sqrt(v_t)))
    assert float(st.metrics["w_clearance"]) >= v5_billed_t - 1e-6, \
        (st.metrics["w_clearance"], v5_billed_t)


def test_blind_reward_numeric_pin_I1():
    # I-1: ABSOLUTE numeric pin of the BLIND stepped-env reward on a deterministic
    # manufactured moving case (key=7, base +0.02, all joints qd=2.0). Captured on
    # commit 4aee167 (Task-1 HEAD, pre-Task-2): reward = 0.892089664936. The blind
    # path is untouched by BOTH Task-1 (clock/schedule/gait cost teacher-only) and
    # Task-2 (phase-native clearance teacher-only), so this must hold to 1e-6 after
    # both — the deploy-artifact reward is byte-frozen.
    BLIND_REWARD_PIN = 0.892089664936
    e = NovaJoystick()                             # blind (heightmap=False)
    s = e.reset(jax.random.PRNGKey(7))
    q = s.pipeline_state.q.at[2].add(0.02)
    qd = s.pipeline_state.qd.at[6:].set(2.0)
    ps = e.pipeline_init(q, qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    assert abs(float(s2.reward) - BLIND_REWARD_PIN) < 1e-6, \
        (float(s2.reward), BLIND_REWARD_PIN)
    assert float(s2.metrics["w_gait"]) == 0.0, s2.metrics["w_gait"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all gait-clock tests passed")
