"""policy_runner's observation contract, from its new home (#289).

Ports sim/nova_mjx/deploy/test_policy_contract.py's checks so the same
enforcement is covered from inside the ros-pytest CI job (which runs
ros2_ws/src/*/test, not sim/nova_mjx) rather than only from a sim-only
invocation nothing here runs automatically. sim/nova_mjx/deploy's own copy of
this test still exists and still passes (repointed at this file's new
location) -- see that module for the byte-for-byte cross-check against the
real Brax env, which needs jax/brax and so stays there.

Pure numpy, no rclpy, no jax/brax -- runs everywhere.
"""
import os
import tempfile

import numpy as np

from nova_locomotion.policy_runner import HIST, PROP, NovaPolicy

OBS = HIST * PROP + 3 + 12  # 105


def _npz(path, obs_dim=OBS, nu=12, meta=True, cmd_scale=(2.0, 2.0, 0.25)):
    b = {
        "mean": np.zeros(obs_dim, np.float32), "std": np.ones(obs_dim, np.float32),
        "action_scale": np.float32(0.4), "default_pose": np.zeros(nu, np.float32),
        "W0": np.zeros((obs_dim, 128), np.float32), "b0": np.zeros(128, np.float32),
        "W1": np.zeros((128, 2 * nu), np.float32), "b1": np.zeros(2 * nu, np.float32),
    }
    if meta:
        b.update({
            "obs_dim": np.int64(obs_dim), "act_dim": np.int64(nu),
            "hist": np.int64(HIST), "prop": np.int64(PROP),
            "cmd_scale": np.asarray(cmd_scale, np.float32),
            "sha": np.str_("test"), "created": np.str_("now"), "label": np.str_("unit"),
        })
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
        NovaPolicy(_npz(_tmp("cs.npz"), cmd_scale=(1.0, 1.0, 1.0)))
        assert False, "wrong cmd_scale loaded silently"
    except ValueError as e:
        assert "cmd_scale mismatch" in str(e)


def test_legacy_npz_without_metadata_loads():
    # weight files exported before the contract keys existed still load
    # (fallback to the runner constants) and still get shape-checked.
    p = NovaPolicy(_npz(_tmp("legacy.npz"), meta=False))
    assert p.hist == HIST and p.prop == PROP
    o = p.build_obs(
        np.zeros(3), np.array([0.0, 0.0, -1.0]),
        np.array([0.25, 0.0, 0.0]), np.zeros(12), np.zeros(12),
    )
    assert o.shape[0] == OBS


def test_build_obs_shape_and_history_order():
    """Sanity on the assembly itself (not just the contract check): 105-d,
    and pushing a new frame shifts history newest-first."""
    p = NovaPolicy(_npz(_tmp("hist.npz")))
    o1 = p.build_obs(np.ones(3), np.array([0.0, 0.0, -1.0]), np.zeros(3), np.zeros(12), np.zeros(12))
    assert o1.shape == (OBS,)
    o2 = p.build_obs(np.full(3, 2.0), np.array([0.0, 0.0, -1.0]), np.zeros(3), np.zeros(12), np.zeros(12))
    # newest frame (gyro*0.25 in the first PROP slots) reflects the latest call
    assert np.allclose(o2[:3], np.full(3, 2.0) * 0.25)
    # the previous newest frame slid into the second history slot
    assert np.allclose(o2[PROP:PROP + 3], np.ones(3) * 0.25)
