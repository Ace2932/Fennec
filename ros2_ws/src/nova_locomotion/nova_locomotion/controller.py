"""Gait-node core: mode state machine -> bus-ordered joint targets.

Roadmap stage 1 item 1 (docs/roadmap-trot-balance.md): everything the
gait node computes, importable and tested WITHOUT rclpy. node.py is the
thin glue that feeds this clock ticks and publishes the result through
nova_ops' SafeJointCommandPublisher.

Pipeline per tick: mode -> canonical foot targets (choreo keyframe
blends / crawl+CoM-shift / trot) -> solve_side with the X-config
KNEE_FORWARD branch (physical radians, solve_side owns the mirror) ->
bus-ID ordering from the canonical joint_id_map (positions[i] = bus ID
i+1, the /joint_commands + envelope convention) -> backlash comp
half-bias (stage 3.3).

Choreo sequences are precomputed at set_mode() and indexed by elapsed
time (robust to any timer rate; the 100 Hz node just samples). After a
sequence finishes the controller HOLDS its last pose. idle returns
None — publish nothing, servos hold at the firmware level.

Mode sequencing (stand before trot, etc.) is the operator's job for
now — stage 1 is bench bring-up; interlocks belong with the preflight
lane once there's hardware truth to gate on.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from nova_locomotion.choreo.stand import ChoreoParams, sit_down, stand_up
from nova_locomotion.gait import crawl as crawl_gait
from nova_locomotion.gait import trot as trot_gait
from nova_locomotion.gait.backlash import BacklashComp
from nova_locomotion.kinematics.body_pose import (
    BodyPose,
    BodyPoseParams,
    foot_targets,
    foot_world,
)
from nova_locomotion.kinematics.leg_ik import KNEE_FORWARD, LEG_SIDE, solve_side

LEGS = ("FL", "FR", "RL", "RR")
JOINTS = ("haa", "hfe", "kfe")  # per-leg chain order == joint_id_map order
MODES = ("idle", "stand_up", "sit", "crawl", "trot")

Pose = Dict[str, Tuple[float, float, float]]


@dataclass(frozen=True)
class ControllerParams:
    choreo: ChoreoParams = ChoreoParams()
    trot: trot_gait.TrotParams = trot_gait.TrotParams()
    crawl: crawl_gait.CrawlParams = crawl_gait.CrawlParams()
    body: BodyPoseParams = BodyPoseParams()
    trot_freq: float = 1.5  # strides/s (roadmap stage-3 starting band)
    crawl_freq: float = 0.4  # slow: statically stable at every instant


def pose_to_positions(pose: Pose, id_map: Dict[str, int]) -> List[float]:
    """Physical joint pose -> 12-slot positions list, positions[i] = bus
    ID i+1 (the /joint_commands convention the envelope indexes by).
    id_map is nova_ops.joint_map.load_joint_id_map() — reused, never
    restated."""
    out = [0.0] * 12
    for leg in LEGS:
        for j, joint in enumerate(JOINTS):
            bus_id = id_map[f"{leg}_{joint}"]
            out[bus_id - 1] = pose[leg][j]
    return out


def positions_to_pose(positions, id_map: Dict[str, int]) -> Pose:
    """Inverse of pose_to_positions (e.g. /joint_states -> start_pose)."""
    pose: Dict[str, list] = {leg: [0.0, 0.0, 0.0] for leg in LEGS}
    for leg in LEGS:
        for j, joint in enumerate(JOINTS):
            pose[leg][j] = float(positions[id_map[f"{leg}_{joint}"] - 1])
    return {leg: tuple(v) for leg, v in pose.items()}


def gait_pose(mode: str, phase: float, p: ControllerParams) -> Pose:
    """Canonical gait targets at `phase` -> physical joint pose.

    trot: generator targets straight through solve_side. crawl: targets
    composed with the CoM pre-shift through body-pose IK (the stage-2
    coupling), then solve_side. All mirroring stays in solve_side /
    body_pose — never here."""
    if mode == "trot":
        feet = trot_gait.all_feet(phase, p.trot)
    elif mode == "crawl":
        raw = crawl_gait.all_feet(phase, p.crawl)
        dx, dy = crawl_gait.body_shift(phase, p.crawl)
        anchors = {leg: foot_world(BodyPose(), leg, raw[leg], p.body) for leg in LEGS}
        feet = foot_targets(BodyPose(dx=dx, dy=dy), anchors, p.body)
    else:
        raise ValueError(f"gait_pose: not a gait mode: {mode!r}")
    return {
        leg: solve_side(LEG_SIDE[leg], feet[leg], p.body.leg, KNEE_FORWARD[leg])
        for leg in LEGS
    }


class GaitController:
    """Time-driven mode machine. Feed monotonic seconds; get physical
    joint poses (or None for idle). Owns the backlash comp state."""

    def __init__(
        self,
        params: ControllerParams = ControllerParams(),
        backlash: Optional[BacklashComp] = None,
    ):
        self.p = params
        self.backlash = backlash  # keyed by joint NAME when present
        self.mode = "idle"
        self._t0 = 0.0
        self._frames: List[Pose] = []  # active choreo sequence
        self._hold: Optional[Pose] = None  # pose held after a sequence/gait stop
        self._last_raw: Dict[str, float] = {}  # pre-bias targets (comp direction)

    def set_mode(self, mode: str, now: float, current_pose: Optional[Pose] = None):
        """Switch mode at time `now`. current_pose (from /joint_states)
        seeds choreo sequences — never assume the robot is at a keyframe
        (post-E-stop rule, choreo/stand.py)."""
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r} (modes: {MODES})")
        start = current_pose or self._hold
        if mode == "stand_up":
            self._frames = list(stand_up(self.p.choreo, start_pose=start))
        elif mode == "sit":
            self._frames = list(sit_down(self.p.choreo, start_pose=start))
        else:
            self._frames = []
        if mode in ("crawl", "trot") and self.backlash is not None:
            # geartrain state is only trustworthy within a motion regime
            self.backlash.reset()
        self.mode = mode
        self._t0 = now

    def update(self, now: float) -> Optional[Pose]:
        """Physical joint pose for time `now`, or None (idle, nothing
        commanded yet)."""
        t = now - self._t0
        if self.mode in ("stand_up", "sit"):
            if not self._frames:
                return self._hold
            i = min(int(t / self.p.choreo.dt), len(self._frames) - 1)
            self._hold = self._frames[i]
            return self._hold
        if self.mode == "trot":
            self._hold = gait_pose("trot", t * self.p.trot_freq, self.p)
            return self._hold
        if self.mode == "crawl":
            self._hold = gait_pose("crawl", t * self.p.crawl_freq, self.p)
            return self._hold
        return self._hold  # idle: hold last commanded pose, or None

    def command_positions(
        self, now: float, id_map: Dict[str, int]
    ) -> Optional[List[float]]:
        """update() -> bus-ordered radians with backlash comp applied.
        The node publishes exactly this (through the safety envelope)."""
        pose = self.update(now)
        if pose is None:
            return None
        positions = pose_to_positions(pose, id_map)
        if self.backlash is not None:
            for leg in LEGS:
                for joint in JOINTS:
                    name = f"{leg}_{joint}"
                    idx = id_map[name] - 1
                    tgt = positions[idx]
                    prev = self._last_raw.get(name)
                    direction = 0.0 if prev is None else tgt - prev
                    self._last_raw[name] = tgt
                    positions[idx] = self.backlash.apply(name, tgt, direction)
        return positions
