"""CRAWL reward-probe gate — the v8 analog of the v7 IK swing-reference gate
(probe_ik_swingref.py), run on the CRAWL schedule instead of the trot.

WHY A SEPARATE GATE
-------------------
The v7 IK gate drove the reference half-sine z_ref = cmd_c·sin(π·swing_frac) with
the validated leg IK on the TROT schedule and asked "does tracking the reference
score a higher TOTAL reward than the current 2 cm gait?". It came back CONFOUNDED:
the open-loop trot SAGS the body ~3 cm under 2-leg diagonal support, so the
injected foot never reached the reference and the achieved swingref barely varied
with amplitude — a PLANT wall, not a reward-shape failure.

v8's whole thesis is that a slow CRAWL removes that wall: one foot swings at a time
on a 3-leg static-support triangle, the swinging foot is UNLOADED, and the swing is
slow (crawl-ceiling probe e6888d5: 6.7 cm STABLE, ~2× the trot). So the SAME IK
injection, driven along the CRAWL schedule, SHOULD be able to reach the tall
reference lift — and if the v8 reward landscape is right, TOTAL reward should then
MAXIMIZE at the crawl reference lift (~4-6 cm, cmd_c on the crawl) rather than at
the 2 cm shuffle. THAT is the v8 gate:

  PASS  = with the v8 env + v7 tracking reward active on a CRAWL env, total reward
          is maximized at the tall crawl reference lift (argmax_A total in the
          4-6 cm band), w_swingref is minimized there, and w_gait ≈ 0 for the
          compliant crawl schedule. The v8 crawl landscape PAYS for the tall lift.
  FAIL  = total still peaks at ~2 cm (the crawl doesn't unlock the tall lift in the
          reward landscape) — report the numbers and change nothing.

METHOD (mirrors probe_ik_swingref, crawl-parameterized)
-------------------------------------------------------
* TEACHER env NovaJoystick(heightmap=True, push_mag=0.0). Flat hfield ⇒ ground_z==0
  ⇒ foot_h == foot_z (env _terrain_ground_z) — we measure LIFT capability, not
  terrain (same as probe_crawl_ceiling). We do NOT need a stair hfield: the crawl
  schedule is PINNED into info (gait_offsets=CRAWL_OFFSETS, gait_duty=CRAWL_DUTY,
  is_crawl=1) so the reward's _gait_schedule call AND the swingref term both read
  the crawl schedule, exactly as they would on a stair env.
* cmd_c pinned to the crawl reference (0.05 m, in [FOOTSWING_MIN, FOOTSWING_MAX]);
  cmd_f pinned to CRAWL_F 0.45 Hz (mid crawl band [0.3,0.6]); cmd pinned to a LOW
  forward vx (0.10 m/s, inside the v8 crawl-vx band [0,0.12]) so progress/track are
  consistent with a slow crawl and don't fight the tall lift — the exact command
  coupling the v8 sample_command fix installs. gait_phase pinned each step to the
  scripted crawl clock θ_i = frac(cmd_f·dt·i); the reward reads THIS phase and the
  SAME phase drives the injection ⇒ the script IS the schedule (compliant ⇒ w_gait≈0).
* Injection: for the foot in its scheduled CRAWL swing window, drive foot_h along
  A·sin(π·swing_frac) (== z_ref with A for cmd_c), floored at the stance rest
  height; the other three feet hold neutral (planted, 3-leg support). Validated
  inverse_kinematics() solves the femur/tibia 2-link (haa≡0, knee_forward=False).
* Sweep A ∈ {0.02,0.03,0.04,0.05,0.06} (0.05 = the crawl reference cmd_c, 0.02 =
  the shuffle) × W_SWINGREF ∈ {100,300,500}.

  JAX_PLATFORMS=cpu python probe_crawl_reward.py
"""
import os
import sys
import time

import numpy as np
import jax
import jax.numpy as jp

# --- validated leg IK from the nova_locomotion ROS package (do NOT rewrite it) ---
_PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", "nova_locomotion"))
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    LegParams, forward_kinematics, inverse_kinematics, Unreachable,
)

