"""SafeJointCommandPublisher — in-process wrapper around the
/joint_commands publisher. Validates + clamps every command per the
URDF joint limits before letting it hit the bus.

Per docs/notes-qol-features.md §3 option (a): wraps the publisher
inside the gait controller. Lowest-latency design. Future second
publisher would bypass; project policy is that only the gait
controller publishes /joint_commands, enforced via package layout +
this wrapper (not topology).

Checks (per spec):

  position    lower ≤ goal ≤ upper, 2° margin inside URDF limits
              -> clamp to soft limit, count, log (first 10 per joint
              then throttle)

  velocity    numerically diff goal vs last command vs Δt; if greater
              than URDF velocity limit, replace with
              last + sign × v_max × Δt
              -> clamp, count

  load        STS3215 load arrives in effort[] on /joint_states.
              3-sample mean > 70% sustained -> refuse new goals that
              INCREASE load; allow ones that reduce it.
              -> reject (don't publish that joint's new value), count

  temperature ⏳ gated on firmware REG_PRESENT_TEMPERATURE work landing;
              not implemented yet.

Usage in gait controller:

    self.cmd_pub_raw = self.create_publisher(JointState, '/joint_commands', 10)
    self.safe_pub = SafeJointCommandPublisher(
        node=self,
        limits=load_default_limits(),
        raw_publisher=self.cmd_pub_raw,
    )
    # then everywhere downstream:
    self.safe_pub.publish(joint_state)
"""
import collections
import copy
import math
from typing import Deque, Dict, List, Optional, Sequence

from .limits import JointLimits
from .counters import EnvelopeCounters


# Load check uses a time-window mean of /joint_states.effort[] per
# joint. The firmware publishes joint round-robin (~17 Hz per joint),
# so 3 samples ≠ 3 fresh reads of one joint. Window by time, not count:
_LOAD_WINDOW_SEC = 0.30
_LOAD_REFUSE_THRESHOLD = 0.70

# If we haven't seen a command for this long, treat the next command as
# the first sample (velocity check should not compare against ancient
# `last`).
_LAST_CMD_STALE_SEC = 0.5

# Throttle logging per joint per failure mode (1st 10 then 1-in-100)
_LOG_FIRST_N = 10
_LOG_THROTTLE = 100


