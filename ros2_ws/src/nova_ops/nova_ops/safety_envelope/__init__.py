"""Per-joint safety envelope library.

Per docs/notes-qol-features.md §3, option (a) in-process wrapper:
  gait code calls SafeJointCommandPublisher.publish(joint_commands),
  the wrapper either passes it through or clamps + logs the violation.
  Lowest latency. Risk: a future second publisher to /joint_commands
  bypasses the check.

Mechanical stops + servo torque limits are the LAST line of defense;
this envelope catches buggy commands BEFORE they hit the bus.
"""

from .limits import JointLimit, JointLimits, load_default_limits
from .wrapper import SafeJointCommandPublisher
from .counters import EnvelopeCounters
from .firmware_limits import JointHomeCalib, build_joint_limits_data

__all__ = [
    "JointLimit",
    "JointLimits",
    "load_default_limits",
    "SafeJointCommandPublisher",
    "EnvelopeCounters",
    "JointHomeCalib",
    "build_joint_limits_data",
]
