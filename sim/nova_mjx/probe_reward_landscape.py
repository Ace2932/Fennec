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

v6 GAIT-CLOCK GATE (2026-07-24): this probe is now the go/no-go gate for the trot
clock. It runs the TEACHER env (heightmap=True — clock + schedule + gait cost +
phase-native clearance all LIVE) and drives the SAME scripted diagonal trot, but
PINS the clock phase each step so the scripted swings land in their SCHEDULED
windows (COMPLIANT) or half a cycle off (ANTI-PHASE), reporting w_gait for both.
The full trot cycle is P=2·T_swing at duty 0.5, so the aligned clock runs at
cmd_f=1/P; cmd_c is pinned to 0.05. gait_phase is reward-only (never enters
physics), so the compliant/anti passes share one trajectory — only the reward
read-out differs. PASS (section F) = compliant w_gait ≈ 0, anti-phase w_gait
strongly billed, and the pose/upright walls hold as lift rises.

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
    zero_action, settle, foot_h_all, base_z,
    calibrate_sign, leg_envelopes, swing_windows, build_actions,
)

SETTLE_STEPS = 50
MEASURE_STEPS = 250          # stays inside one cmd-resample window (resample @250)
AMPLITUDES = [0.2, 0.4, 0.6, 0.8, 1.0]
# v6 GATE: PERIODS are SWING durations T_swing (s). At duty 0.5 the full trot
# cycle is P = 2·T_swing, so the ALIGNED clock frequency is cmd_f = 1/P =
# 1/(2·T_swing). T_swing ∈ [0.3,0.5] → cmd_f ∈ [1.0,1.67] Hz, inside the teacher
# clock band [F_MIN,F_MAX]=[1,2]. (Reading T_swing as the FULL cycle would set
# cmd_f = 1/T_swing ≈ 2× too fast → the clock laps the script and bills a
# perfectly-aligned gait: the "double-clock" trap the plan warns about.)
PERIODS = [0.3, 0.4, 0.5]

# ---- v6 PROBE GATE thresholds (spec §Acceptance + Task-3 brief) ----
# The gait COST is cmd_moving-gated (idle command => STAND, cost off). That gate
# is a COMMAND property, not an achieved-speed one — in training the robot is
# commanded up to 0.35 m/s and must produce a schedule-compliant gait whatever
# speed it actually reaches, because the cost bills TIMING (contact-vs-schedule),
# not speed. The scripted open-loop trot barely translates (|vx|≈0.02-0.03 m/s,
# sometimes backward), well under the 0.05 cmd_moving threshold, so judging w_gait
# against its OWN achieved vx would gate the cost OFF and the probe would read
# w_gait≡0 in BOTH modes (unable to tell compliant from anti). So the collect
# passes command a fixed, representative MOVING velocity: cmd_moving=1, the gait
# cost is live, and the schedule-compliance measurement is meaningful. pose /
# upright / clearance are all cmd-independent, so this only un-gates the gait cost.
GATE_MOVE_CMD = [0.3, 0.0, 0.0]  # in-range forward command; keeps cmd_moving=1
GATE_AMPS = [0.8, 1.0]         # working-lift amplitudes the gate is judged at
GATE_COMPLIANT_WGAIT = -0.05   # aligned trot must bill ≥ this (≈ 0)
GATE_ANTI_WGAIT = -0.20        # half-cycle-shifted trot must bill ≤ this
GATE_POSE_DELTA = -0.11        # w_pose must not FALL by more than this vs a=0.2
GATE_UPRIGHT_DELTA = -0.15     # w_upright must not FALL by more than this vs a=0.2

# ---- v7 SWING-REFERENCE GATE (spec §PROBE GATE) ----
# The decisive pre-run test: with the swing-ref tracking term LIVE, the total
# per-step reward vs amplitude must peak at (or near) the REFERENCE amplitude —
# the scripted amplitude whose peak foot_h reaches ~cmd_c (0.05 m) — NOT at the
# lowest ~2 cm amplitude. PASS means the landscape now pulls the foot UP to the
# reference: argmax_a(total) has peak foot_h >= GATE_REF_PEAK_H and w_swingref is
# minimized (least-negative cost) there. FAIL => raise --w-swingref, re-probe.
GATE_REF_PEAK_H = 0.045        # m; ~cmd_c 0.05 minus tracking slack


def make_env():
    """TEACHER env (heightmap=True): the trot CLOCK, schedule indicators, gait
    COST and phase-native clearance are all LIVE here (the blind default env has
    NO clock). The heightmap is flat-by-default; the probe drives OPEN-LOOP
    scripted actions (no policy), so obs 230 is unused and only the reward
    read-out matters."""
    env = NovaJoystick(heightmap=True)
    jit_reset = jax.jit(env.reset)
    jit_step = jax.jit(env.step)
    return env, jit_reset, jit_step


