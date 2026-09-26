# Training on the tower (#411, #412)

The homelab tower (RTX PRO 5000 Blackwell, 48 GB) runs this repo's MJX/Brax
PPO. **Sim only**: the box has no ROS, no serial, no path to the robot. Nothing
under `deploy/` runs here.

## Environment (#411)

`requirements.txt` pins `jax==0.6.0` + `brax==0.14.2` (brax calls
`jax.device_put_replicated`, removed in jax >= 0.7). The tower's own
`~/jax-env` is jax 0.11/cuda13 and is left alone; training uses a separate venv
on cuda12 wheels, which the 610.x driver runs fine:

```bash
uv venv -p 3.12 ~/fennec-train
VIRTUAL_ENV=~/fennec-train uv pip install "jax[cuda12]==0.6.0" brax==0.14.2 \
    "orbax-checkpoint>=0.11.22" mujoco mujoco-mjx imageio imageio-ffmpeg
~/fennec-train/bin/python -c "import jax; print(jax.devices())"   # [CudaDevice(id=0)]
```

Verified 2026-09-25: jax 0.6.0 / brax 0.14.2 / mujoco 3.14.0, GPU visible, and a
headless render works (`MUJOCO_GL=egl rollout.py ...` wrote a 101-frame mp4).
The `Failed to import warp` lines at import are harmless (optional MJX backend).

## Throughput (2M-step fresh stage-1 teacher, `train.py --cmd-stage 1`)

| | envs | steady steps/s | first eval (JIT) | peak VRAM (box total) | eval_reward @2.46M |
|---|---|---|---|---|---|
| Colab T4 | 2048 | ~4,600 (est.: #411's 7.2 h / 120M) | | | |
| tower | **2048** | **~32,000** | ~95 s | 47.9 / 48.9 GB | 615 |
| tower | 8192 | ~29,500 | ~100 s | 47.9 / 48.9 GB | 53 |
| tower | 16384 | — | — | — | brax assert: `batch_size*num_minibatches` (8192) must divide by `num_envs` |

- **Keep 2048.** The GPU is already ~99 % busy at 2048, so 4x the envs buys no
  throughput. At the fixed PPO batch it also learns worse in the same steps
  (53 vs 615 at 2.46M), because each update sees 4x fewer steps per env.
- ~6.9x a T4: the 120M-step lift-v5 curriculum is **~1.05 h** here, not ~7.2 h.
- Checkpoints are ~1.2 MB each (one per eval, ~2.5M steps), so a 70M-step run is ~40 MB.

## Sharing the GPU with Ollama

`XLA_PYTHON_CLIENT_MEM_FRACTION=0.40` (19.6 GB) sits next to the residents.
While training, the box reads 47.9 of 48.9 GB used, so **the other residents
must already be loaded.** A cold `qwen3:8b` (8.1 GiB) will not fit mid-run.
Stop the run first, or lower the fraction if 2048 envs turn out to need less
(not measured).

a3b latency during a run (3 short prompts, 64 tokens): 248 / 286 / 301 tok/s,
0.48-0.58 s total. Idle baseline in tower-state is 310 tok/s. That is 5-20 %
slower, which is noticeable but fine.

## Unattended runs (#412)

```bash
cp tower/fennec-train@.service ~/.config/systemd/user/ && systemctl --user daemon-reload
ln -sf $PWD/tower/fennec-train-status ~/.local/bin/
mkdir -p ~/fennec-runs/<run>
#   ~/fennec-runs/<run>/cmd        the exact command(s), human-written, idempotent
#   ~/fennec-runs/<run>/plan.json  optional: stages for tower/run_plan.py
systemctl --user start fennec-train@<run>
~/.local/bin/fennec-train-status <run>     # plain ssh PATH lacks ~/.local/bin
```

- **Resume = restart.** `train.py` without `--curriculum` retrains its FULL
  `--timesteps` on every invocation, so a restart loop around it would never
  finish. `tower/run_plan.py` sums every attempt's `PROGRESS` in a stage, trains
  only the remainder, and skips finished stages and evals.
- `Restart=on-failure`, `RestartSec=60`, `StartLimitBurst=5`/h (a
  deterministic crash stops instead of looping), `Nice=5`, and
  `OnFailure=tower-alert@`.
- **Noise (homelab#15, shared bedroom):** runs are started by hand, and there's
  no timer. Night runs need an explicit OK. The first was agreed 2026-09-25.
- **Not enabled at boot** until one full run has completed cleanly by hand.
- Layout: `~/fennec-runs/<run>/...`, never `~/repos/*-work` (agents wipe
  those) and never `~/src`.
