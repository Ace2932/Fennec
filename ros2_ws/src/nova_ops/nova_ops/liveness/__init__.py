"""Liveness watchdog — pure decision logic for the Teensy/firmware monitor.

Nothing on the Jetson currently watches the Teensy `/heartbeat`, so a Teensy
reset or firmware death mid-motion goes unnoticed. (The firmware's own
command-staleness failsafe handles the OTHER direction — Jetson/agent death —
by freezing the robot and asserting `/command_stale`.) This class tracks
heartbeat freshness + `/command_stale` + `/safety_state` and decides whether
the system is live and fault-free.

Clock is injected (now_s) so it is unit-testable without rclpy. The node
(node.py) is a thin wrapper that feeds it ROS messages + a timer.
"""


class LivenessMonitor:
    def __init__(self, heartbeat_timeout_s: float = 3.0):
        # Teensy publishes /heartbeat at 1 Hz; 3 s = 3 missed beats before we
        # call it dead — long enough to ride a single dropped message, short
        # enough to react before a fall.
        self.heartbeat_timeout_s = float(heartbeat_timeout_s)
        self._last_hb_value = None
        self._last_hb_change_s = None
        self._teensy_reset_count = 0
        self._command_stale = False
        self._safety_state = 0  # 0 = SAFETY_NORMAL
        self.reason = ""

    # -- inputs ------------------------------------------------------------

    def on_heartbeat(self, value, now_s: float) -> None:
        value = int(value)
        if self._last_hb_value is None:
            self._last_hb_value = value
            self._last_hb_change_s = now_s
            return
        if value != self._last_hb_value:
            # Counter running backwards = the Teensy rebooted (heartbeat resets
            # to 0 on boot). Still "fresh" — but flag the reset for diagnostics.
            if value < self._last_hb_value:
                self._teensy_reset_count += 1
            self._last_hb_value = value
            self._last_hb_change_s = now_s

    def on_command_stale(self, stale) -> None:
        self._command_stale = bool(stale)

    def on_safety_state(self, state) -> None:
        self._safety_state = int(state)

    # -- queries -----------------------------------------------------------

    @property
    def teensy_reset_count(self) -> int:
        return self._teensy_reset_count

    def heartbeat_fresh(self, now_s: float) -> bool:
        if self._last_hb_change_s is None:
            return False
        return (now_s - self._last_hb_change_s) <= self.heartbeat_timeout_s

    def evaluate(self, now_s: float):
        """Return (ok, reason). ok == system live AND fault-free."""
        if not self.heartbeat_fresh(now_s):
            if self._last_hb_change_s is None:
                self.reason = "no /heartbeat seen yet — Teensy not publishing"
            else:
                age = now_s - self._last_hb_change_s
                self.reason = (
                    f"/heartbeat stale {age:.1f}s "
                    f"(> {self.heartbeat_timeout_s:.1f}s) — Teensy dead/reset"
                )
            return False, self.reason
        if self._command_stale:
            self.reason = (
                "/command_stale — firmware froze the robot "
                "(/joint_commands stopped: agent/Jetson death)"
            )
            return False, self.reason
        if self._safety_state != 0:
            self.reason = f"/safety_state={self._safety_state} latched fault"
            return False, self.reason
        self.reason = ""
        return True, ""
