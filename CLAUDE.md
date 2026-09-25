# Fennec — Autonomous Quadruped

Solo hardware/robotics project by Aiden. Quadruped built on the Nova-SM3 platform, redesigned for
STS3215 (Feetech) servos + Unitree L2 LiDAR + Jetson Orin Nano / ROS 2 Humble. CAD + firmware +
custom power/logic PCBs + MJX sim. (Repo was called NOVA; code, packages and memory still say `nova`.)

Live state: `STATUS.md` (blockers / next actions). Bench/solder state is mirrored from Notion and
lags it — check the edit date on both before trusting either.

## Joint naming (haa / hfe / kfe)

Standard quadruped convention (as ANYmal / Unitree / MIT Cheetah). 3 joints per leg, 12 total.
Canonical map: `ros2_ws/src/nova_description/config/joint_id_map.yaml`.

| name | stands for | motion | axis |
|---|---|---|---|
| `haa` | hip abduction/adduction | swings the whole leg **sideways** — splay outboard, or tuck inboard under the body | fore-aft (x) |
| `hfe` | hip flexion/extension | swings the thigh **fore/aft** — the main walking stroke | lateral (y) |
| `kfe` | knee flexion/extension | bends the **knee** | lateral (y) |

IDs are per-leg sequential, always haa → hfe → kfe:
`FL` 1-3, `FR` 4-6, `RL` 7-9, `RR` 10-12. Legs are `F/R` (front/rear) + `L/R` (left/right).

**Why the split matters for signs/frames:** left↔right is a mirror about the xz plane. `haa`'s
axis is fore-aft, which the mirror leaves alone → all four hips share one `urdf_sign`, and only
the *inboard direction* flips by side. `hfe`/`kfe` axes are lateral — the direction the mirror
*does* flip → their `urdf_sign` differs left vs right. The rear hips are the front placement
**yawed 180°**, so leg-local → canonical hfe bounds are negated at the rear. Getting this
backwards is the dominant bug class here; see `~/claude-memory/patterns/interface-boundary-bugs.md`.

**`haa` carries the hardware risk:** inboard tucks a leg under the belly where the LiPo sits, so
haa stays clamped to a conservative ±15° until the servo sign is confirmed at homing.

## Layout

- `ros2_ws/` — ROS 2 (humble) workspace: `nova_ops`, `nova_locomotion`, `nova_calibration`, `nova_description`.
- `firmware/` — `teensy/` (main controller, PlatformIO + micro-ROS), `arduino-nano/`.
- `hardware/` — `cad/` (active: `leg_v6/`, `chassis/`, `lib/`), `wiring/`, `pcb-mods/` (KiCad).
- `sim/nova_mjx/` — MuJoCo MJX + Brax PPO. Trained policies in `artifacts/policies/` are gitignored inputs.
- `scripts/`, `deploy/` — flashing, servo IDs, Jetson setup.
- `docs/` — design outline, power budget, order list, checklists. `README.md`, `BOM.md` — primary references.

Outside this repo, in `~/codebases/NOVA/` (separate root repo, not ours to edit): `original_body_files/`
(stock Nova-SM3 STLs — source of truth for CAD mods), `nova-sm3-upstream/` (reference, don't edit),
`feetech_servo_models/`, `Unitree_LiDAR/`, `proj_videos/`. Only legacy `leg_v5*`/`archive` scad
reads them by absolute path. **CAD gates must not reach outside the repo** — vendor inputs via
`hardware/cad/cad_assets.py` (#166).

## Active PCBs

`hardware/pcb-mods/nova_pcb_v6_power_v2/` (power) and `hardware/pcb-mods/nova_pcb_v6_logic/` (logic).
Both fabbed (JLCPCB, 2026-07-01) and being hand-populated: canonical sequence is
`hardware/pcb-mods/BUILD_PLAN.md`. Physical boards == current files — don't edit copper on v6; v7
changes go in issues. `.bak` files = staged checkpoints (preroute/prepour/…), gitignored — don't delete.
See the `pcb-design` skill before touching.

## Toolchain (macOS, Darwin arm64)

- Python: `.venv/bin/python` (3.12, uv). See Tests for the PYTHONPATH (`.` alone does NOT work).
- KiCad CLI: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
  - pcbnew python: `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`
- OpenSCAD: `/opt/homebrew/bin/openscad` (arm64).
- Firmware: PlatformIO (`pio run`) in `firmware/teensy/firmware/`.

## Tests

ROS pkg tests, from the repo root. **`PYTHONPATH=.` does NOT work** (`ModuleNotFoundError: No
module named 'nova_ops'`); each package dir must be on the path:
```
S=ros2_ws/src
PYTHONPATH=$S/nova_ops:$S/nova_locomotion:$S/nova_calibration:$S/nova_description \
  .venv/bin/python -m pytest $S/nova_ops/test $S/nova_locomotion/test $S/nova_calibration/test -q
```
406 pass, 0 skipped (2026-09-25, after #420 #422 #426).

**No `--ignore`.** `test_preflight` used to be excluded here and in CI because importing the
preflight registry pulled in `rclpy`, so it ran nowhere and went red unseen (#187). The checks now
defer ROS imports into `run()`. Re-adding an `--ignore` rebuilds that hole.

CAD gates (not pytest; `hardware/cad/leg_v6/build_all.sh`, aborts on failure): `check_fit.py --sweep`
(ROM/fit authority), `check_shoe.py`, `servo_orientation_gate.py`. CI: `.github/workflows/`
(`ros-pytest`, `cad-gates`, `firmware-compile`, `sim-tests`).

## Git

- One repo, `Ace2932/Fennec`. Work on a branch, PR to `main`; squash-merge.
- A stacked PR is CLOSED (not retargeted) when its base branch is deleted on merge — rebase
  `--onto main` and open fresh.
- `archive/nova-proj/*` local branches: unpushed work carried over from the retired
  `~/codebases/NOVA/proj` clone (2026-09-25). Not yet triaged.
- STLs are tracked as plain binaries (no LFS).

## Conventions

- Read STL/CAD source before modifying; never edit upstream or `original_body_files/` in place.
- Onshape CAD via `jarvis-onshape-mcp` plugin (see `onshape` skill).
- Superseded doc claims are annotated inline, never deleted (so a vanished red flag doesn't
  teach you to distrust the next one).
- Memory: `~/claude-memory/nova-proj/` (git-backed). Commit after meaningful changes.
