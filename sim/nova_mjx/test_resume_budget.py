"""Curriculum resume accounting — the arithmetic that decides how many steps a
resumed stage still owes. Got this wrong once: a stage that had already trained
16M steps was restored and then handed the FULL 30M stage budget again, so it
ran 48M steps and burned an extra GPU-hour for nothing.

Brax restarts its step counter at 0 on every restore, so the on-disk checkpoint
step numbers are PER-ATTEMPT, not cumulative — which is exactly why this needs
its own accounting and its own test.

  python test_resume_budget.py
"""
import os
import tempfile
from pathlib import Path

import ckpt_utils
from ckpt_utils import (atomic_write, checkpoint_named, find_latest_checkpoint,
                        record_progress, stage_done_steps)


def _stage(tmp, ckpts=(), progress=None):
    d = Path(tmp) / "stage0_t0.25"
    for step in ckpts:
        (d / f"{step:012d}").mkdir(parents=True, exist_ok=True)
    d.mkdir(parents=True, exist_ok=True)
    if progress is not None:
        (d / "PROGRESS").write_text(str(progress))
    return d


def test_empty_stage_is_zero():
    with tempfile.TemporaryDirectory() as tmp:
        assert stage_done_steps(_stage(tmp)) == 0
        assert stage_done_steps(Path(tmp) / "never_created") == 0


def test_legacy_stage_falls_back_to_max_checkpoint_step():
    # Stage dirs written before PROGRESS existed: no marker, but the largest
    # checkpoint step is exact for a stage that was never interrupted.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(2_293_760, 16_056_320, 9_175_040))
        assert stage_done_steps(d) == 16_056_320


def test_progress_beats_checkpoint_names_after_a_resume():
    # Attempt 1 ran 0 -> 16.05M; attempt 2 resumed and ran 0 -> 14M, overwriting
    # the lower-numbered dirs. Cumulative is 30M, but no dir name says so, and
    # the largest surviving name (16.05M) is a STALE attempt-1 leftover.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(14_000_000, 16_056_320), progress=30_056_320)
        assert stage_done_steps(d) == 30_056_320


def test_corrupt_progress_falls_back_instead_of_crashing():
    # Killed mid-write. Losing accounting must cost steps, not the whole run.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(4_587_520,), progress="")
        assert stage_done_steps(d) == 4_587_520
        (d / "PROGRESS").write_text("nan\n")
        assert stage_done_steps(d) == 4_587_520


def test_record_progress_round_trips_and_overwrites():
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp)
        record_progress(d, 2_293_760)
        assert stage_done_steps(d) == 2_293_760
        record_progress(d, 4_587_520)          # every eval, monotonically
        assert stage_done_steps(d) == 4_587_520


def test_atomic_write_leaves_the_old_file_when_the_rename_fails():
    # These calls run inside Brax's per-eval callback. A Drive hiccup must cost a
    # bookkeeping file, not a six-hour run — and must never leave a half-written
    # policy where the run's only usable output belongs.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "nova_policy.pkl"
        assert atomic_write(target, b"good-params") is True
        real_replace = os.replace
        ckpt_utils.os.replace = lambda *a, **kw: (_ for _ in ()).throw(
            OSError("Input/output error"))
        try:
            assert atomic_write(target, b"new-params", label="policy") is False
        finally:
            ckpt_utils.os.replace = real_replace
        assert target.read_bytes() == b"good-params", "old file must survive"
        assert not list(Path(tmp).glob("*.tmp")), "no tempfile litter"


def test_atomic_write_survives_an_unwritable_dir():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "readonly"
        d.mkdir()
        os.chmod(d, 0o500)
        try:
            assert record_progress(d, 123) is False   # no exception escapes
        finally:
            os.chmod(d, 0o700)


def test_pointer_wins_when_mtime_lies():
    # The scenario mtime cannot survive: attempt 2 resumed and stopped BELOW
    # attempt 1's high-water mark, then something (a Drive sync, a copy, a mount
    # that invents directory mtimes) made the stale checkpoint look newest.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(14_000_000, 16_056_320))
        record_progress(d, 30_000_000, latest="000014000000")
        os.utime(d / "000016056320", (2 ** 31, 2 ** 31))     # far future mtime
        assert find_latest_checkpoint(d).endswith("000014000000")