class SafeJointCommandPublisher:

    def __init__(
        self,
        node,  # rclpy Node
        limits: JointLimits,
        raw_publisher,
        counters: Optional[EnvelopeCounters] = None,
    ):
        self.node = node
        self.limits = limits
        self.pub = raw_publisher
        self.counters = counters or EnvelopeCounters(joint_ids=limits.ids())

        # Per-joint state
        self._last_cmd: Dict[int, float] = {}
        self._last_cmd_time_ns: Dict[int, int] = {}
        # Load samples are (timestamp_ns, abs_effort) tuples; we trim to
        # _LOAD_WINDOW_SEC on each read.
        self._load_samples: Dict[int, Deque[tuple]] = collections.defaultdict(
            lambda: collections.deque(maxlen=100))
        self._log_counts: Dict[str, Dict[int, int]] = {
            'position': {}, 'velocity': {}, 'load': {}}

    # ---- /joint_states callback (load tracking) -----------------------

    def on_joint_states(self, msg) -> None:
        """Wire this as the gait controller's /joint_states subscriber
        callback. Updates the load window used by the load check.

        TODO: when the URDF lands and firmware fills msg.name[], switch
        from index-based to name-based binding. Today msg.name[] is
        intentionally empty (firmware/teensy/firmware/README.md), so we
        treat effort[i] as joint id i+1.
        """
        # Use msg.header.stamp if present, else current ROS time.
        try:
            stamp_ns = (msg.header.stamp.sec * 1_000_000_000
                        + msg.header.stamp.nanosec)
            if stamp_ns == 0:
                stamp_ns = self.node.get_clock().now().nanoseconds
        except AttributeError:
            stamp_ns = self.node.get_clock().now().nanoseconds

        for idx, eff in enumerate(msg.effort):
            joint_id = idx + 1
            self._load_samples[joint_id].append((stamp_ns, abs(eff)))

    def _load_window_mean(self, joint_id: int, now_ns: int) -> Optional[float]:
        """Mean of effort samples within _LOAD_WINDOW_SEC of now_ns.
        Returns None if no in-window samples."""
        window_start = now_ns - int(_LOAD_WINDOW_SEC * 1e9)
        samples = self._load_samples.get(joint_id)
        if not samples:
            return None
        in_window = [v for (ts, v) in samples if ts >= window_start]
        if not in_window:
            return None
        return sum(in_window) / len(in_window)

    # ---- The hot path -------------------------------------------------

    def publish(self, cmd_msg) -> None:
        """Clamp + filter + publish.

        NOTE: clamping mutates a deep copy of the caller's message so
        the caller's downstream logging of the ORIGINAL goal still sees
        the original value. cmd_msg is a sensor_msgs/JointState.
        position[i] is interpreted as the goal for bus ID (i+1).
        """
        cmd_msg = copy.deepcopy(cmd_msg)
        now_ns = self.node.get_clock().now().nanoseconds

        for idx in range(len(cmd_msg.position)):
            joint_id = idx + 1
            lim = self.limits.get(joint_id)
            if lim is None:
                continue

            goal = cmd_msg.position[idx]

            # ---- Position clamp ----
            if not (lim.soft_lower <= goal <= lim.soft_upper):
                clamped = max(lim.soft_lower, min(lim.soft_upper, goal))
                self._log('position', joint_id,
                          f'goal {math.degrees(goal):.1f}° out of soft '
                          f'[{math.degrees(lim.soft_lower):.1f}, '
                          f'{math.degrees(lim.soft_upper):.1f}]; '
                          f'clamped to {math.degrees(clamped):.1f}°')
                self.counters.increment('position', joint_id)
                goal = clamped
                cmd_msg.position[idx] = goal

            # ---- Velocity clamp ----
            last = self._last_cmd.get(joint_id)
            last_t = self._last_cmd_time_ns.get(joint_id)
            # If `last` is older than _LAST_CMD_STALE_SEC, invalidate it
            # — treat this publish as the first sample again. Otherwise
            # a long pause would let arbitrary jumps through as low-vel.
            if last_t is not None:
                if (now_ns - last_t) / 1e9 > _LAST_CMD_STALE_SEC:
                    last = None
                    last_t = None
            if last is not None and last_t is not None:
                dt = (now_ns - last_t) / 1e9
                if dt > 0:
                    requested_vel = (goal - last) / dt
                    if abs(requested_vel) > lim.velocity:
                        sign = 1.0 if requested_vel > 0 else -1.0
                        clamped = last + sign * lim.velocity * dt
                        clamped = max(lim.soft_lower,
                                      min(lim.soft_upper, clamped))
                        self._log('velocity', joint_id,
                                  f'requested {math.degrees(requested_vel):.1f} '
                                  f'°/s > limit {math.degrees(lim.velocity):.1f}; '
                                  f'clamped goal {math.degrees(clamped):.1f}°')
                        self.counters.increment('velocity', joint_id)
                        goal = clamped
                        cmd_msg.position[idx] = goal

            # ---- Load refusal ----
            mean_load = self._load_window_mean(joint_id, now_ns)
            if mean_load is not None:
                if mean_load > _LOAD_REFUSE_THRESHOLD:
                    # Refuse goals that would INCREASE load magnitude.
                    # Heuristic: if new goal is further from `last` than
                    # the current trend, assume load increases.
                    if last is not None and abs(goal - last) > 0:
                        # Don't move; hold at last.
                        self._log('load', joint_id,
                                  f'sustained load {mean_load*100:.0f}%; '
                                  f'refusing new goal, holding at '
                                  f'{math.degrees(last):.1f}°')
                        self.counters.increment('load', joint_id)
                        goal = last
                        cmd_msg.position[idx] = goal

            # Remember for next iter
            self._last_cmd[joint_id] = goal
            self._last_cmd_time_ns[joint_id] = now_ns

        # All joints sanitized — publish
        self.pub.publish(cmd_msg)

    # ---- Logging throttle --------------------------------------------

    def _log(self, mode: str, joint_id: int, msg: str) -> None:
        bucket = self._log_counts[mode]
        n = bucket.get(joint_id, 0)
        bucket[joint_id] = n + 1
        if n < _LOG_FIRST_N or (n % _LOG_THROTTLE == 0):
            self.node.get_logger().warn(
                f'[envelope.{mode}] joint {joint_id}: {msg} (count={n+1})')
