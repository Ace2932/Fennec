"""Kinematic lift-ceiling probe: H-control vs H-valley.

The trained gait's foot lift sits at ~2 cm mean regardless of reward
incentives (clearance is ~7% of return, ignored for 120M steps). This asks
the ground-truth question the RL run can't answer on its own: through the
REAL actuator model (position servos, kp=35, per-joint torque limits,
firmware deadband, bus-latency delay buffer — see env.py step()), what peak
foot clearance can an open-loop SCRIPTED swing produce?

  * H-control (actuator-capped): scripted swings also plateau near ~2 cm ->
    the servo envelope IS the ceiling, no amount of RL will lift higher.
  * H-valley (policy never found it): scripted swings reach well above 2 cm
    -> the actuation chain can do it, the reward landscape just never
    rewarded the policy into finding it.

No file outputs — everything goes to stdout.

  JAX_PLATFORMS=cpu python probe_lift_ceiling.py
"""
import time

import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick

LEG_NAMES = ["FL", "FR", "RL", "RR"]
# joint layout per env.py: DEFAULT_POSE = [haa, hfe, kfe] * 4, legs in LEG_NAMES
# order -> leg i occupies action/joint indices [3i, 3i+1, 3i+2].
HFE_IDX = {leg: 3 * i + 1 for i, leg in enumerate(LEG_NAMES)}
KFE_IDX = {leg: 3 * i + 2 for i, leg in enumerate(LEG_NAMES)}
# trot diagonal pairing: FL+RR swing together, FR+RL swing in antiphase.
PHASE = {"FL": 0.0, "RR": 0.0, "FR": np.pi, "RL": np.pi}

DT = 0.02              # 50 Hz control, matches env._dt / NovaJoystick n_frames
SETTLE_STEPS = 50
MEASURE_STEPS = 250
FALL_BASE_Z = 0.08      # matches env.py's done gate (base_h < 0.08)

AMPLITUDES = [0.2, 0.4, 0.6, 0.8, 1.0]     # fraction of action range [-1,1]
PERIODS = [0.2, 0.3, 0.4]                  # s per full swing/stance cycle


def make_env():
    env = NovaJoystick()          # default flat hfield -> ground_z == 0, foot_h == foot_z
    jit_reset = jax.jit(env.reset)
    jit_step = jax.jit(env.step)
    return env, jit_reset, jit_step


def zero_action(env):
    return jp.zeros(env.action_size)


def settle(env, jit_step, state, n=SETTLE_STEPS):
    for _ in range(n):
        state = jit_step(state, zero_action(env))
    return state


def foot_h_all(env, state):
    """foot_h == foot_z on the default flat hfield (ground_z == 0 everywhere),
    per env.py's _terrain_ground_z docstring — no heightmap needed."""
    return np.asarray(state.pipeline_state.x.pos[np.asarray(env._foot_ids), 2])


def base_z(state):
    return float(state.pipeline_state.x.pos[0, 2])


# ---------------------------------------------------------------------------
# sign calibration — hfe/kfe convention is unverified, so probe it instead of
# guessing. Command a constant offset on one leg (FL) for both sign
# combinations and keep whichever raises that foot's height the most.
# ---------------------------------------------------------------------------
def calibrate_sign(env, jit_step, base_state, leg="FL", amplitude=1.0, n_steps=15):
    leg_i = LEG_NAMES.index(leg)
    baseline_h = foot_h_all(env, base_state)[leg_i]
    results = {}
    for hfe_sign in (1.0, -1.0):
        for kfe_sign in (1.0, -1.0):
            act = np.zeros(env.action_size, dtype=np.float32)
            act[HFE_IDX[leg]] = hfe_sign * amplitude
            act[KFE_IDX[leg]] = kfe_sign * amplitude
            act_j = jp.asarray(act)
            state = base_state
            peak = float(baseline_h)
            for _ in range(n_steps):
                state = jit_step(state, act_j)
                peak = max(peak, float(foot_h_all(env, state)[leg_i]))
            results[(hfe_sign, kfe_sign)] = peak - float(baseline_h)
    best = max(results, key=results.get)
    return best[0], best[1], results


# ---------------------------------------------------------------------------
# scripted trot / single-leg swing
# ---------------------------------------------------------------------------
def leg_envelopes(period, n_steps, legs_active):
    """Per-leg swing envelope: max(sin(2*pi*t/T + phase), 0) — a sinusoidal
    hump over the swing half of each cycle, exactly 0 (== default pose,
    stance) the other half. FL/RR in phase, FR/RL antiphase -> trot."""
    t = np.arange(n_steps) * DT
    w = 2 * np.pi / period
    return {leg: np.maximum(np.sin(w * t + PHASE[leg]), 0.0) for leg in legs_active}


