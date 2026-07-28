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
that was published and REFUSED looks identical from here. Closing that needs
the firmware to publish its receive counters (#186), at which point this check
should also require those to be non-zero.

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


class FirmwareTablesCheck(Check):
    """FAIL when the firmware protection tables were never published."""

    def name(self) -> str:
        return "firmware_tables"

    def run(self, node) -> "CheckResult":
        latest = {"val": None}

        def cb(msg):
            latest["val"] = msg.data

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

        # Same 5 s window as the other checks. It matters here because launch
        # does NOT guarantee start order: bringup lists firmware_tables ahead of
        # preflight as intent, not as a guarantee, so this has to tolerate
        # losing that race rather than fail the robot over it.
        end = node.get_clock().now().nanoseconds + 5_000_000_000
        while latest["val"] is None and node.get_clock().now().nanoseconds < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(sub)

        if latest["val"] is None:
            return self._stale(
                "no firmware_tables_state in 5 s — the publisher "
                "(nova_ops firmware_tables) is not running, so the Teensy is "
                "still on its wide-open boot table"
            )

        return self.classify(latest["val"])

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
