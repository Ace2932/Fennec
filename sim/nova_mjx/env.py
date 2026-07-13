"""NOVA MJX joystick locomotion env — velocity-command quadruped walking.

MJX (GPU-parallel MuJoCo) + Brax PipelineEnv, structured like the official MJX
Barkour tutorial so it trains on a free Colab GPU.

Real-world readiness (so the policy survives the sim-to-real gap):
  * OBSERVATION HISTORY — the policy sees the last HIST proprioceptive frames,
    not one. Real robots have latency + noise, so a single frame under-
    determines the state; a short history lets the policy infer velocity,
    ground contact, and latency. Single biggest transfer lever after actuator
    fidelity, and it removes the need for foot-contact sensors NOVA doesn't
    have — contact is inferable from the joint-vel history (so the obs uses
    ONLY signals the real robot can produce: IMU + servo feedback + command).
  * sensor realism — per-group noise + a per-episode IMU GYRO BIAS (the real
    ICM-42688-P has a bias, not just noise).
  * randomized start, mid-episode PUSHES (fall recovery), a feet-air-time gait
    reward, jerk + stand-still penalties (smooth, no-shuffle = less servo wear
    + better transfer), and wide domain randomization (friction/mass/gains/
    latency). DR + measured params before hardware = the transfer recipe.
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
HIST = 3                                               # proprioceptive frames stacked
PROP = 30                                              # per-frame: gyro3+grav3+jpos12+jvel12

# observation noise (1-sigma) per group — matches real STS3215/IMU order of mag
N_GYRO, N_GRAV, N_JPOS, N_JVEL = 0.2, 0.05, 0.02, 1.5
GYRO_BIAS = 0.05                                       # per-episode constant IMU bias (rad/s)

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
        self._max_delay = 3            # control-latency buffer depth (0..2 steps)

    def sample_command(self, rng):
        return jax.random.uniform(rng, (3,), minval=self._cmd_lo, maxval=self._cmd_hi)

    def reset(self, rng):
        rng, kc, kv, kj, ko, kd, kb = jax.random.split(rng, 7)
        q = self.sys.qpos0.at[7:].set(
            self._default_pose + jax.random.uniform(kj, (self._nu,), minval=-0.1, maxval=0.1))
        qd = jp.zeros(self.sys.nv)
        # start with a small random base shove -> learn to recover from odd states
        qd = qd.at[0:2].set(jax.random.uniform(kv, (2,), minval=-0.3, maxval=0.3))
        pipeline_state = self.pipeline_init(q, qd)
        info = {
            "rng": rng, "cmd": self.sample_command(kc),
            "last_act": jp.zeros(self._nu), "last_act2": jp.zeros(self._nu),
            "feet_air": jp.zeros(4),
            # per-episode IMU gyro bias (constant offset, not just noise)
            "gyro_bias": jax.random.uniform(kb, (3,), minval=-GYRO_BIAS, maxval=GYRO_BIAS),
            # control latency: apply the action `delay` steps late (bus round-trip)
            "act_hist": jp.zeros((self._max_delay, self._nu)),
            "delay": jax.random.randint(kd, (), 0, self._max_delay),
            "prop_hist": jp.zeros((HIST, PROP)),
            "step": 0,
        }
        frame = self._prop_frame(pipeline_state, info, ko)
        info["prop_hist"] = jp.tile(frame, (HIST, 1))     # fill history with frame 0
        obs = self._get_obs(info)
        metrics = {"track": 0.0, "air": 0.0, "height": 0.0, "energy": 0.0}
        return State(pipeline_state, obs, jp.zeros(()), jp.zeros(()), metrics, info)

    def step(self, state, action):
        info = state.info
        rng, ka, ko, kp = jax.random.split(info["rng"], 4)

        # ---- control latency: the servos see an OLDER action (bus + servo lag).
        # `last_act` (obs + smoothness) stays the policy's true output. ----
        hist = jp.concatenate([action[None], info["act_hist"][:-1]], axis=0)
        applied = hist[info["delay"]]
        ctrl = self._default_pose + applied * ACTION_SCALE
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
        # jerk: 2nd difference of actions -> smoother motion, less servo wear
        jerk = jp.sum((action - 2 * info["last_act"] + info["last_act2"]) ** 2)
        energy = jp.sum(action ** 2)
        # stand still when idle: no shuffling when the command is ~zero
        joint_vel = pipeline_state.qd[6:]
        idle = jp.sum(cmd ** 2) < 0.02
        stand = jp.where(idle, jp.sum(joint_vel ** 2), 0.0)

        reward = (1.5 * track + 0.4 * air_rew + 0.1
                  - 0.6 * upright - 4.0 * height_pen - 0.4 * z_pen
                  - 0.02 * act_rate - 2e-3 * energy
                  - 0.01 * jerk - 5e-4 * stand)
        reward = jp.clip(reward, -10.0, 10.0)
        done = jp.where((height < 0.08) | (up[2] < 0.4), 1.0, 0.0)

        # push the new proprioceptive frame into the history buffer (newest first)
        frame = self._prop_frame(pipeline_state, info, ko)

        info["rng"] = rng
        info["last_act2"] = info["last_act"]
        info["last_act"] = action
        info["act_hist"] = hist
        info["feet_air"] = air
        info["prop_hist"] = jp.concatenate([frame[None], info["prop_hist"][:-1]], axis=0)
        info["step"] += 1
        info["cmd"] = jp.where(info["step"] % 250 == 0,
                               self.sample_command(ka), cmd)
        obs = self._get_obs(info)
        state.metrics.update(track=track, air=air_rew, height=height, energy=energy)
        return state.replace(pipeline_state=pipeline_state, obs=obs,
                             reward=reward, done=done, info=info)

    def _prop_frame(self, pipeline_state, info, rng):
        """One PROP-d proprioceptive frame — ONLY signals the real robot can
        produce: IMU gyro (+ per-episode bias) + projected gravity + servo joint
        pos/vel. Plus per-group noise. No foot contacts (NOVA has no foot
        sensors — contact is inferable from the joint-vel history)."""
        quat = pipeline_state.q[3:7]
        qinv = math.quat_inv(quat)
        ang_vel = math.rotate(pipeline_state.xd.ang[0], qinv) + info["gyro_bias"]
        proj_grav = math.rotate(jp.array([0.0, 0.0, -1.0]), qinv)
        joints = pipeline_state.q[7:] - self._default_pose
        joint_vel = pipeline_state.qd[6:]
        frame = jp.concatenate([ang_vel * 0.25, proj_grav, joints, joint_vel * 0.05])
        k1, k2, k3, k4 = jax.random.split(rng, 4)
        noise = jp.concatenate([
            jax.random.normal(k1, (3,)) * N_GYRO * 0.25,
            jax.random.normal(k2, (3,)) * N_GRAV,
            jax.random.normal(k3, (12,)) * N_JPOS,
            jax.random.normal(k4, (12,)) * N_JVEL * 0.05,
        ])
        return frame + noise

    def _get_obs(self, info):
        """Full obs = HIST stacked proprioceptive frames + command + last action
        (= HIST*PROP + 3 + nu). History gives the policy the memory to infer
        velocity/contact/latency from real-only sensors."""
        return jp.concatenate([
            info["prop_hist"].reshape(-1),
            info["cmd"] * jp.array([2.0, 2.0, 0.25]),
            info["last_act"],
        ])


def domain_randomize(sys, rng):
    """Per-env randomization = the sim-to-real bridge. Covers floor friction,
    per-link mass, the STS3215 ACTUATOR model (kp/kv/damping), and per-env
    TERRAIN (a heightfield at a random difficulty level — the blind-locomotion
    curriculum: each env trains on its own rough ground, flat spawn pad, so the
    batch spans flat->rough). Narrow kp/kv/damping around a measured STS3215
    step response later. Control latency is in the env step (per-env delay)."""
    from terrain import terrain_field, TERRAIN_MAX
    n = rng.shape[0]

    @jax.vmap
    def rand(rng):
        k1, k2, k3, k4, k5, kt = jax.random.split(rng, 6)
        friction = jax.random.uniform(k1, (), minval=0.6, maxval=1.4)
        geom_fr = sys.geom_friction.at[:, 0].set(friction)
        mscale = jax.random.uniform(k2, (sys.nbody,), minval=0.85, maxval=1.15)
        body_mass = sys.body_mass * mscale
        # servo position gain kp and velocity gain kv (STS3215 model)
        kp = jax.random.uniform(k3, (sys.nu,), minval=20.0, maxval=50.0)
        kv = jax.random.uniform(k4, (sys.nu,), minval=0.4, maxval=1.6)
        # joint damping (all dofs; base freejoint dofs 0..5 unchanged)
        damp = sys.dof_damping * jax.random.uniform(
            k5, (sys.nv,), minval=0.5, maxval=1.7)
        # per-env terrain at a random difficulty level (implicit curriculum)
        kt1, kt2 = jax.random.split(kt)
        level = jax.random.uniform(kt2, (), minval=0.0, maxval=TERRAIN_MAX)
        hfield = terrain_field(kt1, level)
        return geom_fr, body_mass, kp, kv, damp, hfield

    geom_fr, body_mass, kp, kv, damp, hfield = rand(rng)

    # position actuator: gainprm[:,0]=kp ; biasprm[:,1]=-kp, biasprm[:,2]=-kv
    gainprm = sys.actuator_gainprm[None].repeat(n, axis=0).at[:, :, 0].set(kp)
    biasprm = sys.actuator_biasprm[None].repeat(n, axis=0)
    biasprm = biasprm.at[:, :, 1].set(-kp).at[:, :, 2].set(-kv)

    in_axes = jax.tree_util.tree_map(lambda x: None, sys)
    in_axes = in_axes.tree_replace({
        "geom_friction": 0, "body_mass": 0, "actuator_gainprm": 0,
        "actuator_biasprm": 0, "dof_damping": 0, "hfield_data": 0,
    })
    sys = sys.tree_replace({
        "geom_friction": geom_fr, "body_mass": body_mass,
        "actuator_gainprm": gainprm, "actuator_biasprm": biasprm,
        "dof_damping": damp, "hfield_data": hfield,
    })
    return sys, in_axes