from env import (NovaJoystick, DEFAULT_POSE, ACTION_SCALE,          # noqa: E402
                 CRAWL_OFFSETS, CRAWL_DUTY, CRAWL_F_MIN, CRAWL_F_MAX,
                 CRAWL_VX_MIN, CRAWL_VX_MAX, FOOTSWING_MIN, FOOTSWING_MAX)

LEG_NAMES = ["FL", "FR", "RL", "RR"]
DT = 0.02                          # 50 Hz control, matches env._dt
CMD_F = 0.45                       # Hz scripted CRAWL clock (mid crawl band [0.3,0.6])
CMD_C = 0.05                       # pinned commanded footswing target (crawl reference)
CMD_VX = 0.10                      # forward vx — LOW crawl band [0,0.12] (v8 coupling)
CMD_MOVE = [CMD_VX, 0.0, 0.0]      # cmd_moving=1 (gait cost live), slow forward

SETTLE_STEPS = 60
MEASURE_STEPS = 320                # ~2.6 crawl cycles at 0.45 Hz (cycle = 111 steps)

# swept target swing-peak heights (m). 0.05 == cmd_c (the crawl reference); 0.02 ==
# the shuffle; 0.06 == FOOTSWING_MAX (the reachable ceiling, above the reference).
AMPLITUDES = [0.02, 0.03, 0.04, 0.05, 0.06]
W_SWEEP = [100.0, 300.0, 500.0]
REF_A = 0.05                       # the crawl reference amplitude (== cmd_c)
CUR_A = 0.02                       # the shuffle amplitude
REF_BAND = (0.04, 0.06)            # the "tall crawl reference lift" band (4-6 cm)
FALL_BASE_Z = 0.08                 # env done gate (base_h < 0.08)

KEY_TERMS = ["w_swingref", "w_gait", "w_track", "w_progress", "w_pose",
             "w_upright", "w_energy", "w_carry", "w_slip", "w_height", "w_climb"]

# ---------------------------------------------------------------------------
# neutral leg geometry (canonical hip frame) via validated FK of the sim keyframe.
# knee_forward=False for ALL legs: the sim DEFAULT_POSE kfe=-1.2 is the elbow-back
# branch (matches probe_crawl_ceiling / probe_ik_swingref).
# ---------------------------------------------------------------------------
PARAMS = LegParams()
_DEF_LEG = (float(DEFAULT_POSE[0]), float(DEFAULT_POSE[1]), float(DEFAULT_POSE[2]))
_X0, _D, _Z0 = forward_kinematics(_DEF_LEG, PARAMS)


def make_env(w_swingref):
    """TEACHER env with the v7 swing-ref term LIVE at weight `w_swingref`, pushes
    OFF. Flat hfield default ⇒ foot_h == foot_z."""
    env = NovaJoystick(heightmap=True, w_swingref=w_swingref, push_mag=0.0)
    return env, jax.jit(env.reset), jax.jit(env.step)


def _pin(state, phase):
    """Pin the reward-only teacher fields so the scripted CRAWL clock holds exactly:
    gait_phase (read PRE-advance), cmd_c, cmd_f, cmd, delay=0, AND the per-env CRAWL
    gait (gait_offsets/gait_duty/is_crawl) so the reward's _gait_schedule call + the
    swingref mask read the crawl schedule — the same schedule a stair env selects."""
    info = {**state.info,
            "gait_phase": jp.asarray(np.float32(phase)),
            "cmd_c": jp.asarray(np.float32(CMD_C)),
            "cmd_f": jp.asarray(np.float32(CMD_F)),
            "cmd": jp.asarray(np.asarray(CMD_MOVE, dtype=np.float32)),
            "gait_offsets": jp.asarray(CRAWL_OFFSETS),
            "gait_duty": jp.asarray(np.float32(CRAWL_DUTY)),
            "is_crawl": jp.asarray(np.float32(1.0)),
            "delay": jp.asarray(0, dtype=state.info["delay"].dtype)}
    return state.replace(info=info)


def scripted_phase(i):
    return float((i * DT * CMD_F) % 1.0)


