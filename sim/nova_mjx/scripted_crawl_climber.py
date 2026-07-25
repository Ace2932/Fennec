"""SCRIPTED CRAWL-CLIMB CONTROLLER — the v9 imitation "expert" (PREMISE GATE).

WHY THIS EXISTS
---------------
8 RL generations failed to make the policy DISCOVER a stair-climbing crawl (v8 came
out a splayed in-place shuffle — a learning failure, not a hardware wall: the
CoM-shift de-confound proved rears reach ~5.4 cm and the front-lift ceiling is
~6.7 cm). v9's bet is to CLONE a scripted expert instead of hoping RL finds the
correlated forward-crawl. But behaviour cloning is worthless if the expert can't
climb — so THIS controller must DEMONSTRABLY climb stairs FIRST. If a hand-written
whole-body crawl-climb can't ascend >=2 risers stably, the imitation direction is
dead and we bank the walker (honest hardware/controls wall).

WHAT IT IS
----------
A whole-body, terrain-aware crawl driven OPEN-LOOP through the SAME real actuator
model the probes used (env.step: position servos kp=35, +-1.8 N.m hfe/kfe
forcerange, firmware deadband, latency buffer), joint targets from the VALIDATED
leg IK (nova_locomotion.kinematics.leg_ik — never rewritten). "Scripted" = the
targets come from a foothold plan, NOT a trained net; it reads the measured base
pose (privileged sim odometry — legitimate for a model-based expert) to close the
loop on where the body is.

CONTROL ARCHITECTURE — body-pose control with fixed world footholds
-------------------------------------------------------------------
An early open-loop body-frame "sweep the stance feet backward" gait did NOT propel
(the stiff position servos let the feet slip; net travel ~0). The reliable method,
used here, INVERTS it: the controller commands the BODY POSE (advancing +x, held up
over the treads) and, for each stance leg at its FIXED world foothold, solves the
hip-frame foot target via the measured/known hip mounting geometry -> the stance
legs push against planted feet to drive the body to the commanded pose. Propulsion
is thus DIRECTLY commanded, not hoped for.

  1. CRAWL SCHEDULE — one foot swings at a time, order RL->FL->RR->FR
     (== env CRAWL_OFFSETS=[0.5,0,0.75,0.25], duty CRAWL_DUTY=0.75), slow ~0.45 Hz.
  2. FOOTHOLD PLANNER — when a leg enters swing it retargets its foothold a STEP_LEN
     forward (+x); the landing tread height is read straight off the collision
     surface (env._terrain_ground_z at the projected landing xy — the ground truth
     of the staircase). The swing arc LIFTS the foot CLEARANCE above the higher of
     (liftoff, landing) tread so it clears the riser edge, then sets down on the
     tread. The body glides forward continuously while feet step discretely.
  3. CoM-SHIFT — while a foot swings, the commanded body y sways toward the centroid
     of the 3 planted footholds (gain ~0.5) so the lifting leg unloads and the robot
     doesn't roll (the +3.3 cm de-confound mechanism, applied directly to the body
     target — no calibration needed under body-pose control).
  4. BODY PITCH — the commanded body z rises with the mean tread; front feet land on
     higher treads than rear, and a commanded pitch tracks the local slope so the
     legs stay in workspace as the body climbs.

VALIDATE (the gate): rollout on a stair env (stair-level 0.25 = 2 cm risers first,
then 0.5 = 4 cm), MEASURE base-z ascent, per-foot tread landings, up_z (no fall),
print PASS/FAIL (PASS = base ascends >=2 risers, feet climb successive treads,
up_z>0.9), + render a video + traces.

  JAX_PLATFORMS=cpu MUJOCO_GL=cgl python scripted_crawl_climber.py --stair-level 0.25
"""
import argparse
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import (   # noqa: E402
    NovaJoystick, DEFAULT_POSE, ACTION_SCALE, CRAWL_OFFSETS, CRAWL_DUTY, LEG_NAMES,
)
from terrain import terrain_field, STAIR_RISE   # noqa: E402

DT = 0.02                                        # 50 Hz control, matches env._dt
PARAMS = LegParams()
FRONT_IDX = [LEG_NAMES.index("FL"), LEG_NAMES.index("FR")]
REAR_IDX = [LEG_NAMES.index("RL"), LEG_NAMES.index("RR")]

