"""Base class + result types for preflight checks."""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class CheckStatus(IntEnum):
    """Aligned with diagnostic_msgs/DiagnosticStatus levels."""
    OK = 0
    WARN = 1
    FAIL = 2
    STALE = 3


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    critical: bool = True   # if True, FAIL blocks gait bringup


class Check:
    """Base class for a preflight check.

    Subclasses override `name()` and `run(node)`. `run()` is given the
    rclpy node so it can subscribe / wait for messages. It must return a
    CheckResult and SHOULD complete within 5 seconds (a slow check
    holds up the whole preflight; consider --quick guards).
    """

    #: If True, FAIL result blocks the gait controller from coming up.
    #: WARN results never block. Override on instances or subclasses.
    critical: bool = True

    def name(self) -> str:
        raise NotImplementedError

    def run(self, node) -> CheckResult:
        raise NotImplementedError

    def _fail(self, msg: str) -> CheckResult:
        return CheckResult(self.name(), CheckStatus.FAIL, msg, self.critical)

    def _ok(self, msg: str = 'OK') -> CheckResult:
        return CheckResult(self.name(), CheckStatus.OK, msg, self.critical)

    def _warn(self, msg: str) -> CheckResult:
        return CheckResult(self.name(), CheckStatus.WARN, msg, self.critical)

    def _stale(self, msg: str = 'no recent message') -> CheckResult:
        return CheckResult(self.name(), CheckStatus.STALE, msg, self.critical)