def swing_windows(envelope):
    """Contiguous index runs (inclusive) where envelope > 0."""
    active = envelope > 1e-9
    windows, start = [], None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            windows.append((start, i - 1))
            start = None
    if start is not None:
        windows.append((start, len(active) - 1))
    return windows


def build_actions(env, hfe_sign, kfe_sign, amplitude, period, n_steps, legs_active):
    actions = np.zeros((n_steps, env.action_size), dtype=np.float32)
    for leg, envp in leg_envelopes(period, n_steps, legs_active).items():
        actions[:, HFE_IDX[leg]] = hfe_sign * amplitude * envp
        actions[:, KFE_IDX[leg]] = kfe_sign * amplitude * envp
    return actions


def run_combo(env, jit_step, settled_state, hfe_sign, kfe_sign, amplitude, period,
              legs_active, n_steps=MEASURE_STEPS):
    """Drive one scripted combo for n_steps (or until fall). Returns:
      peaks       — list of per-leg per-cycle PEAK foot_h (m), only for
                    cycles fully executed within the measured window
      fell        — bool, base dropped below FALL_BASE_Z or env done fired
      fall_step   — step index of the fall (None if it didn't)
      n_cycles    — len(peaks)
    """
    actions = build_actions(env, hfe_sign, kfe_sign, amplitude, period, n_steps, legs_active)
    envelopes = leg_envelopes(period, n_steps, legs_active)

    state = settled_state
    h_hist = np.zeros((n_steps, 4), dtype=np.float32)
    fell, fall_step, steps_done = False, None, 0
    for i in range(n_steps):
        state = jit_step(state, jp.asarray(actions[i]))
        h_hist[i] = foot_h_all(env, state)
        steps_done = i + 1
        if float(state.done) > 0.5 or base_z(state) < FALL_BASE_Z:
            fell, fall_step = True, i
            break

    peaks = []
    peak_details = []   # (leg, cycle_start_idx, peak_m) for diagnostics
    for leg in legs_active:
        foot_i = LEG_NAMES.index(leg)
        for (s, e) in swing_windows(envelopes[leg]):
            # keep only cycles fully realized within what we actually ran:
            # drop any window cut short by a fall, and drop the trailing
            # window if it's cut short by hitting the end of the array.
            if e >= steps_done or e == n_steps - 1:
                continue
            pk = float(np.max(h_hist[s:e + 1, foot_i]))
            peaks.append(pk)
            peak_details.append((leg, s, pk))
    return peaks, fell, fall_step, len(peaks), peak_details


def print_table(title, results, legs_label):
    print(f"\n== {title} ({legs_label}) — mean per-cycle peak foot_h ==")
    header = "  T\\a  " + "".join(f"{a:>10.1f}" for a in AMPLITUDES)
    print(header)
    for T in PERIODS:
        row = f"  {T:.1f}s "
        for a in AMPLITUDES:
            peaks, fell, fall_step, nc, _details = results[(a, T)]
            if nc == 0:
                cell = "  no data" if not fell else " FELL<1cyc"
            else:
                mean_cm = np.mean(peaks) * 100
                cell = f"{mean_cm:6.2f}cm{'*' if fell else ' '}"
            row += f"{cell:>10}"
        print(row)
    print("  (* = fell during/after this combo — falling IS data, not failure;")
    print("   cell value is the MEAN per-cycle peak measured before the fall)")

    print(f"\n== {title} — MAX single-cycle peak foot_h ==")
    print(header)
    for T in PERIODS:
        row = f"  {T:.1f}s "
        for a in AMPLITUDES:
            peaks, fell, fall_step, nc, _details = results[(a, T)]
            if nc == 0:
                cell = "  no data" if not fell else " FELL<1cyc"
            else:
                max_cm = max(peaks) * 100
                cell = f"{max_cm:6.2f}cm{'*' if fell else ' '}"
            row += f"{cell:>10}"
        print(row)


