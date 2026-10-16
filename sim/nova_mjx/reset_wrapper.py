"""Training wrapper that really resets episodes (#455).

brax 0.14.2's AutoResetWrapper swaps a done env back to its CACHED first
pipeline_state/obs and never calls env.reset() again, so everything reset()
draws — spawn jitter, command, latency, IMU/joint bias, gait phase — is drawn
once per env per training run, and info (incl. the 3-frame history) carries over
the reset boundary.

This wrapper runs the DR-vmapped env's own reset() with a fresh per-env key and
swaps pipeline_state, obs and every env info field for the done envs. The
reset is computed every step (a select, like MuJoCo Playground) — one extra
pipeline_init. 'steps' and 'truncation' are handled exactly as brax does, so PPO
still bootstraps time-outs.

Use via ppo.train(wrap_env_fn=wrap) — same signature as brax.envs.training.wrap.
"""
import jax
import jax.numpy as jp
from brax.envs.base import Wrapper
from brax.envs.wrappers.training import (DomainRandomizationVmapWrapper,
                                         EpisodeWrapper, VmapWrapper)

_KEEP = ("steps", "truncation", "reset_key")   # never taken from the fresh reset


class FreshResetWrapper(Wrapper):
    def reset(self, rng):
        state = self.env.reset(rng)
        state.info["reset_key"] = jax.vmap(lambda k: jax.random.fold_in(k, 455))(rng)
        return state

    def step(self, state, action):
        if "steps" in state.info:                     # as brax AutoResetWrapper
            steps = jp.where(state.done, jp.zeros_like(state.info["steps"]), state.info["steps"])
            state.info.update(steps=steps)
        state = state.replace(done=jp.zeros_like(state.done))
        state = self.env.step(state, action)

        keys = jax.vmap(jax.random.split)(state.info["reset_key"])      # (n, 2, 2)
        fresh = self.env.reset(keys[:, 0])
        done = state.done

        def sel(new, old):
            d = jp.reshape(done, (done.shape[0],) + (1,) * (old.ndim - 1))
            return jp.where(d > 0.5, new, old)

        info = dict(state.info)
        for k, v in fresh.info.items():
            if k not in _KEEP and k in info:
                info[k] = jax.tree_util.tree_map(sel, v, info[k])
        info["reset_key"] = keys[:, 1]
        return state.replace(
            pipeline_state=jax.tree_util.tree_map(sel, fresh.pipeline_state, state.pipeline_state),
            obs=jax.tree_util.tree_map(sel, fresh.obs, state.obs),
            info=info)


def wrap(env, episode_length=1000, action_repeat=1, randomization_fn=None):
    """brax.envs.training.wrap with FreshResetWrapper in place of AutoResetWrapper."""
    if randomization_fn is None:
        env = VmapWrapper(env)
    else:
        env = DomainRandomizationVmapWrapper(env, randomization_fn)
    env = EpisodeWrapper(env, episode_length, action_repeat)
    return FreshResetWrapper(env)
