"""Locks the MEASURED teacher(234) -> blind(105) obs mapping distill.py depends
on (#304). This is the guard that stops a silent wrong slice: a student trained
on the wrong 105 dims trains and exports FINE and is garbage on hardware, and
nothing downstream would catch it (the shapes all still line up).

Method (same one used to derive `distill.extract_blind_obs` in the first
place, see its docstring): reset `NovaJoystick(heightmap=False)` and
`NovaJoystick(heightmap=True)` from the SAME PRNGKey, step both with IDENTICAL
actions, and diff. Multiple seeds x multiple steps, not a single sample (n>1).

  JAX_PLATFORMS=cpu python test_distill_obs_map.py
"""
import jax
import jax.numpy as jp
import numpy as np

from distill import BLIND_OBS_DIM, extract_blind_obs
from env import NovaJoystick

SEEDS = 5
STEPS = 10


def _blind_and_teacher_obs():
    """Roll both envs from shared seeds/actions; return matched (blind, teacher)
    obs pairs from reset + every step, across SEEDS seeds x STEPS steps."""
    env_b = NovaJoystick(heightmap=False)
    env_t = NovaJoystick(heightmap=True)
    jr_b, js_b = jax.jit(env_b.reset), jax.jit(env_b.step)
    jr_t, js_t = jax.jit(env_t.reset), jax.jit(env_t.step)

    pairs = []
    for seed in range(SEEDS):
        rng = jax.random.PRNGKey(seed)
        sb, st = jr_b(rng), jr_t(rng)
        pairs.append((np.asarray(sb.obs), np.asarray(st.obs)))
        act_rng = jax.random.PRNGKey(seed * 7 + 1)
        for _ in range(STEPS):
            act_rng, k = jax.random.split(act_rng)
            act = jax.random.uniform(k, (env_b.action_size,), minval=-1.0, maxval=1.0)
            sb, st = js_b(sb, act), js_t(st, act)
            pairs.append((np.asarray(sb.obs), np.asarray(st.obs)))
    return pairs


def test_blind_obs_dim_is_105():
    assert BLIND_OBS_DIM == 105


def test_extract_blind_obs_matches_blind_env_exactly():
    """POSITIVE: extract_blind_obs(teacher_obs) must equal the real blind-env
    obs bit-exactly (not approximately) across every seed/step sampled."""
    pairs = _blind_and_teacher_obs()
    assert len(pairs) == SEEDS * (STEPS + 1)
    max_diff = 0.0
    for blind_obs, teacher_obs in pairs:
        assert teacher_obs.shape == (234,)
        assert blind_obs.shape == (105,)
        got = extract_blind_obs(teacher_obs)
        assert got.shape == (105,)
        max_diff = max(max_diff, float(np.max(np.abs(got - blind_obs))))
    assert max_diff == 0.0, f"extractor drifted from the blind env by {max_diff}"


def test_extractor_is_a_contiguous_prefix_not_interleaved():
    """The mapping distill.py relies on is teacher_obs[:105], NOT some
    interleaved subset (e.g. cmd_c/clock dims spliced in early). Confirm the
    slice bounds directly."""
    import inspect
    src = inspect.getsource(extract_blind_obs)
    assert ":BLIND_OBS_DIM" in src or ":105" in src


def test_negative_control_wrong_slice_is_detected():
    """NEGATIVE CONTROL: a plausible WRONG mapping (off-by-8, as if cmd_c +
    the 3 gait-clock dims were interleaved before the blind prefix instead of
    appended after it) must NOT match the real blind obs. If this assertion
    ever fails to fire, the positive test above is not actually discriminating
    between mappings — it would pass on any 105-length slice."""
    pairs = _blind_and_teacher_obs()
    blind_obs, teacher_obs = pairs[0]
    wrong = teacher_obs[8:113]                      # plausible wrong offset
    diff = float(np.max(np.abs(wrong - blind_obs)))
    assert diff > 0.0, (
        "wrong-slice negative control did not fire (diff==0) — this test can "
        "no longer distinguish a correct mapping from an incorrect one")


if __name__ == "__main__":
    test_blind_obs_dim_is_105()
    test_extract_blind_obs_matches_blind_env_exactly()
    test_extractor_is_a_contiguous_prefix_not_interleaved()
    test_negative_control_wrong_slice_is_detected()
    print("ALL OBS-MAPPING CHECKS PASSED")
