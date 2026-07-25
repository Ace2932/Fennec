"""CRAWL-gait foot-clearance ceiling probe — the decisive test of whether a slow
3-leg-support crawl can lift ONE foot high enough to climb tall stairs (to 8 cm),
which a fast trot demonstrably cannot.

THE QUESTION
------------
probe_lift_ceiling.py measured a ~3 cm sustained (best single-cycle ~3-4 cm) foot
clearance on a TROT: fast, 2-leg diagonal support. On a trot each stance leg bears
~1/2 the body weight and the body SAGS under the 2-leg support, so the *achieved*
clearance is capped well below the kinematic reach; the fast swing also fights the
~2.8 rad/s servo velocity envelope.

A CRAWL changes all three of those:
  * 3-leg support -> each stance leg bears ~1/3 body weight (vs 1/2),
  * exactly ONE foot swings at a time and that foot is UNLOADED,
  * the swing is SLOW (0.4-1.2 s) so it never approaches the servo velocity limit.

The claim under test: a crawl reaches 6-8 cm of foot clearance. This probe MEASURES
it through the SAME real actuator model the trot probe used (position servos kp=35,
per-joint forcerange ±1.8 N·m hfe/kfe, firmware deadband, bus-latency buffer — env
step()), driving the feet with the VALIDATED leg IK. It does not assume.

METHOD
------
* env = NovaJoystick(heightmap=True, push_mag=0.0). Flat hfield (default) ->
  ground_z == 0 -> foot_h == foot_z (env _terrain_ground_z). We are measuring LIFT
  CAPABILITY, not terrain, so flat is correct. Latency delay pinned 0, cmd = 0
  (crawl in place): the env's trot reward runs internally but we ignore it — the
  measured quantities are foot_h, base height, up_z, fall, actuator torque.

* CRAWL schedule (STATICALLY-STABLE creep / wave gait): one foot swings at a time,
  the other three planted. Duty 0.75 (each foot DOWN 75% of the cycle, swinging
  25%). With 4 feet each swinging 1/4 of the cycle one-at-a-time they exactly tile
  [0,1) -> ALWAYS exactly 3 feet planted. Lift order (documented, SWING_ORDER):
      RL -> FL -> RR -> FR   (left-rear, left-front, right-rear, right-front)
  the textbook creep/wave sequence — it never lifts two same-END legs back to
  back, and alternates sides, which keeps the CoM nearest the interior of each
  3-foot support triangle. (With stiff position servos actively holding stance the
  exact order barely moves the LIFT number this probe measures; the sequence is
  chosen for the up_z / stability read.)

* IK injection (reused from probe_ik_swingref.py, validated mapping): the neutral
  foot is FK(DEFAULT_POSE leg) in the canonical hip frame; a target foot HEIGHT
  maps to canonical z via the per-leg world hip height (hip_z = h_stance - _Z0),
  and inverse_kinematics() solves the femur/tibia 2-link (haa == 0, knee_forward=
  False matching the sim DEFAULT_POSE kfe=-1.2). action = (joint_target -
  DEFAULT_POSE)/ACTION_SCALE.
    - swinging foot: target foot_h = max(A*sin(pi*swing_frac), h_stance)  (== the
      swingref z_ref; the peak clearance ABOVE GROUND is A, floored at rest so the
      foot never stamps below its planted height at the swing edges).
    - stance feet, TWO modes reported:
        "neutral" : action 0 (hold DEFAULT_POSE — the position servo already
                    resists sag by driving toward the stand keyframe).
        "active"  : per-step, extend the stance legs to counter body drop —
                    command stance foot_h = h_stance - (STAND_HEIGHT - base_h)
                    (clipped >=0), a proportional push-up on measured base height.

* Sweep A in {0.03,0.05,0.06,0.07,0.08,0.10} m (clearance above ground) x swing
  duration in {0.4,0.8,1.2} s (cycle period = 4 x swing) x {neutral, active}.

SANITY FIRST (before the sweep): at A=0.08, slowest swing, stance neutral, print the
achieved peak foot_h of the SINGLE swinging foot with 3 legs planted. It MUST
approach 0.08 (unloaded leg, 8 cm == 34% of the 236 mm leg). If it caps far below
(~4 cm) even unloaded + slow + 3-leg support, the CRAWL PREMISE IS WRONG and stairs
are near-infeasible — flagged loudly.

  JAX_PLATFORMS=cpu python probe_crawl_ceiling.py
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
# nova_ops too: leg_ik imports the chassis ROM envelope from
# nova_ops.rom_envelope (it cannot live in nova_locomotion — nova_locomotion.node
# already imports nova_ops, so that direction would be a package cycle).
sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", "nova_ops"))
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    LegParams, forward_kinematics, inverse_kinematics, Unreachable,
)

from env import NovaJoystick, DEFAULT_POSE, ACTION_SCALE, STAND_HEIGHT   # noqa: E402

LEG_NAMES = ["FL", "FR", "RL", "RR"]                # env _foot_ids order
DT = 0.02                                           # 50 Hz control, matches env._dt

# statically-stable creep / wave sequence (documented above)
SWING_ORDER = ["RL", "FL", "RR", "FR"]
DUTY_SWING = 0.25                                   # each foot swings 1/4 cycle (duty 0.75 down)

SETTLE_STEPS = 60
FALL_BASE_Z = 0.08                                  # env done gate (base_h < 0.08)
FALL_UP_Z = 0.4                                     # env done gate (up_z < 0.4)

AMPLITUDES = [0.03, 0.05, 0.06, 0.07, 0.08, 0.10]   # target clearance above ground (m)
SWING_DURS = [0.4, 0.8, 1.2]                         # single-foot swing time (s)
STANCE_MODES = ["neutral", "active"]
STANCE_CORR_CAP = 0.05                               # m, cap on active push-up correction

# ---------------------------------------------------------------------------
# neutral leg geometry (canonical hip frame) via validated FK of the sim keyframe.
# knee_forward=False for ALL legs: the sim DEFAULT_POSE kfe=-1.2 is the elbow-back
# branch (same for all four legs — the sim does not use the real X-config split).
# ---------------------------------------------------------------------------
PARAMS = LegParams()
_DEF_LEG = (float(DEFAULT_POSE[0]), float(DEFAULT_POSE[1]), float(DEFAULT_POSE[2]))
_X0, _D, _Z0 = forward_kinematics(_DEF_LEG, PARAMS)


def make_env():
    env = NovaJoystick(heightmap=True, push_mag=0.0)
    return env, jax.jit(env.reset), jax.jit(env.step)


def _pin(state):
    """Pin the dynamics-relevant teacher fields: cmd = 0 (crawl in place) and
    latency delay = 0 (feet see the current action, clean open-loop injection)."""
    info = {**state.info,
            "cmd": jp.zeros(3, dtype=np.float32),
            "delay": jp.asarray(0, dtype=state.info["delay"].dtype)}
    return state.replace(info=info)


def foot_h_all(env, state):
    return np.asarray(state.pipeline_state.x.pos[np.asarray(env._foot_ids), 2])


def base_z(state):
    return float(state.pipeline_state.x.pos[0, 2])


def up_z(state):
    """z-component of world-up in the body frame = R[2,2] = 1 - 2(qx^2+qy^2).
    Matches the env done gate (done at up_z < 0.4). x.rot is (w,x,y,z)."""
    q = np.asarray(state.pipeline_state.x.rot[0])
    return float(1.0 - 2.0 * (q[1] ** 2 + q[2] ** 2))


def read_torque(state):
    """Best-effort per-actuator torque (N.m). Returns (12,) or None if the mjx
    pipeline_state does not expose it in this brax build."""
    ps = state.pipeline_state
    for attr in ("qfrc_actuator", "actuator_force"):
        v = getattr(ps, attr, None)
        if v is not None:
            arr = np.asarray(v)
            # qfrc_actuator is per-DOF (6 free-base + 12 joints); take last 12.
            if arr.shape[-1] >= 12:
                return arr[-12:]
    return None


def settle(env, jit_step, state, n=SETTLE_STEPS):
    """Hold neutral (action 0) with pins live; return settled state + per-leg mean
    stance foot_h over the last 10 steps (the rest height each swing lifts above)."""
    zero = jp.zeros(env.action_size)
    tail = []
    for i in range(n):
        state = _pin(state)
        state = jit_step(state, zero)
        if i >= n - 10:
            tail.append(foot_h_all(env, state))
    return state, np.mean(np.stack(tail), axis=0)


def leg_action(li, target_h, hip_z, default):
    """12-vec zeros with leg li driven to place its foot at world height target_h.
    Returns (action12, reachable_bool)."""
    cz = target_h - hip_z[li]
    try:
        t1, t2, t3 = inverse_kinematics((_X0, _D, cz), PARAMS, knee_forward=False)
    except Unreachable:
        return None
    j = 3 * li
    a = np.zeros(12, dtype=np.float32)
    a[j + 0] = (t1 - default[j + 0]) / ACTION_SCALE
    a[j + 1] = (t2 - default[j + 1]) / ACTION_SCALE
    a[j + 2] = (t3 - default[j + 2]) / ACTION_SCALE
    return a


def crawl_phase(i, cycle):
    """(swinging_leg_index in LEG_NAMES, swing_frac in [0,1]) at control step i."""
    ph = (i * DT / cycle) % 1.0
    k = min(int(ph / DUTY_SWING), 3)              # which slot in SWING_ORDER
    frac = (ph - k * DUTY_SWING) / DUTY_SWING
    leg = SWING_ORDER[k]
    return LEG_NAMES.index(leg), float(np.clip(frac, 0.0, 1.0))


def run_combo(env, jit_step, settled, h_stance, A, swing_dur, stance_mode,
              n_cycles=1.35):
    """Drive the crawl for ~n_cycles full cycles. Returns a dict of measurements."""
    cycle = 4.0 * swing_dur
    n_steps = int(np.ceil(n_cycles * cycle / DT))
    hip_z = h_stance - _Z0
    default = np.asarray(DEFAULT_POSE, dtype=np.float64)

    state = settled
    fh = np.zeros((n_steps, 4))
    which = np.full(n_steps, -1, dtype=int)        # swinging leg index per step
    bh = np.zeros(n_steps)
    uz = np.zeros(n_steps)
    tau_stance_max = 0.0                            # max |torque| on any STANCE joint
    tau_ok = False
    n_unreach = 0
    fell, steps_done = False, 0

    for i in range(n_steps):
        sw, frac = crawl_phase(i, cycle)
        which[i] = sw
        act = np.zeros(12, dtype=np.float32)
        # swinging foot: lift to A*sin above ground, floored at rest height
        tgt = max(A * np.sin(np.pi * frac), h_stance[sw])
        a_sw = leg_action(sw, tgt, hip_z, default)
        if a_sw is None:
            n_unreach += 1
        else:
            act += a_sw
        # stance feet
        if stance_mode == "active":
            corr = float(np.clip(STAND_HEIGHT - base_z(state), 0.0, STANCE_CORR_CAP))
            for li in range(4):
                if li == sw:
                    continue
                a_st = leg_action(li, h_stance[li] - corr, hip_z, default)
                if a_st is not None:
                    act += a_st
        # (neutral mode: stance action stays 0 == DEFAULT_POSE)

        state = _pin(state)
        state = jit_step(state, jp.asarray(act))
        fh[i] = foot_h_all(env, state)
        bh[i] = base_z(state)
        uz[i] = up_z(state)
        tau = read_torque(state)
        if tau is not None:
            tau_ok = True
            stance_mask = np.ones(12, dtype=bool)
            stance_mask[3 * sw:3 * sw + 3] = False
            tau_stance_max = max(tau_stance_max, float(np.max(np.abs(tau[stance_mask]))))
        steps_done = i + 1
        if float(state.done) > 0.5 or bh[i] < FALL_BASE_Z or uz[i] < FALL_UP_Z:
            fell = True
            break

    # per-swing peak foot_h: for each foot, the max foot_h over each contiguous
    # window where it is the swinging leg, keeping only windows fully inside the run.
    peaks = []
    for li in range(4):
        active = which[:steps_done] == li
        s = None
        for i in range(steps_done):
            if active[i] and s is None:
                s = i
            elif not active[i] and s is not None:
                peaks.append(float(np.max(fh[s:i, li])))
                s = None
        # a window still open at the end was cut short -> drop it (unless not fell)
        if s is not None and not fell:
            peaks.append(float(np.max(fh[s:steps_done, li])))

    return {
        "A": A, "swing_dur": swing_dur, "mode": stance_mode, "cycle": cycle,
        "peak_max": max(peaks) if peaks else float("nan"),
        "peak_mean": float(np.mean(peaks)) if peaks else float("nan"),
        "n_swings": len(peaks),
        "base_mean": float(np.mean(bh[:steps_done])),
        "sag_mean": STAND_HEIGHT - float(np.mean(bh[:steps_done])),
        "up_z_min": float(np.min(uz[:steps_done])),
        "tau_stance_max": tau_stance_max if tau_ok else float("nan"),
        "tau_ok": tau_ok,
        "n_unreach": n_unreach,
        "fell": fell, "steps_done": steps_done,
    }


def stable(r):
    return (not r["fell"]) and r["up_z_min"] > 0.9


def main():
    t0 = time.time()
    print("=" * 80)
    print("CRAWL-GAIT FOOT-CLEARANCE CEILING PROBE — 3-leg-support single-foot lift")
    print("=" * 80)
    print(f"neutral canonical foot (FK of DEFAULT_POSE): x0={_X0:+.5f} d={_D:.5f} "
          f"z0={_Z0:+.5f}  (leg = femur {PARAMS.femur} + tibia {PARAMS.tibia} = "
          f"{PARAMS.femur+PARAMS.tibia:.3f} m)")
    print(f"crawl swing order = {SWING_ORDER}  duty(down)=0.75  "
          f"STAND_HEIGHT={STAND_HEIGHT}  hfe/kfe forcerange=+-1.8 N.m")
    print(f"A(clearance)={AMPLITUDES}  swing_dur={SWING_DURS}s  modes={STANCE_MODES}")
    print("pushes OFF, latency delay=0, cmd=0, flat hfield (foot_h == foot_z)\n")

    env, jit_reset, jit_step = make_env()
    print(f"NovaJoystick: action_size={env.action_size} obs_size={env.observation_size}")
    # actuator torque limits (from the mjx system), if exposed
    fr = getattr(env.sys, "actuator_forcerange", None)
    if fr is not None:
        print(f"actuator_forcerange[:3] (haa,hfe,kfe) = "
              f"{np.round(np.asarray(fr)[:3], 3).tolist()} N.m")

    state0 = _pin(jit_reset(jax.random.PRNGKey(0)))
    settled, h_stance = settle(env, jit_step, state0)
    print(f"settled base z = {base_z(settled):.4f} m   up_z = {up_z(settled):.4f}")
    print(f"settled stance foot_h (cm) = {np.round(h_stance*100,2).tolist()} "
          f"({LEG_NAMES})")
    print(f"[{time.time()-t0:.0f}s]\n")

    # -------------------------------------------------- SANITY FIRST
    print("=" * 80)
    print("SANITY (A=0.08, slowest swing 1.2 s, stance NEUTRAL): the SINGLE swinging")
    print("foot with 3 legs planted+unloaded MUST approach 0.08 if the crawl premise")
    print("holds. If it caps ~4 cm, the premise is WRONG and stairs are infeasible.")
    print("=" * 80)
    s = run_combo(env, jit_step, settled, h_stance, 0.08, 1.2, "neutral")
    print(f"  achieved peak foot_h (single swinging foot): "
          f"max={s['peak_max']*100:.2f}cm  mean={s['peak_mean']*100:.2f}cm  "
          f"(commanded A=8.00cm)")
    print(f"  n_swings={s['n_swings']}  base_sag={s['sag_mean']*100:.2f}cm  "
          f"up_z_min={s['up_z_min']:.3f}  fell={s['fell']}  n_unreach={s['n_unreach']}")
    if not np.isnan(s["peak_max"]):
        ratio = s["peak_max"] / 0.08
        if ratio >= 0.75:
            print(f"  -> reaches {ratio*100:.0f}% of 8 cm: crawl premise LOOKS SOUND, "
                  f"running full sweep.\n")
        else:
            print(f"  -> !! caps at {s['peak_max']*100:.1f}cm ({ratio*100:.0f}% of "
                  f"8 cm) even unloaded/slow/3-leg. CRAWL PREMISE SUSPECT — see verdict.\n")

    # -------------------------------------------------- FULL SWEEP
    results = {}
    for mode in STANCE_MODES:
        for A in AMPLITUDES:
            for dur in SWING_DURS:
                r = run_combo(env, jit_step, settled, h_stance, A, dur, mode)
                results[(mode, A, dur)] = r
                print(f"  [{mode:7s}] A={A:.2f} dur={dur:.1f}s | "
                      f"peak(max/mean)={r['peak_max']*100:5.2f}/{r['peak_mean']*100:5.2f}cm  "
                      f"sag={r['sag_mean']*100:4.1f}cm  up_z_min={r['up_z_min']:.3f}  "
                      f"tau_st={r['tau_stance_max']:.2f}  fell={str(r['fell']):5s}  "
                      f"[{time.time()-t0:.0f}s]")

    # -------------------------------------------------- TABLES
    for mode in STANCE_MODES:
        print("\n" + "=" * 80)
        print(f"TABLE — stance mode: {mode.upper()}   (cell = achieved peak foot_h cm, "
              f"MAX over swings; +=stable up_z>0.9 no-fall, x=fell/unstable)")
        print("=" * 80)
        hdr = f"{'A(cm)':>7} |" + "".join(f"{d:>10.1f}s" for d in SWING_DURS)
        print(hdr)
        print("-" * len(hdr))
        for A in AMPLITUDES:
            row = f"{A*100:>6.1f} |"
            for dur in SWING_DURS:
                r = results[(mode, A, dur)]
                mark = "+" if stable(r) else "x"
                row += f"{r['peak_max']*100:>8.2f}{mark:>2}"
            print(row)
        print(f"{'sag/up_z':>7} |" + "".join(
            f"  s{results[(mode,AMPLITUDES[-1],d)]['sag_mean']*100:.0f}/"
            f"u{results[(mode,AMPLITUDES[-1],d)]['up_z_min']:.2f}" for d in SWING_DURS)
            + "   (at A=max)")

    # -------------------------------------------------- VERDICT
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    all_r = list(results.values())
    max_any = max((r["peak_max"] for r in all_r if not np.isnan(r["peak_max"])),
                  default=float("nan"))
    stable_peaks = [r["peak_max"] for r in all_r
                    if stable(r) and not np.isnan(r["peak_max"])]
    max_stable = max(stable_peaks) if stable_peaks else float("nan")
    # best stable combo
    best = max((r for r in all_r if stable(r) and not np.isnan(r["peak_max"])),
               key=lambda r: r["peak_max"], default=None)

    print(f"MAX achieved crawl foot_h (any combo)     : {max_any*100:.2f} cm")
    print(f"MAX achieved foot_h STABLE (up_z>0.9,no fall): {max_stable*100:.2f} cm")
    if best is not None:
        print(f"  best stable combo: mode={best['mode']} A={best['A']:.2f} "
              f"dur={best['swing_dur']:.1f}s  sag={best['sag_mean']*100:.2f}cm "
              f"up_z_min={best['up_z_min']:.3f}")

    def stable_reaches(thresh):
        return [(r["mode"], r["A"], r["swing_dur"]) for r in all_r
                if stable(r) and not np.isnan(r["peak_max"]) and r["peak_max"] >= thresh]
    r6 = stable_reaches(0.06)
    r8 = stable_reaches(0.08)
    print(f"\nreaches >= 6 cm STABLY : {'YES' if r6 else 'NO'}"
          + (f"  (e.g. {r6[0]})" if r6 else ""))
    print(f"reaches >= 8 cm STABLY : {'YES' if r8 else 'NO'}"
          + (f"  (e.g. {r8[0]})" if r8 else ""))

    # stance-neutral vs active
    def best_mode(mode):
        ps = [r["peak_max"] for r in all_r
              if r["mode"] == mode and stable(r) and not np.isnan(r["peak_max"])]
        return max(ps) if ps else float("nan")
    bn, ba = best_mode("neutral"), best_mode("active")
    print(f"\nstance NEUTRAL best stable clearance = {bn*100:.2f} cm")
    print(f"stance ACTIVE  best stable clearance = {ba*100:.2f} cm")
    if not (np.isnan(bn) or np.isnan(ba)):
        better = "ACTIVE" if ba > bn + 1e-4 else ("NEUTRAL" if bn > ba + 1e-4 else "TIE")
        print(f"  -> {better} stance holds the body better / lifts higher.")

    print("\nCONTRAST WITH TROT (probe_lift_ceiling.py): the trot measured a ~3 cm")
    print("sustained / ~3-4 cm best-cycle foot clearance (2-leg diagonal support, body")
    print(f"sags, fast swing). Crawl MAX stable here = {max_stable*100:.2f} cm.")
    if not np.isnan(max_stable):
        if max_stable >= 0.06:
            print("  -> CRAWL CLEARS THE TROT CEILING: 3-leg support + unloaded slow swing")
            print("     lifts materially higher. The v8 crawl direction is VALIDATED for")
            print(f"     clearance {'(incl. 8 cm stairs)' if r8 else '(6-8 cm; 8 cm marginal)'}.")
        elif max_stable >= 0.04:
            print("  -> modest gain over trot but SHORT of 6 cm stably: crawl helps but")
            print("     does not unlock tall (6-8 cm) stairs. v8 crawl direction WEAK.")
        else:
            print("  -> NO material gain over the trot ceiling even with 3-leg support:")
            print("     the CRAWL PREMISE IS FALSIFIED, tall stairs near-infeasible. KILL v8.")
    print(f"\ntotal runtime: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