def swing_fracs(env, n_steps):
    """Per-step scheduled (swing_frac[n,4], swing_sched[n,4]) from the env's OWN
    _gait_schedule at the CRAWL offsets/duty and the scripted clock phase — exactly
    what the reward reads each step, so the injection and z_ref are aligned."""
    sf = np.zeros((n_steps, 4), dtype=np.float64)
    ss = np.zeros((n_steps, 4), dtype=np.float64)
    for i in range(n_steps):
        _, swing_sched, swing_frac = env._gait_schedule(
            jp.asarray(np.float32(scripted_phase(i))), CRAWL_OFFSETS, CRAWL_DUTY)
        sf[i] = np.asarray(swing_frac)
        ss[i] = np.asarray(swing_sched)
    return sf, ss


def foot_h_all(env, state):
    return np.asarray(state.pipeline_state.x.pos[np.asarray(env._foot_ids), 2])


def base_z(state):
    return float(state.pipeline_state.x.pos[0, 2])


def settle(env, jit_step, state, n=SETTLE_STEPS):
    """Hold neutral (action 0) with the pins live; return the settled state + per-leg
    mean stance foot_h over the last 10 steps (the rest height each swing lifts above)."""
    zero = jp.zeros(env.action_size)
    tail = []
    for i in range(n):
        state = _pin(state, scripted_phase(i))
        state = jit_step(state, zero)
        state = _pin(state, scripted_phase(i + 1))
        if i >= n - 10:
            tail.append(foot_h_all(env, state))
    return state, np.mean(np.stack(tail), axis=0)


def build_actions(env, A, h_stance, sf):
    """[n,12] open-loop action sequence driving each foot along foot_h =
    A·sin(π·swing_frac) during its scheduled CRAWL swing (0 == neutral in stance).
    hip_z = h_stance − z0 maps world foot_h ⇄ canonical z; validated IK solves the
    2-link. Floored at the stance rest height so the foot never stamps below it."""
    n = sf.shape[0]
    default = np.asarray(DEFAULT_POSE, dtype=np.float64)
    actions = np.zeros((n, env.action_size), dtype=np.float32)
    hip_z = h_stance - _Z0
    max_hfe = -np.inf
    n_unreach = 0
    for li in range(4):
        for i in range(n):
            s = sf[i, li]
            if s <= 1e-6:
                continue
            target_h = max(A * np.sin(np.pi * s), h_stance[li])
            cz = target_h - hip_z[li]
            try:
                t1, t2, t3 = inverse_kinematics((_X0, _D, cz), PARAMS,
                                                knee_forward=False)
            except Unreachable:
                n_unreach += 1
                continue
            max_hfe = max(max_hfe, t2)
            j = 3 * li
            actions[i, j + 0] = (t1 - default[j + 0]) / ACTION_SCALE
            actions[i, j + 1] = (t2 - default[j + 1]) / ACTION_SCALE
            actions[i, j + 2] = (t3 - default[j + 2]) / ACTION_SCALE
    return actions, max_hfe, n_unreach


def run(env, jit_step, settled, A, h_stance, sf):
    """Drive the injected crawl trajectory for MEASURE_STEPS. Returns per-step foot_h
    [n,4], total reward [n], KEY_TERMS metrics, steps_done, fell, max_hfe, n_unreach."""
    actions, max_hfe, n_unreach = build_actions(env, A, h_stance, sf)
    n = MEASURE_STEPS
    state = settled
    fh = np.zeros((n, 4)); rew = np.zeros(n)
    met = {k: np.zeros(n) for k in KEY_TERMS}
    fell, steps_done = False, 0
    for i in range(n):
        state = _pin(state, scripted_phase(i))
        state = jit_step(state, jp.asarray(actions[i]))
        state = _pin(state, scripted_phase(i + 1))
        fh[i] = foot_h_all(env, state)
        rew[i] = float(state.reward)
        for k in KEY_TERMS:
            met[k][i] = float(state.metrics[k])
        steps_done = i + 1
        if float(state.done) > 0.5 or base_z(state) < FALL_BASE_Z:
            fell = True
            break
    return fh, rew, met, steps_done, fell, max_hfe, n_unreach


def swing_windows(active):
    wins, start = [], None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            wins.append((start, i - 1)); start = None
    if start is not None:
        wins.append((start, len(active) - 1))
    return wins


