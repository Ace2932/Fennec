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

  temperature ⏳ NOT implemented here — but the GATING CLAIM was stale, and
              the difference matters. This used to read "gated on firmware
              REG_PRESENT_TEMPERATURE work landing". That work HAS landed:
              feetech_protocol.h:52 defines REG_PRESENT_TEMPERATURE (0x3F),
              and main.cpp reads it per joint and PUBLISHES /servo_temperature
              (12 floats, 5 Hz, main.cpp:1494). The data is on a topic; what is
              missing is only this wrapper's use of it.
              NOTE the firmware already guards itself locally — overtemp at
              NOVA_OVERTEMP_C 70 °C trips limp (main.cpp:333), ahead of the
              servo's own ~80 °C cutoff. So this would be a SECOND layer, not
              the only one, which is why nothing is on fire without it.

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
from typing import Deque, Dict, Optional

from .limits import JointLimits
from .counters import EnvelopeCounters
from nova_ops.rom_envelope import hfe_bounds


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
            lambda: collections.deque(maxlen=100)
        )
        self._log_counts: Dict[str, Dict[int, int]] = {
            "position": {},
            "velocity": {},
            "load": {},
            "posture": {},  # chassis envelope (see _clamp_posture)
        }

        # Leg -> (haa_id, hfe_id, kfe_id) for the posture gate. PER-LEG-
        # SEQUENTIAL bus map: each leg is haa, hfe, kfe in consecutive IDs.
        # Built from the yaml so it tracks the canonical map rather than
        # re-deriving it.
        #
        # If the map is unavailable the posture gate goes inactive, and that
        # is NOT covered by the per-joint scalars (#282). limits.py sets hfe
        # to mechanical (+86 deg) *because* this gate is assumed live — see
        # its own "RE-LOOSENED to mechanical" comment — and at haa -15 deg
        # the real chassis cap is +12.3 deg, nowhere near +86. The genuine
        # fallback is the firmware hfe_envelope
        # (firmware_limits.build_hfe_envelope_data), which is EMPTY until
        # every haa+hfe joint is calibrated — i.e. exactly the pre-homing
        # window when nova_calibration's servo_homing publishes
        # /joint_commands directly, driving joints toward hard stops. So a
        # load failure here is a real safety gap, not a graceful degrade:
        # fail loud and expose it (posture_gate_active), so the
        # `posture_gate` preflight check can refuse bringup on it.
        self._leg_ids: Optional[Dict[str, tuple]] = None
        self.posture_gate_active: bool = False
        try:
            from nova_ops.joint_map import load_joint_id_map

            # LOOK EACH JOINT UP BY NAME. This used to find the haa and assume
            # (jid, jid+1, jid+2). That holds under the current PER-LEG
            # SEQUENTIAL convention, but it is an assumption about the map's
            # SHAPE rather than a read of the map — if the convention ever
            # changes, the posture gate silently reads the wrong joints and
            # clamps the wrong thing. The yaml already names every joint.
            jmap = load_joint_id_map()
            legs = {name.split("_")[0] for name in jmap}
            self._leg_ids = {}
            for leg in sorted(legs):
                try:
                    self._leg_ids[leg] = tuple(
                        jmap[f"{leg}_{jt}"] for jt in ("haa", "hfe", "kfe")
                    )
                except KeyError:
                    continue  # not a 3-joint leg (e.g. the Phase-4 arm)
            self._leg_ids = self._leg_ids or None
            self.posture_gate_active = self._leg_ids is not None
        except Exception as exc:
            self._leg_ids = None
            self.posture_gate_active = False
            self.node.get_logger().error(
                f"posture gate DISABLED: joint_id_map failed to load ({exc!r}). "
                f"_clamp_posture will not run for any publisher. The firmware "
                f"hfe_envelope is the only remaining layer, and it is EMPTY "
                f"until every haa+hfe joint is calibrated — i.e. nothing "
                f"protects the chassis before homing completes."
            )

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
            stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            if stamp_ns == 0:
                stamp_ns = self.node.get_clock().now().nanoseconds
        except AttributeError:
            stamp_ns = self.node.get_clock().now().nanoseconds

        for idx, eff in enumerate(msg.effort):
            joint_id = idx + 1
            # Keep the SIGN — the load-refusal direction check needs to know
            # which way the joint is straining (effort is signed, normalized
            # to ±fraction of stall torque). Was abs(): that discarded the
            # direction, which is why the refusal couldn't tell "push harder"
            # from "back off" and blocked both.
            self._load_samples[joint_id].append((stamp_ns, float(eff)))

    def _load_window(self, joint_id: int, now_ns: int):
        """Return (mean_abs, load_sign) over the effort samples within
        _LOAD_WINDOW_SEC of now_ns. mean_abs = magnitude (for the threshold);
        load_sign (+1/-1/0) = the direction the joint is straining, used to
        allow a back-off but refuse pushing harder. (None, 0.0) if empty."""
        window_start = now_ns - int(_LOAD_WINDOW_SEC * 1e9)
        samples = self._load_samples.get(joint_id)
        if not samples:
            return None, 0.0
        in_window = [v for (ts, v) in samples if ts >= window_start]
        if not in_window:
            return None, 0.0
        mean_signed = sum(in_window) / len(in_window)
        mean_abs = sum(abs(v) for v in in_window) / len(in_window)
        load_sign = 1.0 if mean_signed > 0 else (-1.0 if mean_signed < 0 else 0.0)
        return mean_abs, load_sign

    # ---- The hot path -------------------------------------------------

    def _clamp_posture(self, cmd_msg) -> None:
        """Clamp hfe to the POSTURE-aware chassis bound, per leg.

        THE CHOKE POINT. The per-joint scalars below cannot express the chassis
        constraint: how far a leg may fold before the tibia flank reaches the
        riser skirt depends on how far the hip is splayed and the knee folded AT
        THE SAME TIME (measured: front reaches +70.6 deg at haa 0 but only +51.7
        at full outboard splay). nova_locomotion applies this in solve_side, but
        that is only the GAIT path — nova_calibration's servo_homing and
        actuator_char publish /joint_commands directly and never touch it, and
        homing is the first thing that runs on real hardware, driving joints
        toward hard stops. So the gate belongs HERE, where every publisher
        passes, not only in the IK.

        HAA SIGN IS UNKNOWN in this frame. /joint_commands is in the SERVO
        command frame, and which haa direction is inboard there is exactly what
        HAA_INBOARD_SIGN records as None until homing observes real motion. So
        while a sign is unfilled, evaluate the envelope for BOTH interpretations
        of the commanded haa and take the tighter — the same conservative
        posture limits.py already takes for the haa limit itself.
        """
        legs = getattr(self, "_leg_ids", None)
        if legs is None:
            return
        for leg, (haa_id, hfe_id, kfe_id) in legs.items():
            idxs = [j - 1 for j in (haa_id, hfe_id, kfe_id)]
            if max(idxs) >= len(cmd_msg.position):
                continue
            haa, hfe, kfe = (cmd_msg.position[i] for i in idxs)
            lo_a, hi_a = hfe_bounds(leg, haa, kfe)
            lo_b, hi_b = hfe_bounds(leg, -haa, kfe)  # sign unknown -> both ways
            lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
            if not (lo <= hfe <= hi):
                clamped = max(lo, min(hi, hfe))
                self._log(
                    "posture",
                    hfe_id,
                    f"{leg} hfe {math.degrees(hfe):.1f}° outside the chassis "
                    f"envelope [{math.degrees(lo):.1f}, {math.degrees(hi):.1f}] "
                    f"at haa {math.degrees(haa):.1f}° kfe {math.degrees(kfe):.1f}°; "
                    f"clamped to {math.degrees(clamped):.1f}°",
                )
                self.counters.increment("position", hfe_id)
                cmd_msg.position[idxs[1]] = clamped

    def publish(self, cmd_msg) -> None:
        """Clamp + filter + publish.

        NOTE: clamping mutates a deep copy of the caller's message so
        the caller's downstream logging of the ORIGINAL goal still sees
        the original value. cmd_msg is a sensor_msgs/JointState.
        position[i] is interpreted as the goal for bus ID (i+1).
        """
        cmd_msg = copy.deepcopy(cmd_msg)
        now_ns = self.node.get_clock().now().nanoseconds
        self._clamp_posture(cmd_msg)

        for idx in range(len(cmd_msg.position)):
            joint_id = idx + 1
            lim = self.limits.get(joint_id)
            if lim is None:
                continue

            goal = cmd_msg.position[idx]

            # ---- Position clamp ----
            if not (lim.soft_lower <= goal <= lim.soft_upper):
                clamped = max(lim.soft_lower, min(lim.soft_upper, goal))
                self._log(
                    "position",
                    joint_id,
                    f"goal {math.degrees(goal):.1f}° out of soft "
                    f"[{math.degrees(lim.soft_lower):.1f}, "
                    f"{math.degrees(lim.soft_upper):.1f}]; "
                    f"clamped to {math.degrees(clamped):.1f}°",
                )
                self.counters.increment("position", joint_id)
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
                        clamped = max(lim.soft_lower, min(lim.soft_upper, clamped))
                        self._log(
                            "velocity",
                            joint_id,
                            f"requested {math.degrees(requested_vel):.1f} "
                            f"°/s > limit {math.degrees(lim.velocity):.1f}; "
                            f"clamped goal {math.degrees(clamped):.1f}°",
                        )
                        self.counters.increment("velocity", joint_id)
                        goal = clamped
                        cmd_msg.position[idx] = goal

            # ---- Load refusal ----
            # Under sustained load, refuse ONLY motion that drives FURTHER into
            # the load (a goal change in the same direction the joint is already
            # straining, load_sign) — but ALLOW the opposite (load-reducing)
            # move so it can back off a stall. Previously this refused ANY
            # motion incl. the back-off, which could pin a joint into a stop
            # (the firmware stall-guard would then have to limp the fleet).
            # Fixed 2026-06-27.
            # Per-joint threshold = the JointLimit's effort field (URDF
            # <limit effort>, % of stall); module default is the fallback.
            # This wires the previously-dead `effort` config so hips/legs
            # can be tuned independently (firmware-limits lane 2026-07-06).
            refuse_at = lim.effort if lim.effort else _LOAD_REFUSE_THRESHOLD
            mean_abs, load_sign = self._load_window(joint_id, now_ns)
            if (
                mean_abs is not None
                and mean_abs > refuse_at
                and last is not None
                and load_sign != 0.0
                and (goal - last) * load_sign > 0.0
            ):
                self._log(
                    "load",
                    joint_id,
                    f"sustained load {mean_abs * 100:.0f}% "
                    f"(dir {'+' if load_sign > 0 else '-'}); refusing "
                    f"load-increasing move, holding at "
                    f"{math.degrees(last):.1f}°",
                )
                self.counters.increment("load", joint_id)
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
                f"[envelope.{mode}] joint {joint_id}: {msg} (count={n + 1})"
            )
