"""NOVA MJX joystick locomotion env — velocity-command quadruped walking.

MJX (GPU-parallel MuJoCo) + Brax PipelineEnv, structured like the official MJX
Barkour tutorial so it trains on a free Colab GPU.

Robustness (so the trained policy holds up to real-world failures — a stumble,
a slip, a shove, sensor noise, an off-nominal build):
  * observation noise on every sensor group (real IMU/encoders are noisy),
  * randomized start velocity + joint pose (recover from perturbed states),
  * mid-episode random PUSHES (velocity kicks) — trains fall recovery,
  * a feet-air-time reward for a real stepping gait (not a shuffle/drag),
  * wide domain randomization (`domain_randomize`): friction, per-link mass,
    joint gains. Also lets you train before the final masses are measured.
"""
import jax
import jax.numpy as jp
import mujoco
from brax import math
from brax.envs.base import PipelineEnv, State
from brax.io import mjcf
from etils import epath

DEFAULT_POSE = jp.array([0.0, 0.6, -1.2] * 4)          # stand keyframe joints
ACTION_SCALE = 0.4                                     # rad, target = default + a*scale
STAND_HEIGHT = 0.17

# observation noise (1-sigma) per group — matches real STS3215/IMU order of mag
N_GYRO, N_GRAV, N_JPOS, N_JVEL = 0.2, 0.05, 0.02, 1.5

LEG_NAMES = ["FL", "FR", "RL", "RR"]