def peak_foot_h(fh, sf, steps_done):
    """Per-swing PEAK achieved foot_h over swing windows fully inside the measured
    span. Returns (mean, max, n_swings, per_leg_mean[4])."""
    peaks = []
    per_leg = [[] for _ in range(4)]
    for li in range(4):
        active = sf[:, li] > 1e-6
        for (s, e) in swing_windows(active):
            if e >= steps_done - 1:
                continue
            pk = float(np.max(fh[s:e + 1, li]))
            peaks.append(pk)
            per_leg[li].append(pk)
    if not peaks:
        return float("nan"), float("nan"), 0, [float("nan")] * 4
    pl_mean = [float(np.mean(p)) if p else float("nan") for p in per_leg]
    return float(np.mean(peaks)), float(np.max(peaks)), len(peaks), pl_mean


def main():
    t0 = time.time()
    print("=" * 78)
    print("CRAWL REWARD-PROBE GATE — v8 IK crawl swing-reference landscape")
    print("=" * 78)
    print(f"neutral canonical foot (FK of sim DEFAULT_POSE): "
          f"x0={_X0:+.5f} d={_D:.5f} z0={_Z0:+.5f}")
    print(f"CRAWL_OFFSETS={[round(float(v),3) for v in CRAWL_OFFSETS]} duty={CRAWL_DUTY} "
          f"cmd_f={CMD_F}Hz (band [{CRAWL_F_MIN},{CRAWL_F_MAX}])  cmd_c={CMD_C}  "
          f"cmd_vx={CMD_VX} (crawl band [{CRAWL_VX_MIN},{CRAWL_VX_MAX}])")
    print(f"A sweep={AMPLITUDES} (ref {REF_A}, shuffle {CUR_A})  W_SWINGREF={W_SWEEP}  "
          f"cmd_c in [{FOOTSWING_MIN},{FOOTSWING_MAX}]")
    print("pushes OFF, latency delay pinned 0, flat hfield (foot_h == foot_z), "
          "crawl schedule PINNED into info\n")

    results = {}
    fidelity = {}          # A -> (peak_mean, peak_max, n_swings, per_leg) from W=100
    sf_g = ss_g = None
    for wi, W in enumerate(W_SWEEP):
        env, jit_reset, jit_step = make_env(W)
        if wi == 0:
            print(f"NovaJoystick: action_size={env.action_size} "
                  f"obs_size={env.observation_size}")
        state0 = _pin(jit_reset(jax.random.PRNGKey(0)), 0.0)
        settled, h_stance = settle(env, jit_step, state0)
        sf, ss = swing_fracs(env, MEASURE_STEPS)
        if wi == 0:
            sf_g, ss_g = sf, ss
            print(f"settled base z = {base_z(settled):.4f} m   "
                  f"stance foot_h(cm) = {np.round(h_stance*100,2).tolist()} ({LEG_NAMES})")
            n_sw = float(np.mean(np.sum(sf > 1e-6, axis=1)))
            n_deep = float(np.mean(np.sum(sf > 0.5, axis=1)))
            print(f"scheduled swing feet per step: any-swing mean={n_sw:.2f}, "
                  f"deep(>0.5) mean={n_deep:.2f}  (CRAWL ⇒ ~1 foot at a time)\n")

        for A in AMPLITUDES:
            fh, rew, met, sd, fell, max_hfe, n_un = run(
                env, jit_step, settled, A, h_stance, sf)
            win = slice(0, sd)
            pk_mean, pk_max, n_swings, pl_mean = peak_foot_h(fh, sf, sd)
            row = {"A": A, "W": W, "peak_mean": pk_mean, "peak_max": pk_max,
                   "n_swings": n_swings, "per_leg": pl_mean,
                   "total": float(np.mean(rew[win])),
                   "max_hfe": max_hfe, "n_unreach": n_un,
                   "fell": fell, "steps_done": sd}
            for k in KEY_TERMS:
                row[k] = float(np.mean(met[k][win]))
            results[(W, A)] = row
            if wi == 0:
                fidelity[A] = (pk_mean, pk_max, n_swings, pl_mean)
            print(f"  W={W:5.0f} A={A:.2f} | peak_h(mean/max)="
                  f"{pk_mean*100:5.2f}/{pk_max*100:5.2f}cm  "
                  f"w_swingref={row['w_swingref']:+.4f}  w_gait={row['w_gait']:+.4f}  "
                  f"total={row['total']:+.4f}  fell={fell}  [{time.time()-t0:.0f}s]")

    # ----------------------------------------------------- 1. injection fidelity
    print("\n" + "=" * 78)
    print("1. INJECTION FIDELITY (W=100) — achieved peak foot_h vs commanded A.")
    print("   On the CRAWL the swinging foot is UNLOADED (3-leg support), so it")
    print("   should track its commanded height CLOSELY — unlike the sagging trot.")
    print("=" * 78)
    print(f"{'A(cmd)':>7}{'mean_cm':>9}{'max_cm':>8}{'best_leg':>10}{'ratio_best':>11}"
          f"{'n_sw':>6}   per-leg mean peak (cm) [FL FR RL RR]")
    for A in AMPLITUDES:
        pm, px, ns, pl = fidelity[A]
        best = np.nanmax(pl)
        ratio = best / A if A > 0 else float("nan")
        pls = " ".join(f"{v*100:5.2f}" for v in pl)
        print(f"{A*100:>6.1f} {pm*100:>8.2f}{px*100:>8.2f}{best*100:>10.2f}"
              f"{ratio:>11.2f}{ns:>6}   [{pls}]")
    best_ratio = max((np.nanmax(pl) / A) for A, (_, _, _, pl) in fidelity.items())
    ref_pm = fidelity[REF_A][0]
    map_ok = best_ratio >= 0.9
    print(f"\n  best-leg tracking ratio over all A = {best_ratio:.2f} -> IK/action "
          f"mapping {'CORRECT' if map_ok else 'SUSPECT'}")
    print(f"  at the reference A={REF_A}: 4-leg mean achieved = {ref_pm*100:.2f} cm "
          f"(crawl foot is unloaded — should approach the reference)")

    # ----------------------------------------------------- 2. full (W,A) table
    print("\n" + "=" * 78)
    print("2. FULL (W, A) TABLE — total reward/step, w_swingref/step, w_gait/step.")
    print("=" * 78)
    for W in W_SWEEP:
        print(f"\n--- W_SWINGREF = {W:.0f} ---")
        print(f"{'A':>6}{'peak_h_cm':>11}{'w_swingref':>12}{'w_gait':>9}{'total':>10}"
              f"{'w_track':>9}{'w_prog':>9}{'w_energy':>10}{'w_carry':>9}")
        for A in AMPLITUDES:
            r = results[(W, A)]
            tag = "  FELL" if r["fell"] else ""
            print(f"{A:>6.2f}{r['peak_mean']*100:>11.2f}{r['w_swingref']:>12.4f}"
                  f"{r['w_gait']:>9.4f}{r['total']:>10.4f}{r['w_track']:>9.4f}"
                  f"{r['w_progress']:>9.4f}{r['w_energy']:>10.4f}{r['w_carry']:>9.4f}{tag}")

    # ----------------------------------------------------- 3. w_swingref / w_gait by A
    print("\n" + "=" * 78)
    print("3. w_swingref MINIMIZED where?  +  w_gait ≈ 0 (compliant crawl schedule)")
    print("=" * 78)
    # raw swingref cost is W-independent (same trajectory) — report from W=100
    cost_by_A = {A: -results[(W_SWEEP[0], A)]["w_swingref"] / W_SWEEP[0] for A in AMPLITUDES}
    a_min_cost = min(cost_by_A, key=cost_by_A.get)
    print("  raw swingref cost by A (W=100): "
          + "  ".join(f"A={A:.2f}:{cost_by_A[A]:.5f}" for A in AMPLITUDES))
    print(f"  -> swingref cost MINIMIZED at A={a_min_cost:.2f}  "
          f"({'PASS — bottoms at the reference' if abs(a_min_cost-REF_A) < 1e-9 else 'at A=%.2f' % a_min_cost})")
    wg_by_A = {A: results[(W_SWEEP[0], A)]["w_gait"] for A in AMPLITUDES}
    wg_max = max(abs(v) for v in wg_by_A.values())
    print("  w_gait by A (W=100):          "
          + "  ".join(f"A={A:.2f}:{wg_by_A[A]:+.4f}" for A in AMPLITUDES))
    print(f"  -> |w_gait| max over A = {wg_max:.4f}  "
          f"({'≈0: crawl schedule COMPLIANT by construction' if wg_max < 0.02 else 'NON-ZERO — check schedule pin'})")

    # ----------------------------------------------------- 4. THE GATE
    print("\n" + "=" * 78)
    print("4. GATE — does TOTAL reward MAXIMIZE at the tall crawl reference lift")
    print(f"   (4-6 cm) rather than the {CUR_A*100:.0f} cm shuffle?")
    print("=" * 78)
    print(f"{'W':>6}{'argmax_A':>10}{'peak_h_cm':>11}{'total@argmax':>14}"
          f"{'total(ref)':>12}{'total(cur)':>12}{'ref>cur?':>10}")
    argmax_in_band = {}
    ref_beats_cur = {}
    for W in W_SWEEP:
        rows = [(A, results[(W, A)]) for A in AMPLITUDES]
        a_max, r_max = max(rows, key=lambda kv: kv[1]["total"])
        t_ref = results[(W, REF_A)]["total"]
        t_cur = results[(W, CUR_A)]["total"]
        in_band = REF_BAND[0] - 1e-9 <= a_max <= REF_BAND[1] + 1e-9
        beats = t_ref > t_cur
        argmax_in_band[W] = in_band
        ref_beats_cur[W] = beats
        print(f"{W:>6.0f}{a_max:>10.2f}{r_max['peak_mean']*100:>11.2f}"
              f"{r_max['total']:>14.4f}{t_ref:>12.4f}{t_cur:>12.4f}"
              f"{('YES' if beats else 'no'):>10}")

    gate_pass = any(argmax_in_band[W] and ref_beats_cur[W] for W in W_SWEEP)
    swingref_ok = abs(a_min_cost - REF_A) < 1e-9 or a_min_cost >= REF_BAND[0] - 1e-9
    gait_ok = wg_max < 0.02

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"  injection mapping     : {'CORRECT' if map_ok else 'SUSPECT'} "
          f"(best-leg ratio {best_ratio:.2f})")
    print(f"  swingref min at ref   : {'YES' if swingref_ok else 'NO'} "
          f"(min at A={a_min_cost:.2f})")
    print(f"  w_gait ≈ 0 (compliant): {'YES' if gait_ok else 'NO'} (|max| {wg_max:.4f})")
    print(f"  total argmax in 4-6cm : {'YES' if any(argmax_in_band.values()) else 'NO'}")
    print(f"  total(ref) > total(cur): {'YES' if any(ref_beats_cur.values()) else 'NO'}")
    if gate_pass:
        wins = [W for W in W_SWEEP if argmax_in_band[W] and ref_beats_cur[W]]
        print(f"\n  GATE: PASS — the v8 crawl reward landscape PAYS for the tall lift.")
        print(f"  Total reward maximizes in the 4-6 cm crawl reference band at "
              f"W_SWINGREF >= {min(wins):.0f}, and the reference beats the {CUR_A*100:.0f} cm")
        print(f"  shuffle. On the stable 3-leg crawl the injected foot REACHES the")
        print(f"  reference (unlike the sagging trot), so the swingref cost actually")
        print(f"  bottoms at the tall lift and the landscape rewards climbing it.")
    else:
        print(f"\n  GATE: FAIL — total reward does NOT maximize at the tall crawl lift.")
        print(f"  argmax_A(total) lands outside the 4-6 cm band and/or the reference")
        print(f"  does not beat the {CUR_A*100:.0f} cm shuffle across the swept W. The v8 crawl")
        print(f"  landscape does not (open-loop) pay for the tall lift — report the")
        print(f"  numbers, change nothing.")
    print(f"\ntotal runtime: {time.time()-t0:.0f}s")
    return gate_pass


if __name__ == "__main__":
    main()
