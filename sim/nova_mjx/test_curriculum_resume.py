"""Curriculum stage budgeting, end to end through train.main().

Stubs JAX/Brax/env (this box has no GPU stack) and runs the REAL curriculum loop
against a fake trainer that records what num_timesteps each stage was handed.
That number is the whole point: a resumed stage must be given what it still
OWES, not the full stage budget again.

  python test_curriculum_resume.py
"""
import os
import sys
import tempfile
import types
from pathlib import Path

PER = 30_000_000          # 4 stages x 30M
EVAL_EVERY = 2_293_760    # brax eval interval at these hyperparameters

CALLS = []                # [(ckpt_dir, num_timesteps, restore, restore_params)]
DIE_AFTER = [None]        # evals to survive before simulating a Colab dropout
SKIP_CKPT_AT = [None]     # 1-based eval index whose checkpoint dir is NOT written
SEEDS = []                # seed each stage was trained with

# What Brax hands progress_fn: every key the env put in state.metrics, SUMMED
# over the episode (brax's eval/episode_<name> aggregation) -- realistic
# episode-sum magnitudes at episode_length ~1000, not the 0-1 per-step
# fractions these used to (wrongly) look like.
EVAL_METRICS = {"eval/episode_fwd_speed": 820.0, "eval/episode_w_progress": 1400.0,
                "eval/episode_w_clearance": -300.0, "eval/episode_swing_xy_speed": 210.0,
                "eval/avg_episode_length": 1000.0, "eval/walltime": 12.0}
EVAL_METRICS.update({f"eval/episode_{p}_{f}": 250.0
                     for p in ("air", "airT", "ghost")
                     for f in ("FL", "FR", "RL", "RR")})


def _install_stubs():
    """Minimal fakes for the GPU-only imports train.py pulls in at module load."""
    jax = types.ModuleType("jax")
    jax.default_backend = lambda: "gpu"
    jax.devices = lambda: ["fake"]
    sys.modules["jax"] = jax

    epath = types.ModuleType("etils.epath")
    epath.Path = Path
    etils = types.ModuleType("etils")
    etils.epath = epath
    sys.modules["etils"] = etils
    sys.modules["etils.epath"] = epath

    def fake_train(environment=None, progress_fn=None, policy_params_fn=None,
                   num_timesteps=0, save_checkpoint_path=None, restore_checkpoint_path=None,
                   restore_params=None, seed=None, **kw):
        CALLS.append((save_checkpoint_path, num_timesteps,
                      restore_checkpoint_path, restore_params))
        SEEDS.append(seed)
        # Mimic Brax: step counter restarts at 0, a checkpoint dir per eval --
        # except the eval matching SKIP_CKPT_AT, which simulates a checkpoint
        # write that silently didn't happen (crash mid-write, FS hiccup).
        step, evals = 0, 0
        while step < num_timesteps:
            step += EVAL_EVERY
            evals += 1
            if SKIP_CKPT_AT[0] != evals:
                Path(save_checkpoint_path, f"{step:012d}").mkdir(parents=True, exist_ok=True)
            progress_fn(step, dict(EVAL_METRICS, **{"eval/episode_reward": 1200.0}))
            if DIE_AFTER[0] is not None and evals >= DIE_AFTER[0]:
                raise RuntimeError("simulated Colab dropout")
        policy_params_fn(step, None, {"p": 1})
        return None, {"p": 1}, None

    ppo = types.ModuleType("brax.training.agents.ppo.train")
    ppo.train = fake_train
    nets = types.ModuleType("brax.training.agents.ppo.networks")
    nets.make_ppo_networks = lambda **kw: None
    for name, mod in [("brax", types.ModuleType("brax")),
                      ("brax.training", types.ModuleType("brax.training")),
                      ("brax.training.agents", types.ModuleType("brax.training.agents")),
                      ("brax.training.agents.ppo", types.ModuleType("brax.training.agents.ppo")),
                      ("brax.training.agents.ppo.train", ppo),
                      ("brax.training.agents.ppo.networks", nets)]:
        sys.modules[name] = mod

    env = types.ModuleType("env")
    env.FOOT_RADIUS, env.CONTACT_EPS, env.FOOT_TARGET_Z = 0.014, 0.001, 0.05
    env.HM_N, env.HM_EXTENT = 11, 0.4

    class NovaJoystick:
        _cmd_lo, _cmd_hi, _cmd_stage = (-0.15, -0.15, -0.5), (0.35, 0.15, 0.5), 2
        _heightmap, observation_size = False, 105

        def __init__(self, **kw):
            pass

    env.NovaJoystick = NovaJoystick
    env.make_domain_randomize = lambda *a, **kw: None
    sys.modules["env"] = env