class NovaJoystick(PipelineEnv):
    def __init__(self, xml="nova.xml", push_interval=150, push_mag=0.6, **kwargs):
        path = epath.Path(__file__).parent / xml
        mj = mujoco.MjModel.from_xml_path(str(path))
        sys = mjcf.load_model(mj)
        self._dt = 0.02                                # 50 Hz control
        n_frames = int(self._dt / sys.opt.timestep)    # 5
        super().__init__(sys, backend="mjx", n_frames=n_frames)

        self._default_pose = DEFAULT_POSE
        self._nu = sys.nu
        self._cmd_lo = jp.array([-0.6, -0.4, -0.7])
        self._cmd_hi = jp.array([1.0, 0.4, 0.7])
        # brax link index = mj body id - 1 (world excluded)
        self._foot_ids = jp.array(
            [mj.body(f"{n}_foot").id - 1 for n in LEG_NAMES])
        self._push_interval = push_interval
        self._push_mag = push_mag

    def sample_command(self, rng):
        return jax.random.uniform(rng, (3,), minval=self._cmd_lo, maxval=self._cmd_hi)

    def reset(self, rng):
        rng, kc, kv, kj, ko = jax.random.split(rng, 5)
        q = self.sys.qpos0.at[7:].set(
            self._default_pose + jax.random.uniform(kj, (self._nu,), minval=-0.1, maxval=0.1))
        qd = jp.zeros(self.sys.nv)
        # start with a small random base shove -> learn to recover from odd states
        qd = qd.at[0:2].set(jax.random.uniform(kv, (2,), minval=-0.3, maxval=0.3))
        pipeline_state = self.pipeline_init(q, qd)
        info = {
            "rng": rng, "cmd": self.sample_command(kc),
            "last_act": jp.zeros(self._nu), "feet_air": jp.zeros(4),
            "step": 0,
        }
        obs = self._get_obs(pipeline_state, info, ko)
        metrics = {"track": 0.0, "air": 0.0, "height": 0.0, "energy": 0.0}
        return State(pipeline_state, obs, jp.zeros(()), jp.zeros(()), metrics, info)

    def step(self, state, action):
        info = state.info
        rng, ka, ko, kp = jax.random.split(info["rng"], 4)

        ctrl = self._default_pose + action * ACTION_SCALE
        pipeline_state = self.pipeline_step(state.pipeline_state, ctrl)

        # ---- mid-episode PUSH: kick base xy velocity, learn to recover ----
        do_push = (info["step"] % self._push_interval == 0) & (info["step"] > 0)
        push = jax.random.uniform(kp, (2,), minval=-1.0, maxval=1.0) * self._push_mag
        qvel = pipeline_state.qd.at[0:2].add(jp.where(do_push, push, 0.0))
        pipeline_state = pipeline_state.tree_replace({"qd": qvel})

        x, xd = pipeline_state.x, pipeline_state.xd
        quat = pipeline_state.q[3:7]
        qinv = math.quat_inv(quat)
        up = math.rotate(jp.array([0.0, 0.0, 1.0]), qinv)
        lin_vel = math.rotate(xd.vel[0], qinv)
        ang_vel = math.rotate(xd.ang[0], qinv)
        height = x.pos[0, 2]
        cmd = info["cmd"]

        # ---- feet air time (reward a real stepping gait) ----
        foot_z = x.pos[self._foot_ids, 2]
        contact = foot_z < 0.025
        air = info["feet_air"]
        first_contact = (air > 0.0) & contact
        cmd_moving = math.normalize(cmd[:2])[1] > 0.05
        air_rew = jp.sum((air - 0.1) * first_contact) * cmd_moving
        air = jp.where(contact, 0.0, air + self._dt)

        # ---- rewards ----
        track = jp.exp(-4.0 * jp.sum((cmd[:2] - lin_vel[:2]) ** 2))
        track += 0.5 * jp.exp(-4.0 * (cmd[2] - ang_vel[2]) ** 2)
        upright = jp.sum((up - jp.array([0.0, 0.0, 1.0])) ** 2)
        height_pen = (height - STAND_HEIGHT) ** 2
        z_pen = xd.vel[0, 2] ** 2
        act_rate = jp.sum((action - info["last_act"]) ** 2)
        energy = jp.sum(action ** 2)

        reward = (1.5 * track + 0.4 * air_rew + 0.1
                  - 0.6 * upright - 4.0 * height_pen - 0.4 * z_pen
                  - 0.02 * act_rate - 2e-3 * energy)
        reward = jp.clip(reward, -10.0, 10.0)
        done = jp.where((height < 0.08) | (up[2] < 0.4), 1.0, 0.0)

        info["rng"] = rng
        info["last_act"] = action
        info["feet_air"] = air
        info["step"] += 1
        info["cmd"] = jp.where(info["step"] % 250 == 0,
                               self.sample_command(ka), cmd)
        obs = self._get_obs(pipeline_state, info, ko)
        state.metrics.update(track=track, air=air_rew, height=height, energy=energy)
        return state.replace(pipeline_state=pipeline_state, obs=obs,
                             reward=reward, done=done, info=info)

    def _get_obs(self, pipeline_state, info, rng):
        quat = pipeline_state.q[3:7]
        qinv = math.quat_inv(quat)
        ang_vel = math.rotate(pipeline_state.xd.ang[0], qinv)
        proj_grav = math.rotate(jp.array([0.0, 0.0, -1.0]), qinv)
        joints = pipeline_state.q[7:] - self._default_pose
        joint_vel = pipeline_state.qd[6:]
        foot_z = pipeline_state.x.pos[self._foot_ids, 2]
        contact = (foot_z < 0.025).astype(jp.float32)

        clean = jp.concatenate([
            ang_vel * 0.25, proj_grav,
            info["cmd"] * jp.array([2.0, 2.0, 0.25]),
            joints, joint_vel * 0.05, info["last_act"], contact,
        ])
        # sensor noise (robust to real IMU/encoder noise)
        k1, k2, k3, k4 = jax.random.split(rng, 4)
        noise = jp.concatenate([
            jax.random.normal(k1, (3,)) * N_GYRO * 0.25,
            jax.random.normal(k2, (3,)) * N_GRAV,
            jp.zeros(3),                                    # command: no noise
            jax.random.normal(k3, (12,)) * N_JPOS,
            jax.random.normal(k4, (12,)) * N_JVEL * 0.05,
            jp.zeros(12 + 4),                               # last_act, contact clean
        ])
        return clean + noise


def domain_randomize(sys, rng):
    """Per-env randomization: floor friction, per-link mass, actuator gains.
    The sim-to-real bridge + robustness to an unmeasured/varying build."""
    @jax.vmap
    def rand(rng):
        k1, k2, k3 = jax.random.split(rng, 3)
        friction = jax.random.uniform(k1, (), minval=0.6, maxval=1.4)
        geom_fr = sys.geom_friction.at[:, 0].set(friction)
        # jitter EVERY body mass +/-15% (not just the trunk)
        mscale = jax.random.uniform(k2, (sys.nbody,), minval=0.85, maxval=1.15)
        body_mass = sys.body_mass * mscale
        gain = jax.random.uniform(k3, (sys.nu,), minval=25.0, maxval=45.0)
        return geom_fr, body_mass, gain

    geom_fr, body_mass, gain = rand(rng)
    in_axes = jax.tree_util.tree_map(lambda x: None, sys)
    in_axes = in_axes.tree_replace({
        "geom_friction": 0, "body_mass": 0, "actuator_gainprm": 0,
    })
    gainprm = sys.actuator_gainprm[None].repeat(geom_fr.shape[0], axis=0)
    gainprm = gainprm.at[:, :, 0].set(gain)
    sys = sys.tree_replace({
        "geom_friction": geom_fr, "body_mass": body_mass,
        "actuator_gainprm": gainprm,
    })
    return sys, in_axes