# neutral canonical foot (FK of the sim stand keyframe); knee_forward=False matches
# DEFAULT_POSE kfe=-1.2 (elbow-back branch), same as the probes.
_DEF_LEG = tuple(float(v) for v in DEFAULT_POSE[:3])
_X0, _D, _Z0 = forward_kinematics(_DEF_LEG, PARAMS)

# HAA-mount (canonical-frame origin) offset in the BODY frame, per leg (LEG_NAMES
# order), MEASURED from nova.xml at the stand keyframe (body '<leg>_hip' pos minus
# trunk). The IK canonical target = (foot - hip) in the body frame, +y outboard;
# side_sign maps body-y -> outboard (left +y, right -y is outboard).
HIP_BODY = {
    "FL": np.array([0.1412, 0.039, 0.038]),
    "FR": np.array([0.1412, -0.039, 0.038]),
    "RL": np.array([-0.1412, 0.039, 0.038]),
    "RR": np.array([-0.1412, -0.039, 0.038]),
}
HB = np.array([HIP_BODY[n] for n in LEG_NAMES])          # (4,3)
SIDE = np.array([1.0 if n[1] == "L" else -1.0 for n in LEG_NAMES])   # outboard sign
LAT = _D                                                 # outboard hip->foot y (m)

# --- gait / foothold-plan tunables (the gate knobs) --------------------------
GAIT_FREQ = 0.42          # Hz — full 4-foot cycle rate (slow crawl -> high lift)
DUTY = float(CRAWL_DUTY)  # 0.75 stance fraction (3-leg support)
OFFS = np.asarray(CRAWL_OFFSETS, dtype=np.float64)   # per-leg phase, LEG_NAMES order
STEP_FWD = 0.02           # forward reach of each new foothold AHEAD of its (measured)
#                         # hip at swing (m). Placing relative to the MEASURED hip caps
#                         # the gait to the body's real speed — footholds can't race off
#                         # and over-reach the legs (blind per-swing increments did).
FWD_LEAN = 0.07           # THE PROPULSION: command the body this far AHEAD of the mean
#                         # foothold (a forward lean). The stance legs, now behind the
#                         # body, push it forward. Swept-validated: lean 0.04-0.08 gives
#                         # steady stable forward crawl; 0 (centred) drifts slowly back.
CLEARANCE = 0.05          # swing arc lift above the interpolated tread ramp (m) — clears
#                         # the riser edge (peak above liftoff = riser + CLEARANCE).
COM_GAIN = 0.45          # fraction of support-centroid LATERAL body sway (keeps upright)
PITCH_GAIN = 1.0          # fraction of the tread-slope pitch the body tracks
LEAN_CLIMB = 1.0          # EXTRA forward lean per metre of tread SPREAD (feet straddling a
#                         # riser) — pushes the body up the step. Gentle on flat (spread 0);
#                         # too high topples forward (>=1.2 falls), too low stalls. This is
#                         # the STABLE edge: reaches the riser + front foot up, no fall.
FRONT_LIFT = 0.4          # raise body-z by this * (front_tread - rear_tread) to help lift
#                         # the body onto the step as the front feet climb.
RAMP_CYCLES = 0.0         # ramp 0->full over first N cycles (0 = full from step 0; the
#                         # ramp DESTABILISES this lean-driven gait — keep it off)
SETTLE_STEPS = 80

FALL_BASE_Z = 0.08
FALL_UP_Z = 0.4


# ---------------------------------------------------------------------------
def make_env(stair_level):
    env = NovaJoystick(heightmap=True, push_mag=0.0)
    if stair_level > 0:
        hf = terrain_field(jax.random.PRNGKey(0), stair_level, 0.0, 1.0)  # stair_frac=1
        env.sys = env.sys.tree_replace({"hfield_data": jp.asarray(hf)})
    return env, jax.jit(env.reset), jax.jit(env.step)


def _pin(state):
    """Pin cmd=0 and latency delay=0 (clean open-loop injection — same as probes)."""
    return state.replace(info={**state.info,
                               "cmd": jp.zeros(3, dtype=np.float32),
                               "delay": jp.asarray(0, dtype=state.info["delay"].dtype)})


