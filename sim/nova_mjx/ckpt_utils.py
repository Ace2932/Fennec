"""Checkpoint discovery + curriculum resume accounting. Stdlib only, no JAX —
so it imports (and tests) on a laptop, not just on the Colab GPU box.

Assumes a local filesystem path (Colab's mounted Drive counts); os.walk does not
speak gs://.
"""
import json
import os
import time
from pathlib import Path

PROGRESS = "PROGRESS"


def atomic_write(path, data, label=""):
    """Write bytes/str via a sibling tempfile + rename, so a kill mid-write leaves
    the PREVIOUS file intact rather than a truncated one. Colab dies mid-write for
    a living; the file this protects (nova_policy.pkl, PROGRESS) is exactly what a
    dropout is supposed to leave behind.

    Best-effort and NEVER raises: these calls sit inside Brax's per-eval callback,
    and a Drive hiccup must not take down a six-hour run. Returns True on success.
    On failure the old file is left untouched — a stale-but-loadable policy beats a
    fresh corrupt one.
    """
    path = Path(str(path))
    tmp = path.with_name(path.name + ".tmp")
    try:
        mode, enc = ("wb", None) if isinstance(data, bytes) else ("w", "utf-8")
        with open(tmp, mode, encoding=enc) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except Exception as e:                      # noqa: BLE001 — deliberate
        print(f"  ! could not write {label or path}: {type(e).__name__}: {e} "
              f"(previous file kept)")
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


class EvalMetricsCsv:
    """Append every per-eval metric to ONE csv, across stages and resumes.

    Brax's evaluator averages every key the env puts in state.metrics into
    `eval/episode_<name>` — 40-odd diagnostics per eval that were being computed
    and then discarded. The column set is fixed by the first write and reused
    forever after (re-read from the file on resume), so a plot never has to
    reconcile shifting column order; keys that appear later are dropped rather
    than silently shifting every column right.

    Best-effort like atomic_write: this runs inside Brax's eval callback and must
    not be able to end a run.

    Values stored are the RAW brax episode-sums (eval/episode_<name>), not
    per-step means — except keys already named *_per_step, which brax itself
    divides. Any per-step view (train.py's diagnostics()) is a read-time
    division by episode length, not something this class does.
    """

    def __init__(self, path):
        self.path = Path(str(path))
        self.cols = None
        try:
            if self.path.exists():
                head = self.path.read_text().split("\n", 1)[0].strip()
                if head:
                    self.cols = head.split(",")
        except OSError:
            pass

    def write(self, stage, step, metrics):
        try:
            new = self.cols is None
            if new:
                self.cols = ["stage", "step"] + sorted(metrics)
            row = dict(metrics, stage=stage, step=step)
            with open(self.path, "a", encoding="utf-8") as f:
                if new:
                    f.write(",".join(self.cols) + "\n")
                f.write(",".join(str(row.get(c, "")) for c in self.cols) + "\n")
            return True
        except Exception as e:                  # noqa: BLE001 — deliberate
            print(f"  ! eval-metrics csv write failed: {type(e).__name__}: {e}")
            return False


# ---------------------------------------------------------------- progress ---
# One PROGRESS file per training dir, rewritten every eval:
#   {"steps": <cumulative steps>, "latest": "<checkpoint dirname>",
#    "wallclock": <time.time() when written>}
# `steps` answers "how much of this stage's budget is already paid for"; `latest`
# and `wallclock` answer "which checkpoint is newest" WITHOUT consulting
# filesystem mtimes. Both live in one file so a partial write can never leave the
# step count and the pointer disagreeing.


def read_progress(d):
    """Parse a dir's PROGRESS. Returns {} when absent/unreadable. Accepts the
    legacy plain-integer format (steps only, no pointer)."""
    try:
        raw = (Path(str(d)) / PROGRESS).read_text().strip()
    except OSError:
        return {}
    try:
        rec = json.loads(raw)
    except ValueError:
        return {}
    if isinstance(rec, dict):
        return rec
    # A bare integer is valid JSON, so the legacy steps-only format lands here.
    return {"steps": int(rec)} if isinstance(rec, (int, float)) else {}