def main():
    t0 = time.time()
    env, jit_reset, jit_step = make_env()
    print(f"NovaJoystick: action_size={env.action_size}  obs_size={env.observation_size}")

    rng = jax.random.PRNGKey(0)
    state0 = jit_reset(rng)
    settled = settle(env, jit_step, state0, SETTLE_STEPS)
    print(f"settled base z = {base_z(settled):.4f} m")
    print(f"settled stance foot_h (cm): "
          f"{np.round(foot_h_all(env, settled) * 100, 2).tolist()}  ({LEG_NAMES})")

    # ---- sign calibration ----
    hfe_sign, kfe_sign, calib = calibrate_sign(env, jit_step, settled)
    print("\n-- sign calibration (single-leg FL probe, amplitude=1.0, 15 steps) --")
    for (hs, ks), delta in sorted(calib.items(), key=lambda kv: -kv[1]):
        print(f"  hfe_sign={hs:+.0f} kfe_sign={ks:+.0f} -> FL foot_z delta {delta * 100:+.2f} cm")
    print(f"  chosen (max lift): hfe_sign={hfe_sign:+.0f} kfe_sign={kfe_sign:+.0f}")
    print(f"  [{time.time() - t0:.0f}s elapsed]")

    # ---- trot sweep ----
    print("\n-- running TROT sweep (diagonal FL+RR vs FR+RL) --")
    trot_results = {}
    trot_records = []   # (a, T, leg, cycle_start_step, peak_m) for every measured cycle
    for a in AMPLITUDES:
        for T in PERIODS:
            peaks, fell, fall_step, nc, details = run_combo(
                env, jit_step, settled, hfe_sign, kfe_sign, a, T, LEG_NAMES)
            trot_results[(a, T)] = (peaks, fell, fall_step, nc, details)
            trot_records += [(a, T, leg, s, pk) for (leg, s, pk) in details]
            mean_cm = np.mean(peaks) * 100 if nc else float("nan")
            print(f"  a={a:.1f} T={T:.1f}s -> mean peak {mean_cm:6.2f} cm  "
                  f"cycles_measured={nc:3d}  fell={fell}"
                  + (f"@step{fall_step}" if fell else "")
                  + f"   [{time.time() - t0:.0f}s]")

    print_table("TROT sweep", trot_results, "full quadruped, diagonal gait")

    trot_all_peaks = [p for (peaks, *_r) in trot_results.values() for p in peaks]
    trot_has_data = len(trot_all_peaks) > 0

    fallback_results = None
    fallback_records = []
    if not trot_has_data:
        print("\n!! every trot combo fell before completing a single swing cycle —"
              " trot is too unstable to isolate the actuation ceiling.")
        print("   Falling back to a STANDING single-leg probe (FL swings, "
              "FR/RL/RR hold default stance) to isolate actuation from balance.")
        fallback_results = {}
        for a in AMPLITUDES:
            for T in PERIODS:
                peaks, fell, fall_step, nc, details = run_combo(
                    env, jit_step, settled, hfe_sign, kfe_sign, a, T, ["FL"])
                fallback_results[(a, T)] = (peaks, fell, fall_step, nc, details)
                fallback_records += [(a, T, leg, s, pk) for (leg, s, pk) in details]
                mean_cm = np.mean(peaks) * 100 if nc else float("nan")
                print(f"  a={a:.1f} T={T:.1f}s -> FL mean peak {mean_cm:6.2f} cm  "
                      f"cycles_measured={nc:3d}  fell={fell}"
                      + (f"@step{fall_step}" if fell else "")
                      + f"   [{time.time() - t0:.0f}s]")
        print_table("SINGLE-LEG (standing) sweep", fallback_results, "FL swing only, others stance")

    # ---- overall best (with provenance, so a single-cycle spike is
    # traceable rather than trusted blind) ----
    all_records = list(trot_records)
    all_peaks = list(trot_all_peaks)
    best_source = "trot"
    if fallback_results is not None:
        fb_peaks = [p for (peaks, *_r) in fallback_results.values() for p in peaks]
        if fb_peaks and (not all_peaks or max(fb_peaks) > max(all_peaks or [0.0])):
            best_source = "single-leg standing fallback"
        all_peaks += fb_peaks
        all_records += fallback_records

    if all_records:
        top5 = sorted(all_records, key=lambda r: -r[4])[:5]
        print("\n-- top 5 individual per-cycle peaks (provenance check) --")
        for (a, T, leg, s, pk) in top5:
            print(f"  {pk*100:6.2f} cm  leg={leg}  a={a:.1f} T={T:.1f}s  cycle_start_step={s}")

    if all_peaks:
        best_cm = max(all_peaks) * 100
        print(f"\n== BEST ACHIEVABLE PEAK FOOT CLEARANCE (single cycle): {best_cm:.2f} cm "
              f"(source: {best_source}) ==")
        # also report the best STEADY-STATE mean (most representative of a
        # sustained trot cadence, vs. a single best-case cycle)
        best_mean_combo, best_mean_cm = None, -1.0
        for (a, T), (peaks, fell, fall_step, nc, details) in trot_results.items():
            if nc:
                m = np.mean(peaks) * 100
                if m > best_mean_cm:
                    best_mean_cm, best_mean_combo = m, (a, T)
        if best_mean_combo:
            print(f"== BEST SUSTAINED (mean-per-cycle) TROT: {best_mean_cm:.2f} cm "
                  f"at a={best_mean_combo[0]:.1f} T={best_mean_combo[1]:.1f}s ==")
    else:
        print("\n== NO valid peak measured in ANY combo (every combo fell "
              "before one full cycle, trot AND single-leg) — actuation may be "
              "too weak/damped for this amplitude/period grid, or something "
              "is wrong with the sign calibration. ==")

    print(f"\ntotal runtime: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
