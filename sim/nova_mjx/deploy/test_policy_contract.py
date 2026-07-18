"""The policy runner must REFUSE weights whose observation contract it can't
meet — on hardware a silent mismatch drives 12 servos with garbage. Numpy-only
(no jax/brax), so it runs anywhere and fast.

  python -m pytest deploy/test_policy_contract.py -q
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from policy_runner import NovaPolicy, HIST, PROP   # noqa: E402

OBS = HIST * PROP + 3 + 12   # 105


def _npz(path, obs_dim=OBS, nu=12, meta=True, cmd_scale=(2., 2., .25),
         phase_clock=0, phase_freq=0.0):
    b = {"mean": np.zeros(obs_dim, np.float32), "std": np.ones(obs_dim, np.float32),
         "action_scale": np.float32(0.4), "default_pose": np.zeros(nu, np.float32),
         "W0": np.zeros((obs_dim, 128), np.float32), "b0": np.zeros(128, np.float32),
         "W1": np.zeros((128, 2 * nu), np.float32), "b1": np.zeros(2 * nu, np.float32)}
    if meta:
        b.update({"obs_dim": np.int64(obs_dim), "act_dim": np.int64(nu),
                  "hist": np.int64(HIST), "prop": np.int64(PROP),
                  "cmd_scale": np.asarray(cmd_scale, np.float32),
                  "phase_clock": np.int64(phase_clock),
                  "phase_freq": np.float32(phase_freq),
                  "sha": np.str_("test"), "created": np.str_("now"),
                  "label": np.str_("unit")})
    np.savez(path, **b)
    return path


def _tmp(name):
    return os.path.join(tempfile.mkdtemp(), name)


def test_correct_obs_loads():
    p = NovaPolicy(_npz(_tmp("good.npz")))
    assert p.mean.shape[0] == OBS
    assert p.meta["label"] == "unit"


def test_wrong_obs_dim_rejected():
    # a phase-clock policy (+2 obs) must not silently run on a 105-dim runner
    try:
        NovaPolicy(_npz(_tmp("bad.npz"), obs_dim=OBS + 2))
        assert False, "wrong obs dim loaded silently"
    except ValueError as e:
        assert "obs mismatch" in str(e)


def test_wrong_cmd_scale_rejected():
    try:
        NovaPolicy(_npz(_tmp("cs.npz"), cmd_scale=(1., 1., 1.)))
        assert False, "wrong cmd_scale loaded silently"
    except ValueError as e:
        assert "cmd_scale mismatch" in str(e)


def test_phase_clock_policy_obs_and_advance():
    # a phase-clock policy has obs +2 and the runner must advance the clock +
    # append sin/cos as the LAST 2 dims.
    p = NovaPolicy(_npz(_tmp("phase.npz"), obs_dim=OBS + 2, phase_clock=1, phase_freq=2.0))
    assert p.phase_clock and p.phase_freq == 2.0
    o0 = p.build_obs(np.zeros(3), np.array([0., 0., -1.]),
                     np.array([0.25, 0., 0.]), np.zeros(12), np.zeros(12))
    assert o0.shape[0] == OBS + 2
    # first frame uses phase 0 -> [sin0, cos0] = [0, 1]
    assert abs(o0[-2] - 0.0) < 1e-6 and abs(o0[-1] - 1.0) < 1e-6
    # phase advanced by freq*control_dt = 2.0 * 0.02 = 0.04
    assert abs(p.phase - 0.04) < 1e-6


def test_phase_policy_into_nonphase_runner_math():
    # a 107-dim phase policy WITHOUT phase metadata (or mislabeled) must be
    # rejected by the shape check, not silently run as 105+2 garbage.
    try:
        NovaPolicy(_npz(_tmp("mislabel.npz"), obs_dim=OBS + 2, phase_clock=0))
        assert False, "107-dim non-phase policy loaded silently"
    except ValueError as e:
        assert "obs mismatch" in str(e)


def test_legacy_npz_without_metadata_loads():
    # weight files exported before the contract keys existed still load (fallback
    # to the runner constants) and still get shape-checked.
    p = NovaPolicy(_npz(_tmp("legacy.npz"), meta=False))
    assert p.hist == HIST and p.prop == PROP
    o = p.build_obs(np.zeros(3), np.array([0., 0., -1.]),
                    np.array([0.25, 0., 0.]), np.zeros(12), np.zeros(12))
    assert o.shape[0] == OBS


if __name__ == "__main__":
    for fn in [test_correct_obs_loads, test_wrong_obs_dim_rejected,
               test_wrong_cmd_scale_rejected, test_legacy_npz_without_metadata_loads]:
        fn()
        print(f"OK  {fn.__name__}")
    print("ALL CONTRACT CHECKS PASSED")
