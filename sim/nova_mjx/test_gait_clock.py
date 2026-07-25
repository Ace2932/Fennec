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
                 GAIT_OFFSETS, W_GAIT, F_OBS_SCALE,
                 CRAWL_OFFSETS, CRAWL_DUTY, CRAWL_F_MIN, CRAWL_F_MAX,
                 TROT_F_MIN, TROT_F_MAX, CRAWL_VX_MIN, CRAWL_VX_MAX)
from terrain import terrain_field

_LEG_ORDER = ["FL", "FR", "RL", "RR"]                # LEG_NAMES order


def _v6_trot_schedule(theta):
    """VERBATIM v6 trot-schedule body (GAIT_OFFSETS + GAIT_DUTY=0.5 inlined) — the
    byte-identity reference the parameterized _gait_schedule must still reproduce."""
    phase = np.mod(theta + np.array([0.0, 0.5, 0.5, 0.0]), 1.0)
    center = 0.5 / 2.0
    halfwin = 0.5 / 2.0
    d = np.abs(np.mod(phase - center + 0.5, 1.0) - 0.5)
    t = np.clip((d - (halfwin - GAIT_SMOOTH)) / (2.0 * GAIT_SMOOTH), 0.0, 1.0)
    stance = 0.5 * (1.0 + np.cos(np.pi * t))
    swing = 1.0 - stance
    sf = np.clip((phase - 0.5) / (1.0 - 0.5), 0.0, 1.0)
    return stance, swing, sf


def _crawl_env(seed=0, level=1.0):
    """An env whose terrain is a pure staircase (terrain_field stair_frac=1 — the
    domain_randomize is_stair output), which reset() must select the CRAWL gait on."""
    e = NovaJoystick(heightmap=True)
    stair = np.asarray(terrain_field(jax.random.PRNGKey(seed), level, 0.0, 1.0))
    e.sys = e.sys.tree_replace({"hfield_data": jp.asarray(stair)})
    return e


def _swing_order(sw):
    """Dedup'd sequence of the solo-swinging leg (swing_sched>0.9) as θ advances."""
    order, prev = [], None
    for i in range(sw.shape[0]):
        j = int(np.argmax(sw[i]))
        if sw[i, j] > 0.9 and _LEG_ORDER[j] != prev:
            prev = _LEG_ORDER[j]
            order.append(prev)
    return order

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


def test_obs_234_teacher_105_blind():
    # v8 teacher obs 234: the v6 clock dims [sin 2πθ, cos 2πθ, cmd_f·F_OBS_SCALE]
    # now sit at obs[-7:-4] (the 4 v8 swing_sched dims append AFTER them at obs[-4:]);
    # blind obs 105 and its reward is byte-unchanged by the gait term (the --w-gait
    # kwarg is ignored on the blind path — regression pin for the deploy artifact).
    te = NovaJoystick(heightmap=True)
    s = te.reset(jax.random.PRNGKey(5))
    assert s.obs.shape[-1] == 234, s.obs.shape
    th, f = float(s.info["gait_phase"]), float(s.info["cmd_f"])
    clock3 = np.asarray(s.obs[-7:-4])
    assert abs(clock3[0] - np.sin(2 * np.pi * th)) < 1e-5, clock3
    assert abs(clock3[1] - np.cos(2 * np.pi * th)) < 1e-5, clock3
    assert abs(clock3[2] - f * F_OBS_SCALE) < 1e-5, clock3
    # blind: 105-d obs, no clock/swing_sched dims
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
# v7 SWING-REFERENCE TRACKING (teacher) + the I-1 numeric blind-reward pin.
# v7 REPLACES the v5/v6 one-sided √v teacher clearance with WTW's REAL form:
# two-sided squared TRACKING of each swing foot to a phase-varying reference
#     z_ref = cmd_c·sin(π·swing_frac)   (0 at swing edges, cmd_c mid-swing),
#     swingref_cost = Σ (foot_h − z_ref)² · swing_sched,
# billed as a separate metric `w_swingref` (the teacher's active term). Blind
# keeps the v5 always-on one-sided flat-target form EXACTLY (w_clearance), and
# its reward is byte-frozen. Design:
# docs/superpowers/specs/2026-07-24-swingref-v7-design.md
# ---------------------------------------------------------------------------

