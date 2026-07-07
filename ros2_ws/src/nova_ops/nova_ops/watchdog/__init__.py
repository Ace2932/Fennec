"""Jetson watchdog — systemd WATCHDOG=1 feeder (pure logic).

Closes the system-audit item "Jetson watchdog". Three layers, each
catching what the one below cannot:

  1. `Restart=on-failure` (nova-bringup.service) — process CRASH.
  2. `WatchdogSec=` + this feeder — process HANG/deadlock: systemd
     kills + restarts the bringup tree when WATCHDOG=1 stops arriving.
  3. `RuntimeWatchdogSec=` (/etc/systemd/system.conf, Tegra HW
     watchdog) — kernel/systemd hang: the SoC watchdog reboots the
     board. See docs/setup-jetson.md.

SCOPE (deliberate): the feeder feeds while its OWN executor spins —
it is a Jetson-stack-health signal, NOT a robot-health signal. Topic
freshness (Teensy heartbeat, command staleness) is the liveness node's
job (`/system_ok`); wiring topics into the *watchdog* would turn an
unplugged Teensy into an infinite service-restart loop. The firmware's
command-staleness failsafe already freezes the robot when the Jetson
dies — this lane makes the Jetson also RECOVER.

`sd_notify` is implemented on the stdlib socket module (no systemd
python dependency): datagram to $NOTIFY_SOCKET, '@' prefix = abstract
namespace. Clock + socket are injected for tests.
"""

import os
import socket


def sd_notify(payload: str, sock=None, env=None) -> bool:
    """Send one sd_notify datagram. Returns False (no-op) when not
    running under systemd ($NOTIFY_SOCKET unset) — safe in dev."""
    env = env if env is not None else os.environ
    addr = env.get("NOTIFY_SOCKET")
    if not addr:
        return False
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    own = False
    if sock is None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        own = True
    try:
        sock.sendto(payload.encode(), addr)
        return True
    except OSError:
        return False
    finally:
        if own:
            sock.close()


class WatchdogFeeder:
    """Decides when to emit WATCHDOG=1. Feed at half the systemd
    WatchdogSec interval (systemd convention: WATCHDOG_USEC/2)."""

    def __init__(self, watchdog_usec: int, now_s: float):
        # systemd exports WATCHDOG_USEC to the unit; 0/None = disabled
        self.interval_s = (watchdog_usec / 2) / 1e6 if watchdog_usec else None
        self._last_feed_s = now_s
        self.feed_count = 0

    @property
    def enabled(self) -> bool:
        return self.interval_s is not None

    def due(self, now_s: float) -> bool:
        if not self.enabled:
            return False
        return (now_s - self._last_feed_s) >= self.interval_s

    def fed(self, now_s: float) -> None:
        self._last_feed_s = now_s
        self.feed_count += 1


def watchdog_usec_from_env(env=None) -> int:
    """Parse WATCHDOG_USEC (systemd sets it when WatchdogSec= is on)."""
    env = env if env is not None else os.environ
    try:
        return int(env.get("WATCHDOG_USEC", "0"))
    except ValueError:
        return 0
