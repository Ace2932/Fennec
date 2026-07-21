# Colab — NOVA terrain-relative reward PROBE

`fennec_train.ipynb` runs the probe for the terrain-relative reward fix (PR #130): resume the
stairs teacher under the corrected reward and check whether it steps *up* stairs (instead of
scraping the riser) without losing the flat-ground gait.

## Use
1. Open `fennec_train.ipynb` in Colab (github.com → the notebook → "Open in Colab").
2. **`Runtime → Change runtime type → GPU`** (T4 is enough).
3. Run top to bottom. **Cell 1 is the only place you edit paths/knobs** — everything else reads
   from it. `BRANCH` defaults to `main`; set it to `sim/terrain-relative-reward` to test before
   PR #130 merges.
4. Cell 3 prints the git SHA and **asserts the fix is present** — it refuses to run the probe
   against pre-fix code (the "Already up to date → ran stale code" trap that has cost GPU-hours).

## Resumable
Checkpoints are on Drive, so a disconnect loses nothing. The probe cell (8) detects its own
checkpoint on re-run and **resumes** it — it does not re-graft from the teacher, so no progress is
thrown away. Checkpoint choice is by recorded pointer / step number, not mtime (Drive mtimes lie).

## What the cells produce
- **Probe (8)** → `nova_stairs_fix/…` checkpoints + `nova_policy_stairs_fix.pkl` (written
  atomically every eval) + `eval_metrics.csv` (every `eval/*` term + `training/v_loss`).
- **Judge (10)** → `probe_stairs.mp4` / `probe_flat.mp4` **on Drive**. Read the printed
  `traveled +X m in x, climbed +X.XX m in z` line — `climbed` is the verdict.
- **Export (11)** → 226-input `.npz` — a privileged *teacher*, NOT Jetson-deployable (see below).

## Acceptance bar
- **Stairs** (`--stair-level 1.0`): `climbed ≥ +0.16 m` (two real 8 cm risers — the terrain's
  `TZ=0.20` ceiling caps relief there; raising `TZ` + a stair-frac ramp are in the next-run
  backlog) and a full 601-frame episode.
- **Flat** (`--stair-level 0.0 --vx 0.35`): survives all 601 frames (today's teacher falls at
  step 470 here — that regression is the reason for the flat-frac floor).
- **5M kill-switch:** if `swing_h_per_step` hasn't risen on stair envs and `w_slip` hasn't engaged
  by ~5M steps (with `v_loss` plateaued), the probe is doomed — stop and restart clean.

Full design + adjudicated review findings: `../../../docs/superpowers/specs/2026-07-20-terrain-relative-reward-design.md`.

## ⚠ Teacher, not deployable
Obs 226 includes the *perfect* simulated heightmap. The real D456/L2 cannot supply it, so the
exported `.npz` cannot run on the Jetson as-is. Hardware needs real elevation mapping or student
distillation onto proprioception-only obs. The deployable policy remains the flat 105-d one.

## Deps
Pinned in `../requirements.txt` — `brax 0.14.2` + `jax 0.6.0`. The notebook installs the CUDA
build; if the sanity cell reports `backend cpu`, `Runtime → Restart session` and re-run from the
install cell (the clone persists).

The actuator model is the measured STS3215 (velocity cap 2.8/4.71 rad/s, 0.88° deadband, 0.87°
backlash, ~75 ms latency) — see `../../../docs/bench/README.md` and PR #91.