_install_stubs()
import train  # noqa: E402  (must follow the stubs)


def _run(ckpt):
    CALLS.clear()
    SEEDS.clear()
    sys.argv = ["train.py", "--ckpt", str(ckpt), "--curriculum",
                "--curriculum-stages", "4", "--timesteps", str(4 * PER),
                "--terrain", "1.0", "--out", str(Path(ckpt) / "policy.pkl")]
    train.main()
    return list(CALLS)


def _args(ckpt):
    """The same argparse Namespace main() builds, for planning in isolation."""
    return types.SimpleNamespace(
        ckpt=str(ckpt), curriculum=True, curriculum_stages=4,
        curriculum_start=0.25, terrain=1.0, timesteps=4 * PER, seed=0,
        stair_frac=0.0)


def _seed_dead_attempt(ckpt, stage="stage0_t0.25", upto=16_056_320):
    """A stage killed mid-flight: checkpoints on disk, no DONE marker."""
    d = Path(ckpt) / stage
    step = 0
    while step < upto:
        step += EVAL_EVERY
        (d / f"{min(step, upto):012d}").mkdir(parents=True, exist_ok=True)
    train.record_progress(d, upto)
    return d


def test_diagnostics_prints_per_step_not_raw_episode_sums():
    # Brax SUMS each metric over the whole episode into eval/episode_<name> --
    # printing those raw sums as if they were 0-1 per-step fractions was off by
    # roughly the episode length (~1000x). The printed line must show the
    # per-step value (episode-sum / episode length) for fwd/clear/swing/ghost/
    # airT, while prog and eval_reward (not diagnostics' job) stay raw sums.
    line = train.diagnostics(dict(EVAL_METRICS))
    assert "fwd  0.82" in line, line          # 820.0 / avg_episode_length 1000.0
    assert "clear  -0.30" in line, line       # -300.0 / 1000.0
    assert "swing 0.21" in line, line         # 210.0 / 1000.0
    assert "ghost 0.25" in line, line         # 250.0 / 1000.0, averaged over 4 legs
    assert "len 1000" in line, line           # the fall-rate canary
    assert "prog +1400.00" in line, line      # RAW sum on purpose (historical compare)


def test_resumed_stage_is_charged_only_what_it_owes():
    # THE REGRESSION: stage 1 had 16,056,320 of its 30M banked, was restored,
    # and was then handed a fresh 30M — 48M steps for a 30M stage.
    with tempfile.TemporaryDirectory() as tmp:
        _seed_dead_attempt(tmp)
        calls = _run(tmp)
        assert len(calls) == 4, calls
        ckpt_dir, budget, restore, _ = calls[0]
        assert "stage0_t0.25" in str(ckpt_dir)
        assert budget == PER - 16_056_320, budget
        assert restore is not None, "must resume the dead attempt's checkpoint"


def test_untouched_stages_get_the_full_budget():
    with tempfile.TemporaryDirectory() as tmp:
        _seed_dead_attempt(tmp)
        for _, budget, _, _ in _run(tmp)[1:]:
            assert budget == PER, budget


def test_finished_stage_missing_its_marker_is_skipped_not_retrained():
    # Killed between the last eval and the DONE write. Old behaviour: retrain 30M.
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp, upto=32_112_640)   # over budget, brax rounds up
        calls = _run(tmp)
        assert len(calls) == 3, "stage 1 should not have trained again"
        assert all("stage0_t0.25" not in str(c[0]) for c in calls)
        assert (d / "DONE").exists()


def test_done_stages_still_skip():
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp)
        (d / "DONE").write_text("done")
        calls = _run(tmp)
        assert len(calls) == 3, calls


def test_progress_accumulates_across_attempts():
    # Second attempt's PROGRESS must reflect attempt 1 + attempt 2, so a THIRD
    # attempt doesn't re-buy steps that are already paid for.
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp)
        _run(tmp)
        assert train.stage_done_steps(d) >= PER, train.stage_done_steps(d)


def test_a_dropout_never_claims_steps_it_cannot_prove():
    # PROGRESS lags one eval on purpose. Overcounting would silently skip
    # training the stage still owes; undercounting just redoes one interval.
    with tempfile.TemporaryDirectory() as tmp:
        DIE_AFTER[0] = 3
        try:
            try:
                _run(tmp)
            except RuntimeError as e:
                assert "dropout" in str(e)
        finally:
            DIE_AFTER[0] = None
        d = Path(tmp) / "stage0_t0.25"
        recorded = train.stage_done_steps(d)
        on_disk = max(int(p.name) for p in d.iterdir() if p.name.isdigit())
        assert recorded <= on_disk, (recorded, on_disk)
        assert recorded == on_disk - EVAL_EVERY, "exactly one eval of lag"
        # And the resume charges the difference, not the whole stage.
        DIE_AFTER[0] = None
        assert PER - recorded < PER


