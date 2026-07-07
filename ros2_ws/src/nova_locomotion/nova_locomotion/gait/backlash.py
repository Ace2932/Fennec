"""Backlash compensation with reversal hysteresis (pure logic, no ROS).

Roadmap stage 3 item 3 (docs/roadmap-trot-balance.md): feed-forward the
measured foot backlash (~2 mm at the foot ~= 0.5 deg at the joints, the
Robo9-measured class) at direction reversals. Cheap, transforms
tracking on position servos — the geartrain sits mid-slop after every
reversal and the first half-backlash of commanded motion goes nowhere.

apply() biases the commanded target HALF the joint's backlash in the
direction of motion, so the OUTPUT side lands where the target says.
Hysteresis: the bias only flips after a REAL reversal — the target has
to retreat more than `deadband` from the running extreme reached in the
current direction. Command jitter inside the deadband keeps the old
bias (flipping on noise would inject 2x-backlash square waves, worse
than no compensation).

DEFAULT_BACKLASH_RAD is a placeholder table: 0.0087 rad (0.5 deg) per
joint, MEASURE-AT-STAGE-1 — roadmap stage 1.3 measures per-joint values
at direction reversals during the first powered stand/sit reps; feed
them back here per joint (hips and knees will differ under load).
"""

from __future__ import annotations
import math
from typing import Dict, Hashable

# MEASURE-AT-STAGE-1: per-joint placeholder, the Robo9-measured class
# (~0.5 deg). Keyed FL_haa..RR_kfe to match joint_id_map names.
_LEGS = ("FL", "FR", "RL", "RR")
_JOINTS = ("haa", "hfe", "kfe")
DEFAULT_BACKLASH_RAD: Dict[str, float] = {
    f"{leg}_{joint}": 0.0087 for leg in _LEGS for joint in _JOINTS
}


class BacklashComp:
    """Stateful per-joint half-backlash bias with reversal hysteresis.

    One instance per command stream (it tracks direction state); keys
    are whatever the caller commands by — joint names or bus IDs.
    """

    def __init__(
        self,
        per_joint_rad: Dict[Hashable, float] | None = None,
        deadband: float = 0.002,
    ):
        self.per_joint_rad = dict(
            DEFAULT_BACKLASH_RAD if per_joint_rad is None else per_joint_rad
        )
        self.deadband = deadband
        self._dir: Dict[Hashable, float] = {}  # +1.0 / -1.0 last real direction
        self._extreme: Dict[Hashable, float] = {}  # furthest target in that dir

    def reset(self) -> None:
        """Forget direction state (e.g. after torque-off / E-stop — the
        geartrain position is unknown again)."""
        self._dir.clear()
        self._extreme.clear()

    def apply(
        self, joint: Hashable, target: float, direction_of_motion: float
    ) -> float:
        """Return `target` biased by half-backlash in the motion direction.

        direction_of_motion: the intended motion sign (e.g. the target
        delta or planned velocity); only its sign is used, and a real
        flip is accepted only once the target retreats > deadband from
        the extreme reached in the current direction. Zero / unknown
        direction keeps the current bias. Joints without a table entry
        pass through unbiased.
        """
        b = self.per_joint_rad.get(joint, 0.0)
        d = math.copysign(1.0, direction_of_motion) if direction_of_motion else 0.0

        cur = self._dir.get(joint)
        if cur is None:
            # first commanded motion seeds the direction (no hysteresis
            # to overcome — the train is mid-slop, bias immediately)
            if d != 0.0:
                self._dir[joint] = d
                self._extreme[joint] = target
            cur = self._dir.get(joint)
        elif d != 0.0 and d != cur:
            # candidate reversal: only real beyond the deadband from the
            # running extreme in the CURRENT direction
            if (self._extreme[joint] - target) * cur > self.deadband:
                self._dir[joint] = d
                self._extreme[joint] = target
                cur = d
        if cur is not None and d == cur:
            # still advancing: run the extreme forward
            if (target - self._extreme[joint]) * cur > 0.0:
                self._extreme[joint] = target

        if cur is None:
            return target
        return target + cur * 0.5 * b
