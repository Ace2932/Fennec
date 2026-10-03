"""Fennec#490: the tower thermal guard keeps SEPARATE GPU and CPU guards.

Drives tower/thermal-guard.sh's real check_once() through bash with stubbed readings, so the
test needs no nvidia-smi, sensors or systemd. Run: python sim/nova_mjx/test_thermal_guard.py
(or pytest).
"""
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "tower", "thermal-guard.sh")
# dashboard/dashboard.py's THERMAL_RE: the guard's log lines must keep matching it.
DASH_RE = re.compile(r"^(\S+ \S+) gpu (\d+)C cpu (\d+)C ([\d.]+)W")


def run(readings, script=GUARD):
    """readings: list of (gpu, cpu). Returns (log text, number of stop_training calls)."""
    with tempfile.TemporaryDirectory() as d:
        log, stops, gpu, cpu = (os.path.join(d, n) for n in ("guard.log", "stops", "gpu", "cpu"))
        with open(gpu, "w") as f:
            f.write("\n".join(str(g) for g, _ in readings) + "\n")
        with open(cpu, "w") as f:
            f.write("\n".join(str(c) for _, c in readings) + "\n")
        prog = f"""
set -u
THERMAL_GUARD_LIB=1 THERMAL_LOG={log!r} . {script!r}
i=0
read_gpu() {{ sed -n "$((i+1))p" {gpu!r}; }}
read_cpu() {{ sed -n "$((i+1))p" {cpu!r}; }}
read_pw()  {{ echo 15.5; }}
stop_training() {{ echo x >> {stops!r}; }}
for ((i=0; i<{len(readings)}; i++)); do check_once || true; done   # rc 10 = the GPU guard fired
"""
        subprocess.run(["bash", "-c", prog], check=True)
        text = open(log).read()
        n_stops = len(open(stops).read().split()) if os.path.exists(stops) else 0
        return text, n_stops


def test_cpu_hot_never_stops_training():
    text, stops = run([(30, 96)] * 3)
    assert stops == 0, "CPU heat must never stop GPU training"
    assert "CPU HOT" in text and "THERMAL STOP" not in text


def test_gpu_hot_stops_training_once():
    text, stops = run([(91, 50)] * 3)
    assert stops == 1 and text.count("THERMAL STOP") == 1


def test_cpu_between_90_and_95_is_quiet():
    # The 2026-10-02 false stops: CPU 90-92 C, GPU 28 C.
    text, stops = run([(28, 92)] * 6)
    assert stops == 0 and "CPU HOT" not in text and "THERMAL STOP" not in text


def test_gpu_streak_resets_on_a_cool_reading():
    _, stops = run([(91, 50), (91, 50), (80, 50), (91, 50), (91, 50)])
    assert stops == 0


def test_hot_cpu_does_not_count_toward_the_gpu_guard():
    # Interleaved: neither guard alone reaches 3 in a row. A shared counter would stop here.
    _, stops = run([(91, 50), (30, 96), (91, 50), (30, 96)])
    assert stops == 0


def test_log_lines_still_parse_for_the_dashboard():
    text, _ = run([(29, 63)])
    line = text.splitlines()[0]
    m = DASH_RE.match(line)
    assert m and m.group(2) == "29" and m.group(3) == "63", line


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("THERMAL GUARD TEST OK")