def test_pointer_to_a_vanished_checkpoint_falls_back():
    # Orbax pruned it, or it was never written. Must degrade, not return a path
    # that isn't there.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(9_175_040,))
        record_progress(d, 30_000_000, latest="000014000000")
        got = find_latest_checkpoint(d)
        assert got is not None and Path(got).is_dir()
        assert got.endswith("000009175040")


def test_legacy_dir_with_no_pointer_still_resolves():
    # Every stage dir already on Drive, including the currently-running job.
    # Direct digit children present -> name-max branch, and here it agrees with
    # mtime-max (both pick 4587520), so this passes either way.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(2_293_760, 4_587_520))
        os.utime(d / "000004587520", (2 ** 31, 2 ** 31))
        assert find_latest_checkpoint(d).endswith("000004587520")


def test_legacy_no_pointer_prefers_name_over_lying_mtime():
    # CRITICAL repro: a legacy stage dir (no PROGRESS pointer) with direct
    # digit-named checkpoint children. mtime is scrambled so the LOWEST step
    # looks newest -- a Drive sync, a copy, or a mount inventing mtimes. Within
    # one training dir, Brax's step-numbered names ARE comparable and
    # authoritative, so the name-max must win regardless of what mtime claims.
    # Before the fix this returned the stale 2293760 checkpoint.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(2_293_760, 9_175_040, 16_056_320))
        os.utime(d / "000002293760", (2 ** 31, 2 ** 31))   # far future: looks newest
        assert find_latest_checkpoint(d).endswith("000016056320")


def test_legacy_multi_attempt_stage_prefers_name_over_newer_mtime():
    # Multi-attempt legacy dir: attempt 1 wrote up to 16.05M, a later (failed)
    # attempt 2 wrote a fresher-mtime 14M dir that never caught up. Restoring by
    # mtime would silently hand back attempt 2's less-trained content. Restoring
    # by name-max redoes at most the gap between 14M and 16.05M -- undercount is
    # the safe direction; a silent regression to stale weights is not.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(14_000_000, 16_056_320))
        os.utime(d / "000014000000", (2 ** 31, 2 ** 31))   # newer mtime, older step
        assert find_latest_checkpoint(d).endswith("000016056320")


def test_root_with_no_direct_digit_children_still_uses_mtime_walk():
    # A root holding run_*/stage_* subdirs (no PROGRESS anywhere): step names
    # under DIFFERENT training dirs are not comparable to each other, so there
    # is no name-max to take here -- this must still fall back to _mtime_walk.
    with tempfile.TemporaryDirectory() as tmp:
        old, new = Path(tmp) / "run_1", Path(tmp) / "run_2"
        (old / "000001000000").mkdir(parents=True)
        (new / "000009000000").mkdir(parents=True)
        os.utime(old / "000001000000", (2 ** 31, 2 ** 31))   # newer mtime, lower step
        assert find_latest_checkpoint(tmp).endswith("000001000000")


def test_root_scan_prefers_the_writer_stamped_wallclock():
    # Two training dirs under one root; the newer WRITE wins regardless of what
    # the filesystem thinks, because the writer stamped the time itself.
    with tempfile.TemporaryDirectory() as tmp:
        old, new = Path(tmp) / "run_1", Path(tmp) / "run_2"
        for d, step in ((old, 1_000_000), (new, 2_000_000)):
            (d / f"{step:012d}").mkdir(parents=True)
            record_progress(d, step, latest=f"{step:012d}")
        rec = ckpt_utils.read_progress(new)
        rec["wallclock"] = ckpt_utils.read_progress(old)["wallclock"] + 100
        (new / "PROGRESS").write_text(__import__("json").dumps(rec))
        os.utime(old / "000001000000", (2 ** 31, 2 ** 31))   # mtime says otherwise
        assert find_latest_checkpoint(tmp).endswith("000002000000")