def foot_pos(env, state):
    return np.asarray(state.pipeline_state.x.pos[np.asarray(env._foot_ids)])   # (4,3)


def base_pos(state):
    return np.asarray(state.pipeline_state.x.pos[0])                            # (3,)


def up_z(state):
    q = np.asarray(state.pipeline_state.x.rot[0])   # (w,x,y,z)
    return float(1.0 - 2.0 * (q[1] ** 2 + q[2] ** 2))


def ground_z(env, wx, wy):
    return float(env._terrain_ground_z(jp.asarray(float(wx)), jp.asarray(float(wy))))


def settle(env, jit_step, state, n=SETTLE_STEPS):
    zero = jp.zeros(env.action_size)
    for _ in range(n):
        state = _pin(state)
        state = jit_step(state, zero)
    return state


def ik_action(li, canon_target, default):
    """12-vec with leg li driven to canonical (x,y,z). Returns (action12 or None)."""
    try:
        t1, t2, t3 = inverse_kinematics(canon_target, PARAMS, knee_forward=False)
    except Unreachable:
        return None
    j = 3 * li
    a = np.zeros(12, dtype=np.float32)
    a[j + 0] = (t1 - default[j + 0]) / ACTION_SCALE
    a[j + 1] = (t2 - default[j + 1]) / ACTION_SCALE
    a[j + 2] = (t3 - default[j + 2]) / ACTION_SCALE
    return a


def rot_pitch(p):
    """Body pitch about +y (nose-up positive): world = R @ body."""
    c, s = np.cos(p), np.sin(p)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def leg_phase(theta):
    """(is_swing, frac) per leg (LEG_NAMES order) at global phase theta in [0,1)."""
    out = []
    for i in range(4):
        lp = (theta + OFFS[i]) % 1.0
        if lp < DUTY:
            out.append((False, lp / DUTY))
        else:
            out.append((True, (lp - DUTY) / (1.0 - DUTY)))
    return out


