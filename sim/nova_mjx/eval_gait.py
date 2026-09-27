"""Common gait scorecard for the 2026-09-25 study: every variant, one yardstick.

Runs N domain-randomized envs (the training DR ranges, flat) under a FIXED
eval actuator — by default the firmware as written today (TORQUE_LIMIT 600,
GOAL_ACC 50) — so a policy is scored on the robot it will meet, not the one it
trained on. Two command sets: `fwd` pins cmd = [0.25, 0, 0]; `mixed` lets the
env sample its own stage-2 commands (resampled every 250 steps).

  python eval_gait.py --policy runs/x/policy.pkl [--asym] [--ref-gait] \
      --eval-torque-limit 0.6 --eval-goal-acc-reg 50 --json out.json

Columns:
  fall     fraction of episodes that hit done
  spd%     mean forward speed along the command / commanded speed (alive steps)
  verr     mean |cmd_xy - v_xy| (m/s);  yerr  mean |cmd_wz - wz| (rad/s)
  swing    mean height of airborne feet (cm)
  air      per-foot airborne fraction FL/FR/RL/RR (radius-corrected contact);
           a carried leg reads ~1, a dragged one ~0
  CoT      mean mechanical power / (m g |v|)  (nominal mass, not the per-env DR mass)
Known: the command is pinned after reset/step, so the reset obs and the step-250
in-env resample each carry the sampled command for ONE step of the rollout.
"""
import argparse
import functools
import json
import pickle

import jax
import jax.numpy as jp
import numpy as np
from brax import math
from brax.envs.wrappers.training import DomainRandomizationVmapWrapper

from env import (NovaJoystick, make_domain_randomize, goal_acc_rad, REF_HEIGHT,
                 FW_GUARD_POLLS)


def load_policy(path, env, asym):
    from brax.training.acme import running_statistics
    from brax.training.agents.ppo import networks as ppo_networks
    kw = ({"policy_obs_key": "state", "value_obs_key": "privileged_state"}
          if asym else {})
    net = ppo_networks.make_ppo_networks(
        env.observation_size, env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=(128, 128, 128, 128),
        value_hidden_layer_sizes=(256, 256, 256, 256), **kw)
    with open(path, "rb") as f:
        params = pickle.load(f)
    return ppo_networks.make_inference_fn(net)(params, deterministic=True)