def _swingref_state(theta, c, base_lift=0.03, cmd=(0.3, 0.0, 0.0), key=24):
    """Manufacture a TEACHER step at the EXACT default pose (reset jitter removed)
    with qd=0, so all four feet sit at one controlled height above local ground —
    the two diagonal swing feet are then symmetric. cmd_c and the clock phase θ
    are pinned before the step (the resample fires only at step%250, so a fresh
    reset's first step preserves the overrides). v7 swingref reads foot_h + the
    clock schedule only (NO foot speed), so static feet are exactly what it bills;
    and cmd_c never enters the physics, so foot_h is identical across cmd_c values.
    Returns (env, stepped_state)."""
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(key))
    q = s.pipeline_state.q.at[7:].set(e._default_pose)   # drop reset jitter -> symmetric feet
    q = q.at[2].add(base_lift)
    ps = e.pipeline_init(q, jp.zeros(e.sys.nv))          # qd=0 (v7 uses no foot speed)
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


def test_swingref_matches_reference_form():
    # EXACT reconstruction (the correctness anchor): the billed w_swingref equals
    # -w_swingref·Σ(foot_h − cmd_c·sin(π·swing_frac))²·swing_sched recomputed from
    # state — covers the phase-varying reference AND the swing mask in one shot.
    # θ=0.25 puts FR,RL mid-swing (z_ref=cmd_c) and FL,RR in stance.
    theta, c = 0.25, 0.05
    e, s = _swingref_state(theta, c, base_lift=0.03)
    foot_h, _ = _foot_h_and_v(e, s.pipeline_state)
    _, sw, sf = (np.asarray(x) for x in e._gait_schedule(jp.asarray(theta)))
    z_ref = c * np.sin(np.pi * sf)
    expected = -e._w_swingref * float(np.sum((foot_h - z_ref) ** 2 * sw))
    assert abs(float(s.metrics["w_swingref"]) - expected) < 1e-4, \
        (s.metrics["w_swingref"], expected)
    # the teacher's blind-form w_clearance metric is INERT (0) — no double-bill.
    assert float(s.metrics["w_clearance"]) == 0.0, s.metrics["w_clearance"]


def test_swingref_zero_when_tracking():
    # place the swing feet AT the reference: at θ=0.25 FR,RL sit at swing_frac 0.5
    # -> z_ref=cmd_c. Read the (symmetric) swing-foot height, set cmd_c to it, and
    # the tracked term is ≈0 (the stance feet FL,RR are masked out). foot_h does
    # not depend on cmd_c (physics is cmd_c-free), so this is a clean placement.
    theta = 0.25
    e0, s0 = _swingref_state(theta, c=0.05, base_lift=0.03)
    foot_h, _ = _foot_h_and_v(e0, s0.pipeline_state)
    assert abs(foot_h[1] - foot_h[2]) < 2e-3, ("swing feet must be symmetric", foot_h)
    c_track = float((foot_h[1] + foot_h[2]) / 2.0)
    _, s = _swingref_state(theta, c=c_track, base_lift=0.03)
    assert abs(float(s.metrics["w_swingref"])) < 5e-3, \
        ("tracking the reference bills ~0", s.metrics["w_swingref"])


def test_swingref_bills_below_and_above():
    # TWO-SIDED: the SAME swing feet at height H, billed when the reference sits
    # ABOVE H (foot below ref) AND when it sits BELOW H (foot above ref). The old
    # one-sided form billed only the below-ref case; the squared form bills both.
    theta = 0.25
    e0, s0 = _swingref_state(theta, c=0.05, base_lift=0.03)
    foot_h, _ = _foot_h_and_v(e0, s0.pipeline_state)
    H = float((foot_h[1] + foot_h[2]) / 2.0)
    assert H - 0.02 > 0.0, ("need a positive below-H reference", H)
    _, s_below = _swingref_state(theta, c=H + 0.03, base_lift=0.03)   # z_ref > H
    _, s_above = _swingref_state(theta, c=H - 0.02, base_lift=0.03)   # z_ref < H
    assert float(s_below.metrics["w_swingref"]) < -1e-3, \
        ("foot BELOW the reference must bill", s_below.metrics["w_swingref"])
    assert float(s_above.metrics["w_swingref"]) < -1e-3, \
        ("foot ABOVE the reference must ALSO bill (two-sided)", s_above.metrics["w_swingref"])


