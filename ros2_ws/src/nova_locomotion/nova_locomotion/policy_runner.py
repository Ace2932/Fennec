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
# The command box the policy TRAINED on (sim env.py stage-2 _cmd_lo/_cmd_hi,
# which stay inside the measured 2.8 rad/s actuator envelope). A /cmd_vel outside
# it is extrapolation the policy has never seen, so it is clipped here, where
# every caller's command enters the observation.
CMD_LO = np.array([-0.15, -0.15, -0.5], dtype=np.float32)
CMD_HI = np.array([0.35, 0.15, 0.5], dtype=np.float32)
HIST = 3
PROP = 30
DT = 0.02                                   # 50 Hz control, as in sim


class NovaPolicy:
    def __init__(self, npz_path, dt=DT):
        d = np.load(npz_path, allow_pickle=False)
        self.mean = d["mean"].astype(np.float32)
        self.std = d["std"].astype(np.float32)
        self.default_pose = d["default_pose"].astype(np.float32)
        self.action_scale = float(d["action_scale"])
        n = sum(1 for k in d.files if k.startswith("W"))
        self.W = [d[f"W{i}"].astype(np.float32) for i in range(n)]
        self.b = [d[f"b{i}"].astype(np.float32) for i in range(n)]
        self.nu = len(self.default_pose)
        self.dt = float(dt)          # control period: advances the reference phase clock

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
        # IK SWING REFERENCE (optional, sim gait-study ref_gait): the artifact then
        # carries the lift table + clock, the runner keeps the phase, appends
        # [sin, cos](2 pi phase) to the obs and adds the reference to the targets.
        self.ref = None
        if "ref_table" in d.files:
            self.ref = {k: d[k].astype(np.float32) for k in
                        ("ref_table", "gait_offsets")}
            self.ref.update({k: float(d[k]) for k in
                             ("ref_height", "ref_dz_max", "ref_freq", "gait_duty")})
        expected_obs = self.hist * self.prop + 3 + self.nu + (2 if self.ref else 0)
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
        self.phase = 0.0                 # reference clock, [0, 1)

    def ref_offset(self, phase):
        """(12,) joint offsets of the IK swing reference at `phase` — the numpy
        twin of sim env._ref_offset (trot schedule, lift h*sin(pi*swing_frac),
        lift -> (hfe, kfe) by linear interpolation in the exported table)."""
        r = self.ref
        ph = np.mod(phase + r["gait_offsets"], 1.0)
        sf = np.clip((ph - r["gait_duty"]) / (1.0 - r["gait_duty"]), 0.0, 1.0)
        lift = r["ref_height"] * np.sin(np.pi * sf)
        n = len(r["ref_table"])
        u = np.clip(lift / r["ref_dz_max"], 0.0, 1.0) * (n - 1)
        i0 = np.clip(np.floor(u).astype(int), 0, n - 2)
        f = (u - i0)[:, None]
        hk = r["ref_table"][i0] * (1.0 - f) + r["ref_table"][i0 + 1] * f
        return np.concatenate([np.zeros((4, 1)), hk], axis=1).reshape(-1).astype(np.float32)

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
            np.clip(np.asarray(cmd, np.float32), CMD_LO, CMD_HI) * self.cmd_scale,
            self.last_action,
        ] + ([np.array([np.sin(2 * np.pi * self.phase),
                        np.cos(2 * np.pi * self.phase)], np.float32)]
             if self.ref else [])).astype(np.float32)

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
        q = self.default_pose + a * self.action_scale
        if self.ref:
            q = q + self.ref_offset(self.phase)
            self.phase = (self.phase + self.ref["ref_freq"] * self.dt) % 1.0
        return q