def test_root_scan_can_be_kept_out_of_stage_dirs():
    # "What should stage 0 start from" must never answer with stage 3's policy.
    with tempfile.TemporaryDirectory() as tmp:
        loose = Path(tmp) / "run_1"
        (loose / "000001000000").mkdir(parents=True)
        record_progress(loose, 1_000_000, latest="000001000000")
        st = Path(tmp) / "stage3_t1.00"
        (st / "000099000000").mkdir(parents=True)
        record_progress(st, 99_000_000, latest="000099000000")
        assert find_latest_checkpoint(tmp).endswith("000099000000")
        assert find_latest_checkpoint(
            tmp, skip_prefixes=("stage",)).endswith("000001000000")


def test_checkpoint_named_does_not_assume_brax_padding():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "0000004587520").mkdir()             # 13 wide, not 12
        assert checkpoint_named(d, 4_587_520) == "0000004587520"
        assert checkpoint_named(d, 123) is None


def test_legacy_int_progress_still_reads_as_steps():
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(4_587_520,), progress=16_056_320)
        assert stage_done_steps(d) == 16_056_320


def test_throughput_ignores_stage_boundaries_and_compile_spikes():
    # train_log.csv step counts restart per stage, so a boundary looks like a
    # negative delta; the first eval of each stage carries ~300s of XLA compile.
    # Neither may poison the hours estimate.
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "train_log.csv"
        log.write_text(
            "1000,0,1100\n"
            "1300,2293760,1150\n"          # includes compile: ~7600 steps/s
            "1600,4587520,1200\n"          # steady: ~7646 steps/s
            "1900,6881280,1250\n"
            "2200,0,1260\n"                # <- next stage, counter restarts
            "2500,2293760,1300\n")
        rate = ckpt_utils.steps_per_second(log)
        assert rate is not None and 7000 < rate < 8000, rate


def test_throughput_is_none_without_history():
    with tempfile.TemporaryDirectory() as tmp:
        assert ckpt_utils.steps_per_second(Path(tmp) / "nope.csv") is None
        empty = Path(tmp) / "train_log.csv"
        empty.write_text("")
        assert ckpt_utils.steps_per_second(empty) is None


def test_budget_of_a_finished_stage_is_not_positive():
    # The skip guard: a stage whose DONE marker never landed (killed between the
    # last eval and the marker write) must NOT retrain its whole budget.
    per = 30_000_000
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(32_112_640,), progress=32_112_640)
        assert per - stage_done_steps(d) <= 0


def test_nested_digit_dir_inside_a_checkpoint_cannot_win():
    # A hypothetical numeric dir nested INSIDE an orbax checkpoint (e.g. an
    # internal shard/step dir orbax writes below the step dir) must never be
    # mistaken for a sibling checkpoint by either scanner.
    with tempfile.TemporaryDirectory() as tmp:
        d = _stage(tmp, ckpts=(16_056_320,))
        nested = d / "000016056320" / "0001234"
        nested.mkdir(parents=True)
        assert ckpt_utils._max_checkpoint_step(d) == 16_056_320
        got = ckpt_utils._mtime_walk(d)
        assert got is not None and Path(got).name == "000016056320"


def test_steps_per_second_skips_colab_restart_gaps():
    # Two Colab-restart gaps (>1800s each) outnumber the one steady pair, so
    # without filtering their near-zero rates dominate the median outright --
    # this is deliberately NOT a case the median absorbs on its own. Each gap
    # pair must contribute no sample at all.
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "train_log.csv"
        log.write_text(
            "1000,0,1100\n"
            "1300,2293760,1150\n"          # steady pair: ~7646 steps/s
            "8500,2293761,1160\n"          # 2h gap, ds=1 -- must be skipped
            "15700,2293763,1170\n")        # 2h gap, ds=2 -- must be skipped
        rate = ckpt_utils.steps_per_second(log)
        assert rate is not None and 7000 < rate < 8000, rate


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all resume-budget tests passed")
