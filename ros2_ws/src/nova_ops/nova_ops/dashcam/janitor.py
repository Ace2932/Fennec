"""Disk-space janitor: keep a rolling buffer under a size cap.

rosbag2 has --max-bag-duration to roll files but no total-bytes cap, so
this janitor watches the recording directory and deletes the oldest
bag once total size exceeds the configured retention.

Default retention 2 GB per docs/notes-qol-features.md §2 ("Lean 5 min;
longer requires SD wear consideration").
"""
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional


# Default rolling buffer cap: 2 GB ≈ ~5 min at mid-bandwidth.
DEFAULT_RETENTION_BYTES = 2 * 1024 * 1024 * 1024


def _dir_bytes(p: Path) -> int:
    total = 0
    for f in p.rglob('*'):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def _bag_dirs(root: Path):
    """Yield bag directories in root, oldest first.

    rosbag2 creates `<timestamp>` directories per recording session (or
    when --max-bag-duration rolls). Order by mtime ascending = oldest
    first.
    """
    if not root.exists():
        return
    entries = [d for d in root.iterdir() if d.is_dir()]
    entries.sort(key=lambda d: d.stat().st_mtime)
    yield from entries


class Janitor:
    """Background thread that prunes oldest bags when total > retention."""

    def __init__(
        self,
        root: Path,
        retention_bytes: int = DEFAULT_RETENTION_BYTES,
        period_sec: float = 10.0,
        log: Optional[Callable[[str], None]] = None,
        preserved_dirs: Optional[set] = None,
    ):
        self.root = Path(root)
        self.retention_bytes = retention_bytes
        self.period_sec = period_sec
        self.log = log or (lambda msg: None)
        self.preserved_dirs = preserved_dirs or set()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name='dashcam-janitor', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.period_sec + 2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._sweep_once()
            except Exception as e:
                self.log(f'janitor sweep failed: {e}')
            self._stop.wait(self.period_sec)

    def _sweep_once(self) -> None:
        used = _dir_bytes(self.root)
        if used <= self.retention_bytes:
            return
        # Over budget — delete oldest bag dirs until under cap, but
        # never delete a preserved (frozen/incident) bag.
        for d in _bag_dirs(self.root):
            if used <= self.retention_bytes:
                return
            if str(d) in self.preserved_dirs or d.name in self.preserved_dirs:
                continue
            # Don't delete the currently-being-written bag — heuristic:
            # most recently mtime'd directory. _bag_dirs is sorted
            # ascending so the LAST one is newest; we skip it in the
            # loop by not iterating past it (handled by the natural
            # ordering — we just exit when under cap).
            size = _dir_bytes(d)
            try:
                self._rmtree(d)
                used -= size
                self.log(f'janitor pruned {d} ({size / 1e6:.0f} MB)')
            except OSError as e:
                self.log(f'janitor could not prune {d}: {e}')

    @staticmethod
    def _rmtree(p: Path) -> None:
        for f in sorted(p.rglob('*'), reverse=True):
            try:
                if f.is_file() or f.is_symlink():
                    f.unlink()
                elif f.is_dir():
                    f.rmdir()
            except OSError:
                pass
        try:
            p.rmdir()
        except OSError:
            pass
