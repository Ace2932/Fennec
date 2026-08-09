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

# Both bounds are MEASURED, and the gap between them is the whole point (#315).
#
#   correct slice, macOS arm64 : 0.0          (exact)
#   correct slice, linux x86   : 5.96e-08     (2**-24, one float32 ULP)
#   WRONG slice (off-by-8)     : 0.854 .. 1.771   over the same 55 samples
#
# So real signal and float noise are ~7 ORDERS OF MAGNITUDE apart. 1e-6 sits
# ~17x above the observed noise and ~850,000x below the smallest real error --
# there is no tuning risk here, and no bound in between that would behave
# differently.
FLOAT_NOISE_TOL = 1e-6
# The negative control has to clear the tolerance by a wide margin, or
# loosening the positive test guts it. 1e-3 is 1000x FLOAT_NOISE_TOL and still
# 850x below the smallest measured wrong-slice error.
WRONG_SLICE_FLOOR = 1e-3


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


def test_extract_blind_obs_matches_blind_env():
    """POSITIVE: extract_blind_obs(teacher_obs) must equal the real blind-env
    obs across every seed/step sampled, to within float32 rounding.

    THIS ASSERTED `== 0.0` UNTIL #315 RAN IT ON LINUX. It passes bit-exactly on
    an M-series Mac and fails on a GitHub x86 runner by 5.960464477539063e-08 —
    which is 2**-24, one ULP of float32, in one element.

    Bit-exactness was never guaranteed by construction, and reading the method
    above shows why: this steps TWO INDEPENDENT env instances (heightmap=False
    and heightmap=True) and diffs them. `extract_blind_obs` itself is a pure
    slice and contributes no arithmetic, but the two envs assemble their
    observations in separately-jitted graphs, and XLA is free to fuse them
    differently on different targets. Equal-to-the-last-bit across
    architectures was an accident of the Mac, not a property of the code.
    """
    pairs = _blind_and_teacher_obs()
    assert len(pairs) == SEEDS * (STEPS + 1)
    max_diff = 0.0
    for blind_obs, teacher_obs in pairs:
        assert teacher_obs.shape == (234,)
        assert blind_obs.shape == (105,)
        got = extract_blind_obs(teacher_obs)
        assert got.shape == (105,)
        max_diff = max(max_diff, float(np.max(np.abs(got - blind_obs))))
    assert max_diff <= FLOAT_NOISE_TOL, (
        f"extractor drifted from the blind env by {max_diff}, above the "
        f"{FLOAT_NOISE_TOL} float32-rounding tolerance — at that size this is "
        f"a real mapping error, not fusion noise (a wrong slice measures "
        f"~1e0, see test_negative_control_wrong_slice_is_detected)")


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
    # `> 0.0` UNTIL #315. That was fine only while the positive test demanded
    # exact equality; the moment that became a tolerance, `> 0.0` stopped
    # discriminating, because on x86 a CORRECT slice also differs by ~6e-08.
    # The two assertions are one mechanism and have to move together — relaxing
    # the positive test alone would have left this passing on noise while
    # proving nothing. Bound it well ABOVE the tolerance instead.
    assert diff > WRONG_SLICE_FLOOR, (
        f"wrong-slice negative control did not fire (diff={diff}, needs "
        f"> {WRONG_SLICE_FLOOR}) — this test can no longer distinguish a "
        f"correct mapping from an incorrect one")


if __name__ == "__main__":
    test_blind_obs_dim_is_105()
    test_extract_blind_obs_matches_blind_env()
    test_extractor_is_a_contiguous_prefix_not_interleaved()
    test_negative_control_wrong_slice_is_detected()
    print("ALL OBS-MAPPING CHECKS PASSED")