def run(env, jit_reset, jit_step, stair_level, n_steps, seed=0):
    default = np.asarray(DEFAULT_POSE, dtype=np.float64)
    state = _pin(jit_reset(jax.random.PRNGKey(seed)))
    state = settle(env, jit_step, state)

    f0 = foot_pos(env, state)
    b0 = base_pos(state)
    foot_r = np.array([f0[i, 2] - ground_z(env, f0[i, 0], f0[i, 1]) for i in range(4)])
    # body reference height above the local treads (sag-resistant): keep the commanded
    # body z = mean_tread + BODY_H so the stance legs HOLD the body up as it climbs,
    # instead of following it down into a sag.
    mean_tread0 = np.mean([ground_z(env, f0[i, 0], f0[i, 1]) for i in range(4)])
    BODY_H = float(b0[2] - mean_tread0)
    rise = STAIR_RISE * stair_level

    # initial footholds = the settled foot world positions (so step 0 command ~= now)
    foothold = f0.copy()                     # (4,3) world xyz per leg (planted target)
    swing_from = f0.copy()                   # (4,3) world xyz each swing lifts off from
    prev_swing = np.zeros(4, dtype=bool)

    print(f"settle: base z={b0[2]:.4f} up_z={up_z(state):.4f}  rise/step={rise*100:.2f}cm "
          f"BODY_H={BODY_H:.4f} FWD_LEAN={FWD_LEAN} STEP_FWD={STEP_FWD}")
    print(f"        foot z0(cm)={np.round(f0[:,2]*100,2).tolist()} ({LEG_NAMES})  "
          f"foot_r(cm)={np.round(foot_r*100,2).tolist()}")

    qpos = [np.array(state.pipeline_state.q)]
    bz = np.zeros(n_steps); bx = np.zeros(n_steps); uz = np.zeros(n_steps)
    fz = np.zeros((n_steps, 4)); fgz = np.zeros((n_steps, 4))
    which = np.full(n_steps, -1, dtype=int)
    n_unreach = 0; fell = False; done_step = n_steps

    for k in range(n_steps):
        cyc = k * DT * GAIT_FREQ
        theta = cyc % 1.0
        amp = min(1.0, cyc / RAMP_CYCLES) if RAMP_CYCLES > 0 else 1.0
        ph = leg_phase(theta)
        sw_leg = next((i for i in range(4) if ph[i][0]), -1)
        b_meas = base_pos(state)                 # MEASURED base — anchor everything here

        # --- foothold planner: on swing ENTRY, place this leg's foothold STEP_FWD ahead
        #     of its MEASURED hip (so footholds track the real body, never race it); the
        #     landing tread height is read straight off the collision surface (climb) ---
        for i in range(4):
            is_sw = ph[i][0]
            if is_sw and not prev_swing[i]:
                swing_from[i] = foothold[i].copy()       # lift off from where it stood
                nx = b_meas[0] + HB[i, 0] + _X0 + STEP_FWD
                ny = b_meas[1] + HB[i, 1] + SIDE[i] * LAT
                foothold[i] = np.array([nx, ny, ground_z(env, nx, ny) + foot_r[i]])
            prev_swing[i] = is_sw

        # --- commanded body pose: carrot LEAD ahead of the measured base (steady
        #     forward pull), tread-tracking z, slope pitch, CoM sway ---
        treads_now = np.array([ground_z(env, foothold[i, 0], foothold[i, 1])
                               for i in range(4)])
        front_t = treads_now[FRONT_IDX].mean(); rear_t = treads_now[REAR_IDX].mean()
        spread = float(treads_now.max() - treads_now.min())      # feet straddling a riser
        # body z: track the treads + lift the front onto the step; pitch to the slope.
        body_z = float(treads_now.mean()) + BODY_H + amp * FRONT_LIFT * (front_t - rear_t)
        pitch = amp * PITCH_GAIN * np.arctan2(front_t - rear_t, 2 * abs(HB[0, 0]))
        body_y = 0.0
        if sw_leg >= 0:
            stance = [i for i in range(4) if i != sw_leg]
            body_y = amp * COM_GAIN * foothold[stance, 1].mean()
        # command the body FWD_LEAN ahead of the mean foothold (propulsion: stance legs
        # end behind the leaned body and push it forward), + LEAN_CLIMB*spread EXTRA lean
        # to drive up a riser. Footholds ratchet forward, the mean advances, body follows.
        body_x = (float(foothold[:, 0].mean()) - _X0
                  + amp * (FWD_LEAN + LEAN_CLIMB * spread))
        Pb = np.array([body_x, body_y, body_z])
        R = rot_pitch(pitch)

        # --- per-leg IK from the commanded body pose + world footholds ---
        act = np.zeros(12, dtype=np.float32)
        for i in range(4):
            is_sw, frac = ph[i]
            hip_w = Pb + R @ HB[i]                       # commanded hip world position
            # swing target world xyz (arc from swing_from to the new foothold);
            # stance target = the fixed planted foothold
            if is_sw:
                p_from = swing_from[i]
                p_to = foothold[i]
                fx = p_from[0] + (p_to[0] - p_from[0]) * frac
                fy = p_from[1] + (p_to[1] - p_from[1]) * frac
                base_z_arc = p_from[2] + (p_to[2] - p_from[2]) * frac
                fzt = base_z_arc + amp * CLEARANCE * np.sin(np.pi * frac)
                foot_w = np.array([fx, fy, fzt])
            else:
                foot_w = foothold[i]
            vec_body = R.T @ (foot_w - hip_w)
            canon = (vec_body[0], SIDE[i] * vec_body[1], vec_body[2])
            a = ik_action(i, canon, default)
            if a is None:
                n_unreach += 1
            else:
                act += a

        state = _pin(state)
        state = jit_step(state, jp.asarray(act))
        b = base_pos(state); fpm = foot_pos(env, state)
        bz[k] = b[2]; bx[k] = b[0]; uz[k] = up_z(state); which[k] = sw_leg
        fz[k] = fpm[:, 2]
        for i in range(4):
            fgz[k, i] = ground_z(env, fpm[i, 0], fpm[i, 1])
        qpos.append(np.array(state.pipeline_state.q))
        done_step = k + 1
        if k % 100 == 0 or k == n_steps - 1:
            print(f"  [step {k:4d}] base_x={b[0]:+.3f} base_z={b[2]:.3f} "
                  f"up_z={uz[k]:.3f} meanFH_x={foothold[:,0].mean():+.3f} "
                  f"cmd_bx={body_x:+.3f} sw={sw_leg} nurch={n_unreach}")
        if float(state.done) > 0.5 or b[2] < FALL_BASE_Z or uz[k] < FALL_UP_Z:
            fell = True
            break

    d = done_step
    return {
        "qpos": qpos, "bz": bz[:d], "bx": bx[:d], "uz": uz[:d],
        "fz": fz[:d], "fgz": fgz[:d], "which": which[:d],
        "b0": b0, "f0": f0, "rise": rise, "fell": fell, "done_step": d,
        "n_unreach": n_unreach,
    }


