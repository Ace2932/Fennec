"""Reward-landscape probe: the per-term INCOME STATEMENT of lifting.

Three reward surgeries (contact fix, one-sided clearance, stance-gated pose)
failed to move foot lift off ~2 cm. probe_lift_ceiling.py already proved the
ACTUATION chain can lift far higher than the policy ever does. So the failure is
one of two things, and this probe decides which:

  * A REWARD FINE — some weighted term pays STRICTLY LESS as the foot lifts
    higher, by more than the lift-positive terms pay, so total income FALLS with
    amplitude. The policy is rational; the landscape punishes lift.
  * A PRO-LIFT LANDSCAPE — total income RISES (or is flat) with amplitude. Then
    reward is not the blocker; OPTIMIZATION is (exploration / local minimum), and
    no further reward surgery will help.

Method: drive the CURRENT-CODE flat env with SCRIPTED diagonal trot gaits at
increasing swing amplitude, and read out EVERY weighted reward term. For each
(amplitude, period) combo we do TWO passes:

  PASS 1  run the scripted gait, measure the mean body-frame forward speed it
          actually achieves (mirrors env's own lin_vel: rotate xd.vel[0] by the
          base-quat inverse, take x).
  PASS 2  re-run the IDENTICAL gait but override info["cmd"] to [that_vx, 0, 0]
          so track / progress / move_gate judge the gait against ITS OWN
          achievable speed — the same trade a policy faces. Metrics from THIS
          pass are the recorded ones. (cmd does not enter the physics, so the two
          passes share one trajectory; only the reward read-out differs.)

The cmd override is re-injected every step so the env's 250-step cmd resample
cannot clobber it.

No file outputs beyond stdout (the caller tees it).

  JAX_PLATFORMS=cpu python probe_reward_landscape.py
"""
import time

import jax
import jax.numpy as jp
import numpy as np
from brax import math

from env import NovaJoystick
from probe_lift_ceiling import (
    LEG_NAMES, DT, FALL_BASE_Z,
    make_env, zero_action, settle, foot_h_all, base_z,
    calibrate_sign, leg_envelopes, swing_windows, build_actions,
)

SETTLE_STEPS = 50
MEASURE_STEPS = 250          # stays inside one cmd-resample window (resample @250)
AMPLITUDES = [0.2, 0.4, 0.6, 0.8, 1.0]
PERIODS = [0.3, 0.4, 0.5]

# the 17 weighted reward terms that are LIVE on the flat env (climb terms are
# identically 0 on flat, so they are omitted). Order = task-spec order.
TERMS = [
    "w_track", "w_yaw", "w_progress", "w_air", "w_clearance",
    "w_pose", "w_upright", "w_angvel", "w_height", "w_z", "w_slip",
    "w_splay", "w_carry", "w_actrate", "w_energy", "w_jerk", "w_stand",
]


def make_extractor(env):
    """jitted per-step read-out: (foot_z[4], base_z, body_fwd_speed).

    body_fwd_speed mirrors env.step(): lin_vel = rotate(xd.vel[0], quat_inv), x.
    On the flat env foot_h == foot_z (ground_z == 0), same as probe_lift_ceiling.
    """
    foot_ids = jp.asarray(env._foot_ids)

    @jax.jit
    def extract(ps):
        quat = ps.q[3:7]
        qinv = math.quat_inv(quat)
        fwd = math.rotate(ps.xd.vel[0], qinv)[0]
        foot_z = ps.x.pos[foot_ids, 2]
        bz = ps.x.pos[0, 2]
        return foot_z, bz, fwd

    return extract


def peak_h_per_cycle(h_hist, envelopes, steps_done):
    """Mean per-swing-cycle PEAK foot_h across all active legs — TRUE lift,
    computed in-probe from foot positions exactly like probe_lift_ceiling."""
    peaks = []
    n_steps = h_hist.shape[0]
    for leg in LEG_NAMES:
        foot_i = LEG_NAMES.index(leg)
        for (s, e) in swing_windows(envelopes[leg]):
            if e >= steps_done or e == n_steps - 1:
                continue
            peaks.append(float(np.max(h_hist[s:e + 1, foot_i])))
    return peaks


