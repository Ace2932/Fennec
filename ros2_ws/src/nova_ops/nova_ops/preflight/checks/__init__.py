"""Preflight check registry.

To add a new check: implement Check.run() in a new module, then add it to
the V1_CHECKS list. Every check is critical (failure blocks bringup)
unless `critical=False` is set on the instance.
"""
from .base import Check, CheckStatus, CheckResult
from .bus_ping import BusPingCheck
from .estop import EstopCheck
from .battery import BatteryLatchCheck
from .firmware_tables import FirmwareTablesCheck
from .posture_gate import PostureGateCheck


# v1 check set per docs/notes-qol-features.md §1 (mandatory critical checks).
# v2 additions land here as they're implemented (per-joint V/temp, network
# ping, disk space, firmware version match, time sync).
V1_CHECKS = [
    BusPingCheck(),
    EstopCheck(),
    BatteryLatchCheck(),
    # #187: the Teensy boots with both protection tables WIDE OPEN and only the
    # host can narrow them. Without this, preflight passed a robot with no
    # firmware-side protection at all.
    FirmwareTablesCheck(),
    # #282: wrapper.py's chassis posture gate silently disabled itself on a
    # joint-map load failure, and the per-joint hfe scalar it left behind
    # (+86 deg mechanical) does not cover for it. Without this, preflight
    # passed a robot with no chassis posture protection in the pre-homing
    # window, where the firmware envelope is also empty.
    PostureGateCheck(),
]

__all__ = ['Check', 'CheckStatus', 'CheckResult', 'V1_CHECKS']
