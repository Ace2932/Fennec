"""hardware/cad/leg_v6/build_all.sh and .github/workflows/cad-gates.yml each
carry a hand-typed copy of the mesh_health.py subject list for leg_v6.

WHY THIS EXISTS. Review on #405 found that the PR added `shoulder_sw1.stl`
and `sw1_coupon.stl` to build_all.sh's copy but not cad-gates.yml's -- and
ONLY cad-gates.yml's copy runs in CI (build_all.sh is a local/manual script;
no workflow invokes it, same disease test_ci_runs_every_test_file.py exists
for). So the two new parts passed review unchecked in CI, silently, because
there were two lists of the same subjects instead of one.

Fixing that one instance doesn't stop the next add from doing the same
thing, so this expands both lists to concrete STL filenames (globs like
`*_R.stl` resolved against the real files in leg_v6/) and asserts the sets
are equal. It also asserts every STL leg_v6/build_all.sh renders is checked
by SOMEONE's list, so a new render with no health check fails here instead
of shipping silently.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[4]
LEG_DIR = REPO / "hardware" / "cad" / "leg_v6"
BUILD_ALL = LEG_DIR / "build_all.sh"
WORKFLOW = REPO / ".github" / "workflows" / "cad-gates.yml"

#: STLs build_all.sh renders but deliberately does not mesh_health-check,
#: with the reason. Empty for leg_v6 today -- every rendered leg STL is
#: printable and is checked. Keep this here so a future deliberate
#: exclusion is a one-line, commented addition, not a silent gap.
RENDERED_BUT_NOT_HEALTH_CHECKED = {}


def _expand(names, cwd):
    """Expand a shell-style argument list (globs included) against `cwd`,
    the way bash would when build_all.sh / the CI step run there."""
    out = set()
    for n in names:
        if any(c in n for c in "*?["):
            matches = sorted(p.name for p in cwd.glob(n))
            assert matches, f"glob {n!r} matched nothing in {cwd}"
            out.update(matches)
        else:
            out.add(n)
    return out


def _mesh_health_args_from_build_all():
    text = BUILD_ALL.read_text()
    m = re.search(r"mesh_health\.py\s+(.+)", text)
    assert m, "build_all.sh no longer calls mesh_health.py"
    return _expand(m.group(1).split(), LEG_DIR)


def _mesh_health_args_from_workflow():
    text = WORKFLOW.read_text()
    m = re.search(
        r"Mesh health \(printable leg parts\).*?run:\s*\|\n"
        r"(.*?)(?=\n[ \t]*\n|\n[ \t]*- name:)",
        text, re.DOTALL)
    assert m, "cad-gates.yml no longer has the leg-gates mesh-health step"
    block = m.group(1)
    # Drop the `python ../mesh_health.py` invocation itself and line-continuations.
    args_text = re.sub(r"python\s+\.\./mesh_health\.py", "", block)
    args_text = args_text.replace("\\\n", " ")
    return _expand(args_text.split(), LEG_DIR)


def test_build_all_and_ci_mesh_health_lists_are_the_same_stls():
    local_set = _mesh_health_args_from_build_all()
    ci_set = _mesh_health_args_from_workflow()
    assert local_set == ci_set, (
        "build_all.sh and cad-gates.yml's leg-gates mesh-health step check "
        f"different STLs. Only in build_all.sh: {local_set - ci_set or None}. "
        f"Only in CI: {ci_set - local_set or None}.")


def test_every_stl_build_all_renders_is_mesh_health_checked():
    text = BUILD_ALL.read_text()
    rendered = set(re.findall(r"-o\s+([\w./]+\.stl)\b", text))
    # Only leg_v6's own directory -- a render into another dir (there are
    # none for leg_v6 today) is that dir's subject, not this one's.
    rendered = {r for r in rendered if "/" not in r}
    checked = _mesh_health_args_from_build_all()
    unchecked = rendered - checked - set(RENDERED_BUT_NOT_HEALTH_CHECKED)
    assert not unchecked, (
        f"build_all.sh renders {unchecked} but never mesh_health-checks "
        "them -- add to the mesh_health.py call or to "
        "RENDERED_BUT_NOT_HEALTH_CHECKED with a reason.")
