"""Where the CAD gates find the reference meshes they check against.

WHY THIS EXISTS (#166). The gates used to reach outside this repository for
their inputs — `/Users/afox/codebases/NOVA/original_body_files/...`,
`/Users/afox/codebases/NOVA/feetech_servo_models/...`, or the relative
equivalent `Path(__file__).parents[3] / "feetech_servo_models"`. Those live in
the ROOT repo, which is a DIFFERENT git repository from `proj/` (see CLAUDE.md
"Git"). So the gates ran on exactly one machine — the author's laptop — and
could not run in CI at all.

That matters more than it sounds. The gates are the only automated check on
this project's dominant bug class: geometry that is individually correct and
wrong at the seam (#163's backwards rear hip, #165's stale hip grid). A gate
that runs in one place, by hand, when someone remembers, is a code review with
extra steps.

THE RULE: a gate input is either produced by this repo (rendered STLs) or
VENDORED into it. No gate reaches outside `proj/`.

Vendored copies and where they came from:

  assets/servo.stl        <- NOVA/feetech_servo_models/converted_stl/servo.stl
                             STS3215_03a v1, incl. horn + bottom wheel bodies.
  (stock NovaSM3 meshes)  <- already vendored, long before this module, at
                             ros2_ws/src/nova_description/meshes/ for the URDF.
                             Reused here rather than copied a second time — a
                             second copy of a mesh is a second thing to drift.

To refresh a vendored asset, copy it in deliberately and say so in the commit.
The point is that the version the gates ran against is the version in the
commit, not whatever happened to be on one laptop that day.
"""

from __future__ import annotations

import pathlib

#: proj/ — this file is at proj/hardware/cad/cad_assets.py
PROJ = pathlib.Path(__file__).resolve().parents[2]

ASSETS = PROJ / "hardware" / "cad" / "assets"
#: stock NovaSM3 meshes, vendored for the URDF and reused by the gates
STOCK_MESHES = PROJ / "ros2_ws" / "src" / "nova_description" / "meshes"

_KNOWN = {
    "servo.stl": ASSETS / "servo.stl",
    "SM3_Foot.stl": STOCK_MESHES / "SM3_Foot.stl",
    "SM3_Frame_ChassisTrunk.stl": STOCK_MESHES / "SM3_Frame_ChassisTrunk.stl",
}


def asset(name: str) -> pathlib.Path:
    """Absolute path to a vendored gate input, or raise saying what is missing.

    Raises rather than returning a maybe-path: a gate that silently skips its
    reference mesh reports PASS while checking nothing, which is worse than a
    gate that does not run — you would believe it.
    """
    try:
        path = _KNOWN[name]
    except KeyError:
        raise KeyError(
            f"{name!r} is not a known CAD asset. Known: {sorted(_KNOWN)}. "
            f"Vendor it under {ASSETS} and add it here — do not reach outside "
            f"proj/ for it (see this module's docstring)."
        ) from None
    if not path.exists():
        raise FileNotFoundError(
            f"vendored CAD asset missing: {path}\n"
            f"It should be committed to this repo. If you are on a fresh "
            f"checkout, this is a bug in the vendoring, not something to work "
            f"around by pointing at a copy outside proj/."
        )
    return path


#: leg_v6 rendered parts — produced by this repo, not vendored.
LEG_V6 = PROJ / "hardware" / "cad" / "leg_v6"
