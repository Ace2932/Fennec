"""Rolling MCAP recorder wrapping `ros2 bag record` as a subprocess.

Why subprocess instead of rosbag2_py? The Python API surface changes
between distros; the CLI is stable. For v1 we wrap the CLI, monitor
the process, and let the OS manage the bag files. v2 can migrate to
rosbag2_py if we need finer control (e.g., dynamic topic add).

Storage: MCAP (--storage mcap) — better tooling than sqlite3, Foxglove
plays it directly. Available in Humble via the
ros-humble-rosbag2-storage-mcap apt package.

Rolling: --max-bag-duration 60 splits into 60-second bag files; the
janitor thread (see janitor.py) deletes the oldest when the directory
exceeds the configured retention.
"""
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import List, Optional


class Recorder:

    def __init__(
        self,
        out_dir: Path,
        topics: List[str],
        max_bag_duration: int = 60,
        storage: str = 'mcap',
        compression_mode: str = 'none',  # 'file' to gzip per-bag
        node_name: str = 'dashcam_recorder',
    ):
        self.out_dir = Path(out_dir)
        self.topics = list(topics)
        self.max_bag_duration = max_bag_duration
        self.storage = storage
        self.compression_mode = compression_mode
        self.node_name = node_name
        self._proc: Optional[subprocess.Popen] = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        if self.running:
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        cmd = self._build_cmd()
        # Use a new process group so we can SIGINT cleanly later.
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(self.out_dir),
            preexec_fn=os.setsid,
        )

    def stop(self, timeout: float = 5.0) -> None:
        if not self.running:
            return
        try:
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
            self._proc.wait(timeout=timeout)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            # Force-kill if SIGINT didn't take
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._proc.wait(timeout=2.0)
        self._proc = None

    def _build_cmd(self) -> List[str]:
        # NOTE: --node-name was dropped (not portable across Humble patch
        # versions). The default rosbag2 recorder node name is fine.
        # Output directory is cwd; ros2 bag creates a timestamped subdir.
        cmd = [
            'ros2', 'bag', 'record',
            '--storage', self.storage,
            '--max-bag-duration', str(self.max_bag_duration),
        ]
        if self.compression_mode != 'none':
            cmd += ['--compression-mode', self.compression_mode]
            cmd += ['--compression-format', 'zstd']
        cmd += list(self.topics)
        return cmd

    def healthy(self) -> bool:
        """After start(), check that the subprocess is still running.

        Call this ~1 s after start() to catch fast failures (e.g., MCAP
        storage plugin missing). Returns False if the process exited
        early.
        """
        if self._proc is None:
            return False
        return self._proc.poll() is None

    @staticmethod
    def available() -> bool:
        """True iff `ros2 bag record` is on PATH AND the MCAP storage
        plugin reports as installed via dpkg (best-effort)."""
        if shutil.which('ros2') is None:
            return False
        # Best-effort check for the MCAP storage plugin. On non-apt
        # systems (or if dpkg-query is unavailable) we return True and
        # let the runtime fail loudly via healthy() instead.
        if shutil.which('dpkg-query') is None:
            return True
        import subprocess as _sp
        try:
            r = _sp.run(
                ['dpkg-query', '-W', '-f=${Status}',
                 'ros-humble-rosbag2-storage-mcap'],
                capture_output=True, text=True, timeout=2.0)
            return 'install ok installed' in (r.stdout or '')
        except (OSError, _sp.SubprocessError):
            return True   # don't gate on this — fall through to runtime check
