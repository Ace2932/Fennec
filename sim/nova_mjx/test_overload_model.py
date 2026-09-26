"""Servo overload unload model (env overload_model): a joint held above 80 % duty
must trip at ~2.0 s and then deliver <= 20 % of stall; with the model OFF the
same hold keeps full force (the tripped flag is still tracked as a
"would have tripped" diagnostic).

  JAX_PLATFORMS=cpu python test_overload_model.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick, OVERLOAD_OUT

KNEE = 2                        # FL kfe actuator index; dof index 6 + 2


def hold(overload):
    env = NovaJoystick(push_mag=0.0, overload_model=overload)
    step = jax.jit(env.step)
    s = jax.jit(env.reset)(jax.random.PRNGKey(0))
    s = s.replace(info={**s.info, "delay": jp.asarray(0, s.info["delay"].dtype)})
    a = np.zeros(12, np.float32)
    a[KNEE] = -3.0              # goal 1.2 rad past the stand -> saturates against the load
    out = []
    for i in range(150):        # 3 s
        s = step(s, jp.asarray(a))
        out.append((0.02 * (i + 1), bool(s.info["tripped"][KNEE]),
                    abs(float(s.pipeline_state.qfrc_actuator[6 + KNEE]))))
    return env, out


def main():
    env, on = hold(True)
    stall = float(env.sys.actuator_forcerange[KNEE, 1])   # no DR, TL 1.0 -> the stall
    first = next((t for t, tr, _ in on if tr), None)
    assert first is not None, "held at stall for 3 s and never tripped"
    assert 1.9 <= first <= 2.3, f"tripped at {first:.2f} s, want ~2.0 s"
    after = max(f for t, tr, f in on if t > first + 0.1)
    assert after <= OVERLOAD_OUT * stall + 1e-3, f"post-trip force {after:.2f} > 20 % of {stall:.2f}"
    print(f"ok  tripped at {first:.2f} s; post-trip |tau| <= {after:.2f} N*m (20 % of {stall:.2f})")

    _, off = hold(False)
    # the flag is still tracked with the model off (a "would have tripped"
    # diagnostic for eval), but the physics must NOT be cut
    assert any(tr for _, tr, _ in off), "diagnostic flag not tracked with model off"
    late = np.mean([f for t, _, f in off if t > 2.2])
    assert late > 0.8 * stall, f"model OFF force {late:.2f} not near stall"
    print(f"ok  model off: flag tracked (would-trip), force still {late:.2f} N*m after 2.2 s")
    # TL 0.8 caps duty at 0.8, so the (> 80 %) unload can NEVER fire -- under DR too.
    # Was violated by float rounding: 3 of 16 DR robots latched at a held stall.
    import functools
    from brax.envs.wrappers.training import DomainRandomizationVmapWrapper
    from env import make_domain_randomize
    env8 = NovaJoystick(push_mag=0.0, overload_model=True, torque_limit=0.8)
    n = 16
    venv = DomainRandomizationVmapWrapper(env8, functools.partial(
        make_domain_randomize(0.0), rng=jax.random.split(jax.random.PRNGKey(3), n)))
    s8 = jax.jit(venv.reset)(jax.random.split(jax.random.PRNGKey(0), n))
    st8 = jax.jit(venv.step)
    a8 = np.zeros((n, 12), np.float32)
    a8[:, KNEE] = -3.0
    for _ in range(150):
        s8 = st8(s8, jp.asarray(a8))
    n_trip = int(np.asarray(s8.info["tripped"][:, KNEE]).sum())
    assert n_trip == 0, f"{n_trip}/{n} DR robots unloaded at TL 0.8 (duty can't exceed 0.8)"
    print("ok  TL 0.8 + DR: held stall never unloads (0/16)")
    print("ALL OVERLOAD MODEL CHECKS PASSED")


if __name__ == "__main__":
    main()
