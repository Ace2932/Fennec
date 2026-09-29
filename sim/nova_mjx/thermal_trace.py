"""Per-joint torque traces for an I^2t / thermal-guard study (#428 research).

Records i = |actuator torque| / NOMINAL stall (haa 2.9, hfe/kfe 1.8 N*m) every
50 Hz step, alive-masked. Motor current ~ torque, so i^2 is the copper-loss
fraction of a locked-rotor stall -- the quantity a thermal guard integrates.
Nominal (not DR-sagged) stall is the right denominator: sag lowers the torque
available, not the current a given torque costs.

  JAX_PLATFORMS=cpu python thermal_trace.py --policy P.pkl --asym --tl 1.0 --out x.npz
"""
import argparse
import functools

import jax
import jax.numpy as jp
import numpy as np
from brax.envs.wrappers.training import DomainRandomizationVmapWrapper

from env import NovaJoystick, make_domain_randomize, goal_acc_rad
from eval_gait import load_policy
from probe_curb_height import curb_field, CURB_X


def trace(env, policy, n, steps, seed, pin_cmd, field=None):
    dr = make_domain_randomize(0.0, flat_frac=0.0)

    def rand(sys, rng):
        s2, axes = dr(sys, rng)
        if field is not None:
            s2 = s2.tree_replace({"hfield_data": jp.broadcast_to(field, s2.hfield_data.shape)})
        return s2, axes

    venv = DomainRandomizationVmapWrapper(
        env, functools.partial(rand, rng=jax.random.split(jax.random.PRNGKey(seed + 1), n)))
    stall = jp.where(jp.arange(12) % 3 == 0, 2.9, 1.8)

    def pin(s):
        if pin_cmd is None:
            return s
        return s.replace(info={**s.info, "cmd": jp.broadcast_to(pin_cmd, (n, 3))})

    def body(c, k):
        s, alive = c
        a, _ = policy(s.obs, k)
        s = pin(venv.step(s, a))
        i = jp.abs(s.pipeline_state.qfrc_actuator[:, 6:]) / stall
        alive = alive * (1.0 - s.done)
        return (s, alive), (i, alive, s.info["tripped"].sum(-1), s.pipeline_state.x.pos[:, 0])

    @jax.jit
    def go(key):
        k0, k1 = jax.random.split(key)
        s = pin(venv.reset(jax.random.split(k0, n)))
        _, out = jax.lax.scan(body, (s, jp.ones(n)), jax.random.split(k1, steps))
        return out

    i, alive, trip, base = (np.asarray(x) for x in go(jax.random.PRNGKey(seed)))
    return i, alive, trip, base   # (T,n,12) (T,n) (T,n) (T,n,3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--asym", action="store_true")
    ap.add_argument("--tl", type=float, default=1.0)
    ap.add_argument("--episodes", type=int, default=64)
    # 450 steps = 9 s: at 0.25 m/s a robot spawned mid-field walks off the 5 m hfield at ~10 s
    ap.add_argument("--flat-steps", type=int, default=450)
    ap.add_argument("--curb-steps", type=int, default=400)
    ap.add_argument("--curb-cm", type=float, default=3.0)
    ap.add_argument("--scenarios", default="fwd,mixed,curb,stand")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    env = NovaJoystick(asym=a.asym, torque_limit=a.tl, goal_acc=goal_acc_rad(0),
                       joint_stale_p=0.5, overload_model=True, goal_slew=3.07)
    policy = load_policy(a.policy, env, a.asym)
    out = {}
    for name, pin, steps, field in (
            ("fwd", jp.array([0.25, 0.0, 0.0]), a.flat_steps, None),
            ("mixed", None, a.flat_steps, None),
            ("curb", jp.array([0.25, 0.0, 0.0]), a.curb_steps,
             curb_field(env, a.curb_cm / 100)),
            ("stand", jp.zeros(3), a.flat_steps, None)):
        if name not in a.scenarios.split(","):
            continue
        i, alive, trip, base = trace(env, policy, a.episodes, steps, 0, pin, field)
        up = (base[-1, :, 0] > CURB_X + 0.25) & (base[-1, :, 2] > a.curb_cm / 100 + 0.10) \
            & (alive[-1] > 0.5)
        out[f"{name}_i"] = i.astype(np.float16)
        out[f"{name}_alive"] = alive.astype(np.uint8)
        out[f"{name}_trip"] = trip.astype(np.uint8)
        print(f"{name}: fell {1 - alive[-1].mean():.1%}  up {up.mean():.0%}  "
              f"mean i^2 kfe {np.mean(i[..., 2::3] ** 2):.3f} hfe {np.mean(i[..., 1::3] ** 2):.3f} "
              f"haa {np.mean(i[..., 0::3] ** 2):.3f}", flush=True)
        out[f"{name}_up"] = up
    np.savez_compressed(a.out, **out)


if __name__ == "__main__":
    main()
