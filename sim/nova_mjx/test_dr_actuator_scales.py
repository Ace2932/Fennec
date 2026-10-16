"""DR must keep --kp-scale and --eff-scale (the absolute kp draw discarded kp_scale)."""
import jax
import numpy as np

from env import NovaJoystick, make_domain_randomize

LEG = np.array([a for a in range(12) if a % 3 != 0])   # hfe + kfe
HAA = np.array([0, 3, 6, 9])


def _dr_sys(**kw):
    env = NovaJoystick(**kw)
    dr = make_domain_randomize(0.0, step_frac=0.0, flat_frac=0.0)
    sys_b, _ = dr(env.sys, jax.random.split(jax.random.PRNGKey(0), 256))
    return np.asarray(sys_b.actuator_gainprm[:, :, 0]), np.asarray(sys_b.actuator_forcerange[:, :, 1])


def test_kp_scale_survives_dr():
    kp1, _ = _dr_sys()
    kp5, _ = _dr_sys(kp_scale=0.5)
    np.testing.assert_allclose(kp5[:, LEG].mean() / kp1[:, LEG].mean(), 0.5, rtol=0.05)
    np.testing.assert_allclose(kp5[:, HAA].mean() / kp1[:, HAA].mean(), 1.0, rtol=0.05)   # hips untouched


def test_eff_scale_survives_dr():
    _, fr1 = _dr_sys()
    _, fr2 = _dr_sys(eff_scale=2.72)
    np.testing.assert_allclose(fr2[:, LEG].mean() / fr1[:, LEG].mean(), 2.72, rtol=0.05)
