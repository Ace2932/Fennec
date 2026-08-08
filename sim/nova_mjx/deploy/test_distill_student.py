"""Distilled blind-student artifact (#304) must actually LOAD through the real
Jetson consumer, `nova_locomotion.policy_runner.NovaPolicy`, and produce a
finite 12-d action for a 105-d obs — the same contract every other exported
policy is held to (see `deploy/test_policy_runner.py`).

Only needs numpy (no jax) — same spirit as `test_policy_runner.py`'s untrained
export, but here against a REAL distilled artifact if one has been produced by
`distill.py` (skips cleanly if not — this repo does not commit the .npz).

  python deploy/test_distill_student.py
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../../ros2_ws/src/nova_locomotion/nova_locomotion")))

HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = sorted(glob.glob(os.path.join(
    HERE, "..", "artifacts", "policies", "nova_student_blind*.npz")))


def _find_student_npz():
    return _CANDIDATES[0] if _CANDIDATES else None


def test_student_npz_loads_and_infers():
    npz = _find_student_npz()
    if npz is None:
        print("SKIP  no nova_student_blind*.npz artifact present "
              "(run distill.py first; artifacts are gitignored)")
        return
    from policy_runner import NovaPolicy

    pol = NovaPolicy(npz)
    assert pol.mean.shape == (105,), pol.mean.shape
    assert pol.default_pose.shape == (12,), pol.default_pose.shape

    rng = np.random.default_rng(0)
    obs = rng.normal(size=(105,)).astype(np.float32)
    action = pol.infer(obs)
    assert action.shape == (12,), action.shape
    assert np.all(np.isfinite(action)), "student policy produced a non-finite action"
    assert np.all(np.abs(action) <= 1.0 + 1e-6), "action outside tanh range [-1,1]"

    tgt = pol.joint_targets(
        gyro=np.zeros(3), proj_grav=np.array([0., 0., -1.], np.float32),
        cmd=np.array([0.5, 0.0, 0.0], np.float32),
        joint_pos=pol.default_pose, joint_vel=np.zeros(12, np.float32))
    assert tgt.shape == (12,)
    assert np.all(np.isfinite(tgt))
    print(f"OK  {os.path.basename(npz)} loads through NovaPolicy, "
          f"infer() -> finite (12,) action, joint_targets() -> finite (12,) targets")


if __name__ == "__main__":
    test_student_npz_loads_and_infers()
