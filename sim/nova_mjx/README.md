# NOVA MJX — virtual walking training

Train a NOVA walking policy in simulation (MJX, GPU-parallel MuJoCo) with Brax
PPO, then deploy the learned policy to the Jetson. Built for **no local GPU** —
develop + validate on your Mac (CPU), train on a **free Colab GPU**.

## Files

| file | what |
|---|---|
| `build_mjcf.py` | generates `nova.xml` (MJCF) from the measured link lengths + CAD inertials — same source of truth as `nova_description` |
| `nova.xml` | the MuJoCo model: floating trunk + 4 legs, STS3215 position servos, foot/trunk collision, IMU + joint sensors, stand keyframe |
| `validate_model.py` | CPU check — compiles, right DOF, **stands** under gravity |
| `env.py` | MJX joystick locomotion env (Brax `PipelineEnv`): obs / action / reward / **domain randomization** |
| `train.py` | Brax PPO trainer → pickled policy |
| `requirements.txt` | deps |

## 1. Local (Mac CPU) — validate before burning Colab time

```bash
# python 3.11/3.12; pinned combo (see requirements.txt for why the versions)
pip install "jax[cpu]==0.6.0" brax==0.14.2 "orbax-checkpoint>=0.11.22" mujoco mujoco-mjx
python build_mjcf.py          # -> nova.xml
python validate_model.py      # -> "STANDS ✓"
JAX_PLATFORMS=cpu python -c "import jax,jax.numpy as jp; from env import NovaJoystick; \
  e=NovaJoystick(); s=jax.jit(e.reset)(jax.random.PRNGKey(0)); \
  print('obs',s.obs.shape); print('step ok', jax.jit(e.step)(s, jp.zeros(12)).reward)"
```

The env builds + steps on CPU (obs dim 105 (3-frame history), 12 actions) — good enough to confirm
correctness. **Do not train on CPU** (too slow).

## 2. Train on Colab (free T4 GPU) — checkpointed, survives disconnects

New Colab notebook, **Runtime → change type → T4 GPU**. **Mount Drive first** so
checkpoints survive a disconnect (Colab's `/content` is wiped when the runtime
dies — a local checkpoint dies with it):

```python
from google.colab import drive; drive.mount('/content/drive')
# PINNED versions — brax 0.14.2 only works on jax 0.6.x (see requirements.txt)
!pip install -q "jax[cuda12]==0.6.0" brax==0.14.2 "orbax-checkpoint>=0.11.22" mujoco mujoco-mjx
# upload build_mjcf.py, env.py, train.py  (Files panel, or clone the repo)
!python build_mjcf.py
!python train.py --ckpt /content/drive/MyDrive/nova_ckpt --timesteps 40_000_000
```

Brax writes a full checkpoint (params + normalizer) **every eval** to `--ckpt`.
`eval_reward` climbs over ~20–40 min on a T4.

### If Colab disconnects / crashes partway through
**Just re-run the same `train.py` cell.** It finds the latest checkpoint under
`--ckpt` (by mtime, robust across many resumes) and **continues from it** — no
progress lost. Re-run as many times as needed; each invocation trains
`--timesteps` more from wherever the last checkpoint left off. The run log
(`--ckpt/train_log.csv`) and the latest `nova_policy.pkl` also survive on Drive.

*(Verified end-to-end on CPU: save → find-latest → restore → continue.)*

Scale `--timesteps` up for a cleaner gait; tune the reward weights in `env.py`.

## 3. Robustness — so the trained policy holds up to real failures

The env is built to survive the sim-to-real gap and physical mishaps, not just
walk on flat ideal ground:

- **Observation HISTORY** (3 stacked proprioceptive frames) — the biggest
  transfer lever after actuator fidelity: gives the policy the memory to infer
  velocity / contact / latency from real-only sensors, and removes the need for
  foot-contact sensors NOVA doesn't have (contact is inferred from the joint-vel
  history). Obs = IMU + servo feedback + command only (105-d).