def test_progress_never_advances_past_a_missing_checkpoint():
    # A checkpoint write that silently didn't happen (crash mid-write, FS
    # hiccup) must not let PROGRESS claim credit for it -- a later resume
    # would try to restore a checkpoint that was never there. Eval 2's
    # checkpoint dir is skipped; the run then dies at eval 3, before the
    # unconditional clean-exit write could paper over the gap.
    with tempfile.TemporaryDirectory() as tmp:
        SKIP_CKPT_AT[0] = 2
        DIE_AFTER[0] = 3
        try:
            try:
                _run(tmp)
            except RuntimeError as e:
                assert "dropout" in str(e)
        finally:
            SKIP_CKPT_AT[0] = None
            DIE_AFTER[0] = None
        d = Path(tmp) / "stage0_t0.25"
        recorded = train.stage_done_steps(d)
        # eval 1's checkpoint (EVAL_EVERY) exists; eval 2's (2*EVAL_EVERY) was
        # never written; eval 3's (3*EVAL_EVERY) exists again. PROGRESS must
        # have stalled at eval 1's step, not advanced past the gap.
        assert recorded == EVAL_EVERY, recorded
        assert train.checkpoint_named(d, recorded) is not None, \
            "PROGRESS must only ever point at a checkpoint that actually exists"


def test_every_eval_metric_is_logged_with_a_stable_header():
    with tempfile.TemporaryDirectory() as tmp:
        _run(tmp)
        rows = (Path(tmp) / "eval_metrics.csv").read_text().strip().split("\n")
        header = rows[0].split(",")
        assert header[:2] == ["stage", "step"]
        for k in ("episode_fwd_speed", "episode_ghost_RR", "episode_w_clearance"):
            assert k in header, header
        assert len({len(r.split(",")) for r in rows}) == 1, "ragged rows"
        assert {r.split(",")[0] for r in rows[1:]} == {
            "stage0_t0.25", "stage1_t0.50", "stage2_t0.75", "stage3_t1.00"}


def test_header_survives_a_resume_and_never_shifts_columns():
    # Second attempt appends to the same csv. If a new metric key appeared, the
    # old columns must not slide sideways under it.
    with tempfile.TemporaryDirectory() as tmp:
        _seed_dead_attempt(tmp)
        csv = Path(tmp) / "eval_metrics.csv"
        csv.write_text("stage,step,episode_fwd_speed\n")
        _run(tmp)
        rows = csv.read_text().strip().split("\n")
        assert rows[0] == "stage,step,episode_fwd_speed"
        assert all(len(r.split(",")) == 3 for r in rows), rows[:3]
        assert rows[1].split(",")[2] == "820.0"    # raw episode-sum, csv is unscaled


def test_a_metrics_dict_without_diagnostics_does_not_kill_the_run():
    # Older env, renamed key, whatever — a logging gap must cost a log line, not
    # a six-hour run. The reward key alone must still get through.
    global EVAL_METRICS
    saved = EVAL_METRICS
    EVAL_METRICS = {}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            calls = _run(tmp)
            assert len(calls) == 4
            log = (Path(tmp) / "train_log.csv").read_text().strip().split("\n")
            assert log and log[-1].endswith(",1200.0")
    finally:
        EVAL_METRICS = saved


def test_each_stage_draws_its_own_domain_randomization():
    # One seed for the whole curriculum = all four stages train against the SAME
    # 2048 randomized robots (env.py domain_randomize draws friction/mass/kp/kv
    # off this). Distinct per stage = 4x the hardware the policy must survive.
    with tempfile.TemporaryDirectory() as tmp:
        _run(tmp)
        assert SEEDS == [0, 1, 2, 3], SEEDS
        assert len(set(SEEDS)) == len(SEEDS)


