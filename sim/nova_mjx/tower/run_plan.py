"""Budget-aware, crash-resumable driver for a multi-stage training plan (#412).

    python tower/run_plan.py ~/fennec-runs/<run>/plan.json

plan.json:
  {"stages": [{"name": "s1", "timesteps": 40000000, "args": ["--cmd-stage", "1"]},
              {"name": "s2", "timesteps": 30000000, "args": ["--cmd-stage", "2"],
               "init": "s1"}],
   "evals": [{"name": "fw", "args": ["--eval-goal-acc-reg", "50"]}],
   "eval_args": ["--asym"]}

Each stage trains into <run>/<name>/. Re-running the SAME command is the
resume: a stage's done steps are summed from every attempt's PROGRESS pointer
(train.py writes one run_<ts>/ per attempt, each counting only itself), only the
remainder is trained, and a finished stage is skipped. A stage with "init"
starts from that stage's policy.pkl (or an absolute .pkl path) on its FIRST attempt only; later attempts
resume their own checkpoint. Evals (eval_gait.py) run once each, written to
<run>/eval_<name>.json, skipped if present.
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent          # sim/nova_mjx
sys.path.insert(0, str(HERE))
from ckpt_utils import stage_done_steps                        # noqa: E402


def done_steps(sdir):
    return sum(stage_done_steps(d) or 0 for d in sdir.glob("run_*") if d.is_dir())


def main(plan_path):
    plan_path = pathlib.Path(plan_path).expanduser()
    run = plan_path.parent
    plan = json.loads(plan_path.read_text())
    py = sys.executable
    for st in plan["stages"]:
        sdir = run / st["name"]
        sdir.mkdir(exist_ok=True)
        done = done_steps(sdir)
        left = st["timesteps"] - done
        if "--curriculum" in st.get("args", []):
            left = st["timesteps"]   # train.py's curriculum mode is budget-aware itself
        if (sdir / "DONE").exists() or left <= 0:
            print(f"[plan] {st['name']}: done ({done:,}/{st['timesteps']:,}) - skip", flush=True)
            continue
        cmd = [py, "train.py", "--ckpt", str(sdir), "--timesteps", str(left),
               "--out", str(sdir / "policy.pkl"), *st.get("args", [])]
        if st.get("init") and not any(sdir.glob("run_*/*/")):
            init = pathlib.Path(st["init"]).expanduser()
            src = init if init.is_absolute() else run / st["init"] / "policy.pkl"
            cmd += ["--restore-params-pkl", str(src)]
        print(f"[plan] {st['name']}: {done:,} done, training {left:,}: {' '.join(cmd)}",
              flush=True)
        subprocess.run(cmd, cwd=HERE, check=True)
        (sdir / "DONE").write_text(f"{st['timesteps']}\n")
    final = run / plan["stages"][-1]["name"] / "policy.pkl"
    for ev in plan.get("evals", []):
        out = run / f"eval_{ev['name']}.json"
        if out.exists():
            continue
        cmd = [py, "eval_gait.py", "--policy", str(final), "--json", str(out),
               *plan.get("eval_args", []), *ev.get("args", [])]
        print(f"[plan] eval {ev['name']}: {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, cwd=HERE, check=True)
    print("[plan] COMPLETE", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
