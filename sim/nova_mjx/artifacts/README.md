# Sim artifacts

Everything the sim probes and renderers *write*, kept out of the source tree so a
diff of `sim/nova_mjx/` shows code rather than PNGs.

**All of it is regenerable** — nothing here is an input. If a file looks stale or
you are unsure it matches the current code, delete it and re-run the producer.

| folder | produced by | what it is |
|---|---|---|
| `climber_out/` | `scripted_crawl_climber.py` (`--out-dir`) | per-run `traces_*.png`, `climb_*.mp4`, sampled `frames_*/`. Tagged by stair level and by any non-default flag (`_eff`, `_kp`, `_splay`, `_ab`, `_clr`, knee config), so runs do not overwrite each other. |
| `knee_config_views/` | `render_knee_configs.py` | side-by-side of the three knee configurations. The evidence that the robot is TRANSLATED — knee offset vs the hip→foot chord is −66.0 mm on all four legs. |
| `sit_pose_views/` | `render_sit_poses.py` | the asymmetric sit and belly-down poses, settled under gravity through the real position servos. |
| `standup_views/` | `probe_standup.py` | stand-up recovery filmstrips from sit and from belly-down. |

Regenerate:

```bash
cd sim/nova_mjx
MUJOCO_GL=cgl JAX_PLATFORMS=cpu ../../.venv/bin/python render_knee_configs.py
MUJOCO_GL=cgl JAX_PLATFORMS=cpu ../../.venv/bin/python render_sit_poses.py
MUJOCO_GL=cgl JAX_PLATFORMS=cpu ../../.venv/bin/python probe_standup.py
JAX_PLATFORMS=cpu ../../.venv/bin/python scripted_crawl_climber.py --stair-level 0.25 --steps 3500 --no-render
```

Probes that print only (no artifacts): `probe_lift_force.py`, `probe_lift_envelope.py`,
`probe_posture_search.py`, `probe_sitdown.py`.
