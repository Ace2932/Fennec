"""Every test_*.py in this repo is executed by SOME CI job.

WHY THIS EXISTS. "A test file that no job runs" was found FIVE separate times
in one day (2026-08-08/09), and the fifth was in the fix for the fourth:

  #315  sim/nova_mjx/test_*.py          -- 9 files, no job. Hiding a
                                           BLIND_REWARD_PIN that had never
                                           passed at ANY commit in its history.
  #318  scripts/test_set_servo_ids.py   -- no job. It exists BECAUSE #287 item 5
                                           asked for a test; the test for a
                                           coverage gap had a coverage gap.
  #318  hardware/pcb-mods/tools/
          test_fab_gate.py              -- no job.
  #321  check_hole_breakout.py          -- a GATE with refs=0 (not a test file,
                                           same disease).
  #333  sim/nova_mjx/deploy/test_*.py   -- 4 files. #316's glob was top-level
                                           only, so MY OWN fix reproduced the
                                           bug one directory down.

Five by hand is enough. The failure is silent by construction -- an unrun test
cannot complain -- so the only thing that catches it is something that goes
looking. This is that thing.

HOW IT AVOIDS BEING A LIE ITSELF. A registry mapping paths to jobs would rot
the moment someone edited a workflow, and would then assert coverage that no
longer exists. So each entry also carries EVIDENCE: the literal line from the
workflow that runs those files. Both halves are checked --

  1. every discovered test file matches a registered location, and
  2. every registered location's evidence string still appears in the workflow
     it names.

Editing the workflow without updating this file fails (2). Adding tests in a
new place without wiring CI fails (1).
"""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[4]
WORKFLOWS = REPO / ".github" / "workflows"

#: (location prefix, workflow file, the literal line in it that runs these).
#: Longest prefix wins, so deploy/ is matched before sim/nova_mjx/.
COVERED_BY = (
    ("ros2_ws/src/nova_ops/test/", "ros-pytest.yml",
     "for pkg in nova_ops nova_calibration nova_locomotion; do"),
    ("ros2_ws/src/nova_calibration/test/", "ros-pytest.yml",
     "for pkg in nova_ops nova_calibration nova_locomotion; do"),
    ("ros2_ws/src/nova_locomotion/test/", "ros-pytest.yml",
     "for pkg in nova_ops nova_calibration nova_locomotion; do"),
    ("sim/nova_mjx/deploy/", "sim-tests.yml",
     "for t in test_*.py deploy/test_*.py; do"),
    ("sim/nova_mjx/", "sim-tests.yml",
     "for t in test_*.py deploy/test_*.py; do"),
    ("scripts/", "ros-pytest.yml",
     "python -m pytest scripts/test_set_servo_ids.py -q"),
    ("hardware/pcb-mods/tools/", "ros-pytest.yml",
     "python hardware/pcb-mods/tools/test_fab_gate.py"),
)

#: Directories that are not ours to run.
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pio",
             ".claude", "archive", "nova-sm3-upstream"}


def _discover():
    found = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                found.append(str(pathlib.Path(root, f).relative_to(REPO)))
    return sorted(found)


def test_repo_has_test_files_at_all():
    """Guard the guard: if discovery silently found nothing, every assertion
    below would pass vacuously. That is the exact shape of bug this file is
    about, so it does not get to have it."""
    found = _discover()
    assert len(found) > 20, f"discovery looks broken, found only {found}"


def test_every_test_file_is_run_by_some_ci_job():
    orphans = []
    for rel in _discover():
        prefixes = sorted((p for p, _w, _e in COVERED_BY if rel.startswith(p)),
                          key=len, reverse=True)
        if not prefixes:
            orphans.append(rel)
    assert not orphans, (
        "these test files are executed by NO CI job -- wire them into a "
        "workflow and register the location in COVERED_BY:\n  "
        + "\n  ".join(orphans))


def test_every_registered_location_still_matches_its_workflow():
    """The registry must not outlive the wiring it claims."""
    stale = []
    for prefix, wf, evidence in COVERED_BY:
        path = WORKFLOWS / wf
        if not path.exists():
            stale.append(f"{prefix}: workflow {wf} does not exist")
            continue
        if evidence not in path.read_text():
            stale.append(
                f"{prefix}: {wf} no longer contains the line that runs it "
                f"({evidence!r})")
    assert not stale, "\n  ".join(stale)


def test_every_registered_location_actually_has_tests():
    """A prefix that matches nothing is dead weight that hides a later move."""
    found = _discover()
    for prefix, _wf, _e in COVERED_BY:
        assert any(f.startswith(prefix) for f in found), (
            f"COVERED_BY entry {prefix!r} matches no test file -- delete it "
            f"or fix the path")
