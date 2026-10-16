"""Are the Teensy's protection tables actually armed? (#187)

The Teensy boots with BOTH protection tables wide open — per-joint ROM at
0..4095 and the posture-aware chassis backstop off — and only the host can
narrow them. Until #185 nothing published them at all, so every firmware-side
protection this project built was inert and the Jetson-side wrapper was the
only layer. Preflight checked the E-stop, the battery latch and the servo bus,
and would happily pass a robot with no firmware protection whatsoever.

WHAT THIS CHECKS, AND WHAT IT DOES NOT. It reads `firmware_tables_state`, which
the publisher emits: what the HOST believes it sent. That catches the common
failures — nobody published, the calibration is missing, the calibration is
partial. It does NOT prove the Teensy accepted anything: both firmware
callbacks validate whole-message and reject silently on any fault, so a table
that was published and REFUSED looks identical from here. So once the host
state is `active`, this ALSO requires the Teensy's accept counters
(`/joint_limits_rx`, `/hfe_envelope_rx`, `/limp_pose_rx`, #186, 1 Hz Int32,
incremented only on ACCEPT) to be > 0 (audit F5). `/hfe_envelope_clamps` is a
clamp count, not an ack, and is deliberately not read here.

Deliberately not conflated: reporting "armed" on the strength of a publish
would be a worse lie than reporting nothing, so the message says what was
actually established.
"""

from .base import Check, CheckResult, CheckStatus

# ROS imports live inside run(), NOT at module scope. classify() below holds
# every decision this check makes, and keeping the module importable without
# rclpy is what lets those decisions be tested off the Jetson — where rclpy is
# not installed. A module-level `import rclpy` would make the whole test file
# skip, i.e. a safety check with no test coverage anywhere.


# The Teensy's accept counters (#186). Each one moves only when the firmware
# ACCEPTS a table, so 0 means "never landed or every copy was rejected".
ACK_TOPICS = ("/joint_limits_rx", "/hfe_envelope_rx", "/limp_pose_rx")


class FirmwareTablesCheck(Check):
    """FAIL when the firmware protection tables were never published."""

    def name(self) -> str:
        return "firmware_tables"

    def run(self, node) -> "CheckResult":
        # ROS imports are deferred to run() ON PURPOSE, same convention as
        # bus_ping.py: importing the check REGISTRY must not require a ROS
        # runtime. This file's module-scope comment (below) described that
        # convention but nobody actually put the imports here (#283) — every
        # call to run() raised NameError on QoSProfile/rclpy/String, so
        # preflight could never pass a single robot.
        import rclpy
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
        from std_msgs.msg import Int32, String

        latest = {"val": None}
        acks = {}

        def cb(msg):
            latest["val"] = msg.data

        def ack_cb(topic):
            def _cb(msg):
                acks[topic] = msg.data
            return _cb

        # TRANSIENT_LOCAL here, unlike estop.py's VOLATILE: this topic is
        # published by a HOST node (safety_envelope/tables_node.py), not by
        # micro-ROS, so latching works and is useful — preflight can run after
        # the publisher without having to catch a live sample. estop.py's
        # warning about patchy micro-ROS TRANSIENT_LOCAL support does not apply
        # to a host-to-host topic.
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        sub = node.create_subscription(String, "firmware_tables_state", cb, qos)
        # The acks come from micro-ROS (rclc_publisher_init_default = RELIABLE +
        # VOLATILE). A TRANSIENT_LOCAL subscriber is QoS-incompatible with that
        # and silently receives nothing, so VOLATILE here, same as estop.py.
        ack_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        ack_subs = [
            node.create_subscription(Int32, t, ack_cb(t), ack_qos) for t in ACK_TOPICS
        ]

        # Same 5 s window as the other checks. It matters here because launch
        # does NOT guarantee start order: bringup lists firmware_tables ahead of
        # preflight as intent, not as a guarantee, so this has to tolerate
        # losing that race rather than fail the robot over it.
        end = node.get_clock().now().nanoseconds + 5_000_000_000
        # Keep spinning until every ack is > 0, not just present: the counters
        # publish at 1 Hz and tables_node re-sends every 5 s, so a 0 early in
        # the window can still turn positive inside it.
        # ponytail: one shared 5 s window for state + acks; a Teensy that just
        # rebooted may not have accepted a re-send yet (F6) and fails here.
        # Upgrade: a longer ack window if that bites in practice.
        def done():
            return latest["val"] is not None and all(
                acks.get(t, 0) > 0 for t in ACK_TOPICS
            )

        while not done() and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)
        for s in ack_subs:
            node.destroy_subscription(s)

        if latest["val"] is None:
            return self._stale(
                "no firmware_tables_state in 5 s — the publisher "
                "(nova_ops firmware_tables) is not running, so the Teensy is "
                "still on its wide-open boot table"
            )

        host = self.classify(latest["val"])
        if host.status != CheckStatus.OK:
            return host
        return self.classify_acks(acks)

    @staticmethod
    def classify_acks(acks: dict) -> CheckResult:
        """F5: pass only when the Teensy has ACCEPTED all three tables. Pure."""
        name = "firmware_tables"
        missing = [t for t in ACK_TOPICS if t not in acks]
        zero = [t for t in ACK_TOPICS if t in acks and acks[t] <= 0]
        if missing or zero:
            parts = []
            if missing:
                parts.append(f"no message on {missing} in 5 s (Teensy/agent down?)")
            if zero:
                parts.append(f"{zero} still 0 (table not received or REJECTED)")
            return CheckResult(
                name,
                CheckStatus.FAIL,
                "tables published but the Teensy has not accepted them: "
                + "; ".join(parts),
                True,
            )
        counts = ", ".join(f"{t}={acks[t]}" for t in ACK_TOPICS)
        return CheckResult(
            name,
            CheckStatus.OK,
            f"per-joint ROM + posture backstop + limp pose accepted by the Teensy ({counts})",
            True,
        )

    @staticmethod
    def classify(state: str) -> CheckResult:
        """Every decision this check makes. Pure, so it is tested off-Jetson."""
        name = "firmware_tables"
        head = state.split(";", 1)[0].strip()
        detail = state.split(";", 1)[1].strip() if ";" in state else ""

        if head == "active":
            return CheckResult(
                name,
                CheckStatus.OK,
                "per-joint ROM + posture backstop published "
                "(firmware acceptance not verified — needs #186)",
                True,
            )
        if head == "partial":
            # Not OK: the posture backstop is withheld entirely when any leg is
            # missing a joint, so the chassis is unprotected below the host even
            # though the per-joint table went out.
            return CheckResult(
                name,
                CheckStatus.FAIL,
                f"PARTIAL calibration ({detail}) — per-joint table published, "
                f"but the chassis posture backstop is NOT armed",
                True,
            )
        if head == "uncalibrated":
            return CheckResult(
                name,
                CheckStatus.FAIL,
                "no calibration — the Teensy is on its wide-open boot table "
                "(0..4095, posture backstop off). Run homing first.",
                True,
            )
        return CheckResult(
            name,
            CheckStatus.FAIL,
            f"unrecognised firmware_tables_state {state!r}",
            True,
        )
