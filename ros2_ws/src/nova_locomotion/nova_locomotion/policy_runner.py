"""Framework-free NOVA policy runner for the Jetson — numpy only.

Loads the exported nova_policy.npz (weights + normalizer + action scale +
default pose) and runs the deterministic policy. NO jax / torch / onnxruntime
needed on the robot — the MLP is a few numpy matmuls at 50 Hz.

CRITICAL: build_obs() reproduces sim's obs EXACTLY — same layout, scales, order,
and the SAME proprioceptive HISTORY. A single mismatch (wrong joint order, a
flipped sign, a missing scale, wrong history order) makes the policy output
garbage silently. The obs is HIST stacked frames + command + last action:
  frame (30) = [ gyro*0.25 (3) | proj_grav (3) | (jpos-default) (12) | jvel*0.05 (12) ]
  obs (105)  = [ frame_t, frame_{t-1}, frame_{t-2} | cmd*(2,2,.25) (3) | last_action (12) ]
NO foot-contact input — NOVA has no foot sensors; the policy infers contact from
the joint-velocity history. `test_policy_runner.py` cross-checks this vs the sim.
"""
import numpy as np

CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
HIST = 3
PROP = 30


class NovaPolicy:
    def __init__(self, npz_path):
        d = np.load(npz_path, allow_pickle=False)
        self.mean = d["mean"].astype(np.float32)
        self.std = d["std"].astype(np.float32)
        self.default_pose = d["default_pose"].astype(np.float32)
        self.action_scale = float(d["action_scale"])
        n = sum(1 for k in d.files if k.startswith("W"))
        self.W = [d[f"W{i}"].astype(np.float32) for i in range(n)]
        self.b = [d[f"b{i}"].astype(np.float32) for i in range(n)]
        self.nu = len(self.default_pose)

        # --- VALIDATE THE OBSERVATION CONTRACT (fail LOUD, not on the robot) ---
        # A weight file trained with a different obs layout (different HIST/PROP,
        # a phase clock, a changed cmd scale) must be REJECTED at load, not run.
        # On hardware a silent mismatch drives 12 servos with garbage. Newer .npz
        # files carry the contract (export_policy); older ones don't -> fall back
        # to the runner's own constants with a warning, but still check shapes.
        self.hist = int(d["hist"]) if "hist" in d.files else HIST
        self.prop = int(d["prop"]) if "prop" in d.files else PROP
        self.cmd_scale = (d["cmd_scale"].astype(np.float32)
                          if "cmd_scale" in d.files else CMD_SCALE)
        self.meta = {k: (d[k].item() if d[k].ndim == 0 else d[k].tolist())
                     for k in ("obs_dim", "act_dim", "sha", "created", "label")
                     if k in d.files}
        expected_obs = self.hist * self.prop + 3 + self.nu
        weights_obs = int(self.mean.shape[0])
        if weights_obs != expected_obs:
            raise ValueError(
                f"policy obs mismatch: weights expect {weights_obs}-dim obs but "
                f"this runner builds {expected_obs} "
                f"(hist {self.hist} * prop {self.prop} + 3 cmd + {self.nu} act). "
                f"The policy was trained with a DIFFERENT observation layout — "
                f"do NOT deploy. If you added a phase clock or changed HIST/PROP, "
                f"update policy_runner to match before exporting. "
                f"meta={self.meta}")
        if "cmd_scale" in d.files and not np.allclose(self.cmd_scale, CMD_SCALE):
            raise ValueError(
                f"cmd_scale mismatch: weights {self.cmd_scale.tolist()} vs runner "
                f"{CMD_SCALE.tolist()} — the command was scaled differently in "
                f"training; /cmd_vel would be mis-fed. Sync CMD_SCALE. meta={self.meta}")
        self.reset()

    def reset(self):
        self.last_action = np.zeros(self.nu, np.float32)
        self.prop_hist = None            # filled (tiled) on the first frame

    def _frame(self, gyro, proj_grav, joint_pos, joint_vel):
        """One proprioceptive frame (30). Inputs in the ROBOT/URDF frame + joint
        order (haa,hfe,kfe per leg, FL FR RL RR). `gyro` = the raw IMU reading
        (rad/s, body) — its bias is already baked in, don't add any."""
        return np.concatenate([
            np.asarray(gyro, np.float32) * 0.25,
            np.asarray(proj_grav, np.float32),
            np.asarray(joint_pos, np.float32) - self.default_pose,
            np.asarray(joint_vel, np.float32) * 0.05,
        ]).astype(np.float32)

    def build_obs(self, gyro, proj_grav, cmd, joint_pos, joint_vel):
        f = self._frame(gyro, proj_grav, joint_pos, joint_vel)
        if self.prop_hist is None:
            self.prop_hist = np.tile(f, (self.hist, 1))
        else:                            # push newest first (matches sim)
            self.prop_hist = np.concatenate([f[None], self.prop_hist[:-1]], axis=0)
        return np.concatenate([
            self.prop_hist.reshape(-1),
            np.asarray(cmd, np.float32) * self.cmd_scale,   # from the artifact
            self.last_action,
        ]).astype(np.float32)

    def infer(self, obs):
        """obs (105,) -> action (12) in [-1,1]. Stores it as last_action."""
        x = (obs - self.mean) / self.std
        for i in range(len(self.W) - 1):
            x = x @ self.W[i] + self.b[i]
            x = x * (1.0 / (1.0 + np.exp(-x)))          # silu
        x = x @ self.W[-1] + self.b[-1]
        a = np.tanh(x[:self.nu]).astype(np.float32)
        self.last_action = a
        return a

    def joint_targets(self, gyro, proj_grav, cmd, joint_pos, joint_vel):
        """One 50 Hz step: sensors -> 12 joint POSITION targets (rad)."""
        obs = self.build_obs(gyro, proj_grav, cmd, joint_pos, joint_vel)
        a = self.infer(obs)
        return self.default_pose + a * self.action_scale
