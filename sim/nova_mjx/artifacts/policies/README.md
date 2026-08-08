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


## Provenance — what was pulled, 2026-08-08

Recorded because "which checkpoint is this" was previously unanswerable: training
runs in Colab, artifacts live on Drive, and Drive mtimes lie.

| file | md5 | Drive created | obs width | usable? |
|---|---|---|---|---|
| `nova_policy_hm234.pkl` | `af577941dbcda2809666e3bb1b9452f6` | 2026-07-25 03:57 | **234** | ✅ matches today's teacher env |
| `nova_policy_stairs_fix.pkl` | `fedc030d685ee0e745782e6523c8283e` | 2026-07-21 01:34 | **226** | ❌ STALE — env now emits 234, normalizer shape-mismatches |

⚠️ **Both are tier-2 PRIVILEGED TEACHERS, not deployable policies.** 234 = the
105-d blind vector + an 11x11 perfect height map (+8 further privileged terms).
`deploy/policy_runner.py` — and the whole #289 bridge — takes **105**. There is
no blind student on Drive at all; distilling one is unbuilt work and it sits
between the merged bridge and any policy running on hardware.

Run either with `--heightmap`, or the env builds blind and the shapes will not
meet:

    ../../.venv/bin/python rollout.py --policy artifacts/policies/nova_policy_hm234.pkl \
        --heightmap --vx 0.35 --stair-level 0.0 --steps 601 --out artifacts/policies/walk_flat.mp4

Measured on the CURRENT (post-8e2927a) geometry: **traveled +2.54 m in 8.5 s,
then fell at step 427** of 601. The gait reproduces; this checkpoint is not
robust, which is a separate matter from the seam (see below).

## Retrain question — ANSWERED 2026-08-08, no retrain

`ab_seam.py --policy artifacts/policies/nova_policy_hm234.pkl --heightmap
--episodes 12 --steps 400`, three arms, paired seeds:

| arm | FL foot x | fell | return | travel |
|---|---|---|---|---|
| train (x=0.0) | +141.20 mm | 50.0 % | 842.52 | +2.297 m |
| **real (x=0.0116)** | **+129.60 mm** | **33.3 %** | **792.96** | **+2.173 m** |
| control (x=0.058) | +83.20 mm | 100.0 % | 46.68 | +0.384 m |

real vs train: return **-5.9 %** (95 % CI [-87.76, -9.78]), fall-rate **-16.7 pts**
(CI [-50.0, +16.7], spans zero). Control vs train: return **-94.5 %**, fall-rate
**+50 pts** — the positive control degrades hard, so the null is informative and
not just a blind harness.

**Deploy the existing checkpoint against the corrected geometry.** Note the
return delta's CI excludes zero, so the effect is real but small and inside the
+-10 % bar; the fall rate actually improved. SCOPE: nominal dynamics, no domain
randomization, flat, one command (+0.50 m/s) — it answers "does the trained gait
survive the geometry change", NOT "does it transfer to hardware".
