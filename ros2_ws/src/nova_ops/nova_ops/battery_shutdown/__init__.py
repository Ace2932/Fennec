"""Battery-low → clean Jetson shutdown (notes-qol-features.md §10).

Closes the gap found in the 2026-06-12 software review: the Teensy
publishes /battery_low (13.0 V comparator, hardware-debounced 50 ms and
latched by the firmware FSM) but nothing on the Jetson acted on it — the
pack would sag to 12.4 V under gait load and the HARDCUT MOSFET would yank
the Jetson's rail mid-SD-write.

Split in the nova_ops house style: `ShutdownDecider` is pure logic (unit
tested, no ROS imports beyond stdlib), `node.py` is the thin ROS wrapper.

Decision policy — two independent trigger paths, whichever fires first:

1. LATCHED: /safety_state == SAFETY_BATTERY_LOW_LATCHED (2). The firmware
   FSM already debounced this for 50 ms against a hardware comparator with
   hysteresis; one message is trustworthy. Fires immediately.
2. RAW SUSTAINED: /battery_low == True continuously for >= raw_sustain_s
   (default 2.0 s). Backup path in case the single latched-state edge
   message is lost (micro-ROS edge publishes are not latched topics).

Once fired the decision is permanent for the process lifetime — voltage
recovering after the load drops does NOT cancel the shutdown. A sagging
pack that "recovers" at idle will sag again on the next gait step; the
only safe direction is down.
"""

# Mirrors nova::SafetyState in firmware/teensy/firmware/src/safety_state.h
SAFETY_NORMAL = 0
SAFETY_ESTOP_LATCHED = 1
SAFETY_BATTERY_LOW_LATCHED = 2
SAFETY_FAULT_OTHER = 3


class ShutdownDecider:
    """Pure decision logic. Feed it observations; ask if shutdown is due."""

    def __init__(self, raw_sustain_s: float = 2.0):
        self.raw_sustain_s = float(raw_sustain_s)
        self._raw_high_since: float | None = None
        self._fired = False
        self._reason: str | None = None

    # -- observations ------------------------------------------------------

    def on_battery_low(self, value: bool, t: float) -> None:
        """Raw /battery_low edge (value) observed at time t (seconds)."""
        if value:
            if self._raw_high_since is None:
                self._raw_high_since = t
        else:
            self._raw_high_since = None

    def on_safety_state(self, state: int, t: float) -> None:
        """Latched FSM state observed at time t."""
        if state == SAFETY_BATTERY_LOW_LATCHED and not self._fired:
            self._fired = True
            self._reason = f'safety_state latched BATTERY_LOW at t={t:.1f}s'

    # -- evaluation --------------------------------------------------------

    def evaluate(self, t: float) -> bool:
        """Returns True exactly once work should begin (then stays True)."""
        if not self._fired and self._raw_high_since is not None:
            if (t - self._raw_high_since) >= self.raw_sustain_s:
                self._fired = True
                self._reason = (
                    f'/battery_low raw high sustained '
                    f'{t - self._raw_high_since:.1f}s >= {self.raw_sustain_s}s')
        return self._fired

    @property
    def fired(self) -> bool:
        return self._fired

    @property
    def reason(self) -> str | None:
        return self._reason
