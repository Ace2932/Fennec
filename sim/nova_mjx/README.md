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
pip install mujoco mujoco-mjx "jax[cpu]" brax
python build_mjcf.py          # -> nova.xml
python validate_model.py      # -> "STANDS ✓"
JAX_PLATFORMS=cpu python -c "import jax,jax.numpy as jp; from env import NovaJoystick; \
  e=NovaJoystick(); s=jax.jit(e.reset)(jax.random.PRNGKey(0)); \
  print('obs',s.obs.shape); print('step ok', jax.jit(e.step)(s, jp.zeros(12)).reward)"
```

The env builds + steps on CPU (obs dim 45, 12 actions) — good enough to confirm
correctness. **Do not train on CPU** (too slow).

## 2. Train on Colab (free T4 GPU)

New Colab notebook, **Runtime → change type → T4 GPU**, then:

```python
!pip install -q mujoco mujoco-mjx brax          # Colab already has CUDA jax
# upload build_mjcf.py, env.py, train.py  (Files panel, or clone the repo)
!python build_mjcf.py
!python train.py --timesteps 60_000_000 --num_envs 2048 --out nova_policy.pkl
```

~60 M steps trains a first walking gait in roughly 20–40 min on a T4. Watch
`eval_reward` climb. `nova_policy.pkl` is the trained params — download it.

Scale `--timesteps` up (150 M+) for a cleaner gait once the reward shape looks
right; tune the reward weights in `env.py` (`step`).

## 3. Domain randomization = robustness + "unfinished build" insurance

`env.domain_randomize` jitters floor friction, trunk mass, and per-joint gains
every env. That is the sim-to-real bridge **and** it means you can train **now**,
before the final masses are weighed — the policy learns to be robust to a range
of dynamics, so it survives the real build's variance. Widen the ranges (add
link-mass and CoM jitter, latency, push perturbations) as you get closer to
hardware.

## 4. Deploy to the Jetson (later)

Export the Brax policy → ONNX/TorchScript, run it as a `nova_locomotion` policy
node: read joint state + IMU + `cmd_vel`, build the 45-d obs exactly as `env.py`
does, run inference at 50 Hz, write the 12 joint targets to `/joint_commands`
(via the `joint_id_map.yaml`). Keep the scripted trot as the safety fallback.

## Provisional / to refine

- **Inertials** are CAD estimates (mesh volume × effective PA6-CF density +
  servo box); the hip tensor is diagonal (its CAD frame is mirror-handed — see
  `build_mjcf.py`). **Weigh the printed links** and rescale (backlog #5).
- **Servo model** is a position actuator (`kp=35`) — measure the real STS3215
  step response and match `kp/kv/forcerange`; DR over them meanwhile.
- **Migration:** Brax `PipelineEnv` is in maintenance mode; the actively-
  developed path is **[MuJoCo Playground](https://github.com/google-deepmind/mujoco_playground)**
  (MJX-native locomotion envs + DR). `nova.xml` drops straight into it when you
  want to move over — the model is the reusable asset, the env is the wrapper.