def run_pass(env, jit_step, extract, settled, actions, cmd_override=None):
    """Run one MEASURE_STEPS pass of the scripted `actions`. If cmd_override is
    given, force info["cmd"] to it every step (survives the 250-step resample)
    and collect the per-step reward + metrics; else just collect kinematics.

    Returns (h_hist[N,4], base_z_hist[N], fwd_hist[N], steps_done, fell,
             reward_hist[N] or None, metric_hist{term:[N]} or None).
    """
    n = MEASURE_STEPS
    state = settled
    if cmd_override is not None:
        cmd_j = jp.asarray(np.asarray(cmd_override, dtype=np.float32))
        state = state.replace(info={**state.info, "cmd": cmd_j})

    collect = cmd_override is not None
    met_keys = TERMS + ["swing_h_per_step"]
    h_hist = np.zeros((n, 4), dtype=np.float64)
    bz_hist = np.zeros(n, dtype=np.float64)
    fwd_hist = np.zeros(n, dtype=np.float64)
    rew_hist = np.zeros(n, dtype=np.float64) if collect else None
    met_hist = {k: np.zeros(n, dtype=np.float64) for k in met_keys} if collect else None

    fell, steps_done = False, 0
    for i in range(n):
        state = jit_step(state, jp.asarray(actions[i]))
        if collect:
            # re-pin the command; the env may have just resampled it at step%250==0.
            state = state.replace(info={**state.info, "cmd": cmd_j})
        foot_z, bz, fwd = extract(state.pipeline_state)
        h_hist[i] = np.asarray(foot_z)
        bz_hist[i] = float(bz)
        fwd_hist[i] = float(fwd)
        if collect:
            rew_hist[i] = float(state.reward)
            for k in met_keys:
                met_hist[k][i] = float(state.metrics[k])
        steps_done = i + 1
        if float(state.done) > 0.5 or float(bz) < FALL_BASE_Z:
            fell = True
            break
    return h_hist, bz_hist, fwd_hist, steps_done, fell, rew_hist, met_hist


def measure_combo(env, jit_step, extract, settled, hfe_sign, kfe_sign, a, T):
    """Two-pass measurement for one (amplitude, period) combo."""
    actions = build_actions(env, hfe_sign, kfe_sign, a, T, MEASURE_STEPS, LEG_NAMES)
    envelopes = leg_envelopes(T, MEASURE_STEPS, LEG_NAMES)

    # PASS 1 — kinematics only, get the gait's own achievable forward speed.
    h1, bz1, fwd1, sd1, fell1, _, _ = run_pass(env, jit_step, extract, settled, actions)
    # mean body-frame forward speed over what actually ran (fair even if it fell)
    vx = float(np.mean(fwd1[:sd1])) if sd1 > 0 else 0.0

    # PASS 2 — identical trajectory, judged against cmd=[vx,0,0].
    h2, bz2, fwd2, sd2, fell2, rew, met = run_pass(
        env, jit_step, extract, settled, actions, cmd_override=[vx, 0.0, 0.0])

    steps_done = sd2
    fell = fell2
    # TRUE peak foot_h per swing cycle (from foot positions), mean over cycles
    peaks = peak_h_per_cycle(h2, envelopes, steps_done)
    peak_h = float(np.mean(peaks)) if peaks else float("nan")

    # mean-per-step over the measured window
    win = slice(0, steps_done)
    term_means = {k: float(np.mean(met[k][win])) for k in TERMS}
    return {
        "a": a, "T": T,
        "peak_h": peak_h,
        "n_cycles": len(peaks),
        "vx": float(np.mean(fwd2[win])),
        "total": float(np.mean(rew[win])),
        "arcmean_swing": float(np.mean(met["swing_h_per_step"][win])),
        "terms": term_means,
        "fell": fell,
        "steps_done": steps_done,
    }