def script_phase(i, cmd_f, phase_off):
    """Clock phase θ to PIN before measured step i so the schedule aligns with the
    scripted trot. The script (leg_envelopes, full cycle P=1/cmd_f) swings the
    FL,RR pair while s_i = frac(i·DT·cmd_f) ∈ [0,0.5) and the FR,RL pair while
    s_i ∈ [0.5,1); the schedule (env._gait_schedule, GAIT_OFFSETS=[0,.5,.5,0])
    swings FL,RR while θ ∈ [0.5,1) and FR,RL while θ ∈ [0,0.5). So θ = frac(s_i +
    0.5) makes BOTH diagonal pairs' script-swing coincide with their
    schedule-swing → COMPLIANT (phase_off=0.5). phase_off=0.0 shifts by the
    missing half-cycle so every scheduled swing lands on a planted foot and every
    scheduled stance on an airborne one → ANTI-PHASE (all four feet violate)."""
    return float((i * DT * cmd_f + phase_off) % 1.0)

# the weighted reward terms that are LIVE on the flat env (climb terms are
# identically 0 on flat, so they are omitted). Order = task-spec order. v7:
# w_swingref is the ACTIVE teacher term (two-sided squared foot_h -> cmd_c·sin(phase));
# w_clearance is now identically 0 on the teacher env (BLIND path only) but kept in
# the table so a nonzero value would flag a regression.
TERMS = [
    "w_track", "w_yaw", "w_progress", "w_air", "w_clearance", "w_swingref",
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


def run_pass(env, jit_step, extract, settled, actions, cmd_f=None, phase_off=None,
             cmd_override=None):
    """Run one MEASURE_STEPS pass of the scripted `actions`.

    cmd_override: force info["cmd"] every step (survives the 250-step resample)
      and collect the per-step reward + metrics; else just collect kinematics.
    cmd_f / phase_off: when both given, PIN the trot clock — set info["gait_phase"]
      to script_phase(i, cmd_f, phase_off) BEFORE each step (the gait cost reads the
      PRE-advance phase) and re-pin info["cmd_f"]=cmd_f AFTER, so the env's own
      θ-advance + 250-step f-resample cannot drift the alignment. gait_phase is
      reward-only (never enters physics), so passes with different phase_off share
      one trajectory — only the reward read-out differs.

    Returns (h_hist[N,4], base_z_hist[N], fwd_hist[N], steps_done, fell,
             reward_hist[N] or None, metric_hist{term:[N]} or None).
    """
    n = MEASURE_STEPS
    state = settled
    # LIFT-V5: pin the COMMANDED footswing target cmd_c to the acceptance-gate
    # value (0.05) in EVERY pass, immediately after the (settled) reset — mirroring
    # the cmd override below. On the teacher env cmd_c is sampled U[.015,.06]; the
    # pin makes the landscape gate explicit and survives the 250-step resample.
    cmd_c_j = jp.asarray(np.float32(0.05))
    state = state.replace(info={**state.info, "cmd_c": cmd_c_j})
    cmd_f_j = jp.asarray(np.float32(cmd_f)) if cmd_f is not None else None
    if cmd_f_j is not None:
        state = state.replace(info={**state.info, "cmd_f": cmd_f_j})
    if cmd_override is not None:
        cmd_j = jp.asarray(np.asarray(cmd_override, dtype=np.float32))
        state = state.replace(info={**state.info, "cmd": cmd_j})

    collect = cmd_override is not None
    met_keys = TERMS + ["w_gait", "swing_h_per_step"]
    h_hist = np.zeros((n, 4), dtype=np.float64)
    bz_hist = np.zeros(n, dtype=np.float64)
    fwd_hist = np.zeros(n, dtype=np.float64)
    rew_hist = np.zeros(n, dtype=np.float64) if collect else None
    met_hist = {k: np.zeros(n, dtype=np.float64) for k in met_keys} if collect else None

    fell, steps_done = False, 0
    for i in range(n):
        # PIN the clock phase for THIS step (the schedule cost reads the pre-advance
        # gait_phase) so the scripted swing lands in its scheduled window.
        if phase_off is not None and cmd_f is not None:
            state = state.replace(info={
                **state.info,
                "gait_phase": jp.asarray(np.float32(script_phase(i, cmd_f, phase_off)))})
        state = jit_step(state, jp.asarray(actions[i]))
        # re-pin cmd_c (+ cmd_f + cmd) so the env's 250-step resample can't clobber.
        pins = {"cmd_c": cmd_c_j}
        if cmd_f_j is not None:
            pins["cmd_f"] = cmd_f_j
        if collect:
            pins["cmd"] = cmd_j
        state = state.replace(info={**state.info, **pins})
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
    """Three-pass measurement for one (amplitude, swing-duration) combo. The full
    trot cycle is P=2·T (duty 0.5); the clock is pinned at cmd_f=1/P, ALIGNED
    (compliant, phase_off 0.5) or half-cycle-shifted (anti-phase, phase_off 0.0)."""
    P = 2.0 * T                 # full trot cycle (duty 0.5): swing T + stance T
    cmd_f = 1.0 / P             # aligned clock frequency (Hz), in [F_MIN,F_MAX]
    actions = build_actions(env, hfe_sign, kfe_sign, a, P, MEASURE_STEPS, LEG_NAMES)
    envelopes = leg_envelopes(P, MEASURE_STEPS, LEG_NAMES)

    # PASS 1 — kinematics only (phase-independent: gait_phase is reward-only), get
    # the gait's own achievable body-frame forward speed (reported for context —
    # the scripted open-loop trot translates poorly, which is itself informative).
    h1, bz1, fwd1, sd1, fell1, _, _ = run_pass(env, jit_step, extract, settled, actions)
    # mean body-frame forward speed over what actually ran (fair even if it fell)
    vx = float(np.mean(fwd1[:sd1])) if sd1 > 0 else 0.0

    # PASS 2 — COMPLIANT: clock aligned to the script, under a fixed MOVING command
    # (GATE_MOVE_CMD) so cmd_moving=1 and the gait cost is LIVE (see the note at
    # GATE_MOVE_CMD). This is the recorded per-term income statement.
    h2, bz2, fwd2, sd2, fell2, rew, met = run_pass(
        env, jit_step, extract, settled, actions, cmd_f=cmd_f, phase_off=0.5,
        cmd_override=GATE_MOVE_CMD)
    # PASS 3 — ANTI-PHASE: same trajectory + same moving command, clock shifted
    # half a cycle so every scheduled swing lands on a planted foot. Only w_gait is
    # read from this pass.
    _h3, _b3, _f3, sd3, _fl3, _rw3, met_anti = run_pass(
        env, jit_step, extract, settled, actions, cmd_f=cmd_f, phase_off=0.0,
        cmd_override=GATE_MOVE_CMD)

    steps_done = sd2
    fell = fell2
    # TRUE peak foot_h per swing cycle (from foot positions), mean over cycles
    peaks = peak_h_per_cycle(h2, envelopes, steps_done)
    peak_h = float(np.mean(peaks)) if peaks else float("nan")

    # mean-per-step over the measured window
    win = slice(0, steps_done)
    win_anti = slice(0, sd3)
    term_means = {k: float(np.mean(met[k][win])) for k in TERMS}
    return {
        "a": a, "T": T, "P": P, "cmd_f": cmd_f,
        "peak_h": peak_h,
        "n_cycles": len(peaks),
        "vx": float(np.mean(fwd2[win])),
        "total": float(np.mean(rew[win])),
        "arcmean_swing": float(np.mean(met["swing_h_per_step"][win])),
        "terms": term_means,
        "w_gait": float(np.mean(met["w_gait"][win])),            # COMPLIANT
        "w_gait_anti": float(np.mean(met_anti["w_gait"][win_anti])),
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
    print(f"sweep: amplitudes={AMPLITUDES}  swing_durations(T)={PERIODS}s  "
          f"settle={SETTLE_STEPS} measure={MEASURE_STEPS}  (TEACHER env, v6 clock)")

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
    print("\n-- three-pass sweep (pass1: achievable vx ; pass2: COMPLIANT per-term "
          "income ; pass3: ANTI-PHASE w_gait) --")
    for T in PERIODS:
        for a in AMPLITUDES:
            r = measure_combo(env, jit_step, extract, settled, hfe_sign, kfe_sign, a, T)
            results[(a, T)] = r
            print(f"  a={a:.1f} T={T:.2f}s P={r['P']:.2f}s f={r['cmd_f']:.2f}Hz | "
                  f"peak_h={r['peak_h']*100:6.2f}cm vx={r['vx']:+.3f} "
                  f"wgait_ok={r['w_gait']:+.3f} wgait_anti={r['w_gait_anti']:+.3f} "
                  f"total={r['total']:+.3f} fell={r['fell']}  [{time.time()-t0:.0f}s]")

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

    # ------------------------------------------------------------------ THE GATE
    print("\n" + "=" * 78)
    print("F. PROBE GATE — v6 acceptance (spec §Acceptance + Task-3 brief).")
    print(f"   Per swing-duration T, at the working-lift amplitudes a∈{GATE_AMPS}:")
    print(f"     compliant  w_gait   ≥ {GATE_COMPLIANT_WGAIT:+.2f}  (aligned trot bills ≈ 0)")
    print(f"     anti-phase w_gait   ≤ {GATE_ANTI_WGAIT:+.2f}  (half-cycle-shifted trot is billed)")
    print(f"     pose  Δ vs a=0.2    ≥ {GATE_POSE_DELTA:+.2f}  (pose veto stays closed as lift rises)")
    print(f"     upright Δ vs a=0.2  ≥ {GATE_UPRIGHT_DELTA:+.2f}  (upright wall holds through the stride)")
    print("=" * 78)
    gate_pass = True

    def mark(b):
        return "PASS" if b else "FAIL"

    for T in PERIODS:
        base = results[(0.2, T)]
        pose_b = base["terms"]["w_pose"]
        up_b = base["terms"]["w_upright"]
        print(f"\n--- T={T:.2f}s  (P={2*T:.2f}s, cmd_f={1/(2*T):.2f}Hz) ---")
        for a in GATE_AMPS:
            r = results[(a, T)]
            wg, wga = r["w_gait"], r["w_gait_anti"]
            pose_d = r["terms"]["w_pose"] - pose_b
            up_d = r["terms"]["w_upright"] - up_b
            c1 = wg >= GATE_COMPLIANT_WGAIT
            c2 = wga <= GATE_ANTI_WGAIT
            c3 = pose_d >= GATE_POSE_DELTA
            c4 = up_d >= GATE_UPRIGHT_DELTA
            ok = c1 and c2 and c3 and c4
            gate_pass = gate_pass and ok
            print(f"  a={a:.1f}: compliant w_gait {wg:+.4f} [{mark(c1)}]  "
                  f"anti w_gait {wga:+.4f} [{mark(c2)}]  "
                  f"pose Δ {pose_d:+.4f} [{mark(c3)}]  "
                  f"upright Δ {up_d:+.4f} [{mark(c4)}]  => {mark(ok)}")

    print("\n" + "=" * 78)
    print("PROBE GATE VERDICT: "
          + ("PASS — all criteria hold at every (T, a)" if gate_pass
             else "FAIL — see the FAILs above; touch nothing on FAIL"))
    print("=" * 78)

    # ------------------------------------------------------ G. SWING-REF GATE
    print("\n" + "=" * 78)
    print("G. SWING-REFERENCE GATE (v7 spec §PROBE GATE) — the decisive pre-run test.")
    print("   Per swing-duration T: total per-step reward, peak foot_h and w_swingref")
    print("   at each swept amplitude. PASS = the amplitude that MAXIMIZES total")
    print(f"   reward has peak foot_h >= {GATE_REF_PEAK_H*100:.1f}cm (near cmd_c 0.05, NOT the")
    print("   lowest ~2cm amp) AND w_swingref is minimized (least-negative cost) there.")
    print("   'the landscape now pulls the foot UP to the reference.'")
    print("=" * 78)
    swingref_gate_pass = True
    for T in PERIODS:
        rows = [(a, results[(a, T)]) for a in AMPLITUDES]
        # amplitude that maximizes total per-step reward
        a_max, r_max = max(rows, key=lambda kv: kv[1]["total"])
        # amplitude with the least-negative (minimized) swingref cost
        a_srmax, _ = max(rows, key=lambda kv: kv[1]["terms"]["w_swingref"])
        peak_at_max = r_max["peak_h"]
        c1 = peak_at_max >= GATE_REF_PEAK_H          # max-reward amp lifts to the ref
        c2 = a_srmax == a_max                          # w_swingref minimized at that amp
        ok = c1 and c2
        swingref_gate_pass = swingref_gate_pass and ok
        print(f"\n--- T={T:.2f}s ---   (amplitude-of-max-total = a={a_max:.1f})")
        head = f"{'a':>5}{'total':>10}{'peak_h_cm':>11}{'w_swingref':>12}"
        print(head)
        for a, r in rows:
            mark_max = "  <= MAX total" if a == a_max else ""
            mark_sr = "  (w_swingref min)" if a == a_srmax else ""
            print(f"{a:>5.1f}{r['total']:>10.3f}{r['peak_h']*100:>11.2f}"
                  f"{r['terms']['w_swingref']:>12.4f}{mark_max}{mark_sr}")
        print(f"  amplitude-of-max-total a={a_max:.1f}: peak foot_h={peak_at_max*100:.2f}cm "
              f">= {GATE_REF_PEAK_H*100:.1f}cm [{mark(c1)}]  "
              f"w_swingref minimized here [{mark(c2)}]  => {mark(ok)}")

    print("\n" + "=" * 78)
    print("SWING-REFERENCE GATE VERDICT: "
          + ("PASS — total reward peaks at the reference amplitude (foot pulled UP)"
             if swingref_gate_pass
             else "FAIL — max total still at low amplitude; RAISE --w-swingref, touch nothing else"))
    print("=" * 78)

    print(f"\ntotal runtime: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
