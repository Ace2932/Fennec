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

## What it can and can't touch

- `dashboard.py` is stdlib only. It runs on `/usr/bin/python3`, not the training venv.
- It only reads `~/fennec-runs`, and it never imports the training code.
- It writes only `~/fennec-dashboard/www/index.html`. The write is atomic, so a
  half-written page is never served.
- The server is `python3 -m http.server`, bound to the Tailscale IP only, never
  `0.0.0.0`. The page holds numbers, paths and log lines, and no secrets.
- There is no sudo. Everything runs as systemd **user** units, which is fine
  because `Linger=yes` for aiden.

## Install (on the tower, from a checkout of this dir)

```bash
mkdir -p ~/fennec-dashboard/www ~/.config/systemd/user
cp dashboard.py ~/fennec-dashboard/
cp fennec-dashboard.service fennec-dashboard-gen.service fennec-dashboard-gen.timer ~/.config/systemd/user/
/usr/bin/python3 ~/fennec-dashboard/dashboard.py --selftest
systemctl --user daemon-reload
systemctl --user enable --now fennec-dashboard.service fennec-dashboard-gen.timer
systemctl --user list-timers | grep fennec-dashboard
```

Deploy from the Mac with `scp dashboard.py tower:fennec-dashboard/`. Do not run it
from `~/codebases/Fennec` on the tower. That checkout belongs to the live training
queue.

## Uninstall

```bash
systemctl --user disable --now fennec-dashboard.service fennec-dashboard-gen.timer
rm ~/.config/systemd/user/fennec-dashboard{.service,-gen.service,-gen.timer}
systemctl --user daemon-reload
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
