"""Bringup PROFILES actions resolve to real installed entry points (#285).

#285: PROFILES["walk"] referenced package 'nova_gait', executable
'gait_controller' — neither ever existed (the real package is
nova_locomotion, executable gait_node). Nothing caught it because nothing
parsed setup.py against the profile table, AND because bringup.launch.py's
own PackageNotFoundError handling SKIPs a missing package cleanly (by
design, for external SDK deps) — a typo'd/never-wired-up package looks
identical to a legitimate not-yet-installed one at runtime. This test
tells them apart from the source tree, no colcon build/install needed.

Packages that live in THIS workspace (ros2_ws/src/<pkg>/setup.py present)
must resolve their action's executable to a real console_scripts entry.
Packages that don't are only allowed via KNOWN_EXTERNAL_NODE_PACKAGES —
vendor/apt ROS packages this workspace deliberately does not source-vendor.
Anything else (a typo, or a stub profile entry nobody ever wired up) fails
loudly instead of silently no-op'ing at launch time.
"""
import ast
from pathlib import Path

import pytest

from nova_ops.bringup import PROFILES, resolve_actions

SRC = Path(__file__).resolve().parents[2]  # ros2_ws/src

# 'node' actions whose package is a real external ROS package this
# workspace does not vendor source for (apt/SDK install, not ours to
# parse). bringup.launch.py's PackageNotFoundError SKIP is the intended
# behaviour for these when not installed locally.
KNOWN_EXTERNAL_NODE_PACKAGES = {"foxglove_bridge"}


def _console_script_names(package: str) -> set:
    """Parse `entry_points={"console_scripts": [...]}` out of a local
    package's setup.py via ast — no need to import/execute it."""
    setup_py = SRC / package / "setup.py"
    tree = ast.parse(setup_py.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup":
            for kw in node.keywords:
                if kw.arg == "entry_points":
                    entry_points = ast.literal_eval(kw.value)
                    scripts = entry_points.get("console_scripts", [])
                    return {s.split("=")[0].strip() for s in scripts}
    raise AssertionError(f"no setup() entry_points found in {setup_py}")


def _all_node_actions():
    """(profile_name, pkg, exe) for every ('node', ...) action, across
    every profile, deduped by (pkg, exe)."""
    local_packages = {p.name for p in SRC.iterdir() if (p / "setup.py").is_file()}
    seen = set()
    out = []
    for profile_name in PROFILES:
        for action in resolve_actions(profile_name):
            if action[0] != "node":
                continue
            key = (action[1], action[2])
            if key in seen:
                continue
            seen.add(key)
            out.append((profile_name, action[1], action[2], action[1] in local_packages))
    return out


ALL_NODE_ACTIONS = _all_node_actions()
LOCAL_NODE_ACTIONS = [(p, k, e) for p, k, e, is_local in ALL_NODE_ACTIONS if is_local]


def test_every_node_action_package_is_local_or_a_known_external():
    # The #285 regression itself: 'nova_gait' was neither a workspace
    # package nor a declared external dep — it was a stub that quietly
    # never got wired to the real node. This must be an explicit
    # allowlist entry, not a silent pass.
    unresolved = [
        (profile, pkg, exe)
        for profile, pkg, exe, is_local in ALL_NODE_ACTIONS
        if not is_local and pkg not in KNOWN_EXTERNAL_NODE_PACKAGES
    ]
    assert not unresolved, (
        "node action(s) reference a package that is neither in this workspace "
        "nor in KNOWN_EXTERNAL_NODE_PACKAGES (typo, or a never-wired-up stub — "
        f"see #285): {unresolved}"
    )


@pytest.mark.parametrize(
    "profile_name,pkg,exe",
    LOCAL_NODE_ACTIONS,
    ids=[f"{p}:{k}/{e}" for p, k, e in LOCAL_NODE_ACTIONS],
)
def test_node_action_resolves_to_a_real_entry_point(profile_name, pkg, exe):
    scripts = _console_script_names(pkg)
    assert exe in scripts, (
        f'PROFILES["{profile_name}"] launches {pkg}/{exe}, but {pkg}/setup.py '
        f"console_scripts only has: {sorted(scripts)}"
    )


# --- #289: a profile that can COMMAND JOINTS must publish the firmware tables ---

#: Anything that ends up publishing /joint_commands. Add to this when a new
#: controller appears -- that is the point: the test should start failing until
#: someone decides whether the new controller needs the tables (it does).
CONTROLLERS = {
    ("node", "gait_node"),
    ("launch", "policy.launch.py"),
}


def _controllers_in(profile_name):
    got = set()
    for a in resolve_actions(profile_name):
        if (a[0], a[2]) in CONTROLLERS:
            got.add(a[2])
    return got


def test_every_motion_profile_publishes_firmware_tables():
    """The Teensy boots with BOTH protection tables wide open -- per-joint
    0..4095 and the posture backstop off -- and ONLY firmware_tables narrows
    them (#185). So a profile that can command joints without it runs the
    servos with no firmware-side limit, an inert #142/#280 chassis backstop,
    and no limp_pose, which silently degrades #145's controlled limp to an
    instant torque cut.

    This is not hypothetical. Until #289's profile landed, `policy_node` was in
    NO profile at all, so the only documented way to run the learned policy was
    `policy.launch.py` standalone -- node only, no tables. The scripted path had
    the protection and the neural-network path did not.
    """
    offenders = []
    for name in PROFILES:
        ctrl = _controllers_in(name)
        if not ctrl:
            continue
        execs = {a[2] for a in resolve_actions(name) if a[0] == "node"}
        if "firmware_tables" not in execs:
            offenders.append(f"{name} runs {sorted(ctrl)} without firmware_tables")
    assert not offenders, "; ".join(offenders)


def test_walk_and_policy_carry_the_same_stack():
    """`walk` and `policy` must differ ONLY by their controller.

    They are built from the shared _MOTION_STACK precisely so the learned path
    cannot quietly lose protection the scripted path keeps. If someone inlines
    one of them back into a literal list, this fails.
    """
    def non_controller(name):
        return [a for a in resolve_actions(name) if (a[0], a[2]) not in CONTROLLERS]
    assert non_controller("walk") == non_controller("policy")


def test_walk_and_policy_are_mutually_exclusive():
    """Both end in a controller publishing /joint_commands. If a profile ever
    resolves to BOTH, two publishers race on the joint path and the servos take
    whichever message landed last -- so no profile may include both."""
    for name in PROFILES:
        assert len(_controllers_in(name)) <= 1, (
            f"profile {name!r} resolves to two joint-command publishers: "
            f"{sorted(_controllers_in(name))}")