def test_swingref_masked_on_stance():
    # A scheduled-STANCE foot below the reference bills 0 (swing_sched mask). At
    # θ=0.25 FL,RR are stance; with all four feet near ground (below a high cmd_c),
    # the billed cost equals the swing-feet-only (FR,RL) sum — stance feet add 0.
    theta, c = 0.25, 0.06
    e, s = _swingref_state(theta, c, base_lift=0.0)
    foot_h, _ = _foot_h_and_v(e, s.pipeline_state)
    _, sw, sf = (np.asarray(x) for x in e._gait_schedule(jp.asarray(theta)))
    z_ref = c * np.sin(np.pi * sf)
    per_foot = (foot_h - z_ref) ** 2 * sw
    swing, stance = np.array([1, 2]), np.array([0, 3])
    assert (sw[stance] < 1e-3).all(), sw                 # stance feet masked
    assert per_foot[stance].sum() < 1e-9, per_foot       # ...so they bill 0
    expected = -e._w_swingref * float(per_foot[swing].sum())
    assert abs(float(s.metrics["w_swingref"]) - expected) < 1e-4, \
        (s.metrics["w_swingref"], expected)


def test_swingref_phase_varying_penalizes_hold():
    # THE hold guard: a foot HELD at a FIXED height is billed MORE at an off-peak
    # swing phase than at the peak. All four feet are held at ≈ the peak reference
    # height. At θ=0.25 the swing feet are at swing_frac 0.5 (z_ref=cmd_c -> the
    # held height tracks -> ~0); at θ=0.125 the SAME held feet are at swing_frac
    # 0.25 (z_ref=cmd_c·sin(π/4) < cmd_c -> the reference moved, the foot didn't ->
    # billed). A held foot cannot match a moving target — the √v factor's old job.
    e0, s0 = _swingref_state(0.25, c=0.05, base_lift=0.03)
    foot_h, _ = _foot_h_and_v(e0, s0.pipeline_state)
    c_hold = float((foot_h[1] + foot_h[2]) / 2.0)        # held height == peak reference
    _, s_peak = _swingref_state(0.25, c=c_hold, base_lift=0.03)
    _, s_off = _swingref_state(0.125, c=c_hold, base_lift=0.03)
    assert abs(float(s_peak.metrics["w_swingref"])) < 5e-3, \
        ("held foot tracks the PEAK reference", s_peak.metrics["w_swingref"])
    assert float(s_off.metrics["w_swingref"]) < -1e-2, \
        ("SAME held foot is billed at the OFF-PEAK phase", s_off.metrics["w_swingref"])
    assert float(s_off.metrics["w_swingref"]) < float(s_peak.metrics["w_swingref"]) - 1e-2, \
        ("off-peak must bill strictly MORE than peak (phase-varying)",
         s_off.metrics["w_swingref"], s_peak.metrics["w_swingref"])


def test_envelope_peak_mid_swing():
    # REFERENCE PEAK: at swing_frac 0.5 the v7 target z_ref equals cmd_c
    # (sin(π·0.5)=1). θ=0.25 puts FR,RL at swing_frac 0.5 -> envelope 1 ->
    # z_ref == cmd_c (the apex the swing foot is pulled toward).
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
    # z_ref -> 0, so the v7 reference asks the foot to be at GROUND level at the
    # swing boundaries (touchdown/liftoff) — the correct trajectory endpoints. FL
    # is at the liftoff edge at θ=0.5 (swing_frac 0) and the touchdown edge at
    # θ=1⁻ (swing_frac 1).
    e = NovaJoystick(heightmap=True)
    _, _, sf_lift = e._gait_schedule(jp.asarray(0.5))
    _, _, sf_land = e._gait_schedule(jp.asarray(1.0 - 1e-6))
    env_lift = np.sin(np.pi * np.asarray(sf_lift))
    env_land = np.sin(np.pi * np.asarray(sf_land))
    assert env_lift[0] < 1e-6, (sf_lift[0], env_lift[0])   # liftoff edge
    assert env_land[0] < 1e-5, (sf_land[0], env_land[0])   # touchdown edge


