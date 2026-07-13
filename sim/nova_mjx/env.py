"""NOVA MJX joystick locomotion env — velocity-command quadruped walking.

MJX (GPU-parallel MuJoCo) + Brax PipelineEnv, structured like the official MJX
Barkour tutorial so it trains on a free Colab GPU. Observation = trunk angular
velocity + projected gravity + joint (pos-default, vel) + last action + velocity
command; action = 12 joint position targets around the standing default; reward
tracks the (vx, vy, wz) command while penalizing energy / jerk / bad posture.

Domain randomization (`domain_randomize`) jitters friction, trunk mass, and
per-joint gains — the sim-to-real bridge AND the "robust to an unfinished/varying
build" ask: it also lets you train before the final masses are measured.
"""
import jax
import jax.numpy as jp
import mujoco
from brax import base, math
from brax.envs.base import PipelineEnv, State
from brax.io import mjcf
from etils import epath

DEFAULT_POSE = jp.array([0.0, 0.6, -1.2] * 4)          # stand keyframe joints
ACTION_SCALE = 0.4                                     # rad, target = default + a*scale


class NovaJoystick(PipelineEnv):
    def __init__(self, xml="nova.xml", **kwargs):
        path = epath.Path(__file__).parent / xml
        # load via mujoco then hand the MjModel to brax (mjcf.load re-emits the
        # XML and trips its own schema check on the freejoint+inertial layout).
        mj = mujoco.MjModel.from_xml_path(str(path))
        sys = mjcf.load_model(mj)
        self._dt = 0.02                                # 50 Hz control
        n_frames = int(self._dt / sys.opt.timestep)    # 5
        super().__init__(sys, backend="mjx", n_frames=n_frames)

        self._default_pose = DEFAULT_POSE
        self._nu = sys.nu
        # velocity-command ranges (m/s, m/s, rad/s)
        self._cmd_lo = jp.array([-0.6, -0.4, -0.7])
        self._cmd_hi = jp.array([1.0, 0.4, 0.7])
        self._torso = sys.body("trunk").id if hasattr(sys, "body") else 1

    # ---- helpers ----
    def sample_command(self, rng):
        return jax.random.uniform(rng, (3,), minval=self._cmd_lo, maxval=self._cmd_hi)

    def reset(self, rng):
        rng, k1, k2 = jax.random.split(rng, 3)
        q = self.sys.qpos0.at[7:].set(self._default_pose)
        qd = jp.zeros(self.sys.nv)
        pipeline_state = self.pipeline_init(q, qd)
        cmd = self.sample_command(k2)
        state_info = {
            "rng": rng, "cmd": cmd, "last_act": jp.zeros(self._nu),
            "step": 0,
        }
        obs = self._get_obs(pipeline_state, state_info)
        metrics = {"reward_track": 0.0, "reward_energy": 0.0, "height": 0.0}
        return State(pipeline_state, obs, jp.zeros(()), jp.zeros(()),
                     metrics, state_info)

    def step(self, state, action):
        info = state.info
        ctrl = self._default_pose + action * ACTION_SCALE
        pipeline_state = self.pipeline_step(state.pipeline_state, ctrl)

        x, xd = pipeline_state.x, pipeline_state.xd
        quat = pipeline_state.q[3:7]
        up = math.rotate(jp.array([0.0, 0.0, 1.0]), math.quat_inv(quat))
        lin_vel = math.rotate(xd.vel[0], math.quat_inv(quat))     # body-frame
        ang_vel = math.rotate(xd.ang[0], math.quat_inv(quat))
        height = x.pos[0, 2]

        cmd = info["cmd"]
        # rewards
        track = jp.exp(-4.0 * jp.sum((cmd[:2] - lin_vel[:2]) ** 2))
        track += 0.5 * jp.exp(-4.0 * (cmd[2] - ang_vel[2]) ** 2)
        energy = jp.sum(jp.abs(pipeline_state.qvel[6:] *
                               pipeline_state.actuator_force)) if hasattr(
            pipeline_state, "actuator_force") else jp.sum(action ** 2)
        act_rate = jp.sum((action - info["last_act"]) ** 2)
        upright = jp.sum((up - jp.array([0.0, 0.0, 1.0])) ** 2)
        z_pen = xd.vel[0, 2] ** 2

        reward = (1.5 * track - 0.02 * act_rate - 0.5 * upright
                  - 0.3 * z_pen - 1e-3 * energy)
        reward = jp.clip(reward, -10.0, 10.0)

        # termination: fell over / too low
        done = jp.where((height < 0.08) | (up[2] < 0.4), 1.0, 0.0)

        info["last_act"] = action
        info["step"] += 1
        rng, k = jax.random.split(info["rng"])
        info["rng"] = rng
        # resample command occasionally
        info["cmd"] = jp.where(info["step"] % 250 == 0,
                               self.sample_command(k), info["cmd"])

        obs = self._get_obs(pipeline_state, info)
        state.metrics.update(reward_track=track, reward_energy=energy,
                             height=height)
        return state.replace(pipeline_state=pipeline_state, obs=obs,
                             reward=reward, done=done, info=info)

    def _get_obs(self, pipeline_state, info):
        quat = pipeline_state.q[3:7]
        ang_vel = math.rotate(pipeline_state.xd.ang[0], math.quat_inv(quat))
        proj_grav = math.rotate(jp.array([0.0, 0.0, -1.0]), math.quat_inv(quat))
        joints = pipeline_state.q[7:] - self._default_pose
        joint_vel = pipeline_state.qd[6:]
        return jp.concatenate([
            ang_vel * 0.25,          # (3)
            proj_grav,               # (3)
            info["cmd"] * jp.array([2.0, 2.0, 0.25]),  # (3)
            joints,                  # (12)
            joint_vel * 0.05,        # (12)
            info["last_act"],        # (12)
        ])


def domain_randomize(sys, rng):
    """Per-env randomization for robustness / sim-to-real / unmeasured build.
    Jitters floor friction, trunk mass, and actuator gains. Returns a batched
    sys + the in_axes pytree brax's ppo.train expects."""
    @jax.vmap
    def rand(rng):
        rng, k1, k2, k3 = jax.random.split(rng, 4)
        friction = jax.random.uniform(k1, (), minval=0.7, maxval=1.4)
        geom_fr = sys.geom_friction.at[:, 0].set(friction)
        mass_scale = jax.random.uniform(k2, (), minval=0.85, maxval=1.15)
        body_mass = sys.body_mass.at[1].multiply(mass_scale)     # trunk
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
