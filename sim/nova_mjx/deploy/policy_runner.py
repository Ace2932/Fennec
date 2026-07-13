"""Framework-free NOVA policy runner for the Jetson — numpy only.

Loads the exported nova_policy.npz (weights + normalizer + action scale +
default pose) and runs the deterministic policy. NO jax / torch / onnxruntime
needed on the robot — a 4x128 MLP is a few numpy matmuls at 50 Hz.

CRITICAL: build_obs() reproduces sim's env._get_obs() EXACTLY — same order,
scales, signs. A single mismatch (wrong joint order, a flipped sign, a missing
scale) makes the policy output garbage silently. The obs layout (49-d):
  [ gyro*0.25 (3) | proj_grav (3) | cmd*(2,2,.25) (3) |
    (jpos-default) (12) | jvel*0.05 (12) | last_action (12) | foot_contact (4) ]
`test_policy_runner.py` cross-checks this against the sim env byte-for-byte.
"""
import numpy as np

CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)


class NovaPolicy:
    def __init__(self, npz_path):
        d = np.load(npz_path)
        self.mean = d["mean"].astype(np.float32)
        self.std = d["std"].astype(np.float32)
        self.default_pose = d["default_pose"].astype(np.float32)
        self.action_scale = float(d["action_scale"])
        n = sum(1 for k in d.files if k.startswith("W"))
        self.W = [d[f"W{i}"].astype(np.float32) for i in range(n)]
        self.b = [d[f"b{i}"].astype(np.float32) for i in range(n)]
        self.nu = len(self.default_pose)
        self.reset()

    def reset(self):
        self.last_action = np.zeros(self.nu, np.float32)

    def build_obs(self, gyro, proj_grav, cmd, joint_pos, joint_vel, foot_contact):
        """All inputs in the ROBOT/URDF frame + joint order (haa,hfe,kfe per leg,
        FL FR RL RR). gyro rad/s (body), proj_grav unit down-in-body, cmd
        (vx,vy,wz), joint_pos/vel rad & rad/s, foot_contact 4x {0,1}."""
        return np.concatenate([
            np.asarray(gyro, np.float32) * 0.25,
            np.asarray(proj_grav, np.float32),
            np.asarray(cmd, np.float32) * CMD_SCALE,
            np.asarray(joint_pos, np.float32) - self.default_pose,
            np.asarray(joint_vel, np.float32) * 0.05,
            self.last_action,
            np.asarray(foot_contact, np.float32),
        ]).astype(np.float32)

    def infer(self, obs):
        """obs (49,) -> action (12) in [-1,1]. Stores it as last_action."""
        x = (obs - self.mean) / self.std
        for i in range(len(self.W) - 1):
            x = x @ self.W[i] + self.b[i]
            x = x * (1.0 / (1.0 + np.exp(-x)))          # silu
        x = x @ self.W[-1] + self.b[-1]
        a = np.tanh(x[:self.nu]).astype(np.float32)
        self.last_action = a
        return a

    def joint_targets(self, gyro, proj_grav, cmd, joint_pos, joint_vel, foot_contact):
        """One 50 Hz step: sensors -> 12 joint POSITION targets (rad)."""
        obs = self.build_obs(gyro, proj_grav, cmd, joint_pos, joint_vel, foot_contact)
        a = self.infer(obs)
        return self.default_pose + a * self.action_scale
