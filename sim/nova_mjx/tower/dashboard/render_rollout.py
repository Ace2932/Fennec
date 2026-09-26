#!/usr/bin/python3
"""Render rollout videos + gait diagrams for the dashboard, one at a time, CPU only.

    /usr/bin/python3 render_rollout.py --queue          # render every missing/stale job
    /usr/bin/python3 render_rollout.py --selftest

Queue mode is stdlib: it scans ~/fennec-runs for variants whose LAST plan stage has
DONE + policy.pkl, and for each course (flat, curb) whose mp4 is missing or older
than the pkl it runs ONE job in a child process under the training venv:

    <venv python> render_rollout.py --job VARIANT_DIR COURSE CODE_DIR OUT_DIR

The job imports the sim env from CODE_DIR (a read-only worktree pinned to the code
that queue trains with), builds it with the last stage's physics/obs flags, rolls
the deterministic policy out for 8 s at a fixed 0.25 m/s forward command, and
writes <queue>__<variant>__<course>.{mp4,png,json} into OUT_DIR. A failed job
writes .err instead, so it is not retried until the pkl changes.

The unit (fennec-dashboard-render.service) sets JAX_PLATFORMS=cpu,
CUDA_VISIBLE_DEVICES= and Mesa's EGL vendor (llvmpipe, software GL), so neither
the rollout nor the render can allocate GPU memory next to a training run.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

COURSES = ("flat", "curb")
VX, SECONDS, FPS_OUT = 0.25, 8.0, 25
CURB_H = 0.03                 # probe_curb_height: 3 cm one-cell ramp at CURB_X
GUARD = 0.9                   # firmware stall guard: >= 90 % duty (NOVA_STALL_LOAD_RAW 900)
BOOL_FLAGS = {"--asym": "asym", "--ref-gait": "ref_gait", "--overload-model": "overload_model",
              "--heightmap": "heightmap"}
VAL_FLAGS = {"--torque-limit": ("torque_limit", float), "--ref-height": ("ref_height", float),
             "--joint-stale-p": ("joint_stale_p", float), "--goal-slew": ("goal_slew", float),
             "--cmd-stage": ("cmd_stage", int), "--goal-acc-reg": ("goal_acc_reg", int)}


def env_kwargs(args):
    """Last-stage train args -> NovaJoystick kwargs that change obs size or physics."""
    kw = {}
    for i, a in enumerate(args):
        if a in BOOL_FLAGS:
            kw[BOOL_FLAGS[a]] = True
        elif a in VAL_FLAGS and i + 1 < len(args):
            k, t = VAL_FLAGS[a]
            kw[k] = t(args[i + 1])
    return kw


def jobs(runs, out, code_for):
    """(variant_dir, course, code_dir, stem) for every final policy whose media is stale."""
    todo = []
    for plan in sorted(runs.glob("*/*/plan.json")):
        v = plan.parent
        try:
            last = json.loads(plan.read_text())["stages"][-1]["name"]
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            continue
        pkl = v / last / "policy.pkl"
        if not ((v / last / "DONE").exists() and pkl.exists()):
            continue
        for course in COURSES:
            stem = f"{v.parent.name}__{v.name}__{course}"
            done = [out / f"{stem}.mp4", out / f"{stem}.err"]
            if any(p.exists() and p.stat().st_mtime > pkl.stat().st_mtime for p in done):
                continue
            todo.append((v, course, code_for(v.parent.name), stem))
    return todo


# ------------------------------------------------------------ the job (venv) --

def run_job(vdir, course, code, out):
    vdir, code, out = pathlib.Path(vdir), pathlib.Path(code), pathlib.Path(out)
    stem = f"{vdir.parent.name}__{vdir.name}__{course}"
    t0 = time.time()
    os.chdir(code)                              # env.py loads nova.xml relative to cwd
    sys.path.insert(0, str(code))
    import inspect
    import jax
    import jax.numpy as jp
    import mujoco
    import numpy as np
    import imageio
    import env as E
    from eval_gait import load_policy

    stage = json.loads((vdir / "plan.json").read_text())["stages"][-1]
    kw = env_kwargs(stage.get("args", []))
    if "goal_acc_reg" in kw:
        kw["goal_acc"] = E.goal_acc_rad(kw.pop("goal_acc_reg"))
    allowed = inspect.signature(E.NovaJoystick.__init__).parameters
    kw = {k: v for k, v in kw.items() if k in allowed}
    env = E.NovaJoystick(**kw)
    field = None
    if course == "curb":
        from probe_curb_height import curb_field
        field = curb_field(env, CURB_H)
        env.sys = env.sys.tree_replace({"hfield_data": field})
    policy = jax.jit(load_policy(str(vdir / stage["name"] / "policy.pkl"), env, kw.get("asym", False)))
    cmd = jp.array([VX, 0.0, 0.0])
    stall = env.sys.actuator_forcerange[:, 1] / env._torque_limit
    ground = getattr(env, "_terrain_ground_z", None)

    @jax.jit
    def step(s, k):
        a, _ = policy(s.obs, k)
        s = env.step(s, a)
        s = s.replace(info={**s.info, "cmd": cmd})
        ps = s.pipeline_state
        foot = ps.x.pos[env._foot_ids]
        gz = ground(foot[:, 0], foot[:, 1]) if ground else 0.0
        contact = (foot[:, 2] - gz - E.FOOT_RADIUS) < E.CONTACT_EPS
        duty = jp.abs(ps.qfrc_actuator[6:]) / stall
        return s, (ps.q, contact, duty, s.done)

    rng = jax.random.PRNGKey(0)
    s = jax.jit(env.reset)(rng)
    s = s.replace(info={**s.info, "cmd": cmd})
    qs, cs, ds = [np.asarray(s.pipeline_state.q)], [], []
    fell = None
    n = int(round(SECONDS / float(env.dt)))
    for i in range(n):
        rng, k = jax.random.split(rng)
        s, (q, c, d, done) = step(s, k)
        qs.append(np.asarray(q)); cs.append(np.asarray(c)); ds.append(np.asarray(d))
        if float(done) > 0.5:
            fell = i + 1
            break
    t_sim = time.time() - t0

    m = mujoco.MjModel.from_xml_path("nova.xml")
    if field is not None:
        m.hfield_data[:] = np.asarray(field)
    dd = mujoco.MjData(m)
    every = max(1, int(round(1 / (float(env.dt) * FPS_OUT))))
    tmp = out / f".{stem}.tmp.mp4"
    with mujoco.Renderer(m, height=480, width=640) as r, imageio.get_writer(
            tmp, fps=1 / (float(env.dt) * every), codec="libx264", pixelformat="yuv420p", macro_block_size=None,
            ffmpeg_params=["-crf", "30", "-preset", "slow", "-movflags", "+faststart"]) as w:
        for q in qs[::every]:
            dd.qpos[:] = q
            mujoco.mj_forward(m, dd)
            r.update_scene(dd, camera=m.camera("track").id)
            w.append_data(r.render())
    os.replace(tmp, out / f"{stem}.mp4")

    names = [m.joint(j).name for j in range(m.njnt) if m.jnt_type[j] != mujoco.mjtJoint.mjJNT_FREE]
    C, D = np.array(cs, bool), np.array(ds, float)
    summary = {
        "variant": f"{vdir.parent.name}/{vdir.name}", "course": course, "code": str(code),
        "policy_mtime": (vdir / stage["name"] / "policy.pkl").stat().st_mtime,
        "env_kwargs": {k: v for k, v in kw.items()}, "dt": float(env.dt), "vx_cmd": VX,
        "steps": len(cs), "fell_step": fell,
        "x_travel_m": float(qs[-1][0] - qs[0][0]),
        "stance_frac": [float(x) for x in C.mean(0)],
        "duty_max": [float(x) for x in D.max(0)],
        "guard_cells_pct": float(100 * (D >= GUARD).mean()),
        "joints": names[:D.shape[1]],
        "gl": os.environ.get("MUJOCO_GL"), "sim_s": round(t_sim, 1),
        "total_s": round(time.time() - t0, 1),
    }
    gait_png(C, D, summary, out / f"{stem}.png")
    (out / f"{stem}.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))


def gait_png(C, D, meta, path):
    """Footfall timeline (dark = stance) over a per-joint duty heatmap (red = >= GUARD)."""
    from PIL import Image, ImageDraw
    T = C.shape[0]
    px = max(1, 800 // max(T, 1))
    L, top, fh, jh = 70, 22, 16, 11
    W = L + T * px + 10
    H = top + 4 * fh + 18 + D.shape[1] * jh + 30
    im = Image.new("RGB", (W, H), "white")
    g = ImageDraw.Draw(im)
    g.text((4, 4), f"{meta['variant']} {meta['course']}  footfall (dark=stance)  "
                   f"fell={meta['fell_step']}  dx={meta['x_travel_m']:+.2f} m", fill="black")
    for i, ft in enumerate(("FL", "FR", "RL", "RR")):
        y = top + i * fh
        g.text((4, y + 2), f"{ft} {100 * C[:, i].mean():.0f}%", fill="black")
        for t in range(T):
            g.rectangle([L + t * px, y, L + (t + 1) * px - 1, y + fh - 2],
                        fill=(40, 40, 40) if C[t, i] else (225, 225, 225))
    y0 = top + 4 * fh + 16
    g.text((4, y0 - 14), f"joint duty |tau|/(stall/TL), 0 white -> 1 blue, red = >= {GUARD:.0%} "
                         f"(fw stall guard): {meta['guard_cells_pct']:.1f}% of cells", fill="black")
    for j in range(D.shape[1]):
        y = y0 + j * jh
        g.text((4, y), meta["joints"][j][:11] if j < len(meta["joints"]) else str(j), fill="black")
        for t in range(T):
            d = float(D[t, j])
            col = (220, 30, 30) if d >= GUARD else tuple(int(255 - (255 - c) * min(d, 1.0))
                                                         for c in (30, 80, 200))
            g.rectangle([L + t * px, y, L + (t + 1) * px - 1, y + jh - 2], fill=col)
    g.text((L, H - 14), f"0 s", fill="black")
    g.text((W - 50, H - 14), f"{T * meta['dt']:.1f} s", fill="black")
    im.save(path)


# ------------------------------------------------------------------ queue ----

def queue(runs, out, venv, code_gs, code_vn):
    out.mkdir(parents=True, exist_ok=True)
    code_for = lambda q: code_vn if q == "vnext" else code_gs
    # ponytail: queue->code map is hardcoded (vnext -> sim/v-next, rest -> gait-study);
    # move it into each queue's cmd if a third code line appears.
    while True:
        todo = jobs(runs, out, code_for)
        if not todo:
            print("nothing to render")
            return
        v, course, code, stem = todo[0]
        print(f"render {stem} with {code}", flush=True)
        t = time.time()
        p = subprocess.run([venv, __file__, "--job", str(v), course, str(code), str(out)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            (out / f"{stem}.err").write_text(p.stdout[-2000:] + "\n" + p.stderr[-6000:])
            print(f"  FAILED rc={p.returncode} ({time.time() - t:.0f} s), see {stem}.err")
        else:
            (out / f"{stem}.err").unlink(missing_ok=True)
            print(f"  ok in {time.time() - t:.0f} s")


def selftest():
    import tempfile
    assert env_kwargs(["--cmd-stage", "2", "--asym", "--torque-limit", "0.8",
                       "--goal-acc-reg", "75", "--curriculum", "--terrain", "0.75"]) == \
        {"cmd_stage": 2, "asym": True, "torque_limit": 0.8, "goal_acc_reg": 75}
    with tempfile.TemporaryDirectory() as td:
        runs, out = pathlib.Path(td) / "runs", pathlib.Path(td) / "out"
        out.mkdir()
        for name, done in (("A", True), ("B", False)):
            v = runs / "q" / name
            (v / "s2").mkdir(parents=True)
            (v / "plan.json").write_text('{"stages":[{"name":"s1"},{"name":"s2"}]}')
            (v / "s2" / "policy.pkl").write_text("x")
            if done:
                (v / "s2" / "DONE").write_text("1")
        cf = lambda q: pathlib.Path("/code")
        assert [j[3] for j in jobs(runs, out, cf)] == ["q__A__flat", "q__A__curb"]   # B unfinished
        (out / "q__A__flat.mp4").write_text("v")
        (out / "q__A__curb.err").write_text("e")
        assert jobs(runs, out, cf) == []                                          # both cached
        pkl = runs / "q" / "A" / "s2" / "policy.pkl"
        os.utime(pkl, (time.time() + 60, time.time() + 60))                      # retrained
        assert len(jobs(runs, out, cf)) == 2
    print("selftest OK")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if argv[:1] == ["--job"]:
        return run_job(*argv[1:5])
    home = pathlib.Path.home()
    args = dict(zip(argv[1::2], argv[2::2])) if argv[:1] == ["--queue"] else {}
    queue(pathlib.Path(args.get("--runs", home / "fennec-runs")),
          pathlib.Path(args.get("--out", home / "fennec-dashboard/www/media")),
          args.get("--venv", str(home / "fennec-train/bin/python")),
          pathlib.Path(args.get("--code-gs", home / "fennec-dashboard/simcode-gs/sim/nova_mjx")),
          pathlib.Path(args.get("--code-vn", home / "fennec-dashboard/simcode-vn/sim/nova_mjx")))


if __name__ == "__main__":
    main(sys.argv[1:])
