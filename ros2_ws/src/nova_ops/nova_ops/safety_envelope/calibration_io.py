"""Read the homing calibration artifact into JointHomeCalib (#185).

WHY THIS EXISTS. Homing writes ~/.nova/calibration/servo_offsets_latest.yaml
and its own docstring says that file is "the stable symlink the gait layer
reads on start". Nothing read it. `storage.load_latest()` had zero consumers,
`nova_locomotion/node.py` takes its calibration from ROS params that default to
zeros, and nothing populated those params either — so a completed homing run
never reached the runtime at all.

WHY THE LOADER LIVES HERE AND NOT IN nova_calibration. nova_calibration already
imports nova_ops (servo_homing/node.py pulls confirm_urdf_sign out of
derived_signs), so nova_ops importing nova_calibration back would be a package
cycle — the thing test_leg_ik_stays_pure_math_no_ros_package_pull_in exists to
prevent. Reading the FILE is not the same as importing the package, so the
schema is parsed here.

That leaves the schema written in one package and read in another, which is
exactly the seam this project keeps getting wrong. So it is tested ACROSS the
seam: the test writes with nova_calibration's real save_offsets() and reads it
back with this, rather than asserting against a hand-built dict that would
happily agree with a stale reader.

Validation is NOT re-implemented here. The doc is converted to the bus-ordered
lists build_calib() already takes, so its fail-loud doctrine (a sign with no
home_raw raises rather than defaulting to a 2048-count error) applies unchanged.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from .firmware_limits import N_JOINTS, JointHomeCalib, build_calib

#: Where homing puts it. Overridable so a node can be pointed elsewhere.
DEFAULT_CALIBRATION_PATH = os.path.expanduser(
    "~/.nova/calibration/servo_offsets_latest.yaml"
)

SUPPORTED_SCHEMA = 1


class CalibrationFormatError(ValueError):
    """The artifact exists but is not something we can safely read."""


def calibration_from_doc(doc: dict) -> Dict[int, JointHomeCalib]:
    """Parsed YAML -> {bus id: JointHomeCalib}. Raises rather than guessing.

    An unknown schema version is refused outright. Silently reading a v2 file
    with v1 assumptions is how a calibration turns into a wrong-but-plausible
    limit table, and the firmware backstop is built from this same data — so a
    misread would move the guard and the command together, the #154 shape.
    """
    if not doc:
        return {}
    schema = doc.get("schema")
    if schema != SUPPORTED_SCHEMA:
        raise CalibrationFormatError(
            f"calibration schema {schema!r} is not supported "
            f"(this reads schema {SUPPORTED_SCHEMA}). Refusing to guess: the "
            f"firmware limit table is built from this."
        )
    joints = doc.get("joints") or {}
    if not isinstance(joints, dict):
        raise CalibrationFormatError("'joints' is not a mapping")

    home = [0.0] * N_JOINTS
    sign = [0] * N_JOINTS
    for raw_jid, entry in joints.items():
        try:
            jid = int(raw_jid)
        except (TypeError, ValueError):
            raise CalibrationFormatError(f"joint key {raw_jid!r} is not an int")
        if not 1 <= jid <= N_JOINTS:
            raise CalibrationFormatError(
                f"joint id {jid} outside 1..{N_JOINTS} — wrong file?"
            )
        if not isinstance(entry, dict):
            raise CalibrationFormatError(f"joint {jid}: entry is not a mapping")
        if "home_raw" not in entry:
            raise CalibrationFormatError(f"joint {jid}: no home_raw")
        home[jid - 1] = float(entry["home_raw"])
        # urdf_sign 0 (or absent) = not observed = uncalibrated, which is what
        # build_calib already means by 0. A joint homed before homing produced
        # signs lands here, and that is the correct reading of it.
        sign[jid - 1] = int(entry.get("urdf_sign", 0) or 0)

    return build_calib(home, sign)


def resolve_calibration(home_raw, urdf_sign, path: Optional[str] = None):
    """Calibration for a runtime node, plus WHERE it came from (#188).

    Returns ``(calib, source)``. Order:

      1. ROS params, if they carry a real calibration. A joint is only
         calibrated once its sign has been OBSERVED, so an all-zero
         ``urdf_sign`` is the declared default, not a calibration — that is the
         same reading ``build_calib`` already applies. Params win when set, so
         bench work can override the artifact deliberately.
      2. The homing artifact on disk. This is what homing actually writes and,
         until #188, what nothing actually read: the params had no producer, so
         a node relying on them ran permanently uncalibrated. On the command
         path that means RADIANS published to a firmware reading raw counts.
      3. Nothing, which is the honest pre-homing state.

    `source` exists so the caller can say which it used. Two very different
    situations — "an operator overrode the calibration" and "homing has never
    run" — otherwise look identical from outside.
    """
    signs = list(urdf_sign or [])
    if any(int(s) != 0 for s in signs):
        return build_calib(list(home_raw or []), signs), "params"
    calib = read_calibration(path)
    if calib:
        return calib, f"file:{path or DEFAULT_CALIBRATION_PATH}"
    return {}, "none"


def read_calibration(path: Optional[str] = None) -> Dict[int, JointHomeCalib]:
    """Load from disk. Missing file -> {} (the pre-homing state, not an error).

    A missing artifact is normal before the first homing run and must not stop a
    node from starting; what must not happen is treating it as "calibrated with
    zeros", which is why build_calib's rules do the interpreting.
    """
    import yaml  # local: keeps this module importable without yaml installed

    p = path or DEFAULT_CALIBRATION_PATH
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return calibration_from_doc(yaml.safe_load(f))
