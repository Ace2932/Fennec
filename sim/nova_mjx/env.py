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
# Command scale applied in the OBSERVATION (vx, vy, wz). SINGLE SOURCE OF TRUTH:
# _get_obs uses it, export_policy bundles it into the .npz, and policy_runner
# reads it back FROM the .npz — so the deploy side can never drift from training
# (this exact triple-hardcode is the drift the weight pipeline now closes).
CMD_OBS_SCALE = jp.array([2.0, 2.0, 0.25])

# observation noise (1-sigma) per group — matches real STS3215/IMU order of mag
N_GYRO, N_GRAV, N_JPOS, N_JVEL = 0.2, 0.05, 0.02, 1.5
GYRO_BIAS = 0.05                                       # per-episode constant IMU bias (rad/s)
# measured STS3215 slop (docs/bench/README.md): firmware deadzone 10 counts =
# 0.88 deg (no actuation below this position error), gear backlash 0.87 deg.
JOINT_BIAS = 0.015     # per-episode per-joint position offset (rad, ~0.87 deg) —
                       # home-cal + backlash bias. Like GYRO_BIAS but for joints.
DEADBAND = 0.0154      # rad (10 counts) — servo ignores goal changes below this.

LEG_NAMES = ["FL", "FR", "RL", "RR"]

# Foot geom is a sphere of this radius centred on the foot BODY ORIGIN
# (nova.xml: `<geom name="FL_foot" type="sphere" size="0.014" class="foot"/>`),
# so `foot_z` (the link position) sits one radius ABOVE the ground on touchdown.
# Measured standing on all four, weight fully settled: foot_z = 0.0125.
#
# The contact test WAS `foot_z < 0.025` — 12.5mm above the weight-bearing height,
# so a foot could float a centimetre off the floor and still be scored PLANTED.
# Every gait shaper (air/gait/clearance/slip) read it, so all four were blind
# inside that dead band. Now radius-corrected, per the Barkour reference
# (`contact = (foot_z - foot_radius) < 1e-3`); Playground uses real collision
# sensors, which would be better still but needs contact sensors in the MJCF.
#
# The `airT_*` / `ghost_*` metrics keep BOTH definitions visible so this can never
# silently drift again.
FOOT_RADIUS = 0.014
CONTACT_EPS = 1e-3

# Target swing height for the feet_clearance COST. The reference (Playground Go1)
# uses max_foot_height = 0.1, but that is GO1-SCALED: a 0.1m lift on a robot whose
# body sits at ~0.3m. NOVA stands at STAND_HEIGHT 0.17 with a ~0.21m hip-to-foot
# leg, so 0.1 would demand a lift of 59% of body height every stride — servo-
# punishing and nothing like a real trot. Scaled to NOVA's geometry: 0.1 * 0.17/0.3
# ~= 0.057, and by leg length 0.1 * 0.21/0.35 = 0.06 -> take 0.05 (a lift of ~32%
# of the foot's 157mm vertical range).
#
# ⚠ This is the class of bug that keeps biting: an imported reference constant
# that was never rescaled to NOVA. `track`'s sigma is the other live one — 0.0625
# was correct for a 0.5 m/s command, but 170f072 lowered commands to 0.15-0.35 and
# never rescaled it, so a STANDING robot now scores 0.55 there (measured stand:
# 1.357/step total). Left alone deliberately: the robot walks, so the stand basin
# is not the active failure. Fix it when the evidence says to, not before.
FOOT_TARGET_Z = 0.05

# Carry cost: a foot airborne longer than AIR_MAX seconds is being HELD, not
# stepping (a real swing tops out ~0.2-0.3s). Penalize the excess, capped so one
# parked leg can't swamp the reward. See the derivation at the term itself.
AIR_MAX = 0.4          # s of air a normal stride is allowed, penalty-free
AIR_CARRY_CAP = 0.6    # s — max penalized excess per foot (bounds a held leg)

# ---- HEIGHT MAP (tier-2 PRIVILEGED teacher, opt-in NovaJoystick(heightmap=True)) ----
# A local terrain-elevation grid sampled from the sim heightfield, appended to the
# obs (LAST dims -> obs 105 -> 105+HM_N*HM_N). This is the PERFECT/omniscient map:
# no occlusion, noise, FOV, or latency. Fine for the TEACHER (feasibility + expert)
# but NOT what the real D456+L2 elevation map looks like — the STUDENT must be
# distilled on a realistic occluded/noisy map (needs hardware calibration). See
# project-sim-roadmap-perception-nav. Each cell = terrain_height - base_z (how far
# the ground sits below the robot there; a step up reads less negative). Grid is
# YAW-aligned (rotates with heading) and centred on the base.
HM_N = 11                 # grid is HM_N x HM_N cells
HM_EXTENT = 0.4           # metres: grid spans +-HM_EXTENT around the base (8cm cells)


