"""Is the chassis posture gate (safety_envelope.wrapper._clamp_posture) live? (#282)

wrapper.py builds `_leg_ids` from the joint-ID map at construction time. Before
this fix a load failure was silent — a bare `except Exception: self._leg_ids =
None`, no log, no observable state — and `_clamp_posture` returns immediately
when `_leg_ids is None`, so the node came up looking healthy with the gate
simply gone.

WHY THIS MATTERS. wrapper.py used to claim "the per-joint scalars still apply"
as a fallback. That is false: safety_envelope/limits.py sets hfe to mechanical
(+86 deg) *because* this gate is assumed live (its own "RE-LOOSENED to
mechanical" comment) — at haa -15 deg the real chassis cap is +12.3 deg,
nowhere near +86. The genuine second layer is the firmware hfe_envelope
(firmware_limits.build_hfe_envelope_data), and that returns [] until every
haa+hfe joint is calibrated — i.e. exactly the pre-homing window when
nova_calibration's servo_homing publishes /joint_commands directly, driving
joints toward hard stops. If the joint map also fails to load, that window has
no protection from either layer.

WHAT THIS CHECKS, AND WHAT IT DOES NOT. It reads `posture_gate_state`, a
latched String the gait node (nova_locomotion.node.GaitNode) publishes once at
construction from `SafeJointCommandPublisher.posture_gate_active`. That proves
the joint map LOADED in the currently-running gait node — it does not prove
the map's CONTENT is correct, and it says nothing about any other node (e.g.
policy_node.py) that constructs its own wrapper instance.
"""

from .base import Check, CheckResult, CheckStatus

# ROS imports live inside run(), NOT at module scope. classify() below holds
# every decision this check makes, and keeping the module importable without
# rclpy is what lets those decisions be tested off the Jetson — where rclpy is
# not installed. A module-level `import rclpy` would make the whole test file
# skip, i.e. a safety check with no test coverage anywhere.


class PostureGateCheck(Check):
    """FAIL when the chassis posture gate is inactive or unobserved."""

    def name(self) -> str:
        return "posture_gate"

    def run(self, node) -> "CheckResult":
        # ROS imports are deferred to run() ON PURPOSE, same convention as
        # estop.py/bus_ping.py/firmware_tables.py. #283 is the standing
        # reminder that this convention has been DESCRIBED and not
        # IMPLEMENTED before (firmware_tables.py shipped with none of these
        # names imported, so every run() raised NameError) — every name used
        # below is imported right here, not assumed from elsewhere.
        import rclpy
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from std_msgs.msg import String

        latest = {"val": None}

        def cb(msg):
            latest["val"] = msg.data

        # TRANSIENT_LOCAL: posture_gate_state is a host-to-host topic
        # (published by gait_node, a plain rclpy publisher, not micro-ROS),
        # so latching works — same reasoning as firmware_tables.py.
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        sub = node.create_subscription(String, "posture_gate_state", cb, qos)

        # Same 5 s window as the other checks; launch order is intent, not a
        # guarantee (see firmware_tables.py).
        end = node.get_clock().now().nanoseconds + 5_000_000_000
        while latest["val"] is None and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)

        if latest["val"] is None:
            return self._stale(
                "no posture_gate_state in 5 s — gait_node is not running, so "
                "whether the chassis posture gate is live is unknown"
            )

        return self.classify(latest["val"])

    @staticmethod
    def classify(state: str) -> CheckResult:
        """Every decision this check makes. Pure, so it is tested off-Jetson."""
        name = "posture_gate"
        if state == "active":
            return CheckResult(
                name, CheckStatus.OK, "chassis posture gate is live", True
            )
        # Fail closed: "active" is the only string that passes. A rename, an
        # unrecognised value, or an explicit "inactive" all FAIL rather than
        # silently reading as healthy (same doctrine as
        # firmware_tables.classify's unknown-state test).
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"chassis posture gate {state!r} — the joint-ID map failed to "
            f"load in gait_node, so _clamp_posture never runs. The hfe "
            f"per-joint scalar alone permits +86 deg (the real chassis cap "
            f"can be as tight as +12.3 deg at haa -15), and the firmware "
            f"envelope is empty until calibration completes — nothing "
            f"bounds hfe against the chassis in this window",
            True,
        )
