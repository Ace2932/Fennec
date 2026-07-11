"""Jetson watchdog feeder — pure logic (no rclpy/systemd needed)."""

import socket

from nova_ops.watchdog import WatchdogFeeder, sd_notify, watchdog_usec_from_env


# ---- WatchdogFeeder ----------------------------------------------------


def test_disabled_without_watchdog_usec():
    f = WatchdogFeeder(0, now_s=100.0)
    assert not f.enabled
    assert not f.due(1e9)


def test_feeds_at_half_interval():
    # WatchdogSec=15 -> WATCHDOG_USEC=15e6 -> feed every 7.5s
    f = WatchdogFeeder(15_000_000, now_s=0.0)
    assert f.enabled and f.interval_s == 7.5
    assert not f.due(7.0)
    assert f.due(7.5)
    f.fed(7.5)
    assert f.feed_count == 1
    assert not f.due(14.9)
    assert f.due(15.0)


def test_watchdog_usec_env_parse():
    assert watchdog_usec_from_env({"WATCHDOG_USEC": "15000000"}) == 15_000_000
    assert watchdog_usec_from_env({}) == 0
    assert watchdog_usec_from_env({"WATCHDOG_USEC": "junk"}) == 0


# ---- sd_notify ---------------------------------------------------------


class _FakeSock:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def sendto(self, payload, addr):
        if self.fail:
            raise OSError("no listener")
        self.sent.append((payload, addr))

    def close(self):
        pass


def test_sd_notify_noop_outside_systemd():
    assert sd_notify("WATCHDOG=1", env={}) is False


def test_sd_notify_sends_datagram():
    s = _FakeSock()
    ok = sd_notify("WATCHDOG=1", sock=s, env={"NOTIFY_SOCKET": "/run/sd.sock"})
    assert ok and s.sent == [(b"WATCHDOG=1", "/run/sd.sock")]


def test_sd_notify_abstract_namespace():
    s = _FakeSock()
    sd_notify("READY=1", sock=s, env={"NOTIFY_SOCKET": "@abstract"})
    assert s.sent[0][1] == "\0abstract"


def test_sd_notify_swallow_socket_errors():
    s = _FakeSock(fail=True)
    ok = sd_notify("WATCHDOG=1", sock=s, env={"NOTIFY_SOCKET": "/run/sd.sock"})
    assert ok is False


def test_real_socket_path_does_not_crash():
    # end-to-end with a real unix datagram socket
    import tempfile
    import os

    d = tempfile.mkdtemp()
    path = os.path.join(d, "notify.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    srv.bind(path)
    try:
        assert sd_notify("WATCHDOG=1", env={"NOTIFY_SOCKET": path}) is True
        srv.settimeout(1.0)
        assert srv.recv(64) == b"WATCHDOG=1"
    finally:
        srv.close()
        os.unlink(path)
