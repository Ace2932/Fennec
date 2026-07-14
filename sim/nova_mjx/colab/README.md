# Colab training — NOVA walking policy

`NOVA_train.ipynb` runs the full Tier-1 training loop on a free Colab GPU.

## Use
1. Open `NOVA_train.ipynb` in Colab (github.com → the notebook → "Open in Colab",
   or upload it).
2. **`Runtime → Change runtime type → GPU`** (T4 is enough).
3. Run the cells top to bottom. You'll paste a GitHub PAT (fine-grained, read
   access to `Ace2932/LE_NOVA`) at cell 2 — it's read via `getpass`, not saved.
4. Training (cell 6) writes checkpoints to `Drive/MyDrive/nova_ckpt`.

## Resumable
Colab disconnects don't lose progress — checkpoints are on Drive. Just **re-run
the Train cell**; `train.py` finds the latest checkpoint (by mtime) and continues.
Re-run again to train longer than one invocation's `--timesteps`.

## What each stage produces
- **Train** → `nova_ckpt/run_*/…` checkpoints + `nova_policy.pkl` (latest policy)
  + `train_log.csv` (step, eval_reward).
- **Rollout** → `walk.mp4`, shown inline — eyeball the gait.
- **Export** → `nova_policy.npz` (framework-free, what the Jetson `policy_runner`
  /`policy_node` load) + `nova_policy.onnx`, copied to Drive.

## Deps
Pinned in `../requirements.txt` — `brax 0.14.2` + `jax 0.6.0` is the only window
with both `device_put_replicated` (brax needs it) and `orbax ≥ 0.11.22` support.
The notebook installs the CUDA build. If the sanity cell reports `backend cpu`
after install: `Runtime → Restart session`, then re-run from the install cell
(the clone persists).

## Tuning knobs (in the notebook / files)
- `--timesteps` (cell 6) — more steps = better gait; re-run to add more.
- `--num_envs 2048` — lower if the T4 OOMs.
- rewards / gait shaping — `env.py`.
- terrain difficulty — `terrain.py` `TERRAIN_MAX` (flat first; ramp up once flat
  ground walks).

The actuator model the policy trains against is the measured STS3215 (velocity
cap 2.8/4.71 rad/s, 0.88° deadband, 0.87° backlash, ~75 ms latency) — see
`../../../docs/bench/README.md` and PR #91.
