# Tower training dashboard

**URL (tailnet only): http://100.118.31.63:8765/**

A static page regenerated every 2 min from `~/fennec-runs`. It shows:

- GPU util, VRAM, temp and power.
- Each queue's `fennec-train@` state, restarts and last `[plan]` line.
- The running stage with its rate and ETA. This uses the same accounting as
  `fennec-train-status`.
- A scorecard of every `eval_*.json`, with colored cells.
- Per-variant curves over cumulative steps, with a marker at each stage boundary.
  The curves are reward, forward speed, per-foot air fraction and episode length.
- A traceback box, filled only when a `Traceback` comes after the last `[plan]` line.
- A STALE flag when a unit is active but its newest `train_log.csv` row is more
  than 15 min old.
- A tower health strip: GPU °C, CPU °C and GPU W from `~/fennec-runs/thermal-guard.log`
  (last 24 h), the 90 °C guard limit, and any `THERMAL STOP` line. Long history lives in
  Grafana: http://100.118.31.63:3000/d/tower-metrics/tower (linked from the page).
- Scorecard servo-protection columns when the eval JSON has them: `servos_tripped_end`,
  `slew_clip_frac`, `guard_trip_pct` (red if > 0) and `guard_run_ms_p50/p99/max`.
- Per finished variant, a rollout video and a gait diagram for two courses: flat at
  0.25 m/s, and `probe_curb_height.py`'s 3 cm one-cell ramp at x = 0.4 m. The diagram
  is a footfall timeline (dark = stance, contact = foot height − `FOOT_RADIUS` <
  `CONTACT_EPS`) over a 12-joint duty heatmap (duty = |qfrc_actuator| / (forcerange /
  torque_limit), as in env.py); red cells are ≥ 90 %, the firmware stall-guard threshold.
- `status.json` next to `index.html` (schema 1, a stable contract for the Grafana tower
  hub: one row per variant with `run, variant, stage, steps_done, steps_planned,
  last_eval_reward, running, last_update, done`). Don't rename fields.

## Rollout renders (`render_rollout.py`)

A separate timer (`fennec-dashboard-render.timer`, every 10 min), never the 2-min
generator. A oneshot unit can't overlap itself, so one render runs at a time. Each
run renders every final-stage `policy.pkl` (last plan stage has `DONE`) whose mp4 is
missing or older than the pkl. A failed job writes `<stem>.err`, which the page shows,
and is retried only when the pkl changes. Output: `www/media/<queue>__<variant>__<course>.{mp4,png,json}`.

- **CPU only.** The GPU is full (training + Ollama). The unit sets `JAX_PLATFORMS=cpu`,
  `CUDA_VISIBLE_DEVICES=` and forces Mesa's EGL vendor, so MuJoCo renders on llvmpipe
  (osmesa isn't installed). The process opens no `/dev/nvidia*` device. It runs at
  `Nice=15`, idle CPU and IO class, pinned to cores 24-31. One job takes about 50 s.
- **Code per queue.** Env + nova.xml come from two read-only worktrees pinned to the
  commits the live checkouts train with: `~/fennec-dashboard/simcode-vn` (queue
  `vnext`, sim/v-next) and `~/fennec-dashboard/simcode-gs` (every other queue,
  sim/gait-study). The env is built from the last stage's args (`--asym`, `--ref-gait`,
  `--torque-limit`, `--goal-acc-reg`, `--joint-stale-p`, `--goal-slew`,
  `--overload-model`, ...) so the policy loads. Videos are 640×480 H.264, about 0.2 MB.
- **The pins don't follow the live checkouts.** When a queue's checkout moves, re-pin by hand:
  `git -C ~/fennec-dashboard/simcode-vn checkout --detach "$(git -C ~/codebases/Fennec-vnext rev-parse HEAD)"`
  (likewise `simcode-gs` from `~/codebases/Fennec`). To re-render, delete the media files.

## What it can and can't touch

- `dashboard.py` is stdlib only. It runs on `/usr/bin/python3`, not the training venv.
- It only reads `~/fennec-runs`, and it never imports the training code.
- It writes only `~/fennec-dashboard/www/index.html` and `status.json`. The writes are
  atomic, so a half-written file is never served.
- The server is `python3 -m http.server`, bound to the Tailscale IP only, never
  `0.0.0.0`. The page holds numbers, paths and log lines, and no secrets.
- There is no sudo. Everything runs as systemd **user** units, which is fine
  because `Linger=yes` for aiden.

## Install (on the tower, from a checkout of this dir)

```bash
mkdir -p ~/fennec-dashboard/www/media ~/.config/systemd/user
cp dashboard.py render_rollout.py ~/fennec-dashboard/
cp fennec-dashboard.service fennec-dashboard-gen.service fennec-dashboard-gen.timer \
   fennec-dashboard-render.service fennec-dashboard-render.timer ~/.config/systemd/user/
# read-only sim code for the renders (never the live checkouts); pin to what each queue trains
git -C ~/codebases/Fennec worktree add --detach ~/fennec-dashboard/simcode-gs "$(git -C ~/codebases/Fennec rev-parse HEAD)"
git -C ~/codebases/Fennec worktree add --detach ~/fennec-dashboard/simcode-vn "$(git -C ~/codebases/Fennec-vnext rev-parse HEAD)"
/usr/bin/python3 ~/fennec-dashboard/dashboard.py --selftest
/usr/bin/python3 ~/fennec-dashboard/render_rollout.py --selftest
systemctl --user daemon-reload
systemctl --user enable --now fennec-dashboard.service fennec-dashboard-gen.timer fennec-dashboard-render.timer
systemctl --user list-timers | grep fennec-dashboard
```

Deploy from the Mac with `scp dashboard.py render_rollout.py tower:fennec-dashboard/`. Do not run it
from `~/codebases/Fennec` on the tower. That checkout belongs to the live training
queue.

## Uninstall

```bash
systemctl --user disable --now fennec-dashboard.service fennec-dashboard-gen.timer fennec-dashboard-render.timer
rm ~/.config/systemd/user/fennec-dashboard{.service,-gen.service,-gen.timer,-render.service,-render.timer}
systemctl --user daemon-reload
git -C ~/codebases/Fennec worktree remove ~/fennec-dashboard/simcode-gs
git -C ~/codebases/Fennec worktree remove ~/fennec-dashboard/simcode-vn
rm -r ~/fennec-dashboard
```

## Notes on the data

- Air and speed columns in `eval_metrics.csv` are episode **sums**, so the curves
  divide them by `avg_episode_length`. An air fraction near 1 means the leg is
  carried. Near 0 means it is dragged.
- `episode_airT_*` equals `episode_air_*` in every file checked.
- `eval_metrics.csv` has a `stage` column, which is `run_<ts>` or
  `stage<i>_t<lvl>`. The x offset for each label is the PROGRESS banked by the
  labels before it. That offset is not the previous label's last logged step. For
  example, a crash after the 6.39M eval but before that checkpoint resumes from
  4.26M, and the curve shows that rollback.