def record_progress(sdir, total_steps, latest=None, seed=None):
    """Persist cumulative trained steps + which checkpoint holds them.

    seed, when given, is the seed this stage is TRAINING WITH — persisted so a
    resumed stage can recover the exact domain-randomization draw it started
    under (see train.plan_curriculum), rather than recomputing it from
    args.seed + stage index and risking a mismatch with what actually trained.
    """
    rec = {"steps": int(total_steps), "wallclock": time.time()}
    if latest:
        rec["latest"] = str(latest)
    if seed is not None:
        rec["seed"] = int(seed)
    return atomic_write(Path(str(sdir)) / PROGRESS, json.dumps(rec),
                        label=PROGRESS)


def stage_done_steps(sdir):
    """Steps ALREADY trained in this curriculum stage, across every attempt.

    Brax restarts its step counter at 0 on each restore, so a resumed stage's
    on-disk step numbers are per-attempt and a later attempt overwrites the
    earlier one's lower-numbered dirs — no dir name holds the cumulative total,
    and the largest surviving name can be a stale leftover from a dead attempt.
    Hence PROGRESS, rewritten every eval alongside Brax's own checkpoint.

    Falls back to the largest checkpoint step when PROGRESS is missing or
    unreadable: exact for a stage that ran once without interruption (which is
    what every pre-PROGRESS stage dir on Drive is), and a lower bound otherwise
    — erring toward training a few extra steps, never toward skipping a stage
    that still owes work.
    """
    steps = read_progress(sdir).get("steps")
    if isinstance(steps, int):
        return steps
    return _max_checkpoint_step(sdir)


# ------------------------------------------------------------- discovery -----

def _walk(root, skip_prefixes=()):
    """Yield dirs under root, not descending into children whose name starts with
    any skip prefix (used to keep a curriculum's stage dirs out of a root scan)."""
    pref = tuple(skip_prefixes)
    for dirpath, dirnames, filenames in os.walk(str(root)):
        if pref:
            dirnames[:] = [d for d in dirnames if not d.startswith(pref)]
        yield Path(dirpath), dirnames, filenames


def _max_checkpoint_step(d):
    """Largest digit-named DIRECT child of d. Every caller passes a single
    training dir (a stage dir or a run dir), never a root holding several of
    them, so there is no need to recurse — and not recursing is what keeps a
    hypothetical numeric dir nested inside a checkpoint (see _mtime_walk) from
    ever being mistaken for a sibling checkpoint here too."""
    best = 0
    try:
        for entry in os.scandir(str(d)):
            if entry.is_dir() and entry.name.isdigit():
                best = max(best, int(entry.name))
    except OSError:
        pass
    return best


def _mtime_walk(root, skip_prefixes=()):
    """LAST RESORT: newest all-digit dir by filesystem mtime, used only when
    there is no name-max to trust instead (see find_latest_checkpoint) — a root
    holding several run_*/stage_* dirs, where step numbers are per-attempt and
    not comparable across siblings. Directory mtime on a Drive FUSE mount is not
    something to bet an eight-hour run on, which is exactly why this is a last
    resort rather than the primary mechanism.

    Recurses (unlike _max_checkpoint_step) because the root case needs it, but
    skips any digit dir whose PARENT is itself all-digit, so a hypothetical
    numeric dir nested inside an orbax checkpoint can never win.
    """
    best, best_m = None, -1.0
    for d, _, _ in _walk(root, skip_prefixes):
        if d.name.isdigit() and not d.parent.name.isdigit():
            try:
                m = d.stat().st_mtime
            except OSError:
                continue
            if m > best_m:
                best_m, best = m, str(d)
    return best


