"""Per-joint actuator torque under a trained policy — which joints saturate first,
and what a stronger servo on one joint group buys.

Scenarios (training DR on, 32 episodes each, alive steps only):
  stand   policy, zero command, flat
  trot    policy, fwd 0.25 m/s, flat
  curb    policy, fwd 0.25 m/s, probe_curb_height's full-width step (CURB_CM) — a
          one-cell ~31 deg RAMP at 5 cm hfield cells, not a vertical riser
Per joint group (FL/FR/RL/RR x haa/hfe/kfe): p50 / p95 / max |tau| (N*m) from
MJX qfrc_actuator, and % of steps above 80 % of the part's stall — the STS3215
self-unloads above 80 % duty for 2 s. Stalls: legs 1.91 N*m (7.4 V part),
hips 2.94 (12 V C018), as given for the bench parts.

Counterfactual (--upgrade GROUP): raise that group's actuator forcerange to 2.94
N*m (damping scaled with it, i.e. same no-load speed — the conservative case)
and re-run the curb course at 3/4/5 cm. The policy was NOT retrained, so this is
a lower bound on what the upgrade buys.

Actuator model: whatever the policy flags say (plain position actuator unless
--goal-acc-reg); say which in any report.

  JAX_PLATFORMS=cpu python probe_joint_torque.py --policy P.pkl --asym
"""
import argparse
import functools

import jax
import jax.numpy as jp
import numpy as np
from brax.envs.wrappers.training import DomainRandomizationVmapWrapper

from env import NovaJoystick, make_domain_randomize, goal_acc_rad, LEG_NAMES
from eval_gait import load_policy
from probe_curb_height import curb_field, run as curb_run

STALL = {"haa": 2.94, "hfe": 1.91, "kfe": 1.91}
JOINTS = ("haa", "hfe", "kfe")
CURB_CM = 3


def upgrade(env, groups):
    """groups like ['RL_kfe', 'RR_kfe'] -> forcerange 2.94 N*m, damping scaled."""
    names = [f"{l}_{j}" for l in LEG_NAMES for j in JOINTS]
    idx = [names.index(g) for g in groups]
    fr = env.sys.actuator_forcerange
    scale = jp.ones(env.sys.nu).at[jp.array(idx)].set(2.94 / fr[jp.array(idx), 1])
    env.sys = env.sys.replace(
        actuator_forcerange=fr * scale[:, None],
        dof_damping=env.sys.dof_damping.at[6:].multiply(scale))
    return env


def torques(env, policy, n, steps, cmd, field=None):
    dr = make_domain_randomize(0.0)

    def rand(sys, rng):
        s2, ax = dr(sys, rng)
        if field is not None:
            s2 = s2.tree_replace({"hfield_data": jp.broadcast_to(field, s2.hfield_data.shape)})
        return s2, ax

    venv = DomainRandomizationVmapWrapper(
        env, functools.partial(rand, rng=jax.random.split(jax.random.PRNGKey(1), n)))
    c = jp.broadcast_to(jp.asarray(cmd, jp.float32), (n, 3))

    def body(carry, k):
        s, alive = carry
        a, _ = policy(s.obs, k)
        s = venv.step(s, a)
        s = s.replace(info={**s.info, "cmd": c})
        return (s, alive * (1.0 - s.done)), (jp.abs(s.pipeline_state.qfrc_actuator[:, 6:]), alive)

    @jax.jit
    def go(key):
        k0, k1 = jax.random.split(key)
        s = venv.reset(jax.random.split(k0, n))
        s = s.replace(info={**s.info, "cmd": c})
        _, (tau, alive) = jax.lax.scan(body, (s, jp.ones(n)), jax.random.split(k1, steps))
        return tau, alive

    tau, alive = go(jax.random.PRNGKey(0))
    tau, alive = np.asarray(tau), np.asarray(alive)
    return tau[alive > 0.5]                                         # (samples, 12)


def table(name, tau):
    print(f"\n{name}: |tau| N*m  p50 / p95 / max   (% steps > 80% stall)")
    for j, jn in enumerate(JOINTS):
        cells = []
        for li, ln in enumerate(LEG_NAMES):
            t = tau[:, 3 * li + j]
            hot = 100 * np.mean(t > 0.8 * STALL[jn])
            cells.append(f"{ln} {np.percentile(t, 50):.2f}/{np.percentile(t, 95):.2f}/{t.max():.2f} ({hot:4.1f}%)")
        print(f"  {jn}: " + "   ".join(cells))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--asym", action="store_true")
    ap.add_argument("--ref-gait", action="store_true")
    ap.add_argument("--goal-acc-reg", type=int, default=0)
    ap.add_argument("--episodes", type=int, default=32)
    ap.add_argument("--steps", type=int, default=400)
    a = ap.parse_args()

    def mk():
        return NovaJoystick(asym=a.asym, ref_gait=a.ref_gait, joint_stale_p=0.5,
                            goal_acc=goal_acc_rad(a.goal_acc_reg))

    env = mk()
    policy = load_policy(a.policy, env, a.asym)
    print(f"policy {a.policy}; actuator: plain position servo"
          + (f" + profile reg {a.goal_acc_reg}" if a.goal_acc_reg else " (no accel profile)")
          + f"; sim forcerange legs {float(env.sys.actuator_forcerange[1, 1]):.2f} "
            f"hips {float(env.sys.actuator_forcerange[0, 1]):.2f} N*m")
    table("stand (zero cmd, flat)", torques(env, policy, a.episodes, a.steps, [0, 0, 0]))
    table("trot (0.25 m/s, flat)", torques(env, policy, a.episodes, a.steps, [0.25, 0, 0]))
    table(f"curb {CURB_CM} cm (0.25 m/s)", torques(env, policy, a.episodes, a.steps, [0.25, 0, 0],
                                                    curb_field(env, CURB_CM / 100)))

    print("\ncounterfactual: curb course success %, policy NOT retrained")
    print(f"  {'upgrade':24s} " + " ".join(f"{h} cm" for h in (3, 4, 5)))
    for label, groups in (("none", []), ("rear kfe -> 2.94", ["RL_kfe", "RR_kfe"]),
                          ("rear hfe -> 2.94", ["RL_hfe", "RR_hfe"]),
                          ("front kfe -> 2.94", ["FL_kfe", "FR_kfe"])):
        e = upgrade(mk(), groups) if groups else mk()
        res = [curb_run(e, policy, h / 100, a.episodes, a.steps, 0) for h in (3, 4, 5)]
        print(f"  {label:24s} " + "  ".join(f"{u:4.0%}" + (f"/f{fl:.0%}" if fl else "") for u, fl, _ in res))


if __name__ == "__main__":
    main()