def test_a_resumed_legacy_stage_keeps_args_seed_not_the_formula():
    # Constant within a stage: a resume must not swap the DR draw mid-stage.
    # This stage has checkpoints but NO recorded seed -- pre-seed-persistence
    # code, which always trained the whole curriculum on plain args.seed, never
    # args.seed+i. Resuming it MUST use args.seed exactly: the args.seed+i
    # formula would silently swap it onto a draw it was never trained under.
    with tempfile.TemporaryDirectory() as tmp:
        _seed_dead_attempt(tmp, stage="stage1_t0.50")
        (Path(tmp) / "stage0_t0.25").mkdir()
        (Path(tmp) / "stage0_t0.25" / "DONE").write_text("done")
        _run(tmp)
        assert SEEDS[0] == 0, SEEDS       # legacy resume -> args.seed (0), not 1


def test_recorded_seed_wins_over_the_formula_even_after_a_seed_typo():
    # A resumed stage must keep the EXACT DR draw it trained under, even when
    # --seed differs from whatever produced that draw (a typo, or just a
    # different --seed passed out of habit on the next Colab cell run).
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp, stage="stage2_t0.75")
        train.record_progress(d, train.stage_done_steps(d), seed=7)
        for s in ("stage0_t0.25", "stage1_t0.50"):
            (Path(tmp) / s).mkdir()
            (Path(tmp) / s / "DONE").write_text("done")
        _run(tmp)
        assert SEEDS[0] == 7, SEEDS        # recorded seed wins over args.seed+2 == 2


def test_progress_records_the_seed_the_stage_trained_with():
    with tempfile.TemporaryDirectory() as tmp:
        _run(tmp)
        rec = train.read_progress(Path(tmp) / "stage2_t0.75")
        assert rec.get("seed") == 2, rec


def test_stage_chaining_uses_the_recorded_pointer_not_mtime():
    # Chaining must survive a filesystem that misreports mtime: stage N+1 has to
    # start from stage N's real final checkpoint.
    with tempfile.TemporaryDirectory() as tmp:
        calls = _run(tmp)
        s0 = Path(tmp) / "stage0_t0.25"
        final = max(int(p.name) for p in s0.iterdir() if p.name.isdigit())
        os.utime(s0 / f"{EVAL_EVERY:012d}", (2 ** 31, 2 ** 31))   # early one "newest"
        assert train.find_latest_checkpoint(str(s0)).endswith(f"{final:012d}")
        assert str(calls[1][2]).endswith(f"{final:012d}")


def test_dry_run_trains_nothing_and_writes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp)
        before = sorted(p.name for p in Path(tmp).rglob("*"))
        CALLS.clear()
        sys.argv = ["train.py", "--ckpt", tmp, "--curriculum", "--dry-run",
                    "--curriculum-stages", "4", "--timesteps", str(4 * PER),
                    "--terrain", "1.0"]
        train.main()
        assert CALLS == [], "dry run must not train"
        assert not (d / "DONE").exists(), "dry run must not mark stages done"
        assert not (Path(tmp) / "train_log.csv").exists()
        assert sorted(p.name for p in Path(tmp).rglob("*")) == before


def test_the_printed_plan_is_the_executed_plan():
    # The whole reason planning is a separate function: a plan that can drift
    # from what runs is worse than no plan. Same inputs -> same budgets, in order.
    with tempfile.TemporaryDirectory() as tmp:
        _seed_dead_attempt(tmp)
        (Path(tmp) / "stage2_t0.75").mkdir()
        (Path(tmp) / "stage2_t0.75" / "DONE").write_text("done")
        args = _args(tmp)
        plan = train.plan_curriculum(Path(tmp), args)
        planned = [p["budget"] for p in plan if p["action"] == "run"]
        planned_seeds = [p["seed"] for p in plan if p["action"] == "run"]
        calls = _run(tmp)
        assert planned == [c[1] for c in calls], (planned, [c[1] for c in calls])
        assert planned_seeds == SEEDS, (planned_seeds, SEEDS)
        assert [p["action"] for p in plan] == ["run", "run", "skip", "run"]


def test_plan_reports_a_finished_stage_without_marking_it():
    with tempfile.TemporaryDirectory() as tmp:
        d = _seed_dead_attempt(tmp, upto=32_112_640)
        plan = train.plan_curriculum(Path(tmp), _args(tmp))
        assert plan[0]["action"] == "mark-done"
        assert not (d / "DONE").exists(), "planning must not mutate"


def test_stage_chaining_still_walks_forward():
    # Each later stage must init from the PREVIOUS stage's checkpoint.
    with tempfile.TemporaryDirectory() as tmp:
        calls = _run(tmp)
        assert calls[0][2] is None, "fresh run, nothing to restore"
        for prev, cur in zip(calls, calls[1:]):
            assert cur[2] is not None and str(prev[0]) in str(cur[2]), (prev, cur)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all curriculum-resume tests passed")
