# Trained policies — drop them here

Unlike the rest of `artifacts/`, **these are inputs, not outputs.** Nothing in
this repo produces them: training runs in Colab (`../../colab/fennec_train.ipynb`)
and writes checkpoints to Drive. This folder exists so a downloaded checkpoint
has one obvious home instead of `~/Downloads`.

The binaries are gitignored. This README is not.

## What to drop

| file | from | what it is |
|---|---|---|
| `nova_policy_stairs_fix.pkl` | Colab cell 8 (probe), written atomically every eval | the PPO params `rollout.py --policy` wants |
| `eval_metrics.csv` | Colab cell 8 | every `eval/*` term + `training/v_loss`, per eval |
| `*.npz` | Colab cell 11 (export) | 226-input **teacher** export — see the warning below |

Checkpoint choice on Drive is **by recorded pointer / step number, not mtime** —
Drive mtimes lie (`../../colab/README.md`).

## Render a walk

```bash
cd sim/nova_mjx
../../.venv/bin/python rollout.py \
    --policy artifacts/policies/nova_policy_stairs_fix.pkl \
    --vx 0.35 --stair-level 0.0 --steps 601 \
    --out artifacts/policies/walk_flat.mp4
```

`--stair-level 0.0` is flat standard MuJoCo ground. No `MUJOCO_GL` needed — the
script picks `cgl` on macOS, EGL elsewhere.

Stairs instead: `--stair-level 1.0`. Read the printed
`traveled +X m in x, climbed +X.XX m in z` line; `climbed` is the verdict.

## What "walks cleanly" means

From `../../colab/README.md`'s acceptance bar:

- **Flat** (`--stair-level 0.0 --vx 0.35`): survives all **601 frames**.
- **Stairs** (`--stair-level 1.0`): `climbed ≥ +0.16 m` and a full 601-frame episode.

⚠️ That same README records **"today's teacher falls at step 470"** on flat. So a
short clip can look clean while the episode still fails the bar. Run the full 601
and check it survives before calling it a clean walk — a video that stops at 400
frames is not evidence.

## Two things that make a good-looking video wrong

1. **The `.npz` export is a privileged TEACHER, not deployable.** Its 226-input
   obs includes the *perfect* simulated heightmap. The real D456/L2 cannot supply
   that, so a video of it is not a video of what the robot can do.
2. **The normalizer gotcha.** Training uses `normalize_observations=True`;
   `make_ppo_networks` defaults to an identity preprocessor, which silently
   ignores the pickled normalizer and feeds raw obs. `rollout.py` handles this
   now — but its own comment records that **every earlier rollout video rendered
   a mis-driven policy.** If you find an old mp4 lying around, do not trust it.


## Lineage sweep + a checkpoint-identity correction (2026-08-08)

⚠️ **`nova_policy_hm234.pkl` and `nova_policy_hm227.pkl` are NOT trained artifacts.**
Verified on the first-layer kernels: their first 226 rows are bitwise identical to
`nova_policy_hm`, and every added row is zero. They are `graft_obs.py` outputs —
the 300M flat walker widened to 234/227 dims — and the training that was meant to
follow never landed back in these filenames. `stairs_final` / `climb` /
`climb_reward` ARE trained (max|dW| vs hm = 0.40 / 0.34 / —).

**Consequence: the "newest file on Drive" is the oldest policy.** Choose by
recorded pointer or by weight comparison, never by name or mtime.

### Flat, vx = 0.35, 8 paired episodes, nominal dynamics (older ones grafted to 234)

| checkpoint | fell | speed | % of cmd | distance |
|---|---|---|---|---|
| **`nova_policy_hm`** (flat walker) | **0.0 %** | +0.346 | **99 %** | +2.215 m |
| `hm227`, `hm234` (= hm, grafted) | 0.0 % | +0.346 | 99 % | +2.215 m |
| `climb_reward` | 37.5 % | +0.378 | 108 % | +2.334 m |
| `stairs_final` | 75.0 % | +0.396 | 113 % | +2.453 m |
| `climb` | 75.0 % | +0.408 | 117 % | +2.493 m |

The stairs campaign **traded flat robustness for speed** — trained descendants
over-track by 8–17 % and fall in 3 of 4 episodes; the ancestor tracks to 99 % and
never falls.

⚠️ **The "falls 50 % of episodes" figure elsewhere in this repo is at vx = 0.50.**
At vx = 0.35 the same policy does not fall at all. Quote the command with the
number.

**For first hardware motion, use `nova_policy_hm`.**