def find_latest_checkpoint(ckpt_dir, skip_prefixes=()):
    """Newest Brax checkpoint under ckpt_dir.

    Prefers each training dir's self-recorded PROGRESS pointer, ordered by the
    wallclock the WRITER stamped — our own timestamp, not the filesystem's, so it
    survives a Drive sync, a copied checkpoint tree, and any mtime the mount feels
    like inventing.

    No pointer anywhere (legacy dir, written before PROGRESS carried one): if
    ckpt_dir itself has direct all-digit-named children, return the max-BY-NAME
    one. That agrees with stage_done_steps by construction (both trust dir
    names over mtime), and within ONE training dir Brax's step-numbered names
    ARE comparable and authoritative — unlike mtime, which a Drive sync, a
    copy, or a FUSE mount can invent freely. For a multi-attempt legacy dir,
    name-max's worst case is redoing the gap between attempts, which is
    undercount-safe; mtime-max's worst case is silently restoring a STALER
    checkpoint that merely got touched more recently. Only when there are NO
    direct digit children — a root dir holding run_*/stage_* subdirs, whose
    step names are per-attempt and not comparable across siblings — fall back
    to the mtime walk.

    skip_prefixes keeps a curriculum's own stage dirs out of a root-level scan, so
    "what should stage 0 start from" can never answer with stage 3's policy.
    """
    best = None                                  # (wallclock, path)
    for d, _, filenames in _walk(ckpt_dir, skip_prefixes):
        if PROGRESS not in filenames:
            continue
        rec = read_progress(d)
        latest, wall = rec.get("latest"), rec.get("wallclock")
        if not latest or not isinstance(wall, (int, float)):
            continue                             # legacy int-only PROGRESS
        target = d / str(latest)
        if not target.is_dir():
            continue                             # pruned or never written
        if best is None or wall > best[0]:
            best = (wall, str(target))
    if best:
        return best[1]
    step = _max_checkpoint_step(ckpt_dir)
    if step:
        return str(Path(str(ckpt_dir)) / checkpoint_named(ckpt_dir, step))
    return _mtime_walk(ckpt_dir, skip_prefixes)


_MAX_RATE_GAP_S = 1800    # wallclock gap past which a pair is a restart, not a rate


def steps_per_second(log_path):
    """Median observed throughput from train_log.csv (wallclock,step,reward), or
    None if there isn't enough history. Used only to turn a step budget into an
    hours estimate — the number that decides whether a plan fits in a Colab
    session. Per-stage step counters restart, so negative deltas are skipped, and
    the median keeps the first eval of each stage (which carries ~300s of XLA
    compile) from dragging the estimate down.

    Pairs whose wallclock delta exceeds _MAX_RATE_GAP_S are skipped outright
    (not just left to the median): append-mode train_log.csv spans Colab
    restarts, and a multi-hour dropout gap between two rows produces a rate
    near zero for that one pair. A single such outlier is usually absorbed by
    the median, but a log with frequent dropouts can carry enough of them to
    skew even that — and they carry no throughput information at all, so
    dropping them costs nothing.
    """
    try:
        rows = []
        for line in Path(str(log_path)).read_text().splitlines():
            parts = line.split(",")
            if len(parts) >= 2:
                rows.append((float(parts[0]), int(parts[1])))
    except (OSError, ValueError):
        return None
    rates = []
    for (t0, s0), (t1, s1) in zip(rows, rows[1:]):
        if t1 > t0 and s1 > s0 and t1 - t0 <= _MAX_RATE_GAP_S:
            rates.append((s1 - s0) / (t1 - t0))
    if not rates:
        return None
    rates.sort()
    return rates[len(rates) // 2]


def checkpoint_named(ckpt_dir, step):
    """The checkpoint dir Brax wrote for `step`, by its actual name on disk (the
    zero-pad width is Brax's business, not ours). None if it isn't there yet."""
    try:
        for p in Path(str(ckpt_dir)).iterdir():
            if p.is_dir() and p.name.isdigit() and int(p.name) == step:
                return p.name
    except OSError:
        pass
    return None
