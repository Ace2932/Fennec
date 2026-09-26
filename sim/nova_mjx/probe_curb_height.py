"""How tall a step can a policy get up? A fixed course, not sampled terrain.

⚠ With nova.xml's 5 cm hfield cells the "curb" is a ONE-CELL RAMP, not a vertical
riser: 3 cm = ~31 deg, 4 cm = ~39 deg, 8 cm = ~58 deg (fennec-94 review,
2026-09-25). Heights below are ramp-step heights. A real riser is harder; a true
curb course needs 1-1.5 cm cells (#456/#457).

eval_gait's --terrain/--step-frac scorecard turned out NOT to test this: robots
travel ~1.15 m per episode from a 60 cm flat spawn pad onto sparse terrain, and a
direct measurement of the ground under the feet showed the median episode never
touched raised ground (peak 0.0 cm; max 4.1 cm even at "12 cm steps"). So:

Course: flat, then a full-width step UP of height h whose edge is CURB_X ahead
of spawn (one 5 cm hfield cell of ramp, as the terrain generator makes). Forward
command 0.25 m/s, 400 steps, the training DR (friction, mass, gains, torque
headroom) on, N episodes per height. An episode SUCCEEDS if the base ends past
the curb (x > CURB_X + 0.25 m, i.e. whole body up), not fallen.

  JAX_PLATFORMS=cpu python probe_curb_height.py --policy P.pkl [--asym] [--ref-gait]
"""
import argparse
import functools

import jax
import jax.numpy as jp
import numpy as np
from brax.envs.wrappers.training import DomainRandomizationVmapWrapper

from env import NovaJoystick, make_domain_randomize, goal_acc_rad
from eval_gait import load_policy

CURB_X = 0.40
HEIGHTS_CM = (1, 2, 3, 4, 5, 6, 8)


def curb_field(env, h):
    rx, ry, ztop = (float(v) for v in env._hf_size[:3])
    n = env._hf_ncol
    x = np.linspace(-rx, rx, n)                          # col -> world x
    row = np.where(x >= CURB_X, h, 0.0) / ztop
    return jp.asarray(np.tile(row, (env._hf_nrow, 1)).reshape(-1), jp.float32)


def run(env, policy, h, n, steps, seed):
    dr = make_domain_randomize(0.0)
    field = curb_field(env, h)

    def rand(sys, rng):
        s2, axes = dr(sys, rng)
        return s2.tree_replace({"hfield_data": jp.broadcast_to(field, s2.hfield_data.shape)}), axes

    venv = DomainRandomizationVmapWrapper(
        env, functools.partial(rand, rng=jax.random.split(jax.random.PRNGKey(seed + 1), n)))
    cmd = jp.broadcast_to(jp.array([0.25, 0.0, 0.0]), (n, 3))

    def body(c, k):
        s, alive = c
        a, _ = policy(s.obs, k)
        s = venv.step(s, a)
        s = s.replace(info={**s.info, "cmd": cmd})
        return (s, alive * (1.0 - s.done)), None

    @jax.jit
    def go(key):
        k0, k1 = jax.random.split(key)
        s = venv.reset(jax.random.split(k0, n))
        s = s.replace(info={**s.info, "cmd": cmd})
        (s, alive), _ = jax.lax.scan(body, (s, jp.ones(n)), jax.random.split(k1, steps))
        return alive, s.pipeline_state.x.pos[:, 0]

    alive, base = go(jax.random.PRNGKey(seed))
    alive, base = np.asarray(alive), np.asarray(base)
    up = (base[:, 0] > CURB_X + 0.25) & (base[:, 2] > h + 0.10) & (alive > 0.5)
    return up.mean(), 1 - alive.mean(), np.median(base[:, 0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--asym", action="store_true")
    ap.add_argument("--ref-gait", action="store_true")
    ap.add_argument("--torque-limit", type=float, default=1.0)
    ap.add_argument("--goal-acc-reg", type=int, default=0)
    ap.add_argument("--episodes", type=int, default=32)
    ap.add_argument("--steps", type=int, default=400)
    a = ap.parse_args()
    env = NovaJoystick(asym=a.asym, ref_gait=a.ref_gait, joint_stale_p=0.5,
                       torque_limit=a.torque_limit, goal_acc=goal_acc_rad(a.goal_acc_reg))
    policy = load_policy(a.policy, env, a.asym)
    print(f"1-cell RAMP step (5 cm cells, not a vertical riser) at x={CURB_X} m, fwd 0.25 m/s, "
          f"{a.steps} steps, {a.episodes} DR episodes/height")
    print(f"{'curb cm':>7s} {'up %':>6s} {'fell %':>7s} {'median base x':>14s}")
    for h in HEIGHTS_CM:
        up, fell, mx = run(env, policy, h / 100, a.episodes, a.steps, 0)
        print(f"{h:7d} {up:6.0%} {fell:7.0%} {mx:14.2f}")


if __name__ == "__main__":
    main()