def verdict(r, stair_level):
    rise = r["rise"]
    b0z = r["b0"][2]
    bz = r["bz"]
    base_ascent = float(bz[-1] - b0z)
    base_peak = float(np.max(bz) - b0z)
    x_travel = float(r["bx"][-1] - r["b0"][0])
    up_min = float(np.min(r["uz"]))
    fgz = r["fgz"]
    foot_peak_tread = np.max(fgz, axis=0)         # highest tread each foot reached
    risers_per_foot = foot_peak_tread / max(rise, 1e-6)
    n_risers_base = base_ascent / max(rise, 1e-6)

    print("\n" + "=" * 78)
    print(f"VERDICT — stair-level {stair_level:.2f} (rise {rise*100:.2f} cm/step)")
    print("=" * 78)
    print(f"  base ascent (final-spawn) = {base_ascent*100:+6.2f} cm  "
          f"= {n_risers_base:+.2f} risers   (peak {base_peak*100:+.2f} cm)")
    print(f"  base x travel             = {x_travel*100:+6.2f} cm")
    print(f"  up_z min                  = {up_min:.3f}   fell={r['fell']}  "
          f"steps={r['done_step']}  n_unreach={r['n_unreach']}")
    print(f"  per-foot highest tread reached (cm) = "
          f"{np.round(foot_peak_tread*100,2).tolist()} ({LEG_NAMES})")
    print(f"  per-foot risers climbed             = "
          f"{np.round(risers_per_foot,2).tolist()}")
    feet_climbed = int(np.sum(foot_peak_tread >= 1.5 * rise)) if rise > 1e-6 else 0
    stable = (not r["fell"]) and up_min > 0.9
    climbs = base_ascent >= 2.0 * rise
    feet_ok = feet_climbed >= 2
    passed = climbs and stable and feet_ok
    print("-" * 78)
    print(f"  climb >=2 risers          : {'YES' if climbs else 'NO':3}  "
          f"({base_ascent*100:.2f}cm vs {2*rise*100:.2f}cm needed)")
    print(f"  >=2 feet on higher treads : {'YES' if feet_ok else 'NO':3}  "
          f"({feet_climbed}/4 feet)")
    print(f"  stable (up_z>0.9, no fall): {'YES' if stable else 'NO'}")
    print(f"\n  ===> {'PASS — IT CLIMBS' if passed else 'FAIL — does not climb >=2 risers stably'}")
    return passed, base_ascent, up_min, stable


def render(env, stair_level, qpos, out_mp4, frame_dir):
    import mujoco
    m = mujoco.MjModel.from_xml_path(os.path.join(os.path.dirname(__file__), "nova.xml"))
    if stair_level > 0:
        m.hfield_data[:] = np.asarray(
            terrain_field(jax.random.PRNGKey(0), stair_level, 0.0, 1.0))
    d = mujoco.MjData(m)
    cam = m.camera("track").id
    frames = []
    with mujoco.Renderer(m, height=480, width=640) as rnd:
        for q in qpos:
            d.qpos[:] = q
            mujoco.mj_forward(m, d)
            rnd.update_scene(d, camera=cam)
            frames.append(rnd.render())
    import imageio
    imageio.mimsave(out_mp4, frames, fps=50, macro_block_size=None)
    os.makedirs(frame_dir, exist_ok=True)
    idxs = np.linspace(0, len(frames) - 1, 8).astype(int)
    for j, ix in enumerate(idxs):
        imageio.imwrite(os.path.join(frame_dir, f"frame_{j:02d}_step{ix}.png"), frames[ix])
    print(f"  video: {out_mp4} ({len(frames)} frames)  frames: {frame_dir}/")


