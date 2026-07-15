"""joint_map: rad<->ticks round-trip, clamp, and JOINT_ORDER vs joint_id_map.yaml.

  python deploy/test_joint_map.py      (or: pytest)
Only needs numpy + pyyaml (no jax / ROS).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joint_map import (  # noqa: E402
    JOINT_ORDER, NUM_JOINTS, RAW_FULL, JointMap, load_id_map,
)

_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../../ros2_ws/src/nova_description/config/joint_id_map.yaml"))


def test_order_matches_yaml():
    # policy index i must correspond to servo ID i+1 (identity, per-leg-seq)
    id_map = load_id_map(_YAML)
    assert len(id_map) == NUM_JOINTS == 12
    for i, name in enumerate(JOINT_ORDER):
        assert id_map[name] == i + 1, f"{name}: yaml id {id_map[name]} != {i+1}"
    print("OK  JOINT_ORDER matches joint_id_map.yaml (12 joints, identity)")


def test_roundtrip():
    jm = JointMap()                            # placeholder cal — formula must invert
    rng = np.random.default_rng(0)
    rad = rng.uniform(-1.0, 1.0, 12)           # within travel, won't clamp
    back = jm.ticks_to_rad(jm.rad_to_ticks(rad))
    err = float(np.max(np.abs(back - rad)))
    assert err < 2.0 / (RAW_FULL / (2 * np.pi)), err   # ~1-tick quantization
    print(f"OK  rad->ticks->rad within {err:.2e} rad (1-tick quant)")


def test_clamp_and_bounds():
    jm = JointMap()
    ticks = jm.rad_to_ticks(np.full(12, 10.0))          # way past travel
    assert ticks.shape == (12,)
    assert np.all(ticks >= 0) and np.all(ticks < RAW_FULL), ticks
    print("OK  extreme commands clamp into [0, 4095]")


def test_direction_flips_sign():
    jm = JointMap(home_tick=[2048] * 12, direction=[+1] * 12)
    jm_inv = JointMap(home_tick=[2048] * 12, direction=[-1] * 12)
    r = np.full(12, 0.5)
    # opposite direction -> ticks mirror about the home tick
    assert np.allclose(jm.rad_to_ticks(r) - 2048, -(jm_inv.rad_to_ticks(r) - 2048))
    print("OK  direction sign mirrors ticks about home")


if __name__ == "__main__":
    test_order_matches_yaml()
    test_roundtrip()
    test_clamp_and_bounds()
    test_direction_flips_sign()
    print("ALL JOINT-MAP CHECKS PASSED")
