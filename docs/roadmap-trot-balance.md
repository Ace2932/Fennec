# Roadmap: Stable Trot → Balance Controller

2026-07-06. The two gates in front of the Phase-4 arm (backlog #28) and
the inboard-jog unlock. Grounded in what exists: leg_ik + trot generator
+ choreo (85/85 tests), 100 Hz cmd / 50 Hz state firmware, safety
envelope, IMU breakout planned (#14), no foot sensors (servo current
instead), ~2 mm foot backlash, shoe crush-zone pending (#20).

Position-mode servos = no torque control = no force/MPC balance. The
proven architecture for this class is **kinematic reactive balance**
(Raibert heuristics), and everything below builds toward it.

## Stage 1 — static competence (first powered week)

1. **gait_node glue** (buildable now, pure software): choreo/trot
   targets → `solve_side` (X-config `KNEE_FORWARD`) → `joint_id_map` →
   `SafeJointCommandPublisher` → `/joint_commands`. Thin; the logic
   under it is already tested.
2. **body-pose IK module** (buildable now): (roll, pitch, z, xy-shift) +
   four world foot anchors → per-leg hip-frame targets. The missing
   primitive that every later stage uses (weight shift, attitude trim,
   balance).
3. On-robot: stand/sit reps → envelope counters stay zero, hip temps
   (#17 data), servo loads vs static predictions, **backlash measured**
   at direction reversals (feeds the comp table, below).
4. Weight-shift box: standing, drive CoM around the support polygon via
   body-pose IK. Verifies signs, ROM, and the estimator inputs before
   anything dynamic.

## Stage 2 — crawl before trot (the de-risk most people skip)

Static walk: one foot up at a time, CoM pre-shifted over the remaining
triangle. Statically stable at every instant — exercises the entire
pipeline (gait timing, IK, envelope, cabling, thermals) with zero
balance requirement. Implementation: phase offsets (0, .5, .25, .75) +
duty 0.8 on the existing generator + body-pose CoM coupling. If crawl
isn't clean, trot won't be — debug here where falling is impossible.

## Stage 3 — open-loop trot ("stable trot")

What makes position-servo open-loop trot stable — in order of leverage:

1. **Parameters, not control**: stride 1.5–2 Hz, duty 0.55–0.6 (stance
   overlap), step_length 30–40 mm and step_height ~20 mm to start, the
   207 mm track (chosen for exactly this) and a LOW stand height.
2. **Shoe crush zone (#20) before hard-floor tuning** — ~4 mm of
   engineered compliance is the difference between tuning a robot and
   tuning a jackhammer.
3. **Backlash compensation**: feed-forward the measured ~2 mm (≈0.5°)
   at direction reversals in the gait node. Cheap, transforms tracking.
4. **Data-driven tuning loop**: rosbag every run (dashcam node exists);
   metrics script scores IMU pitch/roll RMS + servo load spikes + drift
   per parameter set. Grid the 3-4 gait params against the score —
   afternoons of tuning, not weeks, because the measurement is scripted.
5. **Attitude trim (stage 3.5)**: slow (1–5 Hz bandwidth) lowpassed IMU
   roll/pitch → body-pose offset. Not a balance controller — a trim tab
   that keeps the open-loop trot centered. First consumer of the IMU.

Definition of done: 60 s treadmill-free trot on flat ground, no drift
off a 2 m lane, no envelope interventions, hips < 55 °C.

## Stage 4 — balance controller

Architecture (kinematic-reactive, the class standard from Raibert
through today's hobby quadrupeds):

1. **State estimator**: ICM-42688 at 1 kHz on the Teensy (firmware
   driver + `/imu` topic = NEW firmware work item), Mahony/complementary
   filter on-Teensy → attitude at 100 Hz; fused with stance-leg FK
   odometry on the host → body pose + velocity.
2. **Contact estimation**: servo-current threshold (50 Hz state now
   fast enough) gated by gait phase → early/late touchdown detection.
   Per-leg INA (v7) upgrades this later.
3. **Foot placement = Raibert heuristic**: touchdown target = neutral
   point + k_v·(v_actual − v_cmd) + k_p·capture-point offset. THIS is
   the balance controller for position servos — placing feet, not
   torquing joints.
4. **Attitude regulation**: PD on roll/pitch error → per-stance-leg Δz
   through body-pose IK (promotes the stage-3.5 trim to full bandwidth).
5. **Tuning path**: MuJoCo sim first (docs/sim-training.md lane; URDF
   lengths + ROM real, masses from the weigh session) — the scripted
   controller tunes in sim before hardware; the MJX-learned policy
   stays a parallel track, not a prerequisite.

Definition of done: recovers a firm lateral shove at stance; stands on
a 10° ramp; trots over a 10 mm obstacle without falling. Then the
inboard-jog decision reopens (balance controller was its gate) and the
arm (#28) unblocks.

## Buildable before any hardware arrives

gait_node glue · body-pose IK · crawl variant + tests · backlash-comp
hook · trot metrics script · Raibert stepper as pure logic with tests ·
MuJoCo scene from the URDF. The hardware-blocked items: IMU firmware
driver, homing calibration, everything on-robot.