def save_traces(r, stair_level, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"  (matplotlib unavailable, skipping traces: {e})")
        return
    t = np.arange(r["done_step"]) * DT
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    ax[0].plot(t, (r["bz"] - r["b0"][2]) * 100, "b-")
    for n in range(1, 6):
        ax[0].axhline(n * r["rise"] * 100, color="gray", ls=":", lw=0.7)
    ax[0].set_ylabel("base ascent (cm)"); ax[0].grid(alpha=0.3)
    ax[0].set_title(f"scripted crawl-climb — stair-level {stair_level:.2f} "
                    f"(rise {r['rise']*100:.1f}cm)")
    for i, nm in enumerate(LEG_NAMES):
        ax[1].plot(t, r["fgz"][:, i] * 100, label=nm)
    ax[1].set_ylabel("foot ground-tread z (cm)"); ax[1].legend(ncol=4); ax[1].grid(alpha=0.3)
    ax[2].plot(t, r["uz"], "g-"); ax[2].axhline(0.9, color="r", ls="--", lw=0.8)
    ax[2].set_ylabel("up_z"); ax[2].set_xlabel("time (s)"); ax[2].set_ylim(0, 1.05)
    ax[2].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=90)
    print(f"  traces: {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stair-level", type=float, default=0.25)
    ap.add_argument("--steps", type=int, default=900)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--freq", type=float, default=None)
    ap.add_argument("--step-fwd", type=float, default=None)
    ap.add_argument("--fwd-lean", type=float, default=None)
    ap.add_argument("--clearance", type=float, default=None)
    ap.add_argument("--com-gain", type=float, default=None)
    ap.add_argument("--pitch-gain", type=float, default=None)
    ap.add_argument("--ramp", type=float, default=None)
    args = ap.parse_args()

    global GAIT_FREQ, STEP_FWD, FWD_LEAN, CLEARANCE, COM_GAIN, PITCH_GAIN, RAMP_CYCLES
    if args.freq is not None: GAIT_FREQ = args.freq
    if args.step_fwd is not None: STEP_FWD = args.step_fwd
    if args.fwd_lean is not None: FWD_LEAN = args.fwd_lean
    if args.clearance is not None: CLEARANCE = args.clearance
    if args.com_gain is not None: COM_GAIN = args.com_gain
    if args.pitch_gain is not None: PITCH_GAIN = args.pitch_gain
    if args.ramp is not None: RAMP_CYCLES = args.ramp

    t0 = time.time()
    lvl = args.stair_level
    out_dir = args.out_dir or os.path.join(os.path.dirname(__file__), "climber_out")
    os.makedirs(out_dir, exist_ok=True)
    tag = f"L{lvl:.2f}".replace(".", "p")

    print("=" * 78)
    print(f"SCRIPTED CRAWL-CLIMB CONTROLLER — stair-level {lvl:.2f}  ({args.steps} steps)")
    print("=" * 78)
    print(f"neutral canonical foot: x0={_X0:+.5f} d={_D:.5f} z0={_Z0:+.5f}")
    print(f"gait freq={GAIT_FREQ}Hz duty={DUTY} order(RL,FL,RR,FR) step_fwd={STEP_FWD} "
          f"fwd_lean={FWD_LEAN} clearance={CLEARANCE} com_gain={COM_GAIN} pitch={PITCH_GAIN}")

    env, jit_reset, jit_step = make_env(lvl)
    print(f"NovaJoystick action={env.action_size} obs={env.observation_size}  "
          f"stairs injected (stair_frac=1, level={lvl})\n")

    r = run(env, jit_reset, jit_step, lvl, args.steps)
    passed, ascent, up_min, stable = verdict(r, lvl)

    save_traces(r, lvl, os.path.join(out_dir, f"traces_{tag}.png"))
    if not args.no_render:
        try:
            render(env, lvl, r["qpos"], os.path.join(out_dir, f"climb_{tag}.mp4"),
                   os.path.join(out_dir, f"frames_{tag}"))
        except Exception as e:
            print(f"  (render failed: {e} — traces + data still saved)")
    print(f"\ntotal runtime: {time.time()-t0:.0f}s")
    return passed


if __name__ == "__main__":
    main()
