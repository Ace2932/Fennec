"""#455: an episode boundary must redraw reset()'s per-episode draws.

Episode length 4, 8 envs, zero action. After the 4th step every env is done
(truncation). With the stock brax AutoResetWrapper, gyro_bias / delay / cmd are
unchanged (the bug); with reset_wrapper.wrap they are redrawn, prop_hist is the
fresh reset's, and 'truncation' still reads 1 on that step (PPO bootstrapping).

  JAX_PLATFORMS=cpu python test_reset_wrapper.py
"""
import functools

import jax
import jax.numpy as jp
import numpy as np
from brax.envs import training as brax_training

from env import NovaJoystick, make_domain_randomize
import reset_wrapper

N, L = 8, 4


def run(wrap_fn):
    env = NovaJoystick()
    dr = functools.partial(make_domain_randomize(0.0), rng=jax.random.split(jax.random.PRNGKey(1), N))
    w = wrap_fn(env, episode_length=L, action_repeat=1, randomization_fn=dr)
    s = jax.jit(w.reset)(jax.random.split(jax.random.PRNGKey(0), N))
    first = jax.tree_util.tree_map(np.asarray, s.info)
    step = jax.jit(w.step)
    for _ in range(L):
        s = step(s, jp.zeros((N, env.action_size)))
    return first, jax.tree_util.tree_map(np.asarray, s.info), np.asarray(s.done)


def main():
    f0, i0, d0 = run(brax_training.wrap)
    assert d0.all()
    assert np.array_equal(f0["gyro_bias"], i0["gyro_bias"]), "stock wrapper changed bias?"
    print("ok  stock brax AutoResetWrapper: gyro_bias NOT redrawn at the boundary (the #455 bug)")

    f1, i1, d1 = run(reset_wrapper.wrap)
    assert d1.all()
    for k in ("gyro_bias", "joint_bias", "cmd"):
        assert not np.allclose(f1[k], i1[k]), f"{k} not redrawn"
    assert (i1["delay"] != f1["delay"]).any(), "delay never redrawn across 8 envs"
    assert np.all(i1["truncation"] == 1), "truncation lost — PPO would stop bootstrapping time-outs"
    assert np.all(i1["step"] == 0), "env step counter not reset"
    print("ok  reset_wrapper: bias/cmd/delay redrawn, env step counter 0, truncation preserved")
    print("ALL RESET WRAPPER CHECKS PASSED")


if __name__ == "__main__":
    main()