class NovaJoystick(PipelineEnv):
    def __init__(self, xml="nova.xml", push_interval=150, push_mag=0.6,
                 cmd_stage=2, heightmap=False, **kwargs):
        self._heightmap = heightmap
        path = epath.Path(__file__).parent / xml
        mj = mujoco.MjModel.from_xml_path(str(path))
        sys = mjcf.load_model(mj)
        self._dt = 0.02                                # 50 Hz control
        n_frames = int(self._dt / sys.opt.timestep)    # 5
        super().__init__(sys, backend="mjx", n_frames=n_frames)

        self._default_pose = DEFAULT_POSE
        self._nu = sys.nu
        # COMMAND CURRICULUM.
        #
        # STAGE 1 (forward-only) built the gait. Runs 1-8 kept converging to a
        # stand/wiggle because the range included idle + backward + big turns, and
        # standing SATISFIES an idle command, so the policy hedged toward not
        # moving. Stage 1 made every command forward, so standing NEVER satisfied
        # the task -> the only way to score was to walk. It worked: a forward trot.
        #
        # STAGE 2 (default now) opens reverse + lateral + turning for an
        # omnidirectional joystick policy. RESUME the stage-1 walk into it; do NOT
        # train stage 2 from scratch (that reopens the stand-basin the curriculum
        # exists to avoid). The stand basin is now also guarded by the fixed
        # reward: `track` is floor-free (a stand scores ~0 for any nonzero cmd) and
        # the `stand` penalty handles commanded-idle correctly, so standing-when-
        # idle is the CORRECT behavior here, not the trap it was pre-fix.
        #
        # ⚠ ALL ranges stay INSIDE the MEASURED actuator envelope. Leg joints cap
        # at 2.8 rad/s (bench, #91) -> body speed tops out ~0.2-0.3 m/s. The old
        # commented hint (vx to 1.0, the "[-0.6..1.0]" line) predated that finding
        # and commanded 3x-unreachable speeds -> the tracking gradient flattened
        # and a torque-cheap CROUCH became optimal (the #112 regression). We do NOT
        # use it. Stage 2 keeps vx at the same 0.35 forward cap, adds only GENTLE
        # reverse (reverse is harder), modest lateral, and a moderate yaw the legs
        # can produce by foot placement (not forward-speed-limited). Widen further
        # only after a probe shows the walk survived this step.
        if cmd_stage == 1:
            self._cmd_lo = jp.array([0.15, -0.10, -0.2])
            self._cmd_hi = jp.array([0.35,  0.10,  0.2])
        else:                                    # stage 2 — omnidirectional, capped
            self._cmd_lo = jp.array([-0.15, -0.15, -0.5])
            self._cmd_hi = jp.array([ 0.35,  0.15,  0.5])
        self._cmd_stage = cmd_stage
        # heightfield geom centre + span, for the height-map sampler (world<->grid).
        # Static (only hfield_data is per-env randomized), so cache it here.
        self._floor_pos = jp.array(mj.geom("floor").pos)
        self._hf_size = jp.array(mj.hfield_size[0])           # [rx, ry, ztop, zbot]
        self._hf_nrow = int(mj.hfield_nrow[0])
        self._hf_ncol = int(mj.hfield_ncol[0])
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
        obs = self._get_obs(info, pipeline_state)
        # INSTRUMENTATION (no effect on reward): every WEIGHTED reward
        # contribution + the per-foot stats needed to diagnose a farm. Only
        # track/air/height/energy were logged through ckpt12, which is why the
        # held-foot farm ran unseen for 12 checkpoints — the clearance and gait
        # terms that pay for it were never in the metrics.
        metrics = {k: 0.0 for k in (
            "track", "air", "height", "energy",
            # weighted contributions (what actually competes for the policy)
            "w_track", "w_yaw", "w_progress", "w_air", "w_clearance",
            "w_pose", "w_upright", "w_angvel", "w_height", "w_z", "w_slip",
            "w_carry",
            "w_splay", "w_actrate", "w_energy", "w_jerk", "w_stand",
            # diagnostics: per-foot airborne fraction [FL, FR, RL, RR] — a
            # carried leg reads ~1.0 here while the others cycle
            "air_FL", "air_FR", "air_RL", "air_RR",
            # same, under the RADIUS-CORRECTED contact test, + the "ghost"
            # fraction where the proxy says planted but the foot is airborne
            "airT_FL", "airT_FR", "airT_RL", "airT_RR",
            "ghost_FL", "ghost_FR", "ghost_RL", "ghost_RR",
            # mean |xy| speed of feet that are OFF the ground: the number the
            # clearance farm is scaled by (was assumed, never measured)
            "swing_xy_speed", "move_gate", "fwd_speed",
        )}
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
        foot_xy = x.pos[self._foot_ids, :2]
        # height above the LOCAL collision surface — the quantity every gait
        # term below actually means. On flat (all-zero hfield) ground_z == 0
        # and foot_h == foot_z: bit-identical to the pre-terrain-relative code.
        ground_z = self._terrain_ground_z(foot_xy[:, 0], foot_xy[:, 1])
        foot_h = foot_z - ground_z
        # done/height ground reference: MIN over the four feet, NOT a CoM point
        # sample — hip span (~0.28 m) exceeds a tread run (~0.20 m), so a
        # climbing robot NORMALLY straddles two treads; a CoM sample past the
        # riser reads the upper tread and can under-read base_h by ~0.10 m,
        # spuriously terminating a healthy climb. min() errs toward survival
        # and is identical on flat (all zeros).
        base_h = height - jp.min(ground_z)
        # TERRAIN-RELATIVE contact — reads foot_h (height above LOCAL ground; see
        # _terrain_ground_z), not absolute world z. On the radial staircase an
        # absolute-z test read a foot PLANTED on an elevated step as airborne, so
        # slip stopped billing and scraping a foot against a riser was free.
        # RADIUS-CORRECTED (Barkour ref: `(foot_z - foot_radius) < 1e-3`).
        # Was `foot_z < 0.025` — 12.5mm above the measured weight-bearing height
        # (0.0125), so a foot could float a centimetre up and still score as
        # planted. PROBED on ckpt12: FR/RL were airborne 11.0%/12.2% of the time
        # and the reward saw 0.0% — their ENTIRE air time fell inside the dead
        # band. Every gait shaper reads this, so small correct steps were both
        # invisible (no clearance/air/gait) and PUNISHED (slip bills a swinging
        # foot as sliding, because contact never went false). The policy carried
        # a leg because that was the only motion the reward could see.
        contact = (foot_h - FOOT_RADIUS) < CONTACT_EPS
        air = info["feet_air"]
        first_contact = (air > 0.0) & contact
        cmd_moving = math.normalize(cmd[:2])[1] > 0.05
        air_rew = jp.sum(jp.clip(air - 0.2, 0.0, 0.4) * first_contact) * cmd_moving
        air = jp.where(contact, 0.0, air + self._dt)
        # CARRY COST — a foot airborne past one stride bleeds. This is the term
        # the reward was missing: at 0.15-0.35 m/s THREE legs already satisfy
        # track + progress, so the 4th is dead weight the reward was indifferent
        # to (probe after the contact/clearance fix: RR still carried 0.970,
        # PINNED at ckpt12's value — zero gradient, not slow). The clearance cost
        # is |z - 0.05|, so a foot PARKED at the 0.05 target costs nothing; the
        # target height just became the carry height. This makes the carry itself
        # expensive, regardless of how cleverly it's held.
        #
        # A real swing tops out ~0.2-0.3s, so AIR_MAX 0.4 leaves normal stepping
        # free; only a HELD foot crosses it. Capped so one parked leg can't swamp
        # the whole reward (a foot airborne the full episode would otherwise dwarf
        # everything). It is a COST — it shapes HOW, so it is not positive. This
        # does not reopen a farm: there is no way to earn by triggering it.
        carry_cost = jp.sum(jp.clip(air - AIR_MAX, 0.0, AIR_CARRY_CAP))

        # ---- gait reward: DELETED ----
        # Was: `|(FL+RR) - (FR+RL)|/2` — instantaneous diagonal asymmetry, with NO
        # temporal component, so a FROZEN half-trot scores exactly like a real one.
        # ckpt12 found that: it held the FL/RR diagonal up and dragged FR/RL, and
        # the term paid |(0.472+0.970) - 0|/2 * 0.5 = 0.3606/step for it — matching
        # the probe's measured 0.3606 to four decimals. Rewarding alternation needs
        # a phase, and a phase the policy cannot observe is noise (that's what
        # sank the run-6 clock — see the note in the class docstring). The
        # reference (MuJoCo Playground Go1) carries NO gait reward at all and
        # still produces a clean trot on flat ground; the gait falls out of
        # tracking + the clearance/slip COSTS. Removed rather than re-shaped.

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
        # NORMALIZED progress = achieved speed along the commanded direction,
        # capped at the commanded speed. (The old dot-product form capped at
        # ||cmd||^2, which scales QUADRATICALLY with command speed — at 0.25 m/s
        # it nearly vanished, 0.0625/step, silently gutting the forward driver.)
        cmd_speed = jp.linalg.norm(cmd_xy) + 1e-6
        progress = jp.clip(jp.dot(cmd_xy, lin_vel[:2]) / cmd_speed, 0.0, cmd_speed)
        # MOVE GATE: the gait is stable + dynamic but IN-PLACE (survives 400 steps
        # yet traveled only 0.12 m at vx 0.5). The gait-shapers (air/gait/clearance)
        # are farmable by stepping in place, so it does. Scale them by forward speed
        # -> an in-place gait earns ~0 on them, so the stepping must TRANSLATE to
        # score. The robot already steps (no discovery chicken-egg now).
        # gate fully open at 0.1 m/s achieved along the command (~half the new
        # achievable command range)
        move_gate = jp.clip(jp.dot(cmd_xy, lin_vel[:2]) / cmd_speed / 0.1, 0.0, 1.0)
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
        # TERRAIN-RELATIVE posture cost — reads base_h (base height above LOCAL
        # ground; see the min-over-feet note above), not absolute world z. With
        # absolute z this quadratic penalized the robot for being elevated at
        # all: on the radial staircase every step climbed added (step_h)^2 of
        # cost, a direct anti-climb gradient. base_h strips the terrain offset so
        # the target posture costs the same at every elevation; on flat (all-zero
        # hfield) base_h == height and this is bit-identical to the old code.
        height_pen = (base_h - STAND_HEIGHT) ** 2
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
        # SCALED BY horizontal foot speed (reference feet_clearance): a SWINGING
        # foot earns, a HELD foot (xy-speed ~0) earns ~nothing. The unscaled form
        # reopened the hold-a-foot farm — the ckpt12 walker carried the rear-right
        # foot in the air the ENTIRE rollout (~0.24/step free once the move-gate
        # opened) and the 3-legged thrust asymmetry caused the heading VEER.
        # FLIPPED to the reference COST form (Playground `_cost_feet_clearance`):
        #     sum(|foot_z - target| * sqrt(|vel_xy|)),  weight -2.0
        # The old form REWARDED height*speed, so max height * max speed = max pay,
        # with nothing requiring the foot to ever land — farmable by construction,
        # whatever the speed. Probed on ckpt12 it paid +0.709/step (20.6% of all
        # positive reward) to a leg carried 97.5% of the time doing zero
        # locomotion. Swing-scaling (25bad0c) didn't close that; it only stopped a
        # MOTIONLESS held foot, and the policy simply waved the foot instead
        # (measured swing_xy_speed 0.754 m/s).
        #
        # The cost form is self-limiting from BOTH sides: a foot dragging too low
        # while moving is penalized, a foot held too high while moving is
        # penalized, and a foot at the target pays nothing however fast it swings.
        # It also reads NO contact flag, so it cannot be fooled by a bad contact
        # threshold at all.
        #
        # TERRAIN-RELATIVE: the swing target is FOOT_TARGET_Z above the LOCAL
        # ground (foot_h; see _terrain_ground_z), not absolute world z. Reading
        # foot_z taxed every swing by how high the terrain sat under it — up to
        # 2*ztop on a step — penalising exactly the lift needed to climb. foot_h
        # makes the target the same 0.05 m clearance on a step as on the flat.
        clearance_cost = jp.sum(jp.abs(foot_h - FOOT_TARGET_Z) * jp.sqrt(foot_xy_speed))
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

        # ---- REWARD ARCHITECTURE (read this before adding a term) ----
        # Twelve runs of shaping history are in git; the pattern across all of
        # them is one line:
        #
        #     EVERY POSITIVE SHAPER GOT FARMED. NO COST EVER DID.
        #
        # clearance+, gait+, air+ each went in to fix the previous run's symptom
        # and each became the next run's exploit. slip-, splay-, upright- just
        # quietly did their job. That is not luck: an additive bonus on a proxy
        # creates an incentive to maximise the proxy, and the policy always finds
        # the cheapest way — which is rarely locomotion. A cost only ever
        # constrains.
        #
        # The reference (Playground Go1) makes this explicit. Its whole POSITIVE
        # budget is 2.1 (tracking_lin_vel 1.0, tracking_ang_vel 0.5, pose 0.5,
        # feet_air_time 0.1) and every other one of its 16 terms is a cost. It has
        # no gait reward and no progress term, and it still learns a clean trot on
        # flat ground. NOVA's positive weight had reached 16.4, with clearance
        # alone at +10.0 — 5x the reference's entire positive budget, sign-flipped.
        #
        # RULE: the ONLY positive terms are the task (track / yaw_track /
        # progress) plus the alive bonus. Anything shaping HOW the robot moves is
        # a COST. If you are about to add a positive shaper, you are about to
        # start run 13.
        #
        # progress is the one deliberate exception to the reference: linear and
        # floor-free, it pulls a slow (0.15-0.35 m/s) robot forward where the
        # saturating exp of `track` gives little gradient. It is not farmable —
        # it requires real displacement.
        # Each weighted term is a NAMED variable, and `reward` is their sum, so
        # the logged metrics are the reward by construction and cannot drift
        # from it. (They already had: the comment above says "+ 3.0 *
        # clearance_rew" while the live weight was 10.0.)
        w_track = 1.5 * track
        # 0.3 -> 0.75: at 0.3 the policy walked a constant-yaw CIRCLE (rollout at
        # cmd [0.25,0,0]: traveled 0.51m in world x but body-frame fwd_speed 0.253
        # -> an arc, yaw_track only 0.38). The heading command is wz=0, so holding
        # heading is the TASK, not a shaper. NOVA ran track:yaw = 1.5:0.3 = 5:1;
        # the reference (Playground Go1) runs lin:ang = 1.0:0.5 = 2:1. 0.75 puts
        # yaw back on the reference ratio so a residual gait asymmetry can't steer
        # a slow drift the tracking term is happy to ignore.
        w_yaw = 0.75 * yaw_track
        w_progress = 3.0 * progress
        w_air = move_gate * 0.5 * air_rew
        # NOT gated by move_gate: gating a COST by forward speed would let the
        # robot dodge it by standing still. Ungated is also the reference's form,
        # and it needs no gate — a planted foot has ~zero xy speed, so it pays
        # ~zero regardless.
        w_clearance = -2.0 * clearance_cost
        w_pose = 0.5 * pose_rew
        w_upright = -2.5 * upright
        w_angvel = -0.2 * ang_vel_xy
        w_height = -1.5 * height_pen
        w_z = -0.4 * z_pen
        w_slip = -0.5 * slip_pen
        w_splay = -0.8 * splay_pen
        # -1.5: a fully-carried foot (excess clipped to AIR_CARRY_CAP 0.6) costs
        # 0.9/step, which no positive term can offset for a leg contributing
        # nothing — so putting it down is strictly uphill. A normal stride stays
        # below AIR_MAX and pays 0.
        w_carry = -1.5 * carry_cost
        w_actrate = -0.02 * act_rate
        w_energy = -2e-3 * energy
        w_jerk = -0.01 * jerk
        w_stand = -5e-4 * stand
        reward = (w_track + w_yaw + w_progress + w_air + w_clearance
                  + w_pose + 0.1
                  + w_upright + w_angvel + w_height + w_z
                  + w_slip + w_splay + w_carry
                  + w_actrate + w_energy + w_jerk + w_stand)
        reward = jp.clip(reward, -10.0, 10.0)
        # TERRAIN-RELATIVE termination — the low-height gate reads base_h (height
        # above LOCAL ground; see the min-over-feet note above), not absolute
        # world z. With absolute z a face-planted robot on an elevated step never
        # tripped the 0.08 floor (its base_z stays well above it), so corpses
        # kept accruing reward and polluting metrics. min-over-feet errs toward
        # survival (a straddling climber reads the LOWER tread), so a healthy
        # climb is never spuriously killed. On flat base_h == height: identical.
        done = jp.where((base_h < 0.08) | (up[2] < 0.4), 1.0, 0.0)

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
        obs = self._get_obs(info, pipeline_state)
        # airborne fraction per foot — averaged over an episode, a CARRIED leg
        # reads ~1.0 while a stepping leg reads ~0.3-0.5 (its swing duty).
        foot_air_f = jp.logical_not(contact).astype(jp.float32)
        # TRUE contact (radius-corrected, Barkour ref) vs the live proxy. `ghost`
        # = the reward believes this foot is planted while it is actually in the
        # air. Diagnostic only — the reward still uses `contact` above. Reads the
        # SAME terrain-relative foot_h (see _terrain_ground_z) as `contact`, so
        # the two stay in lockstep on terrain and ghost_* keeps meaning what it
        # did on flat; an absolute-z test here would fire phantom ghosts on every
        # elevated step (T9 pins the lockstep).
        contact_true = (foot_h - FOOT_RADIUS) < CONTACT_EPS
        air_true_f = jp.logical_not(contact_true).astype(jp.float32)
        ghost_f = (contact & jp.logical_not(contact_true)).astype(jp.float32)
        # mean |xy| speed over feet that are off the ground (0 if all planted) —
        # this is the multiplier the clearance term pays on.
        n_swing = jp.sum(foot_air_f)
        swing_xy_speed = jp.where(n_swing > 0,
                                  jp.sum(foot_xy_speed * foot_air_f) / jp.maximum(n_swing, 1.0),
                                  0.0)
        state.metrics.update(
            track=track, air=air_rew, height=height, energy=energy,
            w_track=w_track, w_yaw=w_yaw, w_progress=w_progress, w_air=w_air,
            w_clearance=w_clearance, w_pose=w_pose,
            w_upright=w_upright, w_angvel=w_angvel, w_height=w_height, w_z=w_z,
            w_slip=w_slip, w_splay=w_splay, w_carry=w_carry,
            w_actrate=w_actrate,
            w_energy=w_energy, w_jerk=w_jerk, w_stand=w_stand,
            air_FL=foot_air_f[0], air_FR=foot_air_f[1],
            air_RL=foot_air_f[2], air_RR=foot_air_f[3],
            airT_FL=air_true_f[0], airT_FR=air_true_f[1],
            airT_RL=air_true_f[2], airT_RR=air_true_f[3],
            ghost_FL=ghost_f[0], ghost_FR=ghost_f[1],
            ghost_RL=ghost_f[2], ghost_RR=ghost_f[3],
            swing_xy_speed=swing_xy_speed, move_gate=move_gate,
            fwd_speed=jp.dot(cmd_xy, lin_vel[:2]) / cmd_speed)
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

    def _terrain_ground_z(self, wx, wy):
        """ABSOLUTE terrain z at world (wx, wy) matching MuJoCo's hfield COLLISION
        surface exactly — per-cell fixed-diagonal (v00-v11) triangulation, NOT
        bilinear. Bilinear (what the obs uses) diverges from the surface physics
        stands on by up to ~19 mm inside riser-boundary cells, in BOTH directions
        — enough to re-open the absolute-z contact bug at exactly the tread edges
        climbing needs (spec 2026-07-20, empirically measured vs mj_ray). The
        reward/done consumers therefore read THIS, and the obs keeps bilinear
        (_sample_heightmap) because the policy was trained on it.

        Flat no-op invariant (foot_h == foot_z on flat) is bit-exact only because
        fz == 0: nova.xml's floor geom sits at z == 0, so `z*ztop + fz` collapses
        to `z*ztop` and a zero field returns EXACTLY 0. Reposition the floor and
        that identity breaks (test_T1 is the canary)."""
        rx, ry, ztop = self._hf_size[0], self._hf_size[1], self._hf_size[2]
        fx, fy, fz = self._floor_pos[0], self._floor_pos[1], self._floor_pos[2]
        # world xy -> fractional (row, col), same mapping as _sample_heightmap
        # (x -> col, y -> row); T3's asymmetric ramp pins the orientation.
        col = (wx - (fx - rx)) / (2 * rx) * (self._hf_ncol - 1)
        row = (wy - (fy - ry)) / (2 * ry) * (self._hf_nrow - 1)
        data = self.sys.hfield_data.reshape(self._hf_nrow, self._hf_ncol)
        r0 = jp.clip(jp.floor(row).astype(jp.int32), 0, self._hf_nrow - 2)
        c0 = jp.clip(jp.floor(col).astype(jp.int32), 0, self._hf_ncol - 2)
        fr = jp.clip(row - r0, 0.0, 1.0)
        fc = jp.clip(col - c0, 0.0, 1.0)
        v00 = data[r0, c0]
        v01 = data[r0, c0 + 1]
        v10 = data[r0 + 1, c0]
        v11 = data[r0 + 1, c0 + 1]
        z = v00 + jp.where(fc >= fr,
                           fc * (v01 - v00) + fr * (v11 - v01),
                           fr * (v10 - v00) + fc * (v11 - v10))
        return z * ztop + fz

    def _sample_heightmap(self, pipeline_state):
        """Local terrain elevation grid (HM_N x HM_N), yaw-aligned + base-centred,
        each cell = terrain_height - base_z. Reads self.sys.hfield_data, which the
        brax randomization wrapper makes PER-ENV inside step (so it's this env's
        terrain, not the nominal flat one). PRIVILEGED (perfect) — see the header."""
        import jax.scipy.ndimage as jnd
        base = pipeline_state.x.pos[0]
        bx, by, bz = base[0], base[1], base[2]
        w, qx, qy, qz = pipeline_state.q[3], pipeline_state.q[4], \
            pipeline_state.q[5], pipeline_state.q[6]
        yaw = jp.arctan2(2 * (w * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
        g = jp.linspace(-HM_EXTENT, HM_EXTENT, HM_N)
        gx, gy = jp.meshgrid(g, g, indexing="ij")     # gx forward, gy lateral
        c, s = jp.cos(yaw), jp.sin(yaw)
        wx = bx + c * gx - s * gy                      # robot-frame -> world
        wy = by + s * gx + c * gy
        rx, ry, ztop = self._hf_size[0], self._hf_size[1], self._hf_size[2]
        fx, fy, fz = self._floor_pos[0], self._floor_pos[1], self._floor_pos[2]
        # world xy -> fractional (row,col) into the hfield grid (x->col, y->row)
        col = (wx - (fx - rx)) / (2 * rx) * (self._hf_ncol - 1)
        row = (wy - (fy - ry)) / (2 * ry) * (self._hf_nrow - 1)
        data = self.sys.hfield_data.reshape(self._hf_nrow, self._hf_ncol)
        terrain = jnd.map_coordinates(
            data, [row.ravel(), col.ravel()], order=1, mode="nearest")
        terrain = terrain * ztop + fz                  # hfield data[0,1] -> metres
        return (terrain - bz).reshape(-1)              # relative to base

    def _get_obs(self, info, pipeline_state=None):
        """Full obs = HIST proprioceptive frames + command + last action
        (= HIST*PROP + 3 + nu), plus the height-map grid (HM_N^2) LAST when the
        teacher's heightmap is enabled. History lets the policy infer velocity/
        contact/latency from real-only sensors."""
        parts = [
            info["prop_hist"].reshape(-1),
            info["cmd"] * CMD_OBS_SCALE,
            info["last_act"],
        ]
        if self._heightmap:
            parts.append(self._sample_heightmap(pipeline_state))
        return jp.concatenate(parts)


def make_domain_randomize(terrain_max=None, dr_scale=1.0, step_frac=0.0, stair_frac=0.0, flat_frac=0.0):
    """Build the per-env randomization fn.

    terrain_max: rough-ground ceiling (None -> terrain.TERRAIN_MAX = flat). Obs is
      unchanged (proprioceptive terrain inference), so terrain policies stay
      deploy-compatible.
    dr_scale: global width multiplier on every DR range about its measured center.
      1.0 = the measured-grounded defaults; >1 = wider (more conservative, safer
      transfer at some sim-peak cost); <1 = tighter. Resume a trained walk into a
      wider dr_scale the same way as terrain — the policy generalizes to the added
      uncertainty. The real robot must fall inside every range or transfer fails,
      so widen when the real params are genuinely uncertain.
    step_frac: fraction of envs whose terrain is quantized into DISCRETE STEPS
      (terraces of STEP_M*level) rather than smooth rough — tier-1 blind curb/step
      robustness. 0 = all smooth (current). Needs terrain_max>0 to have any effect
      (steps quantize the terrain height). Resume a terrain policy into it; obs
      unchanged (blind), deploy-compatible."""
    from terrain import TERRAIN_MAX as _TM_DEFAULT
    tmax = _TM_DEFAULT if terrain_max is None else float(terrain_max)
    ds = float(dr_scale)

    # Each range is (center, half-width). `dr_scale` widens/narrows the half-width
    # about the center (1.0 = the measured-grounded default below, >1 = more
    # conservative for safer transfer, <1 = tighter for peak sim performance). The
    # center is the best estimate; the width is the genuine UNCERTAINTY about the
    # real robot -- the real NOVA is one sample from this, so it must fall inside.
    def span(center, hw, lo=None, hi=None):
        a, b = center - hw * ds, center + hw * ds
        return (max(a, lo) if lo is not None else a,
                min(b, hi) if hi is not None else b)

    FR_LO, FR_HI = span(1.0, 0.4, lo=0.1)          # foot-floor friction (surface unknown)
    M_LO, M_HI = span(1.0, 0.15, lo=0.5)           # per-link mass (payload + estimate error)
    KP_LO, KP_HI = span(35.0, 10.0, lo=5.0)        # servo P gain (~measured 32)
    KV_LO, KV_HI = span(0.15, 0.15, lo=0.0)        # control-damping uncertainty
    D_LO, D_HI = span(1.05, 0.25, lo=0.1)          # velocity-cap slope (no-load speed +-20%)
    # TORQUE HEADROOM (NEW): the forcerange in the MJCF is the FULL-VOLTAGE stall
    # torque (haa 2.9 @12V, hfe/kfe 1.8 @7.4V). Real available torque is LOWER and
    # varies: battery sag under load, warm servos, and the 19kg-vs-30kg variant all
    # cut headroom. Randomizing 0.7-1.0x teaches the policy to walk when torque is
    # short (low battery / hot / weak servo) instead of leaning on headroom that
    # isn't always there -- a top transfer lever the DR was missing. Capped at 1.0
    # (never exceed the physical full-voltage stall).
    T_LO, T_HI = span(0.85, 0.15, lo=0.3, hi=1.0)

    def domain_randomize(sys, rng):
        """Per-env randomization = the sim-to-real bridge. Covers floor friction,
        per-link mass + INERTIA (scaled together), the STS3215 ACTUATOR model
        (kp/kv/damping + TORQUE HEADROOM), and per-env TERRAIN. Control latency is
        in the env step. All ranges are measured-grounded (docs/bench) and scaled
        by dr_scale. The real robot must land inside every range or transfer
        fails; wider (dr_scale>1) trades sim peak for transfer safety."""
        from terrain import terrain_field
        n = rng.shape[0]

        @jax.vmap
        def rand(rng):
            k1, k2, k3, k4, k5, k6, kt = jax.random.split(rng, 7)
            friction = jax.random.uniform(k1, (), minval=FR_LO, maxval=FR_HI)
            geom_fr = sys.geom_friction.at[:, 0].set(friction)
            # mass AND inertia scale by the SAME per-body factor (a denser/lighter
            # link has proportional inertia — scaling mass alone is inconsistent).
            mscale = jax.random.uniform(k2, (sys.nbody,), minval=M_LO, maxval=M_HI)
            body_mass = sys.body_mass * mscale
            body_inertia = sys.body_inertia * mscale[:, None]
            kp = jax.random.uniform(k3, (sys.nu,), minval=KP_LO, maxval=KP_HI)
            kv = jax.random.uniform(k4, (sys.nu,), minval=KV_LO, maxval=KV_HI)
            damp = sys.dof_damping * jax.random.uniform(
                k5, (sys.nv,), minval=D_LO, maxval=D_HI)
            # per-servo torque headroom -> scale the |forcerange| bounds
            tscale = jax.random.uniform(k6, (sys.nu,), minval=T_LO, maxval=T_HI)
            forcerange = sys.actuator_forcerange * tscale[:, None]
            kt1, kt2, kt3 = jax.random.split(kt, 3)
            # flat-env floor: force `flat_frac` of envs to level 0 (both terrain
            # branches provably collapse to zero). Flat was ~5% of stage-4 envs;
            # a deterministic fall there cost ~2% of batch return — beneath
            # PPO's notice, which is exactly how the flat gait rotted while the
            # terrain gait improved. 25% makes flat worth not falling over on,
            # and matches deployment: NOVA lives mostly on floors.
            is_flat = jax.random.uniform(kt3, ()) < flat_frac
            level = jp.where(is_flat, 0.0,
                             jax.random.uniform(kt2, (), minval=0.0, maxval=tmax))
            hfield = terrain_field(kt1, level, step_frac, stair_frac)
            return geom_fr, body_mass, body_inertia, kp, kv, damp, forcerange, hfield

        geom_fr, body_mass, body_inertia, kp, kv, damp, forcerange, hfield = rand(rng)

        # position actuator: gainprm[:,0]=kp ; biasprm[:,1]=-kp, biasprm[:,2]=-kv
        gainprm = sys.actuator_gainprm[None].repeat(n, axis=0).at[:, :, 0].set(kp)
        biasprm = sys.actuator_biasprm[None].repeat(n, axis=0)
        biasprm = biasprm.at[:, :, 1].set(-kp).at[:, :, 2].set(-kv)

        in_axes = jax.tree_util.tree_map(lambda x: None, sys)
        in_axes = in_axes.tree_replace({
            "geom_friction": 0, "body_mass": 0, "body_inertia": 0,
            "actuator_gainprm": 0, "actuator_biasprm": 0, "dof_damping": 0,
            "actuator_forcerange": 0, "hfield_data": 0,
        })
        sys2 = sys.tree_replace({
            "geom_friction": geom_fr, "body_mass": body_mass,
            "body_inertia": body_inertia, "actuator_gainprm": gainprm,
            "actuator_biasprm": biasprm, "dof_damping": damp,
            "actuator_forcerange": forcerange, "hfield_data": hfield,
        })
        return sys2, in_axes

    return domain_randomize


# backward-compatible module-level fn (flat terrain, terrain.TERRAIN_MAX default)
domain_randomize = make_domain_randomize()