- **Observation noise + a per-episode IMU gyro bias** (real ICM-42688-P drift).
- **Jerk + stand-still penalties** — smooth motion, no idle shuffling (less servo
  wear, better transfer).
- **Randomized start** — random base velocity + joint pose each episode, so the
  policy learns to recover from off-nominal states, not just the home stance.
- **Mid-episode pushes** — a random base-velocity kick every ~150 steps; trains
  active recovery from a shove / stumble / slip (a *physical* failure partway
  through a walk).
- **Feet-air-time reward** — rewards a real stepping gait with ground clearance,
  not a foot-dragging shuffle that face-plants on any bump.
- **Domain randomization** (`domain_randomize`): floor friction, **per-link**
  mass (±15%, every body), and actuator gains — the sim-to-real bridge, and it
  lets you train **before** the final masses are weighed (robust to whatever the
  real build turns out to be).

Widen these (latency, terrain, harder pushes) as you approach hardware.

## 4. Watch the trained gait

```bash
pip install imageio imageio-ffmpeg
python rollout.py --policy nova_policy.pkl --vx 0.5 --steps 400 --out walk.mp4
```

Steps the policy with a fixed forward command, records qpos, renders it in
MuJoCo with a follow-cam → `walk.mp4` (prints how far it traveled in x). With no
`--policy` it renders a zero-action stand — a quick way to test the render path
before training. **Headless (Colab/servers): `MUJOCO_GL=egl python rollout.py …`**
(on macOS use the default, don't set it).

## 5. Deploy to the Jetson

Scaffold is in `deploy/`. Pipeline:

```bash
# export the trained policy (on the training machine / Colab)
python export_policy.py --policy nova_policy.pkl   # -> nova_policy.npz (+ .onnx)
```

- **`export_policy.py`** — extracts the deterministic policy (normalizer + 4×128
  MLP) into `nova_policy.npz` (**numpy weights — the Jetson runs it with zero
  heavy deps**) and `nova_policy.onnx` (portable, optional). Verified numerically
  against the Brax policy (~1e-8).
- **`deploy/policy_runner.py`** — framework-free runner (numpy only). `build_obs`
  reproduces sim's 105-d history obs EXACTLY; `joint_targets(sensors) -> 12 rad targets`.
- **`deploy/policy_node.py`** — ROS 2 node: joint state + IMU + `cmd_vel` @ 50 Hz
  → policy → `/joint_commands`, gated on `/safety_state`. Moves into
  `nova_locomotion` beside the scripted-trot fallback when real.
- **`deploy/test_policy_runner.py`** — cross-checks `build_obs` against the sim
  env byte-for-byte (obs mismatch = silent transfer failure). Passing.

⚠ **Bench-blocked hardware bindings** (marked ⛏ in `policy_node.py`), each
transfer-critical: **joint order** (URDF ↔ Feetech IDs via `joint_id_map.yaml`),
**rad↔ticks** (nova_calibration home offsets — same zeros the sim assumes), **IMU
frame** (ICM-42688-P axes → trunk frame; needs the IMU integrated), **foot
contact** (no sensors — estimate or retrain without those 4 obs), **safety**
(clamp to limits, ramp from current pose, harness bring-up). See the
sim-to-real reality-check before trusting any of it.

## Provisional / to refine

- **Inertials** are CAD estimates (mesh volume × effective PA6-CF density +
  servo box); the hip tensor is diagonal (its CAD frame is mirror-handed — see
  `build_mjcf.py`). **Weigh the printed links** and rescale (backlog #5).
- **Servo model** — position actuator, now domain-randomized over kp/kv/joint-
  damping **plus control latency** (per-env action delay). Once you measure a
  real STS3215 step response, NARROW the DR ranges around the measured values
  (`env.domain_randomize`) — the biggest remaining transfer-gap closer.
- **Migration:** Brax `PipelineEnv` is in maintenance mode; the actively-
  developed path is **[MuJoCo Playground](https://github.com/google-deepmind/mujoco_playground)**
  (MJX-native locomotion envs + DR). `nova.xml` drops straight into it when you
  want to move over — the model is the reusable asset, the env is the wrapper.