def fmt(x, w=9, p=3):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return f"{'--':>{w}}"
    return f"{x:>{w}.{p}f}"


def main():
    t0 = time.time()
    env, jit_reset, jit_step = make_env()
    extract = make_extractor(env)
    print(f"NovaJoystick: action_size={env.action_size}  obs_size={env.observation_size}")
    print(f"sweep: amplitudes={AMPLITUDES}  periods={PERIODS}  "
          f"settle={SETTLE_STEPS} measure={MEASURE_STEPS}  (flat env, current weights)")

    state0 = jit_reset(jax.random.PRNGKey(0))
    settled = settle(env, jit_step, state0, SETTLE_STEPS)
    print(f"settled base z = {base_z(settled):.4f} m   "
          f"stance foot_h(cm) = {np.round(foot_h_all(env, settled)*100,2).tolist()} ({LEG_NAMES})")

    hfe_sign, kfe_sign, calib = calibrate_sign(env, jit_step, settled)
    print("\n-- sign calibration (single-leg FL, amp 1.0, 15 steps) --")
    for (hs, ks), d in sorted(calib.items(), key=lambda kv: -kv[1]):
        print(f"  hfe={hs:+.0f} kfe={ks:+.0f} -> FL foot_z delta {d*100:+.2f} cm")
    print(f"  chosen: hfe_sign={hfe_sign:+.0f} kfe_sign={kfe_sign:+.0f}   [{time.time()-t0:.0f}s]")

    results = {}       # (a,T) -> row dict
    print("\n-- two-pass sweep (pass1: achievable vx ; pass2: fair per-term income) --")
    for T in PERIODS:
        for a in AMPLITUDES:
            r = measure_combo(env, jit_step, extract, settled, hfe_sign, kfe_sign, a, T)
            results[(a, T)] = r
            print(f"  a={a:.1f} T={T:.1f}s | peak_h={r['peak_h']*100:6.2f}cm "
                  f"vx={r['vx']:+.3f} total/step={r['total']:+.3f} "
                  f"cycles={r['n_cycles']:2d} fell={r['fell']}  [{time.time()-t0:.0f}s]")

    # ---------------------------------------------------------------- tables
    print("\n" + "=" * 78)
    print("A. FULL PER-TERM TABLE (mean per step over the measured window)")
    print("=" * 78)
    cols = ["peak_h", "arcswing", "vx", "total"] + TERMS
    for T in PERIODS:
        print(f"\n--- T = {T:.1f}s ---   (peak_h & arcswing in cm; rest = reward/step)")
        head = f"{'a':>4}" + "".join(f"{c.replace('w_',''):>9}" for c in cols)
        print(head)
        for a in AMPLITUDES:
            r = results[(a, T)]
            sh = r["arcmean_swing"]
            vals = [r["peak_h"]*100, sh*100, r["vx"], r["total"]] + [r["terms"][k] for k in TERMS]
            line = f"{a:>4.1f}"
            for c, v in zip(cols, vals):
                p = 2 if c in ("peak_h", "arcswing") else 3
                line += fmt(v, 9, p)
            if r["fell"]:
                line += "  FELL"
            print(line)

    # ---------------------------------------------------------------- deltas
    print("\n" + "=" * 78)
    print("B. DELTA TABLE — each term's change vs the a=0.2 baseline (the near-")
    print("   current gait). Sorted by MOST-NEGATIVE delta at a=0.8. THE FINE =")
    print("   the biggest negative delta (term paying least as lift rises).")
    print("=" * 78)
    delta_tables = {}
    for T in PERIODS:
        base = results[(0.2, T)]
        # delta at a=0.8 for ranking
        rank = []
        for k in TERMS + ["total"]:
            def term_val(rr, key):
                return rr["total"] if key == "total" else rr["terms"][key]
            d08 = term_val(results[(0.8, T)], k) - term_val(base, k)
            rank.append((k, d08))
        rank.sort(key=lambda kv: kv[1])   # most negative first
        delta_tables[T] = rank
        print(f"\n--- T = {T:.1f}s --- delta vs a=0.2, columns = amplitudes ---")
        head = f"{'term':>12}" + "".join(f"{a:>9.1f}" for a in AMPLITUDES) + "   d/da(0.2->1.0)"
        print(head)
        for k, _d08 in rank:
            def tv(rr):
                return rr["total"] if k == "total" else rr["terms"][k]
            b = tv(base)
            line = f"{k:>12}"
            for a in AMPLITUDES:
                line += fmt(tv(results[(a, T)]) - b, 9, 3)
            slope = tv(results[(1.0, T)]) - tv(results[(0.2, T)])
            line += f"   {slope:+.3f}"
            print(line)

    # ---------------------------------------------------------------- verdict
    print("\n" + "=" * 78)
    print("C. VERDICT — d(total reward)/d(amplitude) per cadence")
    print("=" * 78)
    for T in PERIODS:
        b = results[(0.2, T)]["total"]
        top = results[(1.0, T)]["total"]
        slope = top - b
        # dominant term of the change
        rank = delta_tables[T]
        dom_terms = [(k, d) for (k, d) in rank if k != "total"]
        dom_neg = dom_terms[0]                       # most negative
        dom_pos = max(dom_terms, key=lambda kv: kv[1])  # most positive
        direction = "RISES" if slope > 1e-3 else ("FALLS" if slope < -1e-3 else "FLAT")
        # peak_h span for context
        ph_lo = results[(0.2, T)]["peak_h"] * 100
        ph_hi = results[(1.0, T)]["peak_h"] * 100
        print(f"\n  T={T:.1f}s: total income {direction}  "
              f"({b:+.3f} -> {top:+.3f}/step, d={slope:+.3f})  "
              f"as peak lift {ph_lo:.1f}->{ph_hi:.1f} cm")
        print(f"    most-NEGATIVE term (the fine): {dom_neg[0]:>10}  d={dom_neg[1]:+.3f}")
        print(f"    most-POSITIVE term (pays lift): {dom_pos[0]:>10}  d={dom_pos[1]:+.3f}")

    # ---------------------------------------------------------------- pose gate
    print("\n" + "=" * 78)
    print("D. POSE-GATE SANITY — post-v4, w_pose should NOT fall with amplitude")
    print("   (it's contact-gated to stance legs; swing flexion should be free).")
    print("=" * 78)
    for T in PERIODS:
        b = results[(0.2, T)]["terms"]["w_pose"]
        top = results[(1.0, T)]["terms"]["w_pose"]
        d = top - b
        # "materially" = drops by > 0.05 reward/step
        flag = "FLAG: w_pose FALLS materially -> gate not working in situ" if d < -0.05 \
            else ("ok (roughly flat)" if abs(d) <= 0.05 else "rises (fine)")
        print(f"  T={T:.1f}s: w_pose {b:+.3f} -> {top:+.3f} (d={d:+.3f})  {flag}")

    # ---------------------------------------------------------------- calibration
    print("\n" + "=" * 78)
    print("E. CALIBRATION — peak_h / arcmean_swing (how much the swing display")
    print("   metric understates TRUE peak lift)")
    print("=" * 78)
    for T in PERIODS:
        for a in AMPLITUDES:
            r = results[(a, T)]
            sh = r["arcmean_swing"]
            ratio = r["peak_h"] / sh if (sh and not np.isnan(sh) and sh > 1e-9) else float("nan")
            print(f"  a={a:.1f} T={T:.1f}s: peak_h={r['peak_h']*100:5.2f}cm "
                  f"arcswing={sh*100 if not np.isnan(sh) else float('nan'):5.2f}cm "
                  f"ratio={ratio:5.2f}x")

    print(f"\ntotal runtime: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
