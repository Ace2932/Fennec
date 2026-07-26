"""Drift guard: the CAD cable gate must sweep the ROM the robot actually has.

`hardware/cad/leg_v6/check_fit.py`'s cable check used to sweep a SYMMETRIC
haa +-45, which spent most of its samples on INBOARD travel the robot is not
permitted to use while sampling the legal outboard travel once (#157). It now
sweeps the asymmetric envelope, 15 deg inboard to 40 deg outboard, from
constants in that file.

The CAD tree is deliberately standalone -- it runs under build_all.sh with no
ROS on the path -- so it cannot import the MJCF or the ROS limits to check
itself. Those constants can therefore drift away from the model with nothing
to notice. This is that notice, and it lives here because this is the side that
CAN see both.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[4]
MJCF = REPO / "sim" / "nova_mjx" / "nova.xml"
CHECK_FIT = REPO / "hardware" / "cad" / "leg_v6" / "check_fit.py"

LEGS = ("FL", "FR", "RL", "RR")


def _load_leg_v6_check_fit():
    """Load leg_v6/check_fit.py BY PATH under a distinct module name.

    There are two `check_fit.py` in the tree (`hardware/cad/chassis/` and
    `hardware/cad/leg_v6/`). Importing by bare name means whichever test ran
    first and inserted its directory wins, and the second silently gets the
    WRONG module -- which is exactly how an earlier version of this guard
    ended up SKIPPING with what looked like a missing optional dependency.
    The distinct name is what prevents the collision; the path entry is still
    needed for the loaded module's own sibling imports.
    """
    if not CHECK_FIT.exists():
        pytest.skip(f"{CHECK_FIT} not present")
    spec = importlib.util.spec_from_file_location("_nova_leg_v6_check_fit", CHECK_FIT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_nova_leg_v6_check_fit"] = mod
    added = str(CHECK_FIT.parent)
    if added not in sys.path:
        sys.path.insert(0, added)
    try:
        spec.loader.exec_module(mod)
    except ImportError as exc:  # pragma: no cover - trimesh optional locally
        pytest.skip(f"leg_v6 check_fit unavailable: {exc}")
    return mod


@pytest.mark.skipif(not MJCF.exists(), reason="MJCF not present")
def test_cable_gate_haa_envelope_matches_the_model():
    import mujoco
    import numpy as np

    cf = _load_leg_v6_check_fit()
    m = mujoco.MjModel.from_xml_path(str(MJCF))

    for leg in LEGS:
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_hip")
        side = float(np.sign(m.body_pos[b][1]))
        lo, hi = m.jnt_range[
            mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{leg}_haa")
        ]
        # +haa moves the foot toward +y, so OUTBOARD is the limit on the leg's
        # own side of the model.
        outboard = hi if side > 0 else -lo
        inboard = -lo if side > 0 else hi
        assert np.degrees(outboard) == pytest.approx(
            cf.HAA_OUTBOARD_MAX_DEG, abs=0.6
        ), leg
        assert np.degrees(inboard) == pytest.approx(cf.HAA_INBOARD_MAX_DEG, abs=0.6), (
            leg
        )


def test_outboard_sign_is_declared():
    cf = _load_leg_v6_check_fit()
    assert cf.HAA_OUTBOARD_SIGN in (-1, 1)


def test_envelope_is_actually_asymmetric():
    """The bug being guarded was a symmetric sweep over an asymmetric range.

    If these two ever become equal the sweep is symmetric again and the whole
    point of #157 has quietly been undone.
    """
    cf = _load_leg_v6_check_fit()
    assert cf.HAA_OUTBOARD_MAX_DEG > cf.HAA_INBOARD_MAX_DEG