def test_blind_clearance_unchanged_numeric():
    # I-1: ABSOLUTE numeric pin of the BLIND stepped-env reward on a deterministic
    # manufactured moving case (key=7, base +0.02, all joints qd=2.0). Captured on
    # commit 4aee167: reward = 0.892089664936. The blind path is untouched by the
    # v6 clock (teacher-only) AND the v7 swing-reference term (teacher-only), so
    # this must still hold to 1e-6 — the deploy-artifact reward is byte-frozen.
    BLIND_REWARD_PIN = 0.892089664936
    e = NovaJoystick()                             # blind (heightmap=False)
    s = e.reset(jax.random.PRNGKey(7))
    q = s.pipeline_state.q.at[2].add(0.02)
    qd = s.pipeline_state.qd.at[6:].set(2.0)
    ps = e.pipeline_init(q, qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    assert abs(float(s2.reward) - BLIND_REWARD_PIN) < 1e-6, \
        (float(s2.reward), BLIND_REWARD_PIN)
    # blind carries the v5 one-sided clearance (active) and NO swingref term.
    assert float(s2.metrics["w_gait"]) == 0.0, s2.metrics["w_gait"]
    assert float(s2.metrics["w_swingref"]) == 0.0, \
        ("v7 swingref is teacher-only — blind must read 0", s2.metrics["w_swingref"])
    assert float(s2.metrics["w_clearance"]) < 0.0, \
        ("blind keeps the ACTIVE v5 one-sided clearance", s2.metrics["w_clearance"])


def test_swingref_w_swingref_kwarg_scales():
    # W_SWINGREF default + kwarg: the teacher term scales linearly with the weight.
    # Same manufactured below-reference state (θ=0.25, feet near ground) at two
    # weights -> the billed w_swingref scales by exactly the weight ratio.
    theta, c = 0.25, 0.06
    e100, s100 = _swingref_state(theta, c, base_lift=0.0)
    e50 = NovaJoystick(heightmap=True, w_swingref=50.0)
    s = e50.reset(jax.random.PRNGKey(24))
    q = s.pipeline_state.q.at[7:].set(e50._default_pose).at[2].add(0.0)
    ps = e50.pipeline_init(q, jp.zeros(e50.sys.nv))
    s = s.replace(pipeline_state=ps,
                  info={**s.info, "cmd_c": jp.asarray(c),
                        "gait_phase": jp.asarray(theta),
                        "cmd": jp.array([0.3, 0.0, 0.0])})
    s50 = e50.step(s, jp.zeros(e50.action_size))
    assert float(s100.metrics["w_swingref"]) < -0.001, s100.metrics["w_swingref"]
    assert abs(float(s100.metrics["w_swingref"]) / float(s50.metrics["w_swingref"]) - 2.0) < 0.02, \
        (s100.metrics["w_swingref"], s50.metrics["w_swingref"])


# ---------------------------------------------------------------------------
# v8 CRAWL GAIT — parameterized schedule, terrain-selected trot/crawl, F_MIN 0.3,
# obs 234. Crawl = one foot swings at a time on 3-leg static support (the tall-
# stairs gait; crawl-ceiling probe e6888d5 reached 6.7cm stable, ~2x the trot).
# Reuses the v7 tracking reward + v6 gait cost UNCHANGED — both read the schedule,
# which becomes gait-parameterized. Design:
# docs/superpowers/specs/2026-07-24-crawl-gait-v8-design.md
# ---------------------------------------------------------------------------

def test_gait_schedule_trot_unchanged():
    # REGRESSION PIN: _gait_schedule(θ, GAIT_OFFSETS, 0.5) reproduces the v6 trot
    # schedule bit-for-bit (the whole v7 tracking chain depends on it). Two checks:
    # (a) the explicit-args call == the numpy v6 reference (functional identity),
    # (b) the DEFAULT-args call == the explicit-args call EXACTLY (parameterization
    # is a no-op for trot — the defaults are the old module consts).
    e = NovaJoystick(heightmap=True)
    grid = jp.linspace(0.0, 1.0, 257)
    st_e, sw_e, sf_e = (np.asarray(x) for x in
                        jax.vmap(lambda th: e._gait_schedule(th, GAIT_OFFSETS, 0.5))(grid))
    for i, th in enumerate(np.asarray(grid)):
        rst, rsw, rsf = _v6_trot_schedule(float(th))
        assert np.allclose(st_e[i], rst, atol=1e-6), (th, st_e[i], rst)
        assert np.allclose(sw_e[i], rsw, atol=1e-6), (th, sw_e[i], rsw)
        assert np.allclose(sf_e[i], rsf, atol=1e-6), (th, sf_e[i], rsf)
    # default-args == explicit trot args, EXACTLY (both float32)
    st_d, sw_d, sf_d = (np.asarray(x) for x in jax.vmap(e._gait_schedule)(grid))
    assert np.array_equal(st_d, st_e) and np.array_equal(sw_d, sw_e) \
        and np.array_equal(sf_d, sf_e), "default trot args must be a byte no-op"


def test_crawl_one_foot_at_a_time():
    # crawl schedule: exactly one foot swings at a time -> stance_sched sums to ~3
    # (3-leg static support) at EVERY θ, and each foot gets its solo swing.
    e = NovaJoystick(heightmap=True)
    grid = jp.linspace(0.0, 1.0, 2001)[:-1]
    st, sw, _ = (np.asarray(x) for x in
                 jax.vmap(lambda th: e._gait_schedule(th, CRAWL_OFFSETS, CRAWL_DUTY))(grid))
    tot = st.sum(axis=1)
    assert np.allclose(tot, 3.0, atol=1e-4), ("3-leg support at every θ", tot.min(), tot.max())
    # total swing == exactly ONE foot's worth at every θ (= 4 - stance_sum = 1): the
    # crawl never has two feet swinging at once. At the smooth handoff two feet are
    # momentarily mid-edge (each ~0.5, one landing as the next lifts) but their swing
    # SUMS to 1, so no more than one foot is ever in DEEP swing (>0.6).
    assert np.allclose(sw.sum(axis=1), 1.0, atol=1e-4), (sw.sum(axis=1).min(), sw.sum(axis=1).max())
    n_deep = (sw > 0.6).sum(axis=1)
    assert int(n_deep.max()) <= 1, ("at most ONE foot in deep swing", n_deep.max())
    assert (sw.max(axis=0) > 0.99).all(), ("each foot gets a solo swing", sw.max(axis=0))


def test_crawl_duty_075():
    # duty 0.75: each foot swing-scheduled ~25% of the cycle (mean swing_sched
    # ~0.25, mean stance ~0.75), and the swing ORDER is the probe's VALIDATED stable
    # creep RL->FL->RR->FR (probe_crawl_ceiling.py SWING_ORDER — a wrong order is a
    # silently unstable gait).
    e = NovaJoystick(heightmap=True)
    grid = jp.linspace(0.0, 1.0, 2001)[:-1]
    st, sw, _ = (np.asarray(x) for x in
                 jax.vmap(lambda th: e._gait_schedule(th, CRAWL_OFFSETS, CRAWL_DUTY))(grid))
    assert np.allclose(sw.mean(axis=0), 1.0 - CRAWL_DUTY, atol=0.01), sw.mean(axis=0)
    assert np.allclose(st.mean(axis=0), CRAWL_DUTY, atol=0.01), st.mean(axis=0)
    order = _swing_order(sw)
    assert order[:4] == ["RL", "FL", "RR", "FR"], ("stable creep sequence", order[:4])


def test_terrain_selects_gait():
    # terrain SELECTS the gait (reset reads the per-env hfield): STAIR -> crawl,
    # FLAT + ROUGH -> trot. Blind always trots (checked elsewhere).
    ec = _crawl_env(seed=0, level=1.0)
    sc = ec.reset(jax.random.PRNGKey(1))
    assert float(sc.info["is_crawl"]) == 1.0, "stair env must select crawl"
    assert np.allclose(np.asarray(sc.info["gait_offsets"]), np.asarray(CRAWL_OFFSETS)), \
        sc.info["gait_offsets"]
    assert abs(float(sc.info["gait_duty"]) - CRAWL_DUTY) < 1e-9, sc.info["gait_duty"]
    # FLAT (nominal terrain, peak 0) -> trot
    ef = NovaJoystick(heightmap=True)
    sf = ef.reset(jax.random.PRNGKey(1))
    assert float(sf.info["is_crawl"]) == 0.0, "flat env must select trot"
    assert np.allclose(np.asarray(sf.info["gait_offsets"]), np.asarray(GAIT_OFFSETS)), \
        sf.info["gait_offsets"]
    assert abs(float(sf.info["gait_duty"]) - GAIT_DUTY) < 1e-9, sf.info["gait_duty"]
    # ROUGH (2D bumps, stair_frac=0) -> trot (row-std > 0, not a staircase)
    er = NovaJoystick(heightmap=True)
    rough = np.asarray(terrain_field(jax.random.PRNGKey(3), 1.0, 0.0, 0.0))
    er.sys = er.sys.tree_replace({"hfield_data": jp.asarray(rough)})
    sr = er.reset(jax.random.PRNGKey(1))
    assert float(sr.info["is_crawl"]) == 0.0, ("rough env must trot", sr.info["is_crawl"])
    # ELEVATED CONSTANT PLATEAU -> trot. A plateau is y-invariant with a nonzero
    # peak (the raw stair signature) but does NOT rise in x, so the detector must
    # exclude it via the max-min relief gate (else it reads as a staircase — the
    # test_terrain_relative T5-T7 regression). This is the direct guard.
    ep = NovaJoystick(heightmap=True)
    nr, nc = ep._hf_nrow, ep._hf_ncol
    ep.sys = ep.sys.tree_replace(
        {"hfield_data": jp.asarray(np.full((nr, nc), 0.18 / 0.20).reshape(-1))})
    sp = ep.reset(jax.random.PRNGKey(1))
    assert float(sp.info["is_crawl"]) == 0.0, \
        ("elevated constant plateau must trot, not crawl", sp.info["is_crawl"])


def test_f_min_extended():
    # F_MIN extended to 0.3; crawl envs sample cmd_f in the slow band [0.3,0.6],
    # trot envs keep the fast band [1,2] (byte-unchanged).
    assert abs(F_MIN - 0.3) < 1e-9, F_MIN
    ec = _crawl_env(seed=0, level=1.0)
    cfs = [float(ec.reset(jax.random.PRNGKey(k)).info["cmd_f"]) for k in range(16)]
    for f in cfs:
        assert CRAWL_F_MIN - 1e-6 <= f <= CRAWL_F_MAX + 1e-6, ("crawl cmd_f band", f)
    assert max(cfs) - min(cfs) > 0.05, ("crawl cmd_f should vary across resets", cfs)
    ef = NovaJoystick(heightmap=True)                 # flat -> trot band
    tfs = [float(ef.reset(jax.random.PRNGKey(k)).info["cmd_f"]) for k in range(16)]
    for f in tfs:
        assert TROT_F_MIN - 1e-6 <= f <= TROT_F_MAX + 1e-6, ("trot cmd_f band", f)


def test_obs_234_teacher_last4_swingsched():
    # teacher obs 234, the LAST 4 dims == this env's per-foot swing_sched; blind 105.
    e = NovaJoystick(heightmap=True)
    s = e.reset(jax.random.PRNGKey(5))
    assert s.obs.shape[-1] == 234, s.obs.shape
    _, sw, _ = e._gait_schedule(s.info["gait_phase"], s.info["gait_offsets"],
                                s.info["gait_duty"])
    assert np.allclose(np.asarray(s.obs[-4:]), np.asarray(sw), atol=1e-6), \
        (np.asarray(s.obs[-4:]), np.asarray(sw))
    # on a CRAWL env the last-4 carry the crawl (one-foot-swing) schedule
    ec = _crawl_env(seed=0, level=1.0)
    sc = ec.reset(jax.random.PRNGKey(5))
    _, sw_c, _ = ec._gait_schedule(sc.info["gait_phase"], CRAWL_OFFSETS, CRAWL_DUTY)
    assert np.allclose(np.asarray(sc.obs[-4:]), np.asarray(sw_c), atol=1e-6), \
        (np.asarray(sc.obs[-4:]), np.asarray(sw_c))
    be = NovaJoystick()                               # blind
    assert be.reset(jax.random.PRNGKey(5)).obs.shape[-1] == 105


def test_crawl_cmd_vx_low_band_trot_unchanged():
    # v8 COMMAND COUPLING (spec §6): sample_command draws a CRAWL env's forward vx
    # from the low band [CRAWL_VX_MIN, CRAWL_VX_MAX]; a TROT env (is_crawl=0) and the
    # ungated (is_crawl=None) draw are BYTE-IDENTICAL, and vy/wz are untouched on a
    # crawl draw (same underlying uniform, only vx's affine scale changes).
    e = NovaJoystick(heightmap=True)                  # stage 2 default vx[-0.15,0.35]
    key = jax.random.PRNGKey(0)
    ungated = np.asarray(e.sample_command(key))                    # pre-v8 signature
    trot = np.asarray(e.sample_command(key, jp.asarray(0.0)))      # trot gating
    crawl = np.asarray(e.sample_command(key, jp.asarray(1.0)))     # crawl gating
    assert np.array_equal(ungated, trot), ("trot gate is a byte no-op", ungated, trot)
    assert CRAWL_VX_MIN - 1e-6 <= crawl[0] <= CRAWL_VX_MAX + 1e-6, ("crawl vx band", crawl)
    assert np.allclose(crawl[1:], trot[1:], atol=1e-7), ("vy/wz untouched", crawl, trot)
    # across many keys a crawl draw NEVER exceeds the low cap
    for k in range(64):
        c = np.asarray(e.sample_command(jax.random.PRNGKey(k), jp.asarray(1.0)))
        assert CRAWL_VX_MIN - 1e-6 <= c[0] <= CRAWL_VX_MAX + 1e-6, (k, c)


def test_crawl_env_reset_seeds_low_vx():
    # END TO END: a stair->crawl env's reset-seeded command has vx in the low band,
    # while a flat->trot env keeps the full stage-2 vx range (draws above the cap).
    ec = _crawl_env(seed=0, level=1.0)
    for k in range(16):
        vx = float(ec.reset(jax.random.PRNGKey(k)).info["cmd"][0])
        assert CRAWL_VX_MIN - 1e-6 <= vx <= CRAWL_VX_MAX + 1e-6, ("crawl reset vx", k, vx)
    ef = NovaJoystick(heightmap=True)                 # flat -> trot
    vxs = [float(ef.reset(jax.random.PRNGKey(k)).info["cmd"][0]) for k in range(32)]
    assert max(vxs) > CRAWL_VX_MAX + 1e-3, ("trot vx must exceed the crawl cap", max(vxs))


def test_blind_reward_pin_holds():
    # v8 is TEACHER-ONLY (terrain-gait, swing_sched obs, F_MIN band) — the blind
    # 105-d deploy reward must be byte-frozen. Same manufactured moving state as
    # test_blind_clearance_unchanged_numeric (key=7, base +0.02, all joints qd=2.0);
    # pin captured on commit 4aee167.
    BLIND_REWARD_PIN = 0.892089664936
    e = NovaJoystick()                                # blind (heightmap=False)
    s = e.reset(jax.random.PRNGKey(7))
    q = s.pipeline_state.q.at[2].add(0.02)
    qd = s.pipeline_state.qd.at[6:].set(2.0)
    ps = e.pipeline_init(q, qd)
    s2 = e.step(s.replace(pipeline_state=ps), jp.zeros(e.action_size))
    assert abs(float(s2.reward) - BLIND_REWARD_PIN) < 1e-6, \
        (float(s2.reward), BLIND_REWARD_PIN)
    # blind gait is trot (schedule unused in the 105-d reward)
    assert np.allclose(np.asarray(s.info["gait_offsets"]), np.asarray(GAIT_OFFSETS)), \
        s.info["gait_offsets"]
    assert float(s.info["is_crawl"]) == 0.0, s.info["is_crawl"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(); print(f"ok  {name}")
    print("all gait-clock tests passed")