def score(env, policy, n, steps, seed, pin_cmd, terrain=0.0, step_frac=0.0):
    dr = make_domain_randomize(terrain, step_frac=step_frac, flat_frac=0.0)
    keys = jax.random.split(jax.random.PRNGKey(seed + 1), n)
    venv = DomainRandomizationVmapWrapper(env, functools.partial(dr, rng=keys))
    mass = float(jp.sum(env.sys.body_mass))

    def pin(s):
        if pin_cmd is None:
            return s
        return s.replace(info={**s.info, "cmd": jp.broadcast_to(pin_cmd, (n, 3))})

    def body(carry, key):
        s, alive = carry
        a, _ = policy(s.obs, key)
        s = pin(venv.step(s, a))
        ps = s.pipeline_state
        qinv = jax.vmap(math.quat_inv)(ps.q[:, 3:7])
        v = jax.vmap(math.rotate)(ps.xd.vel[:, 0], qinv)
        w = jax.vmap(math.rotate)(ps.xd.ang[:, 0], qinv)
        cmd = s.info["cmd"]
        cs = jp.linalg.norm(cmd[:, :2], axis=1)
        moving = (cs > 0.1).astype(jp.float32)
        fwd = jp.sum(cmd[:, :2] * v[:, :2], axis=1) / jp.maximum(cs, 1e-6)
        power = jp.sum(jp.abs(ps.qfrc_actuator[:, 6:] * ps.qd[:, 6:]), axis=1)
        spd = jp.linalg.norm(v[:, :2], axis=1)
        m = s.metrics
        rec = dict(
            alive=alive,
            spd=fwd / jp.maximum(cs, 1e-6) * moving * alive, moving=moving * alive,
            verr=jp.linalg.norm(cmd[:, :2] - v[:, :2], axis=1) * alive,
            yerr=jp.abs(cmd[:, 2] - w[:, 2]) * alive,
            swing=m["swing_h_per_step"] * alive,
            air=jp.stack([m[f"airT_{k}"] for k in ("FL", "FR", "RL", "RR")], 1)
            * alive[:, None],
            cot=power / (mass * 9.81 * jp.maximum(spd, 0.05)) * moving * alive,
            tripped=m["n_tripped"] * alive, slew=m["slew_clip"] * alive,
            gmax=m["g_max"] * alive, g2max=m["g2_max"] * alive, i2=m["i2_leg"] * alive, tau=m["tau_leg"] * alive)
        alive = alive * (1.0 - s.done)
        return (s, alive), rec

    @jax.jit
    def rollout(key):
        k0, k1 = jax.random.split(key)
        s = pin(venv.reset(jax.random.split(k0, n)))
        (_, alive), rec = jax.lax.scan(body, (s, jp.ones(n)), jax.random.split(k1, steps))
        return alive, rec

    alive, rec = rollout(jax.random.PRNGKey(seed))
    rec = jax.tree_util.tree_map(np.asarray, rec)
    na = rec["alive"].sum()
    nm = max(rec["moving"].sum(), 1.0)
    return {
        "fall": float(1.0 - np.asarray(alive).mean()),
        "spd_pct": float(100 * rec["spd"].sum() / nm),
        "verr": float(rec["verr"].sum() / na),
        "yerr": float(rec["yerr"].sum() / na),
        "swing_cm": float(100 * rec["swing"].sum() / na),
        "air": [float(x) for x in rec["air"].sum((0, 1)) / na],
        "cot": float(rec["cot"].sum() / nm),
        # per-episode values FROZEN at the fall (max over alive steps): a fallen robot
        # keeps stepping against the ground in this loop (no auto-reset), which would
        # otherwise inflate the guard runs and zero the trip count (review of #444).
        "i2_leg": float(rec["i2"].sum() / na),   # hfe/kfe mean (tau/tau_stall)^2 (#484)
        "tau_leg_nm": float(rec["tau"].sum() / na),  # hfe/kfe mean |tau|, N*m (rail current)
        "servos_tripped_end": float(rec["tripped"].max(0).mean()),
        "slew_clip_frac": float(rec["slew"].sum() / na),
        # firmware stall guard: per-episode longest run at >= 90 % duty (ms at 50 Hz)
        "guard_trip_pct": float(100 * np.mean(rec["gmax"].max(0) >= FW_GUARD_POLLS)),
        "guard_run_ms_p50": float(20 * np.percentile(rec["gmax"].max(0), 50)),
        "guard_run_ms_p99": float(20 * np.percentile(rec["gmax"].max(0), 99)),
        "guard_run_ms_max": float(20 * rec["gmax"].max()),
        # guard v2 (stall_guard.h): same, counting only JAM polls
        "guard2_trip_pct": float(100 * np.mean(rec["g2max"].max(0) >= FW_GUARD_POLLS)),
        "guard2_run_ms_p50": float(20 * np.percentile(rec["g2max"].max(0), 50)),
        "guard2_run_ms_p99": float(20 * np.percentile(rec["g2max"].max(0), 99)),
        "guard2_run_ms_max": float(20 * rec["g2max"].max()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--asym", action="store_true")
    ap.add_argument("--ref-gait", action="store_true")
    ap.add_argument("--ref-height", type=float, default=REF_HEIGHT)
    ap.add_argument("--eval-torque-limit", type=float, default=0.6)
    ap.add_argument("--eval-goal-acc-reg", type=int, default=50)
    ap.add_argument("--joint-stale-p", type=float, default=0.5)
    ap.add_argument("--episodes", type=int, default=256)
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", default=None)
    ap.add_argument("--goal-slew", type=float, default=0.0,
                    help="firmware goal slew limit rad/s (3.07 = main.cpp); 0 = off")
    ap.add_argument("--overload-model", action="store_true",
                    help="servo self-unload after 2 s above 80%% duty (latched)")
    ap.add_argument("--terrain", type=float, default=0.0,
                    help="rough-terrain ceiling for the eval envs (0 = flat)")
    ap.add_argument("--step-frac", type=float, default=0.0,
                    help="fraction of eval envs with discrete steps (needs --terrain)")
    ap.add_argument("--eff-scale", type=float, default=1.0,
                    help="leg hfe/kfe stall x this; must match the policy's training")
    ap.add_argument("--kp-scale", type=float, default=1.0)
    ap.add_argument("--jam-joint", type=int, default=-1,
                    help="plant a JAM: lock this joint (0-11) within +-1 mrad of its default pose, "
                         "to prove guard v2 trips on the thing it exists for")
    a = ap.parse_args()

    env = NovaJoystick(torque_limit=a.eval_torque_limit,
                       goal_acc=goal_acc_rad(a.eval_goal_acc_reg),
                       joint_stale_p=a.joint_stale_p, asym=a.asym,
                       ref_gait=a.ref_gait, ref_height=a.ref_height,
                       overload_model=a.overload_model, goal_slew=a.goal_slew,
                       eff_scale=a.eff_scale, kp_scale=a.kp_scale)
    if a.jam_joint >= 0:
        # joint 0 is the free base, so leg joint k is joint k+1 (damping 1e3 NaN'd MJX)
        q0 = float(env._default_pose[a.jam_joint])
        env.sys = env.sys.replace(jnt_range=env.sys.jnt_range.at[1 + a.jam_joint].set(
            jp.array([q0 - 1e-3, q0 + 1e-3])))
    policy = load_policy(a.policy, env, a.asym)
    out = {"policy": a.policy, "eval_torque_limit": a.eval_torque_limit,
           "eval_goal_acc_reg": a.eval_goal_acc_reg, "joint_stale_p": a.joint_stale_p,
           "terrain": a.terrain, "step_frac": a.step_frac}
    for name, pin in (("fwd", jp.array([0.25, 0.0, 0.0])), ("mixed", None)):
        r = score(env, policy, a.episodes, a.steps, a.seed, pin, a.terrain, a.step_frac)
        out[name] = r
        print(f"{name:5s} fall {r['fall']:5.1%}  spd% {r['spd_pct']:5.1f}  "
              f"verr {r['verr']:.3f}  yerr {r['yerr']:.3f}  swing {r['swing_cm']:.2f}cm  "
              f"air {' '.join(f'{x:.2f}' for x in r['air'])}  CoT {r['cot']:.2f}  "
              f"tripped/robot {r['servos_tripped_end']:.2f}  slew-clip {r['slew_clip_frac']:.1%}  "
              f"fw-guard trip {r['guard_trip_pct']:.0f}% of eps (>=90% duty run p50/p99/max "
              f"{r['guard_run_ms_p50']:.0f}/{r['guard_run_ms_p99']:.0f}/{r['guard_run_ms_max']:.0f} ms)  "
              f"i2 {r['i2_leg']:.2f}  guard-v2 trip {r['guard2_trip_pct']:.0f}% (jam run p50/p99/max {r['guard2_run_ms_p50']:.0f}/"
              f"{r['guard2_run_ms_p99']:.0f}/{r['guard2_run_ms_max']:.0f} ms)")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
