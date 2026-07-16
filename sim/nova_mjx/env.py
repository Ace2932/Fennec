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
# measured STS3215 slop (docs/bench/README.md): firmware deadzone 10 counts =
# 0.88 deg (no actuation below this position error), gear backlash 0.87 deg.
JOINT_BIAS = 0.015     # per-episode per-joint position offset (rad, ~0.87 deg) —
                       # home-cal + backlash bias. Like GYRO_BIAS but for joints.
DEADBAND = 0.0154      # rad (10 counts) — servo ignores goal changes below this.

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
        # CURRICULUM STAGE 1 — forward-only commands. Runs 1-8 kept converging to
        # a stand/wiggle because the command range included idle + backward + big
        # turns, and standing SATISFIES the idle commands, so the policy hedged
        # toward not-moving. Every command here has forward velocity (0.3-0.7 m/s)
        # + gentle lateral/yaw, so standing NEVER satisfies the task -> the only
        # way to score is to walk forward. Widen back to full range (below) once a
        # forward gait is solid. (legged_gym-style command curriculum.)
        self._cmd_lo = jp.array([0.3, -0.1, -0.2])
        self._cmd_hi = jp.array([0.7, 0.1, 0.2])
        # full range for stage 2: jp.array([-0.6,-0.4,-0.7]) .. jp.array([1.0,0.4,0.7])
        # brax link index = mj body id - 1 (world excluded)
        self._foot_ids = jp.array(
            [mj.body(f"{n}_foot").id - 1 for n in LEG_NAMES])
        self._push_interval = push_interval
        self._push_mag = push_mag
        # control-latency buffer. Measured servo command->motion deadtime ~75 ms
        # (docs/bench); the sim already produces ~32 ms intrinsically (friction
        # breakaway + deadband + inertia), so the transport delay adds 0..4 steps
        # (0..80 ms) -> total 32..112 ms, mean ~72 ms, bracketing the real 75 ms.
        self._max_delay = 5            # delay 0..4 steps @ 50 Hz

    def sample_command(self, rng):
        return jax.random.uniform(rng, (3,), minval=self._cmd_lo, maxval=self._cmd_hi)

    def reset(self, rng):
        rng, kc, kv, kj, ko, kd, kb, kjb = jax.random.split(rng, 8)
        q = self.sys.qpos0.at[7:].set(
            self._default_pose + jax.random.uniform(kj, (self._nu,), minval=-0.1, maxval=0.1))
        qd = jp.zeros(self.sys.nv)
        # start with a small random base shove -> learn to recover from odd states
        qd = qd.at[0:2].set(jax.random.uniform(kv, (2,), minval=-0.3, maxval=0.3))
        pipeline_state = self.pipeline_init(q, qd)
        info = {
            "rng": rng, "cmd": self.sample_command(kc),
            "last_act": jp.zeros(self._nu), "last_act2": jp.zeros(self._nu),
            "last_ctrl": self._default_pose,   # effective servo target (deadband)
            "feet_air": jp.zeros(4),
            # per-episode IMU gyro bias (constant offset, not just noise)
            "gyro_bias": jax.random.uniform(kb, (3,), minval=-GYRO_BIAS, maxval=GYRO_BIAS),
            # per-episode per-joint position bias (home-cal + backlash offset)
            "joint_bias": jax.random.uniform(kjb, (self._nu,),
                                             minval=-JOINT_BIAS, maxval=JOINT_BIAS),
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
        # servo firmware DEADBAND: the real STS3215 ignores goal updates smaller
        # than 10 counts (0.88 deg) -> hold the last effective target (still full
        # holding torque) unless the new target moves past the deadband. Stops the
        # policy relying on finer-than-deadband positioning. The residual sag /
        # sensing uncertainty is covered by the joint obs noise + joint_bias.
        last_ctrl = info["last_ctrl"]
        ctrl = jp.where(jp.abs(ctrl - last_ctrl) > DEADBAND, ctrl, last_ctrl)
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

        # ---- feet air time (bootstraps stepping) ----
        # Gated ONLY on a nonzero command (NOT on forward velocity, per legged_gym
        # /Rudin). Runs 3-5 STOOD partly because a forward-velocity gate here was a
        # chicken-and-egg: no stepping reward until already moving, but you can't
        # move without stepping. threshold 0.2 s + cap 0.4 s -> rewards real swings,
        # not a held foot; short in-place shuffles pay little.
        foot_z = x.pos[self._foot_ids, 2]
        contact = foot_z < 0.025
        air = info["feet_air"]
        first_contact = (air > 0.0) & contact
        cmd_moving = math.normalize(cmd[:2])[1] > 0.05
        air_rew = jp.sum(jp.clip(air - 0.2, 0.0, 0.4) * first_contact) * cmd_moving
        air = jp.where(contact, 0.0, air + self._dt)

        # ---- trot GAIT-PHASE reward (the stand-basin breaker) ----
        # A 2 Hz clock; diagonal pairs (FL,RR)/(FR,RL) alternate swing. Rewarding
        # SELF-ORGANIZED trot (no clock) — reward DIAGONAL asymmetry: a diagonal
        # foot-pair airborne while the other pair is planted (the trot swing).
        # Run 6 used a fixed-phase clock, but the phase is NOT in the observation,
        # so the policy was blind to it and couldn't match it — the reward was
        # effectively noise and it plateaued at a stand (~280). This form rewards a
        # pattern the policy DIRECTLY CONTROLS (which feet are up), so it's
        # discoverable: from a stand, lifting a diagonal pair is immediately +.
        # Stand / pronk (all up) / bound (front or rear pair) all score 0; only a
        # diagonal swing pays. Continuous -> dense gradient.
        foot_up = jp.logical_not(contact).astype(jp.float32)   # [FL, FR, RL, RR]
        gait_rew = jp.abs((foot_up[0] + foot_up[3]) - (foot_up[1] + foot_up[2])) / 2.0 * cmd_moving

        # ---- rewards ----
        # PRIMARY locomotion driver — LINEAR forward/lateral progress, FLOOR-FREE:
        # dot(cmd_xy, vel_xy) is 0 for a stationary robot and paid up to the
        # command magnitude for moving the commanded way. Runs 1-2 STOOD (traveled
        # 0.02 / 0.07 m at vx=0.5) because the exp `track` below has a FLOOR (a
        # stand at cmd 0.5 scored ~0.14) AND the yaw term handed a stationary robot
        # a free 0.5 for "not rotating" — a stand farmed ~1.7/step. This term pays
        # ONLY for real movement, so a stand now scores near zero.
        cmd_xy = cmd[:2]
        # floor-free forward progress: 0 for a stand, paid for real displacement.
        progress = jp.clip(jp.dot(cmd_xy, lin_vel[:2]), 0.0, jp.dot(cmd_xy, cmd_xy) + 1e-6)
        # MOVE GATE: the gait is stable + dynamic but IN-PLACE (survives 400 steps
        # yet traveled only 0.12 m at vx 0.5). The gait-shapers (air/gait/clearance)
        # are farmable by stepping in place, so it does. Scale them by forward speed
        # -> an in-place gait earns ~0 on them, so the stepping must TRANSLATE to
        # score. The robot already steps (no discovery chicken-egg now).
        move_gate = jp.clip(jp.dot(cmd_xy, lin_vel[:2]) / 0.2, 0.0, 1.0)  # 0 at rest, 1 at 0.2 m/s fwd
        # SHARP velocity tracking — sigma 0.25 (legged_gym): a stand at cmd 0.5
        # scores exp(-4)=0.02, near zero, vs the old exp(-8*.25)=0.14 floor.
        track = jp.exp(-jp.sum((cmd_xy - lin_vel[:2]) ** 2) / 0.0625)
        yaw_track = jp.exp(-(cmd[2] - ang_vel[2]) ** 2 / 0.0625)
        upright = jp.sum((up - jp.array([0.0, 0.0, 1.0])) ** 2)
        # roll/pitch angular-velocity penalty — damps the tipping motion. With
        # bigger/faster steps (feet_clearance) the robot NOSE-DIVED forward and
        # fell (rollout: fell at 1.3 s). This + a stronger upright weight give it
        # the pitch stability to support a dynamic gait. (ref: ang_vel_xy.)
        ang_vel_xy = jp.sum(ang_vel[:2] ** 2)
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

        # ---- reference gait-shapers (MuJoCo Playground Go1 uses these to get a
        # clean gait on flat WITHOUT a gait prior; NOVA was missing them, and 9
        # runs stood or wiggled in place). These target the EXACT failures the
        # rollout video showed: a splayed stance + feet dragging in place. ----
        foot_xy_speed = jp.linalg.norm(xd.vel[self._foot_ids, :2], axis=-1)   # (4,) world
        # feet_slip: penalize a foot sliding while IN CONTACT. A wiggle/shuffle
        # DRAGS feet on the ground; this forces the robot to LIFT a foot to move it
        # -> real forward steps, not an in-place drag. (ref: feet_slip.)
        slip_pen = jp.sum(foot_xy_speed * contact.astype(jp.float32))
        # feet_clearance: REWARD swing feet lifting toward a target height. The
        # gait learned correct form (normal stance, real steps) but is TIMID —
        # tiny steps, 0.14 m at vx 0.5, plateaued ~990. Rewarding a higher swing
        # lift -> bigger, committed steps -> more forward speed. Capped at target
        # so it can't farm by holding feet absurdly high. (ref: feet_clearance.)
        clearance_rew = jp.sum(jp.minimum(foot_z, 0.08) * jp.logical_not(contact).astype(jp.float32))
        # splay: the rollout showed the hips abducted WIDE. Penalize haa (hip-
        # abduction, joint idx 0,3,6,9) deviation from the default (0); the hfe/kfe
        # swing joints stay free. (ref: pose regularizer, focused on the splay.)
        splay_pen = jp.sum(pipeline_state.q[7:][jp.array([0, 3, 6, 9])] ** 2)
        # pose: reward the thigh/shank (hfe/kfe) staying near their default bend
        # (0.6 / -1.2). The video showed the FRONT LEGS BUCKLED/COLLAPSED into a
        # hunched crouch; this pulls the legs back to a normal extended stance.
        # exp -> mild, so they can still swing for the gait. (ref: pose regularizer.)
        _hk = jp.array([1, 2, 4, 5, 7, 8, 10, 11])   # hfe,kfe of each leg
        pose_rew = jp.exp(-2.0 * jp.sum((pipeline_state.q[7:][_hk] - self._default_pose[_hk]) ** 2))

        # Research-grounded set (legged_gym sharp tracking + ungated air, Walk-
        # These-Ways trot gait clock). Rough per-step at cmd 0.5: STAND ~0.4,
        # TROT-IN-PLACE ~2.0, TROT-FORWARD ~3.4 — the gait clock lifts stepping far
        # above a stand (breaking the basin), then progress+track pull the trot
        # forward. Every transition is uphill.
        # progress 1.0 -> 2.5: run 7 broke the stand basin (diagonal gait reward)
        # but plateaued ~1360 on a ONE-LEG WIGGLE — stepping in place without going
        # anywhere, because forward displacement was under-incentivized. Make it
        # the dominant term so the stepping is pulled forward.
        # air_rew 1.0 -> 0.5: the MuJoCo Playground Go1 reference weights feet-air-
        # time at only 0.1; NOVA's 1.0 (10x) is what the march/wiggle farmed. Trim
        # it toward the reference so forward progress dominates. gait_rew kept (it
        # broke the stand basin) but is the wiggle's other farm — watch it.
        # gait_rew 1.5 -> 0.5: it broke the stand basin but the wiggle farmed it;
        # slip_pen + splay_pen (below) are the real gait-shapers now, so demote it.
        # + 3.0 * clearance_rew: reward bigger swing lifts to un-stick the timid
        # gait. progress 2.5 -> 3.0: a bit more forward-speed pull (it tracked only
        # ~0.02 of the 0.5 m/s command).
        reward = (1.5 * track + 0.3 * yaw_track + 3.0 * progress
                  + move_gate * (0.5 * air_rew + 0.5 * gait_rew + 3.0 * clearance_rew)
                  + 0.5 * pose_rew + 0.1
                  - 2.5 * upright - 0.2 * ang_vel_xy - 1.5 * height_pen - 0.4 * z_pen
                  - 0.5 * slip_pen - 0.8 * splay_pen
                  - 0.02 * act_rate - 2e-3 * energy
                  - 0.01 * jerk - 5e-4 * stand)
        reward = jp.clip(reward, -10.0, 10.0)
        done = jp.where((height < 0.08) | (up[2] < 0.4), 1.0, 0.0)

        # push the new proprioceptive frame into the history buffer (newest first)
        frame = self._prop_frame(pipeline_state, info, ko)

        info["rng"] = rng
        info["last_act2"] = info["last_act"]
        info["last_act"] = action
        info["last_ctrl"] = ctrl
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
        # joints reported relative to default pose, with a per-episode constant
        # bias (home-cal + backlash offset) — the policy sees a persistently
        # offset joint zero, as on the real robot.
        joints = pipeline_state.q[7:] - self._default_pose + info["joint_bias"]
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
    batch spans flat->rough). Control latency is in the env step (per-env delay).
    kp/kv/damping ranges are NARROWED around the measured STS3215 (docs/bench):
    kp~35 (P=32), kv~0 (control damping folded into the joint torque-speed
    damping = the velocity cap), damping randomized 0.8-1.3x so the no-load speed
    cap spans ~+-20% of the real 2.8/4.71 rad/s."""
    from terrain import terrain_field, TERRAIN_MAX
    n = rng.shape[0]

    @jax.vmap
    def rand(rng):
        k1, k2, k3, k4, k5, kt = jax.random.split(rng, 6)
        friction = jax.random.uniform(k1, (), minval=0.6, maxval=1.4)
        geom_fr = sys.geom_friction.at[:, 0].set(friction)
        mscale = jax.random.uniform(k2, (sys.nbody,), minval=0.85, maxval=1.15)
        body_mass = sys.body_mass * mscale
        # servo gains around measured STS3215: kp~35 (P=32), kv~0 (folded into
        # the joint torque-speed damping); keep a small kv spread for control-
        # damping uncertainty.
        kp = jax.random.uniform(k3, (sys.nu,), minval=25.0, maxval=45.0)
        kv = jax.random.uniform(k4, (sys.nu,), minval=0.0, maxval=0.3)
        # joint damping = the torque-speed slope (velocity cap); 0.8-1.3x spans
        # the no-load speed +-20%. base freejoint dofs 0..5 have 0 damping (x0).
        damp = sys.dof_damping * jax.random.uniform(
            k5, (sys.nv,), minval=0.8, maxval=1.3)
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
